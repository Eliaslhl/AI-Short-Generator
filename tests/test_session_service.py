"""SQLAlchemy-backed regression tests for opaque application sessions."""

import asyncio
from datetime import timedelta
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.database import Base
from backend.models.user import AuthSession, User
import backend.services.session_service as session_service_module
from backend.services.session_service import (
    DEFAULT_SESSION_TTL,
    SessionServiceError,
    SessionUserUnavailable,
    hash_session_token,
    session_service,
    utc_now,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'sessions.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    try:
        yield factory
    finally:
        asyncio.run(engine.dispose())


def _create_user(session_factory, user_id: str, *, is_active: bool = True) -> User:
    async def create():
        async with session_factory() as db:
            user = User(
                id=user_id,
                email=f"{user_id}@example.com",
                hashed_password="not-used-in-test",
                is_active=is_active,
                is_verified=True,
            )
            db.add(user)
            await db.commit()
            return user

    return asyncio.run(create())


def _create_session(session_factory, user_id: str, **kwargs):
    async def create():
        async with session_factory() as db:
            created = await session_service.create_session(db, user_id, **kwargs)
            await db.commit()
            return created

    return asyncio.run(create())


def test_create_session_returns_opaque_token_and_stores_only_hash(session_factory):
    _create_user(session_factory, "user-a")
    created = _create_session(session_factory, "user-a")

    assert len(created.raw_token) >= 32
    assert created.raw_token not in created.session.__dict__.values()
    assert created.raw_token not in repr(created)
    assert created.raw_token not in str(created)
    assert created.raw_token
    assert created.session.token_hash == hash_session_token(created.raw_token)
    assert created.session.created_at.tzinfo is not None
    assert created.session.expires_at - created.session.created_at == DEFAULT_SESSION_TTL


def test_hash_is_deterministic_and_distinct_tokens_are_unique(session_factory):
    _create_user(session_factory, "user-a")
    first = _create_session(session_factory, "user-a")
    second = _create_session(session_factory, "user-a")

    assert hash_session_token(first.raw_token) == hash_session_token(first.raw_token)
    assert first.raw_token != second.raw_token
    assert first.session.token_hash != second.session.token_hash
    assert len(first.session.token_hash) == 64


@pytest.mark.parametrize(
    "raw_token",
    [None, "", "   ", 7, b"token", ["token"], "a" * 10000],
)
def test_get_valid_session_normalizes_invalid_tokens(session_factory, raw_token):
    _create_user(session_factory, "user-a")

    async def verify():
        async with session_factory() as db:
            assert await session_service.get_valid_session(db, raw_token) is None

    asyncio.run(verify())


def test_get_valid_session_rejects_expired_revoked_and_disabled_users(session_factory):
    _create_user(session_factory, "user-a")
    valid = _create_session(session_factory, "user-a")
    expired = _create_session(session_factory, "user-a", ttl=timedelta(seconds=1), now=utc_now() - timedelta(seconds=2))
    revoked = _create_session(session_factory, "user-a")

    async def verify():
        async with session_factory() as db:
            assert (await session_service.get_valid_session(db, valid.raw_token)).id == valid.session.id
            assert await session_service.get_valid_session(db, expired.raw_token) is None
            assert await session_service.revoke_session(db, revoked.session.id) is True
            await db.commit()
            assert await session_service.get_valid_session(db, revoked.raw_token) is None
            user = await db.get(User, "user-a")
            user.is_active = False
            await db.commit()
            assert await session_service.get_valid_session(db, valid.raw_token) is None

    asyncio.run(verify())


def test_revocation_is_idempotent_by_id_and_token(session_factory):
    _create_user(session_factory, "user-a")
    created = _create_session(session_factory, "user-a")

    async def revoke():
        async with session_factory() as db:
            assert await session_service.revoke_session(db, created.session.id) is True
            await db.commit()
            first_timestamp = (await db.get(AuthSession, created.session.id)).revoked_at
            assert await session_service.revoke_session(db, created.session.id) is False
            assert await session_service.revoke_session_by_token(db, created.raw_token) is False
            assert await session_service.revoke_session_by_token(db, "invalid") is False
            await db.commit()
            assert (await db.get(AuthSession, created.session.id)).revoked_at == first_timestamp

    asyncio.run(revoke())


def test_revoke_all_user_sessions_does_not_touch_another_user(session_factory):
    _create_user(session_factory, "user-a")
    _create_user(session_factory, "user-b")
    first = _create_session(session_factory, "user-a")
    _create_session(session_factory, "user-a")
    other = _create_session(session_factory, "user-b")

    async def revoke_all():
        async with session_factory() as db:
            assert await session_service.revoke_all_user_sessions(db, "user-a") == 2
            await db.commit()
            assert await session_service.get_valid_session(db, first.raw_token) is None
            assert (await session_service.get_valid_session(db, other.raw_token)).user_id == "user-b"

    asyncio.run(revoke_all())


def test_touch_is_atomic_and_cleanup_expired_sessions_in_bounded_batches(session_factory):
    _create_user(session_factory, "user-a")
    valid = _create_session(session_factory, "user-a")
    expired_one = _create_session(session_factory, "user-a", ttl=timedelta(seconds=1), now=utc_now() - timedelta(seconds=3))
    expired_two = _create_session(session_factory, "user-a", ttl=timedelta(seconds=1), now=utc_now() - timedelta(seconds=2))
    will_expire = _create_session(session_factory, "user-a", ttl=timedelta(seconds=1))

    async def cleanup():
        async with session_factory() as db:
            current = await session_service.get_valid_session(db, valid.raw_token)
            assert current is not None
            assert await session_service.touch_session(db, current) is True
            await db.commit()
            touched = await db.get(AuthSession, valid.session.id, populate_existing=True)
            assert touched.last_seen_at is not None
            last_seen_at = touched.last_seen_at

            stale_revoked = await db.get(AuthSession, valid.session.id)
            assert await session_service.revoke_session(db, valid.session.id) is True
            await db.commit()
            assert await session_service.touch_session(db, stale_revoked) is False
            assert (
                await db.get(AuthSession, valid.session.id, populate_existing=True)
            ).last_seen_at == last_seen_at

            stale_expired = await db.get(AuthSession, will_expire.session.id)
            assert await session_service.touch_session(
                db, stale_expired, now=utc_now() + timedelta(seconds=2)
            ) is False
            await db.commit()
            deleted = await db.get(AuthSession, expired_two.session.id)
            await db.delete(deleted)
            await db.commit()
            assert await session_service.touch_session(db, deleted) is False
            assert await session_service.cleanup_expired_sessions(db, batch_size=1) == 1
            await db.commit()
            assert await db.get(AuthSession, expired_one.session.id) is None
            assert await session_service.cleanup_expired_sessions(db, batch_size=10) == 0
            await db.commit()
            assert await db.get(AuthSession, expired_one.session.id) is None
            assert await db.get(AuthSession, expired_two.session.id) is None
            assert await db.get(AuthSession, valid.session.id) is not None

    asyncio.run(cleanup())


def test_token_hash_unique_constraint_and_unavailable_user_are_enforced(session_factory):
    _create_user(session_factory, "user-a")
    created = _create_session(session_factory, "user-a")

    async def enforce():
        async with session_factory() as db:
            duplicate = AuthSession(
                id="duplicate-session",
                user_id="user-a",
                token_hash=created.session.token_hash,
                created_at=utc_now(),
                expires_at=utc_now() + timedelta(days=1),
            )
            db.add(duplicate)
            with pytest.raises(IntegrityError):
                await db.flush()
            await db.rollback()
            with pytest.raises(SessionUserUnavailable):
                await session_service.create_session(db, "missing-user")

    asyncio.run(enforce())


def test_create_session_rejects_inactive_users_and_invalid_parameters(session_factory):
    _create_user(session_factory, "active-user")
    _create_user(session_factory, "inactive-user", is_active=False)

    async def verify():
        async with session_factory() as db:
            with pytest.raises(SessionUserUnavailable):
                await session_service.create_session(db, "missing-user")
            with pytest.raises(SessionUserUnavailable):
                await session_service.create_session(db, "inactive-user")
            with pytest.raises(ValueError, match="ttl must be positive"):
                await session_service.create_session(db, "active-user", ttl=timedelta())
            with pytest.raises(ValueError, match="ttl must be positive"):
                await session_service.create_session(db, "active-user", ttl=timedelta(days=-1))
            with pytest.raises(TypeError, match="ttl must be a timedelta"):
                await session_service.create_session(db, "active-user", ttl=1)
            created = await session_service.create_session(
                db,
                "active-user",
                now=utc_now().replace(tzinfo=None),
            )
            assert created.session.created_at.tzinfo is not None
            with pytest.raises(TypeError, match="now must be a datetime"):
                await session_service.create_session(db, "active-user", now="now")
            with pytest.raises(TypeError, match="batch_size must be a positive integer"):
                await session_service.cleanup_expired_sessions(db, batch_size=True)
            with pytest.raises(TypeError, match="batch_size must be a positive integer"):
                await session_service.cleanup_expired_sessions(db, batch_size="1")
            with pytest.raises(ValueError, match="batch_size must be positive"):
                await session_service.cleanup_expired_sessions(db, batch_size=0)
            with pytest.raises(ValueError, match="batch_size must be positive"):
                await session_service.cleanup_expired_sessions(db, batch_size=-1)

    asyncio.run(verify())


def test_create_session_retries_only_confirmed_token_hash_collisions(session_factory, monkeypatch):
    _create_user(session_factory, "user-a")
    collision_token = "a" * 43
    fresh_token = "b" * 43
    _create_session(session_factory, "user-a", now=utc_now())

    async def seed_collision():
        async with session_factory() as db:
            duplicate = AuthSession(
                id="collision-session",
                user_id="user-a",
                token_hash=hash_session_token(collision_token),
                created_at=utc_now(),
                expires_at=utc_now() + timedelta(days=1),
            )
            db.add(duplicate)
            await db.commit()

    asyncio.run(seed_collision())
    generated = iter([collision_token, fresh_token])
    monkeypatch.setattr(session_service_module.secrets, "token_urlsafe", lambda _: next(generated))

    async def verify():
        async with session_factory() as db:
            created = await session_service.create_session(db, "user-a")
            assert created.raw_token == fresh_token
            await db.commit()
            assert db.in_transaction() is False

    asyncio.run(verify())


@pytest.mark.parametrize(
    "database_message",
    ["FOREIGN KEY constraint failed", "NOT NULL constraint failed: auth_sessions.user_id"],
)
def test_create_session_propagates_non_collision_integrity_errors(
    session_factory, monkeypatch, database_message
):
    _create_user(session_factory, "user-a")

    async def verify():
        async with session_factory() as db:
            async def fail_flush(*_args, **_kwargs):
                raise IntegrityError("INSERT", {}, Exception(database_message))

            monkeypatch.setattr(db, "flush", fail_flush)
            with pytest.raises(IntegrityError, match="constraint failed"):
                await session_service.create_session(db, "user-a")
            await db.rollback()
            assert (await db.get(User, "user-a")).id == "user-a"

    asyncio.run(verify())


def test_create_session_stops_after_three_confirmed_collisions(session_factory, monkeypatch):
    _create_user(session_factory, "user-a")
    collision_token = "c" * 43

    async def seed_collision():
        async with session_factory() as db:
            db.add(
                AuthSession(
                    id="collision-session",
                    user_id="user-a",
                    token_hash=hash_session_token(collision_token),
                    created_at=utc_now(),
                    expires_at=utc_now() + timedelta(days=1),
                )
            )
            await db.commit()

    asyncio.run(seed_collision())
    monkeypatch.setattr(session_service_module.secrets, "token_urlsafe", lambda _: collision_token)

    async def verify():
        async with session_factory() as db:
            with pytest.raises(SessionServiceError, match="unable to create a unique session"):
                await session_service.create_session(db, "user-a")
            await db.commit()

    asyncio.run(verify())


def test_service_masks_tokens_in_logs_and_callers_can_roll_back_after_db_error(session_factory, monkeypatch, caplog):
    _create_user(session_factory, "user-a")

    async def rollback():
        async with session_factory() as db:
            original_flush = db.flush

            async def fail_flush(*_args, **_kwargs):
                raise SQLAlchemyError("simulated database failure")

            monkeypatch.setattr(db, "flush", fail_flush)
            with pytest.raises(SQLAlchemyError):
                await session_service.create_session(db, "user-a")
            await db.rollback()
            monkeypatch.setattr(db, "flush", original_flush)
            assert (await db.execute(select(User).where(User.id == "user-a"))).scalar_one().id == "user-a"

    asyncio.run(rollback())
    created = _create_session(session_factory, "user-a")
    logging.getLogger("session-test").warning("created session: %s", created)
    assert created.raw_token not in caplog.text


def test_production_requires_a_distinct_strong_session_hash_key():
    base_env = {**os.environ, "APP_ENVIRONMENT": "production"}
    for value in ("", "dev-session-hash-key", "short-key"):
        env = {**base_env, "SESSION_HASH_KEY": value}
        result = subprocess.run(
            [sys.executable, "-c", "from backend.services.session_service import hash_session_token; hash_session_token('a' * 43)"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "SESSION_HASH_KEY" in result.stderr

    env = {
        **base_env,
        "SESSION_HASH_KEY": "production-session-hash-key-value-long-enough-012345",
    }
    result = subprocess.run(
        [sys.executable, "-c", "from backend.services.session_service import hash_session_token; print(len(hash_session_token('a' * 43)))"],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "64"
