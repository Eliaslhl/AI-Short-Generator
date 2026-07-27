"""Safe process-wide configuration for the backend test suite."""

import os


os.environ.setdefault("APP_ENVIRONMENT", "test")
os.environ.setdefault("SESSION_HASH_KEY", "test-session-key-not-for-production")
