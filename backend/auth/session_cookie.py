"""Centralized, safe cookie policy for opaque web sessions."""

from typing import Any

from fastapi import HTTPException, Request, Response, status

from backend.config import settings
from backend.auth.origin_policy import allowed_origins, require_trusted_origin_for_cookie_auth


def _cookie_options() -> dict[str, Any]:
    validate_session_cookie_configuration()
    domain = settings.session_cookie_domain
    return {
        "httponly": True,
        "secure": settings.app_environment == "production" or settings.session_cookie_secure,
        "samesite": settings.session_cookie_samesite,
        "path": settings.session_cookie_path,
        "domain": domain,
    }


def validate_session_cookie_configuration() -> None:
    """Fail fast for configurations that weaken or invalidate session cookies."""
    name = settings.session_cookie_name
    domain = settings.session_cookie_domain
    secure = settings.app_environment == "production" or settings.session_cookie_secure
    if not name or any(character.isspace() or character in ";," for character in name):
        raise RuntimeError("SESSION_COOKIE_NAME must be a valid cookie name")
    if domain and ("*" in domain or "://" in domain or "/" in domain):
        raise RuntimeError("SESSION_COOKIE_DOMAIN must be a single host name")
    if settings.session_cookie_max_age <= 0:
        raise RuntimeError("SESSION_COOKIE_MAX_AGE must be positive")
    if settings.session_cookie_samesite == "none" and not secure:
        raise RuntimeError("SESSION_COOKIE_SAMESITE=none requires SESSION_COOKIE_SECURE")
    if settings.app_environment == "production" and not name.startswith("__Host-"):
        raise RuntimeError("production SESSION_COOKIE_NAME must use the __Host- prefix")
    if name.startswith("__Host-") and (not secure or domain is not None or settings.session_cookie_path != "/"):
        raise RuntimeError("__Host- cookies require Secure, Path=/, and no Domain")


def read_session_cookie(request: Request) -> str | None:
    """Read opaque cookie material without logging or transforming it."""
    values = _session_cookie_values(request)
    return values[0] if len(values) == 1 else None


def session_cookie_present(request: Request) -> bool:
    return bool(_session_cookie_values(request))


def reject_ambiguous_session_cookie(request: Request) -> None:
    """Fail closed rather than letting Starlette select a duplicate cookie value."""
    if len(_session_cookie_values(request)) > 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _session_cookie_values(request: Request) -> list[str]:
    """Extract only the configured auth cookie from raw Cookie headers."""
    values: list[str] = []
    for header in request.headers.getlist("cookie"):
        for item in header.split(";"):
            name, separator, value = item.strip().partition("=")
            if name == settings.session_cookie_name:
                values.append(value if separator else "")
    return values


def set_session_cookie(response: Response, token: str) -> None:
    """Set an HttpOnly opaque-session cookie after its database commit succeeds."""
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_cookie_max_age,
        **_cookie_options(),
    )


def delete_session_cookie(response: Response) -> None:
    """Delete a session cookie using the same scope as its creation."""
    response.delete_cookie(
        key=settings.session_cookie_name,
        **_cookie_options(),
    )


def require_allowed_origin(request: Request) -> None:
    """Compatibility wrapper for the shared cookie-CSRF Origin policy."""
    require_trusted_origin_for_cookie_auth(request)
