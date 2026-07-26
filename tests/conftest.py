"""Safe process-wide configuration for the backend test suite."""

import os


os.environ.setdefault("APP_ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-not-for-production")
