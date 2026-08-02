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
