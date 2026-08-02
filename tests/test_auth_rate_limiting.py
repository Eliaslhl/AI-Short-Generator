"""Rate limiting must actually be enforced on sensitive auth routes.

Limiter.default_limits alone is inert: it only takes effect through
SlowAPIMiddleware or an explicit @limiter.limit(...) on a route. This was
previously configured but never wired up (audit P0-1) — these tests fail
against that prior state and pass now that both are in place.
"""

from test_dual_auth import auth_client, _seed_user  # noqa: F401 (fixture import)


def test_login_is_rate_limited_after_5_attempts_per_minute(auth_client):
    client, session_factory = auth_client
    _seed_user(session_factory, "rate-limit-login", password="correct-password")

    for _ in range(5):
        response = client.post(
            "/auth/login",
            json={"email": "wrong@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

    limited = client.post(
        "/auth/login",
        json={"email": "wrong@example.com", "password": "wrong"},
    )
    assert limited.status_code == 429


def test_register_is_rate_limited_after_5_attempts_per_minute(auth_client):
    client, _session_factory = auth_client

    for i in range(5):
        response = client.post(
            "/auth/register",
            json={"email": f"rl-register-{i}@example.com", "password": "password123"},
        )
        assert response.status_code in (200, 400)

    limited = client.post(
        "/auth/register",
        json={"email": "rl-register-overflow@example.com", "password": "password123"},
    )
    assert limited.status_code == 429


def test_rate_limit_resets_between_tests(auth_client):
    """Sanity check for the autouse limiter.reset() fixture: a fresh test
    must never inherit an exhausted bucket from a previous test's requests."""
    client, session_factory = auth_client
    _seed_user(session_factory, "rate-limit-fresh", password="correct-password")

    response = client.post(
        "/auth/login",
        json={"email": "rate-limit-fresh@example.com", "password": "correct-password"},
    )
    assert response.status_code == 200


def test_limiter_middleware_is_mounted():
    from backend.main import app

    middleware_names = [m.cls.__name__ for m in app.user_middleware]
    assert "SlowAPIMiddleware" in middleware_names
