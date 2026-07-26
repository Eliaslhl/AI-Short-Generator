"""HTTP regressions for the transitional cookie-first authentication boundary."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.auth.jwt import create_access_token
import backend.auth.router as auth_router
from backend.config import settings
from backend.database import Base, get_db
from backend.main import app
from backend.models.user import AuthSession, EmailConfirmationToken, User
from backend.auth.router import hash_password
from backend.services.session_service import session_service, utc_now


@pytest.fixture
def auth_client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'auth.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    asyncio.run(create_schema())
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, session_factory
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        asyncio.run(engine.dispose())


def _seed_user(
    session_factory,
    user_id: str,
    *,
    active: bool = True,
    password: str = "not-used",
) -> User:
    async def seed():
        async with session_factory() as db:
            user = User(
                id=user_id,
                email=f"{user_id}@example.com",
                hashed_password=hash_password(password),
                is_active=active,
                is_verified=True,
            )
            db.add(user)
            await db.commit()
            return user

    return asyncio.run(seed())


def _mint_session(session_factory, user_id: str, **kwargs):
    async def mint():
        async with session_factory() as db:
            created = await session_service.create_session(db, user_id, **kwargs)
            await db.commit()
            return created

    return asyncio.run(mint())


def _bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.email)}"}


def _session_count(session_factory, user_id: str | None = None) -> int:
    async def count():
        async with session_factory() as db:
            statement = select(AuthSession)
            if user_id is not None:
                statement = statement.where(AuthSession.user_id == user_id)
            return len((await db.execute(statement)).scalars().all())

    return asyncio.run(count())


def test_jwt_and_cookie_both_authenticate_me(auth_client):
    client, session_factory = auth_client
    user = _seed_user(session_factory, "user-a")

    assert client.get("/auth/me", headers=_bearer(user)).status_code == 200
    created = client.post("/auth/session", headers=_bearer(user))
    assert created.status_code == 201
    assert "session" not in created.json()
    assert "httponly" in created.headers["set-cookie"].lower()
    assert "samesite=lax" in created.headers["set-cookie"].lower()

    assert client.get("/auth/me").json()["id"] == user.id
    assert client.get("/auth/me", headers=_bearer(user)).status_code == 200


def test_password_login_creates_cookie_session_without_returning_a_jwt(auth_client):
    client, session_factory = auth_client
    user = _seed_user(session_factory, "password-user", password="correct-password")

    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": "correct-password"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["id"] == user.id
    assert "access_token" not in response.json()
    assert "token_type" not in response.json()
    assert "httponly" in response.headers["set-cookie"].lower()
    assert client.get("/auth/me").json()["id"] == user.id
    assert _session_count(session_factory, user.id) == 1


@pytest.mark.parametrize(
    ("active", "verified", "password", "expected_status"),
    [
        (True, True, "wrong-password", 401),
        (False, True, "correct-password", 403),
        (True, False, "correct-password", 403),
    ],
)
def test_password_login_failures_do_not_create_sessions_or_cookies(
    auth_client, active, verified, password, expected_status
):
    client, session_factory = auth_client
    user = _seed_user(session_factory, "login-failure", active=active, password="correct-password")

    async def set_verification():
        async with session_factory() as db:
            stored_user = await db.get(User, user.id)
            stored_user.is_verified = verified
            await db.commit()

    asyncio.run(set_verification())
    response = client.post("/auth/login", json={"email": user.email, "password": password})

    assert response.status_code == expected_status
    assert "set-cookie" not in response.headers
    assert _session_count(session_factory, user.id) == 0


def test_email_confirmation_creates_cookie_session_without_returning_a_jwt(auth_client):
    client, session_factory = auth_client
    user = _seed_user(session_factory, "confirmation-user", password="correct-password")

    async def create_confirmation_token():
        async with session_factory() as db:
            stored_user = await db.get(User, user.id)
            stored_user.is_verified = False
            token = EmailConfirmationToken.create_token(stored_user.id, stored_user.email)
            db.add(token)
            await db.commit()
            return token.token

    confirmation_token = asyncio.run(create_confirmation_token())
    response = client.post("/auth/confirm-email", json={"token": confirmation_token})

    assert response.status_code == 200
    assert response.json()["user"]["id"] == user.id
    assert "access_token" not in response.json()
    assert "token_type" not in response.json()
    assert "httponly" in response.headers["set-cookie"].lower()
    assert client.get("/auth/me").json()["id"] == user.id
    assert _session_count(session_factory, user.id) == 1


def test_invalid_confirmation_and_register_do_not_authenticate(auth_client):
    client, session_factory = auth_client

    invalid_confirmation = client.post("/auth/confirm-email", json={"token": "invalid-token"})
    assert invalid_confirmation.status_code == 400
    assert "set-cookie" not in invalid_confirmation.headers
    assert _session_count(session_factory) == 0

    registration = client.post(
        "/auth/register",
        json={"email": "pending@example.com", "password": "correct-password"},
    )
    assert registration.status_code == 200
    assert registration.json()["requires_email_confirmation"] is True
    assert "access_token" not in registration.json()
    assert "token_type" not in registration.json()
    assert "set-cookie" not in registration.headers
    assert _session_count(session_factory) == 0


def test_login_session_creation_failure_rolls_back_without_cookie(auth_client, monkeypatch):
    client, session_factory = auth_client
    user = _seed_user(session_factory, "login-create-failure", password="correct-password")
    set_cookie = Mock()

    async def fail_create_session(*_args, **_kwargs):
        raise RuntimeError("session storage unavailable")

    monkeypatch.setattr(auth_router.session_service, "create_session", fail_create_session)
    monkeypatch.setattr(auth_router, "set_session_cookie", set_cookie)

    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": "correct-password"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to log in. Please try again."
    assert "set-cookie" not in response.headers
    assert _session_count(session_factory, user.id) == 0
    set_cookie.assert_not_called()


def test_login_commit_failure_rolls_back_without_cookie(auth_client, monkeypatch):
    client, session_factory = auth_client
    user = _seed_user(session_factory, "login-commit-failure", password="correct-password")
    set_cookie = Mock()

    async def failing_get_db():
        async with session_factory() as db:
            async def fail_commit():
                raise RuntimeError("database unavailable")

            db.commit = fail_commit
            try:
                yield db
            except Exception:
                await db.rollback()
                raise

    monkeypatch.setitem(app.dependency_overrides, get_db, failing_get_db)
    monkeypatch.setattr(auth_router, "set_session_cookie", set_cookie)
    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": "correct-password"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to log in. Please try again."
    assert "set-cookie" not in response.headers
    assert _session_count(session_factory, user.id) == 0
    set_cookie.assert_not_called()


def test_confirmation_session_creation_failure_rolls_back_without_cookie_or_email(
    auth_client, monkeypatch
):
    client, session_factory = auth_client
    user = _seed_user(session_factory, "confirmation-create-failure")
    welcome_email = AsyncMock()

    async def prepare_token():
        async with session_factory() as db:
            stored_user = await db.get(User, user.id)
            stored_user.is_verified = False
            token = EmailConfirmationToken.create_token(stored_user.id, stored_user.email)
            db.add(token)
            await db.commit()
            return token.token

    async def fail_create_session(*_args, **_kwargs):
        raise RuntimeError("session storage unavailable")

    token = asyncio.run(prepare_token())
    monkeypatch.setattr(auth_router.session_service, "create_session", fail_create_session)
    monkeypatch.setattr(auth_router, "send_welcome_email", welcome_email)
    response = client.post("/auth/confirm-email", json={"token": token})

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to confirm email. Please try again."
    assert "set-cookie" not in response.headers
    assert _session_count(session_factory, user.id) == 0
    welcome_email.assert_not_awaited()

    async def verify_rollback():
        async with session_factory() as db:
            stored_user = await db.get(User, user.id)
            stored_token = (
                await db.execute(select(EmailConfirmationToken).where(EmailConfirmationToken.token == token))
            ).scalar_one()
            assert stored_user.is_verified is False
            assert stored_token.used is False

    asyncio.run(verify_rollback())


def test_confirmation_commit_failure_rolls_back_without_cookie_or_email(auth_client, monkeypatch):
    client, session_factory = auth_client
    user = _seed_user(session_factory, "confirmation-commit-failure")
    welcome_email = AsyncMock()

    async def prepare_token():
        async with session_factory() as db:
            stored_user = await db.get(User, user.id)
            stored_user.is_verified = False
            token = EmailConfirmationToken.create_token(stored_user.id, stored_user.email)
            db.add(token)
            await db.commit()
            return token.token

    token = asyncio.run(prepare_token())
    async def failing_get_db():
        async with session_factory() as db:
            async def fail_commit():
                raise RuntimeError("database unavailable")

            db.commit = fail_commit
            try:
                yield db
            except Exception:
                await db.rollback()
                raise

    monkeypatch.setitem(app.dependency_overrides, get_db, failing_get_db)
    monkeypatch.setattr(auth_router, "send_welcome_email", welcome_email)
    response = client.post("/auth/confirm-email", json={"token": token})

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to confirm email. Please try again."
    assert "set-cookie" not in response.headers
    assert _session_count(session_factory, user.id) == 0
    welcome_email.assert_not_awaited()

    async def verify_rollback():
        async with session_factory() as db:
            stored_user = await db.get(User, user.id)
            stored_token = (
                await db.execute(select(EmailConfirmationToken).where(EmailConfirmationToken.token == token))
            ).scalar_one()
            assert stored_user.is_verified is False
            assert stored_token.used is False

    asyncio.run(verify_rollback())


def test_confirmation_token_is_consumed_once_under_concurrent_requests(auth_client, monkeypatch):
    _client, session_factory = auth_client
    user = _seed_user(session_factory, "concurrent-confirmation")
    welcome_email = AsyncMock()

    async def prepare_token():
        async with session_factory() as db:
            stored_user = await db.get(User, user.id)
            stored_user.is_verified = False
            token = EmailConfirmationToken.create_token(stored_user.id, stored_user.email)
            db.add(token)
            await db.commit()
            return token.token

    token = asyncio.run(prepare_token())
    monkeypatch.setattr(auth_router, "send_welcome_email", welcome_email)
    async def confirm_concurrently():
        barrier = asyncio.Barrier(2)
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as contender:
            async def confirm():
                await barrier.wait()
                return await contender.post("/auth/confirm-email", json={"token": token})

            return await asyncio.gather(confirm(), confirm())

    responses = asyncio.run(confirm_concurrently())

    successes = [response for response in responses if response.status_code == 200]
    failures = [response for response in responses if response.status_code == 400]
    assert len(successes) == 1
    assert len(failures) == 1
    assert "set-cookie" in successes[0].headers
    assert "set-cookie" not in failures[0].headers
    assert _session_count(session_factory, user.id) == 1
    welcome_email.assert_awaited_once()

    async def verify_single_consumption():
        async with session_factory() as db:
            stored_user = await db.get(User, user.id)
            stored_token = (
                await db.execute(select(EmailConfirmationToken).where(EmailConfirmationToken.token == token))
            ).scalar_one()
            assert stored_user.is_verified is True
            assert stored_token.used is True

    asyncio.run(verify_single_consumption())


def test_cookie_is_authoritative_and_conflicts_are_rejected(auth_client):
    client, session_factory = auth_client
    first = _seed_user(session_factory, "user-a")
    second = _seed_user(session_factory, "user-b")
    created = _mint_session(session_factory, first.id)
    client.cookies.set(settings.session_cookie_name, created.raw_token)

    assert client.get("/auth/me", headers=_bearer(second)).status_code == 401
    client.cookies.set(settings.session_cookie_name, "unknown-session-token-value" * 3)
    assert client.get("/auth/me", headers=_bearer(first)).status_code == 401


def test_expired_revoked_and_inactive_cookie_sessions_are_refused(auth_client):
    client, session_factory = auth_client
    user = _seed_user(session_factory, "user-a")
    user_id = user.id
    expired = _mint_session(
        session_factory,
        user.id,
        ttl=timedelta(seconds=1),
        now=utc_now() - timedelta(seconds=2),
    )
    client.cookies.set(settings.session_cookie_name, expired.raw_token)
    assert client.get("/auth/me").status_code == 401

    active = _mint_session(session_factory, user.id)
    async def revoke_and_disable():
        async with session_factory() as db:
            assert await session_service.revoke_session(db, active.session.id)
            await db.commit()

    asyncio.run(revoke_and_disable())
    client.cookies.set(settings.session_cookie_name, active.raw_token)
    assert client.get("/auth/me").status_code == 401

    enabled = _mint_session(session_factory, user.id)

    async def disable_user():
        async with session_factory() as db:
            stored_user = await db.get(User, user_id)
            stored_user.is_active = False
            await db.commit()

    asyncio.run(disable_user())
    client.cookies.set(settings.session_cookie_name, enabled.raw_token)
    assert client.get("/auth/me").status_code == 401


def test_session_endpoint_requires_bearer_and_logout_is_csrf_protected(auth_client):
    client, session_factory = auth_client
    user = _seed_user(session_factory, "user-a")

    assert client.post("/auth/session").status_code == 403
    created = client.post("/auth/session", headers=_bearer(user))
    assert created.status_code == 201
    assert client.post("/auth/logout", headers={"Origin": "https://evil.example"}).status_code == 403

    logout = client.post("/auth/logout", headers={"Origin": "http://localhost:5173"})
    assert logout.status_code == 204
    assert "max-age=0" in logout.headers["set-cookie"].lower()
    assert client.get("/auth/me").status_code == 403
    assert client.get("/auth/me", headers=_bearer(user)).status_code == 200


@pytest.mark.parametrize("cookie", ["", "   ", "a" * 10000])
def test_malformed_cookie_never_falls_back_to_bearer(auth_client, cookie):
    client, session_factory = auth_client
    user = _seed_user(session_factory, "user-a")
    client.cookies.set(settings.session_cookie_name, cookie)
    assert client.get("/auth/me", headers=_bearer(user)).status_code == 401


@pytest.mark.parametrize(
    "origin",
    [None, "null", "http://localhost:5173/", "https://app.example.com.attacker.test"],
)
def test_logout_rejects_non_exact_origins(auth_client, origin):
    client, session_factory = auth_client
    user = _seed_user(session_factory, "user-a")
    assert client.post("/auth/session", headers=_bearer(user)).status_code == 201
    headers = {} if origin is None else {"Origin": origin}
    assert client.post("/auth/logout", headers=headers).status_code == 403


def test_basic_and_empty_bearer_are_not_credentials(auth_client):
    client, _ = auth_client
    assert client.get("/auth/me", headers={"Authorization": "Basic abc"}).status_code == 403
    assert client.get("/auth/me", headers={"Authorization": "Bearer "}).status_code in {401, 403}


def test_production_cookie_is_secure(monkeypatch):
    from fastapi import Response
    from backend.auth.session_cookie import set_session_cookie

    monkeypatch.setattr(settings, "app_environment", "production")
    monkeypatch.setattr(settings, "session_cookie_name", "__Host-ai_shorts_session")
    response = Response()
    set_session_cookie(response, "opaque-token")
    assert "secure" in response.headers["set-cookie"].lower()
    assert "path=/" in response.headers["set-cookie"].lower()


def test_host_cookie_and_samesite_configuration_are_validated(monkeypatch):
    from backend.auth.session_cookie import validate_session_cookie_configuration

    monkeypatch.setattr(settings, "app_environment", "production")
    monkeypatch.setattr(settings, "session_cookie_name", "__Host-ai_shorts_session")
    validate_session_cookie_configuration()
    monkeypatch.setattr(settings, "session_cookie_domain", "example.com")
    with pytest.raises(RuntimeError, match="__Host-"):
        validate_session_cookie_configuration()
    monkeypatch.setattr(settings, "session_cookie_domain", None)
    monkeypatch.setattr(settings, "app_environment", "test")
    monkeypatch.setattr(settings, "session_cookie_name", "session")
    monkeypatch.setattr(settings, "session_cookie_samesite", "none")
    monkeypatch.setattr(settings, "session_cookie_secure", False)
    with pytest.raises(RuntimeError, match="SAMESITE"):
        validate_session_cookie_configuration()
