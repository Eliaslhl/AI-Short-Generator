"""HTTP coverage for cookie-only CSRF enforcement."""

import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.requests import Request

from backend.config import settings
from backend.database import Base, get_db
from backend.main import app
from backend.models.user import Plan, User
from backend.services.session_service import session_service
from backend.auth.session_cookie import reject_ambiguous_session_cookie


@pytest.fixture
def csrf_client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'csrf.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    asyncio.run(create_schema())
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, session_factory
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        asyncio.run(engine.dispose())


def _seed_user(session_factory, user_id: str, *, subscription: bool = False) -> User:
    async def seed():
        async with session_factory() as db:
            user = User(
                id=user_id,
                email=f"{user_id}@example.com",
                hashed_password="not-used",
                is_active=True,
                is_verified=True,
                plan=Plan.PRO if subscription else Plan.FREE,
                stripe_subscription_id="sub_test" if subscription else None,
            )
            db.add(user)
            await db.commit()
            return user

    return asyncio.run(seed())


def _cookie_session(session_factory, user_id: str) -> str:
    async def create():
        async with session_factory() as db:
            session = await session_service.create_session(db, user_id)
            await db.commit()
            return session.raw_token

    return asyncio.run(create())


def _duplicate_auth_cookie(first: str, second: str) -> str:
    name = settings.session_cookie_name
    return f"{name}={first}; {name}={second}"


def test_cookie_mutations_require_origin_before_route_effects(csrf_client, monkeypatch):
    client, session_factory = csrf_client
    user = _seed_user(session_factory, "cookie-user", subscription=True)
    client.cookies.set(settings.session_cookie_name, _cookie_session(session_factory, user.id))
    stripe_calls = []
    monkeypatch.setattr("backend.auth.router.stripe.api_key", "sk_test")
    monkeypatch.setattr("backend.auth.router.stripe.Subscription.modify", lambda *args, **kwargs: stripe_calls.append(args))

    response = client.post("/auth/stripe/cancel")

    assert response.status_code == 403
    assert response.json() == {"detail": "Untrusted request origin"}
    assert stripe_calls == []


def test_cookie_checkout_is_rejected_before_stripe_customer_creation(csrf_client, monkeypatch):
    client, session_factory = csrf_client
    user = _seed_user(session_factory, "checkout-user")
    client.cookies.set(settings.session_cookie_name, _cookie_session(session_factory, user.id))
    customer_calls = []
    monkeypatch.setattr("backend.auth.router.stripe.api_key", "sk_test")
    monkeypatch.setattr(
        "backend.auth.router.stripe.Customer.create",
        lambda *args, **kwargs: customer_calls.append((args, kwargs)),
    )

    response = client.post("/auth/stripe/checkout", json={"price_id": "price_not_reached"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Untrusted request origin"}
    assert customer_calls == []


def test_cookie_generation_is_rejected_before_enqueue(csrf_client, monkeypatch):
    client, session_factory = csrf_client
    user = _seed_user(session_factory, "generator-user")
    client.cookies.set(settings.session_cookie_name, _cookie_session(session_factory, user.id))

    pipeline_calls = []

    async def fake_pipeline(*args, **kwargs):
        pipeline_calls.append((args, kwargs))

    monkeypatch.setattr("backend.api.routes.run_pipeline", fake_pipeline)

    response = client.post("/api/generate", json={"youtube_url": "https://youtube.com/watch?v=test"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Untrusted request origin"}
    assert pipeline_calls == []


def test_cookie_preview_and_twitch_are_rejected_before_external_requests(csrf_client, monkeypatch):
    client, session_factory = csrf_client
    user = _seed_user(session_factory, "external-user")
    client.cookies.set(settings.session_cookie_name, _cookie_session(session_factory, user.id))

    def external_call_must_not_run(*args, **kwargs):
        raise AssertionError("external service must follow CSRF validation")

    monkeypatch.setattr("subprocess.run", external_call_must_not_run)
    monkeypatch.setattr("backend.api.routes.TwitchAPIClient", external_call_must_not_run)

    preview = client.post("/api/preview", json={"url": "https://youtube.com/watch?v=test"})
    twitch = client.post("/api/twitch/vods", json={"channel_login": "channel"})

    assert preview.status_code == 403
    assert twitch.status_code == 403
    assert preview.json() == twitch.json() == {"detail": "Untrusted request origin"}


def test_cookie_valid_origin_allows_mutation(csrf_client, monkeypatch):
    client, session_factory = csrf_client
    user = _seed_user(session_factory, "cookie-user", subscription=True)
    client.cookies.set(settings.session_cookie_name, _cookie_session(session_factory, user.id))
    stripe_calls = []
    monkeypatch.setattr("backend.auth.router.stripe.api_key", "sk_test")
    monkeypatch.setattr("backend.auth.router.stripe.Subscription.modify", lambda *args, **kwargs: stripe_calls.append(args))

    assert client.post("/auth/stripe/cancel", headers={"Origin": "http://localhost:5173"}).status_code == 200
    assert len(stripe_calls) == 1



def test_invalid_cookies_do_not_bypass_csrf(csrf_client):
    client, session_factory = csrf_client
    first = _seed_user(session_factory, "first")
    client.cookies.set(settings.session_cookie_name, _cookie_session(session_factory, first.id))

    client.cookies.set(settings.session_cookie_name, "invalid-cookie-token" * 4)
    assert client.post("/api/preview", json={"url": "https://example.com"}).status_code == 401


def test_duplicate_auth_cookies_are_rejected(csrf_client):
    client, session_factory = csrf_client
    user = _seed_user(session_factory, "duplicate-cookie-user")
    valid = _cookie_session(session_factory, user.id)

    for cookie in (
        _duplicate_auth_cookie(valid, "invalid-cookie"),
        _duplicate_auth_cookie("invalid-cookie", valid),
        _duplicate_auth_cookie(valid, valid),
    ):
        response = client.post(
            "/api/preview",
            json={"url": "https://example.com"},
            headers={"Cookie": cookie},
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Could not validate credentials"}


def test_duplicate_production_host_cookie_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "session_cookie_name", "__Host-ai_shorts_session")
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [
                (
                    b"cookie",
                    b"__Host-ai_shorts_session=first; __Host-ai_shorts_session=second",
                )
            ],
        }
    )

    with pytest.raises(HTTPException) as error:
        reject_ambiguous_session_cookie(request)
    assert error.value.status_code == 401


def test_legacy_session_conversion_route_is_absent(csrf_client):
    client, session_factory = csrf_client
    _seed_user(session_factory, "legacy-session-user")

    assert client.post("/auth/session", headers={"Authorization": "Bearer legacy-token"}).status_code == 404


def test_cookie_reads_and_cors_preflight_are_not_csrf_blocked(csrf_client):
    client, session_factory = csrf_client
    user = _seed_user(session_factory, "read-user")
    client.cookies.set(settings.session_cookie_name, _cookie_session(session_factory, user.id))

    assert client.get("/auth/me").status_code == 200
    preflight = client.options(
        "/api/preview",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert preflight.status_code == 200


def test_cookie_job_deletion_is_rejected_before_queue_access(csrf_client, monkeypatch):
    client, session_factory = csrf_client
    user = _seed_user(session_factory, "job-user")
    client.cookies.set(settings.session_cookie_name, _cookie_session(session_factory, user.id))

    def queue_must_not_be_used():
        raise AssertionError("queue access must follow CSRF validation")

    monkeypatch.setattr("backend.api.advanced_routes.get_queue", queue_must_not_be_used)

    response = client.delete("/api/api/jobs/foreign-job")

    assert response.status_code == 403
    assert response.json() == {"detail": "Untrusted request origin"}


def test_cookie_advanced_generation_is_rejected_before_rq_enqueue(csrf_client, monkeypatch):
    client, session_factory = csrf_client
    user = _seed_user(session_factory, "advanced-job-user")
    client.cookies.set(settings.session_cookie_name, _cookie_session(session_factory, user.id))

    def queue_must_not_be_used():
        raise AssertionError("RQ enqueue must follow CSRF validation")

    monkeypatch.setattr("backend.api.advanced_routes.get_queue", queue_must_not_be_used)

    response = client.post(
        "/api/api/generate/twitch/advanced", json={"url": "https://twitch.tv/channel"}
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Untrusted request origin"}


def test_cookie_logout_requires_origin_before_session_revocation(csrf_client, monkeypatch):
    client, session_factory = csrf_client
    user = _seed_user(session_factory, "logout-user")
    client.cookies.set(settings.session_cookie_name, _cookie_session(session_factory, user.id))
    revocations = []

    async def fake_revoke(*args, **kwargs):
        revocations.append((args, kwargs))

    monkeypatch.setattr("backend.auth.router.session_service.revoke_session_by_token", fake_revoke)

    response = client.post("/auth/logout")

    assert response.status_code == 403
    assert response.json() == {"detail": "Untrusted request origin"}
    assert revocations == []
