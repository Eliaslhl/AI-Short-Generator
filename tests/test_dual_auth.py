"""HTTP regressions for the transitional cookie-first authentication boundary."""

import asyncio
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.auth.jwt import create_access_token
from backend.config import settings
from backend.database import Base, get_db
from backend.main import app
from backend.models.user import User
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


def _seed_user(session_factory, user_id: str, *, active: bool = True) -> User:
    async def seed():
        async with session_factory() as db:
            user = User(
                id=user_id,
                email=f"{user_id}@example.com",
                hashed_password="not-used",
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
