"""Canonical Origin policy shared by CORS and cookie-authenticated mutations."""

import ipaddress
import re
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, status
from starlette.datastructures import Headers
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse

from backend.config import settings


_LOCAL_ORIGINS = (
    "http://localhost:5173",
    "http://localhost:4173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
)
_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def _normalise_hostname(hostname: str) -> str:
    """Return a safe canonical DNS name or IP address."""
    if not hostname or hostname.endswith(".") or hostname.isdigit():
        raise ValueError("origin hostname is invalid")

    try:
        return str(ipaddress.ip_address(hostname))
    except ValueError:
        pass

    try:
        normalized = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as error:
        raise ValueError("origin hostname is invalid") from error
    if len(normalized) > 253 or any(
        not _DNS_LABEL.fullmatch(label) for label in normalized.split(".")
    ):
        raise ValueError("origin hostname is invalid")
    return normalized


def _is_production_loopback(hostname: str) -> bool:
    """Identify loopback IPs and browser-reserved localhost names."""
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return address.is_loopback or (
        address.ipv4_mapped is not None and address.ipv4_mapped.is_loopback
    )


def _normalise_origin(value: str, *, allow_root_path: bool) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 2048:
        raise ValueError("origin must be a non-empty origin")
    if any(character.isspace() or ord(character) < 32 for character in value):
        raise ValueError("origin must not contain whitespace or control characters")
    if value.lower() == "null":
        raise ValueError("origin must not be null")

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise ValueError("origin has an invalid port") from error

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("origin must use http or https and include a host")
    if "*" in parsed.hostname:
        raise ValueError("origin must not contain a wildcard")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("origin must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("origin must not contain a query or fragment")
    if parsed.path not in ({"", "/"} if allow_root_path else {""}):
        raise ValueError("origin must not contain a path")

    hostname = _normalise_hostname(parsed.hostname)
    scheme = parsed.scheme.lower()
    if port is not None and port == (443 if scheme == "https" else 80):
        port = None
    host = f"[{hostname}]" if ":" in hostname else hostname
    return f"{scheme}://{host}{f':{port}' if port is not None else ''}"


def normalise_configured_origin(value: str) -> str:
    """Canonicalise an operator-provided root origin or fail closed."""
    return _normalise_origin(value, allow_root_path=True)


def normalise_request_origin(value: str) -> str:
    """Canonicalise a browser Origin header; serialized origins have no path."""
    return _normalise_origin(value, allow_root_path=False)


def allowed_origins() -> list[str]:
    """Return the exact normalized origins used for CORS and CSRF checks."""
    raw_origins = [] if settings.app_environment == "production" else list(_LOCAL_ORIGINS)
    frontend_url = settings.frontend_url
    if frontend_url:
        raw_origins.append(frontend_url)

    origins: list[str] = []
    for raw_origin in raw_origins:
        try:
            origin = normalise_configured_origin(raw_origin)
        except ValueError as error:
            raise RuntimeError("FRONTEND_URL must be a valid http(s) origin") from error
        if settings.app_environment == "production" and _is_production_loopback(
            urlsplit(origin).hostname or ""
        ):
            raise RuntimeError("production FRONTEND_URL must not use localhost")
        if origin not in origins:
            origins.append(origin)
    return origins


def is_trusted_origin_header(origin: str) -> bool:
    """Return whether one raw Origin header matches the canonical allowlist."""
    try:
        return normalise_request_origin(origin) in allowed_origins()
    except ValueError:
        return False


def _single_origin_header(headers: Headers) -> str | None:
    origins = headers.getlist("origin")
    return origins[0] if len(origins) == 1 else None


def require_trusted_origin_for_cookie_auth(request: Request) -> None:
    """Reject unsafe cookie-authenticated requests without an exact Origin."""
    if request.method.upper() not in _MUTATING_METHODS:
        return
    origin = _single_origin_header(request.headers)
    if origin is None or not is_trusted_origin_header(origin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Untrusted request origin",
        )


class CanonicalCORSMiddleware(CORSMiddleware):
    """CORS middleware that delegates every Origin decision to this policy."""

    def is_allowed_origin(self, origin: str) -> bool:
        return is_trusted_origin_header(origin)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        origins = headers.getlist("origin")
        if len(origins) > 1:
            if scope["method"] == "OPTIONS" and "access-control-request-method" in headers:
                response = PlainTextResponse(
                    "Disallowed CORS origin", status_code=400, headers=self.preflight_headers
                )
                await response(scope, receive, send)
                return
            await self.app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)
