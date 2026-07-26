"""End-to-end HTTP checks for the Google callback's sensitive boundaries."""

import asyncio
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import backend.auth.router as auth_router
from backend.database import Base, get_db
from backend.main import app
from backend.models.user import AuthSession, User


class _GoogleResponse:
    def __init__(self, profile): self.profile = profile
    def json(self): return self.profile


class _GoogleClient:
    profile = {"sub": "google-sub", "email": "creator@example.test", "name": "Creator"}
    failure = None
    def __init__(self, *args, **kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *args): return False
    def create_authorization_url(self, _url, **kwargs):
        return (f"https://accounts.google.test/auth?state={kwargs['state']}", None)
    async def fetch_token(self, *_args, **_kwargs):
        if self.failure: raise self.failure
    async def get(self, *_args, **_kwargs): return _GoogleResponse(self.profile)


@pytest.fixture
def oauth_client(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'oauth-http.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async def schema():
        async with engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
    async def override():
        async with factory() as db:
            try: yield db
            except Exception:
                await db.rollback()
                raise
    asyncio.run(schema())
    monkeypatch.setattr(auth_router, "GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(auth_router, "GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(auth_router, "GOOGLE_REDIRECT_URI", "http://testserver/auth/google/callback")
    monkeypatch.setattr(auth_router, "FRONTEND_URL", "http://localhost:5173")
    monkeypatch.setattr(auth_router, "AsyncOAuth2Client", _GoogleClient)
    app.dependency_overrides[get_db] = override
    client = TestClient(app, raise_server_exceptions=False)
    try: yield client, factory
    finally:
        client.close(); app.dependency_overrides.pop(get_db, None); asyncio.run(engine.dispose())


def _state(client):
    start = client.get("/auth/google", follow_redirects=False)
    assert start.status_code in {302, 307}
    return parse_qs(urlparse(start.headers["location"]).query)["state"][0]


def _assert_clean_redirect(response):
    assert response.status_code == 302
    location = response.headers["location"]
    assert urlparse(location).path == "/auth/callback"
    for value in ("token=", "jwt=", "access_token=", "refresh_token=", "session=", "state=", "code="):
        assert value not in location.lower()
        assert value not in response.text.lower()
    cookie = response.headers["set-cookie"].lower()
    for value in ("token=", "jwt=", "access_token=", "refresh_token=", "state=", "code="):
        assert value not in cookie


def test_google_callback_sets_cookie_without_sensitive_redirect_data(oauth_client):
    client, factory = oauth_client
    response = client.get(f"/auth/google/callback?code=google-code&state={_state(client)}", follow_redirects=False)
    _assert_clean_redirect(response)
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=lax" in response.headers["set-cookie"].lower()

    async def verify():
        async with factory() as db:
            assert (await db.execute(select(User))).scalar_one().email == "creator@example.test"
            assert (await db.execute(select(AuthSession))).scalar_one()
    asyncio.run(verify())


@pytest.mark.parametrize("state", ["", "unknown", "a" * 300])
def test_invalid_state_never_creates_cookie_or_session(oauth_client, state):
    client, factory = oauth_client
    response = client.get(f"/auth/google/callback?code=google-code&state={state}", follow_redirects=False)
    assert response.status_code == 400
    assert "set-cookie" not in response.headers
    async def verify():
        async with factory() as db: assert not (await db.execute(select(AuthSession))).scalars().all()
    asyncio.run(verify())


def test_state_is_single_use_and_google_failure_never_sets_cookie(oauth_client, monkeypatch):
    client, factory = oauth_client
    state = _state(client)
    first = client.get(f"/auth/google/callback?code=google-code&state={state}", follow_redirects=False)
    _assert_clean_redirect(first)
    assert client.get(f"/auth/google/callback?code=google-code&state={state}", follow_redirects=False).status_code == 400
    state = _state(client)
    monkeypatch.setattr(_GoogleClient, "failure", TimeoutError("google unavailable"))
    failed = client.get(f"/auth/google/callback?code=sensitive-code&state={state}", follow_redirects=False)
    assert failed.status_code == 500 and "set-cookie" not in failed.headers
