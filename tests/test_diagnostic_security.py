"""Regression tests for public diagnostics and sensitive error handling."""

import asyncio
from copy import deepcopy
from io import StringIO
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.auth import router as auth_router
from backend.security_logging import (
    SensitiveDataFilter,
    configure_logging,
    redact_sensitive_data,
    sanitize_value,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SENSITIVE_DATABASE_URL = "postgresql://secret-user:secret-password@private-host/database"
SENSITIVE_TOKEN = "Bearer secret-jwt-test"


def _routes_for(environment: str) -> set[str]:
    env = {
        **os.environ,
        "APP_ENVIRONMENT": environment,
        "SESSION_HASH_KEY": "test-production-session-key-long-enough-012345",
        "DATABASE_URL": "sqlite+aiosqlite:///./data/app.db.test",
        "MIGRATE_ON_START": "false",
    }
    if environment == "production":
        # Exercise the secure production default: no implicit localhost origin.
        env.pop("FRONTEND_URL", None)
    command = [
        sys.executable,
        "-c",
        (
            "from fastapi.testclient import TestClient; "
            "from backend.main import app; "
            "client = TestClient(app); client.__enter__(); "
            "print('\\n'.join(sorted(route.path for route in app.routes))); "
            "client.__exit__(None, None, None)"
        ),
    ]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.splitlines())


def test_production_routes_exclude_sensitive_diagnostics():
    routes = _routes_for("production")

    assert "/_debug/db" not in routes
    assert "/api/debug/refresh-cookies" not in routes
    assert "/api/debug/youtube-cookies" not in routes
    assert "/api/debug/job/{job_id}" not in routes
    assert "/health" in routes


def test_development_only_registers_owned_job_diagnostic():
    routes = _routes_for("development")

    assert "/api/debug/job/{job_id}" in routes
    assert "/_debug/db" not in routes
    assert "/api/debug/refresh-cookies" not in routes
    assert "/api/debug/youtube-cookies" not in routes


def test_invalid_environment_is_rejected_before_routes_are_registered():
    env = {**os.environ, "APP_ENVIRONMENT": "debug"}
    result = subprocess.run(
        [sys.executable, "-c", "import backend.main"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "app_environment" in result.stderr


def test_production_requires_a_configured_session_hash_key():
    env = {**os.environ, "APP_ENVIRONMENT": "production"}
    env.pop("SESSION_HASH_KEY", None)
    env["FRONTEND_URL"] = "https://app.example.test"
    result = subprocess.run(
        [sys.executable, "-c", "import backend.main"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "SESSION_HASH_KEY" in result.stderr


def test_production_rejects_weak_session_hash_keys():
    for secret in ("dev-secret-key", "change-me", "short-secret"):
        env = {
            **os.environ,
            "APP_ENVIRONMENT": "production",
            "FRONTEND_URL": "https://app.example.test",
            "SESSION_HASH_KEY": secret,
        }
        result = subprocess.run(
            [sys.executable, "-c", "import backend.main"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "SESSION_HASH_KEY" in result.stderr


def test_development_accepts_documented_local_session_hash_key():
    env = {
        **os.environ,
        "APP_ENVIRONMENT": "development",
        "SESSION_HASH_KEY": "dev-session-key",
    }
    result = subprocess.run(
        [sys.executable, "-c", "import backend.main"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0


def test_api_and_worker_share_explicit_environment_configuration():
    session_key = "test-shared-session-key-with-sufficient-length"
    env = {
        **os.environ,
        "APP_ENVIRONMENT": "test",
        "SESSION_HASH_KEY": session_key,
    }
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from backend.config import settings; "
                "from backend.services.session_service import hash_session_token; "
                "import backend.queue.worker; "
                "print(settings.app_environment); "
                "print(bool(hash_session_token('session-token')))"
            ),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == ["test", "True"]


def test_docker_compose_shares_local_environment_file_with_workers():
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text()

    assert compose.count("- .env.docker") == 3
    assert compose.count("- APP_ENVIRONMENT=development") == 3


def test_login_error_does_not_return_connection_string_or_secret():
    class BrokenSession:
        async def execute(self, *_args, **_kwargs):
            raise RuntimeError(
                f"{SENSITIVE_DATABASE_URL} {SENSITIVE_TOKEN} super-secret-test-value"
            )

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            auth_router.login(
                auth_router.LoginRequest(email="user@example.com", password="password123"),
                BrokenSession(),
            )
        )

    assert error.value.status_code == 500
    assert SENSITIVE_DATABASE_URL not in str(error.value.detail)
    assert "super-secret-test-value" not in str(error.value.detail)


def test_health_is_public_and_contains_no_configuration():
    from backend.main import app

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "database" not in response.text.lower()


def test_log_filter_redacts_simulated_credentials():
    record = logging.LogRecord(
        "diagnostic-security-test",
        logging.ERROR,
        __file__,
        1,
        "database=%s authorization=%s password=%s path=%s",
        (
            SENSITIVE_DATABASE_URL,
            SENSITIVE_TOKEN,
            "super-secret-test-value",
            "/Users/test-user/private/video.mp4",
        ),
        None,
    )

    SensitiveDataFilter().filter(record)
    rendered = record.getMessage()

    for secret in (
        SENSITIVE_DATABASE_URL,
        "secret-password",
        "secret-jwt-test",
        "super-secret-test-value",
        "/Users/test-user",
    ):
        assert secret not in rendered
    assert redact_sensitive_data(SENSITIVE_TOKEN) == "Bearer [REDACTED]"


def _render_log(callback) -> str:
    configure_logging()
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("diagnostic-security-handler")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    callback(logger)
    return stream.getvalue()


def test_logging_factory_redacts_nested_values_without_mutation():
    payload = {
        "request_id": "safe-request-id",
        "nested": {
            "access_token": "secret-access-value",
            "refresh_token": "secret-refresh-value",
        },
        "items": [
            {"authorization": "Bearer secret-bearer-value"},
            ("safe-context", {"cookie": "session=secret-cookie-value"}),
        ],
    }
    original = deepcopy(payload)
    rendered = _render_log(lambda logger: logger.info("payload=%s", payload))

    for secret in (
        "secret-access-value",
        "secret-refresh-value",
        "secret-bearer-value",
        "secret-cookie-value",
    ):
        assert secret not in rendered
    assert "safe-request-id" in rendered
    assert payload == original


def test_logging_factory_redacts_urls_jwts_and_exceptions():
    url = "https://example.test/callback?access_token=secret-query-value"
    database_url = "postgresql://user:secret-password@private-host/db"
    jwt = "header.payload.signature"

    def log_exception(logger):
        try:
            raise RuntimeError(
                f"url={url} database={database_url} jwt={jwt} access_token=secret-access-value"
            )
        except RuntimeError:
            logger.exception("OAuth callback processing failed")

    rendered = _render_log(log_exception)

    for secret in (
        "secret-query-value",
        "secret-password",
        "header.payload.signature",
        "secret-access-value",
    ):
        assert secret not in rendered
    assert "OAuth callback processing failed" in rendered
    assert "RuntimeError" in rendered


def test_sanitizer_never_raises_for_unprintable_objects():
    class Unprintable:
        def __str__(self):
            raise RuntimeError("secret-object-value")

    assert "UNPRINTABLE" in sanitize_value(Unprintable())


def test_youtube_auto_refresh_logs_do_not_include_subprocess_output(monkeypatch, caplog):
    from backend.services import youtube_service

    configure_logging()
    secret = "secret-cookie-output-value"
    monkeypatch.setattr(youtube_service, "_is_auto_refresh_enabled", lambda: True)
    monkeypatch.setattr(
        youtube_service.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=7, stdout=secret, stderr=secret
        ),
    )

    with caplog.at_level(logging.INFO, logger="backend.services.youtube_service"):
        with pytest.raises(RuntimeError):
            youtube_service._auto_refresh_and_retry_download([], "job-safe", "https://youtube.com/watch?v=safe")

    assert secret not in caplog.text
    assert "return_code=7" in caplog.text
