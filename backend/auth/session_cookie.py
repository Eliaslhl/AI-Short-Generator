"""Centralized, safe cookie policy for opaque web sessions."""

import os
from typing import Any

from fastapi import HTTPException, Request, Response, status

from backend.config import settings


_LOCAL_ORIGINS = (
    "http://localhost:5173",
    "http://localhost:4173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
)


def allowed_origins() -> list[str]:
    """Return the exact explicit origins accepted by CORS and cookie CSRF checks."""
    origins = [] if settings.app_environment == "production" else list(_LOCAL_ORIGINS)
    frontend_url = settings.frontend_url or os.getenv("FRONTEND_URL", "")
    if frontend_url and frontend_url not in origins:
        origins.append(frontend_url)
    if frontend_url.startswith("https://"):
        www_origin = frontend_url.replace("https://", "https://www.", 1)
        if www_origin not in origins:
            origins.append(www_origin)
    return origins


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
    return request.cookies.get(settings.session_cookie_name)


def session_cookie_present(request: Request) -> bool:
    return settings.session_cookie_name in request.cookies


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
    """Apply a narrow CSRF boundary to cookie-authenticated state changes."""
    origin = request.headers.get("origin")
    if origin not in allowed_origins():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origin not allowed",
        )
