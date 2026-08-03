"""Safe process-wide configuration for the backend test suite."""

import os

import pytest

os.environ.setdefault("APP_ENVIRONMENT", "test")
os.environ.setdefault("SESSION_HASH_KEY", "test-session-key-not-for-production")


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """slowapi's in-memory storage is a module-level singleton shared by every
    TestClient request in the whole process (they all share the same source
    IP, so it's also shared across tests). Reset it before each test so a
    test's own login/register/etc. calls are never rate-limited by requests
    another, unrelated test made earlier in the same run."""
    from backend.rate_limiter import limiter

    limiter.reset()
    yield


@pytest.fixture(autouse=True)
def _stub_source_duration_probe(monkeypatch):
    """POST /api/generate calls _probe_source_duration_seconds(), which shells
    out to the real yt-dlp against the real internet. Without this, every
    existing test that posts to /generate makes a live network call for a
    fake test URL — slow, flaky offline, and a violation of "no external
    services in tests". Default to "unknown duration" (probe returns None,
    same as its real failure mode) so the length check never fires unless a
    test explicitly overrides this to exercise it."""
    import backend.api.routes as routes

    monkeypatch.setattr(routes, "_probe_source_duration_seconds", lambda _url: None)
    yield
