import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from backend.auth.origin_policy import (
    allowed_origins,
    CanonicalCORSMiddleware,
    is_trusted_origin_header,
    normalise_configured_origin,
    normalise_request_origin,
    require_trusted_origin_for_cookie_auth,
)
from backend.config import settings


def _request(method: str, origin: str | None = None, *, extra_headers=None) -> Request:
    headers = [] if origin is None else [(b"origin", origin.encode())]
    headers.extend(extra_headers or [])
    return Request({"type": "http", "method": method, "path": "/", "headers": headers})


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://APP.example.com", "https://app.example.com"),
        ("https://app.example.com:443", "https://app.example.com"),
        ("http://localhost:5173/", "http://localhost:5173"),
    ],
)
def test_configured_origins_are_normalized(value, expected):
    assert normalise_configured_origin(value) == expected


@pytest.mark.parametrize(
    "origin",
    [
        "",
        " ",
        "null",
        "https://app.example.com/",
        "https://app.example.com/path",
        "https://app.example.com?x=1",
        "https://app.example.com#fragment",
        "https://user@app.example.com",
        "javascript://app.example.com",
        "file:///tmp/app",
        "ftp://app.example.com",
        "https://*.example.com",
        "https://app.example.com,https://evil.test",
        "https://app.example.com\nhttps://evil.test",
        "x" * 2049,
    ],
)
def test_request_origin_rejects_ambiguous_or_untrusted_syntax(origin):
    with pytest.raises(ValueError):
        normalise_request_origin(origin)


def test_cookie_mutation_requires_exact_origin(monkeypatch):
    monkeypatch.setattr(settings, "app_environment", "test")
    monkeypatch.setattr(settings, "frontend_url", "https://app.example.com")

    require_trusted_origin_for_cookie_auth(_request("POST", "https://app.example.com"))
    require_trusted_origin_for_cookie_auth(_request("GET"))

    for origin in (
        None,
        "null",
        "https://app.example.com/",
        "https://app.example.com.evil.test",
        "https://evilapp.example.com",
    ):
        with pytest.raises(HTTPException) as error:
            require_trusted_origin_for_cookie_auth(_request("POST", origin))
        assert error.value.status_code == 403
        assert error.value.detail == "Untrusted request origin"


def test_production_rejects_localhost_and_invalid_config(monkeypatch):
    monkeypatch.setattr(settings, "app_environment", "production")
    monkeypatch.setattr(settings, "frontend_url", "https://localhost:5173")
    with pytest.raises(RuntimeError):
        allowed_origins()

    monkeypatch.setattr(settings, "frontend_url", "https://app.example.com/path")
    with pytest.raises(RuntimeError, match="FRONTEND_URL"):
        allowed_origins()


def test_production_without_frontend_origin_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "app_environment", "production")
    monkeypatch.setattr(settings, "frontend_url", "")

    assert allowed_origins() == []


@pytest.mark.parametrize(
    "origin",
    [
        "https://localhost.",
        "https://foo.localhost",
        "https://127.0.0.1",
        "https://127.23.45.67",
        "https://[::1]",
        "https://[0:0:0:0:0:0:0:1]",
        "https://[::ffff:127.0.0.1]",
    ],
)
def test_production_rejects_every_loopback_spelling(monkeypatch, origin):
    monkeypatch.setattr(settings, "app_environment", "production")
    monkeypatch.setattr(settings, "frontend_url", origin)

    with pytest.raises(RuntimeError):
        allowed_origins()


@pytest.mark.parametrize(
    "origin",
    [
        "https://app.example.com\\",
        "https://app.example.com.",
        "https://2130706433",
        "https://-app.example.com",
        "https://app-.example.com",
        "https://app..example.com",
        "https://app.example.com:99999",
    ],
)
def test_configured_origin_rejects_ambiguous_hostnames(origin):
    with pytest.raises(ValueError):
        normalise_configured_origin(origin)


def test_production_allows_localhost_as_part_of_a_public_domain(monkeypatch):
    monkeypatch.setattr(settings, "app_environment", "production")
    monkeypatch.setattr(settings, "frontend_url", "https://localhost.example.com")

    assert allowed_origins() == ["https://localhost.example.com"]


def test_origin_policy_rejects_duplicate_headers_in_every_order(monkeypatch):
    monkeypatch.setattr(settings, "app_environment", "test")
    monkeypatch.setattr(settings, "frontend_url", "https://app.example.com")

    for headers in (
        [(b"origin", b"https://app.example.com"), (b"origin", b"https://evil.test")],
        [(b"origin", b"https://evil.test"), (b"origin", b"https://app.example.com")],
        [(b"origin", b"https://app.example.com"), (b"origin", b"https://app.example.com")],
    ):
        with pytest.raises(HTTPException) as error:
            require_trusted_origin_for_cookie_auth(_request("POST", extra_headers=headers))
        assert error.value.status_code == 403


def _cors_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CanonicalCORSMiddleware,
        allow_origins=allowed_origins(),
        allow_credentials=True,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
    )

    @app.post("/mutation")
    async def mutation(request: Request):
        require_trusted_origin_for_cookie_auth(request)
        return {"ok": True}

    return app


def test_cors_and_csrf_share_canonical_origin_decisions(monkeypatch):
    monkeypatch.setattr(settings, "app_environment", "production")
    monkeypatch.setattr(settings, "frontend_url", "https://app.example.com")
    client = TestClient(_cors_test_app())

    for origin in (
        "https://app.example.com",
        "https://APP.EXAMPLE.COM",
        "https://app.example.com:443",
    ):
        preflight = client.options(
            "/mutation",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )
        response = client.post(
            "/mutation", headers={"Origin": origin, "Cookie": "session=opaque"}
        )
        assert is_trusted_origin_header(origin)
        assert preflight.status_code == response.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == origin
        assert response.headers["access-control-allow-origin"] == origin
        assert preflight.headers["access-control-allow-credentials"] == "true"


def test_cors_and_csrf_reject_untrusted_and_duplicate_origins(monkeypatch):
    monkeypatch.setattr(settings, "app_environment", "production")
    monkeypatch.setattr(settings, "frontend_url", "https://app.example.com")
    client = TestClient(_cors_test_app())

    for origin in ("null", "https://app.example.com.evil.test"):
        assert client.options(
            "/mutation",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        ).status_code == 400
        assert client.post("/mutation", headers={"Origin": origin}).status_code == 403

    duplicate = [
        ("Origin", "https://app.example.com"),
        ("Origin", "https://evil.test"),
    ]
    assert client.options(
        "/mutation", headers=[*duplicate, ("Access-Control-Request-Method", "POST")]
    ).status_code == 400
    assert client.post("/mutation", headers=duplicate).status_code == 403
