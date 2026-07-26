"""
auth/dependencies.py – FastAPI dependencies for authenticated routes.
"""

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.user import User
from backend.auth.jwt import decode_token
from backend.auth.session_cookie import read_session_cookie, session_cookie_present
from backend.services.session_service import session_service

bearer_scheme = HTTPBearer(auto_error=False)


def _authentication_failed() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _credentials_missing() -> HTTPException:
    """Preserve the existing HTTPBearer response for entirely anonymous calls."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authenticated",
    )


async def _active_user(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user if user is not None and user.is_active else None


async def resolve_user_from_bearer_token(
    credentials: HTTPAuthorizationCredentials | None, db: AsyncSession
) -> User | None:
    """Resolve an active user from the existing JWT Bearer credential."""
    if credentials is None:
        return None
    payload = decode_token(credentials.credentials)
    return await _active_user(db, payload["sub"])


async def get_current_user_from_bearer(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """JWT-only boundary for transitional endpoints that mint sessions."""
    if credentials is None:
        raise _credentials_missing()
    user = await resolve_user_from_bearer_token(credentials, db)
    if user is None:
        raise _authentication_failed()
    return user


async def resolve_user_from_session_cookie(request: Request, db: AsyncSession) -> User:
    """Resolve a cookie session or return one opaque authentication failure."""
    auth_session = await session_service.get_valid_session(db, read_session_cookie(request))
    if auth_session is None or auth_session.user is None or not auth_session.user.is_active:
        raise _authentication_failed()
    return auth_session.user


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Cookie-first dual boundary; a present invalid cookie never falls back to JWT."""
    if session_cookie_present(request):
        cookie_user = await resolve_user_from_session_cookie(request, db)
        bearer_user = await resolve_user_from_bearer_token(credentials, db)
        if bearer_user is not None and bearer_user.id != cookie_user.id:
            raise _authentication_failed()
        return cookie_user

    if credentials is None:
        raise _credentials_missing()
    user = await resolve_user_from_bearer_token(credentials, db)
    if user is None:
        raise _authentication_failed()
    return user


async def require_can_generate(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that checks (and lazily resets) the monthly generation quota."""
    now = datetime.now(timezone.utc)

    # Lazy monthly reset: if we're in a new month since last reset, clear the counter
    last_reset = user.plan_reset_date
    if last_reset.tzinfo is None:
        last_reset = last_reset.replace(tzinfo=timezone.utc)

    if (now.year, now.month) > (last_reset.year, last_reset.month):
        user.generations_this_month = 0
        user.plan_reset_date = now
        await db.commit()
        await db.refresh(user)

    if not user.can_generate:
        plan_messages = {
            "free": "You've used your 2 free generations this month. Upgrade to Standard or Pro for more.",
            "standard": "You've used all 20 of your Standard plan generations this month.",
            "pro": "You've used all 50 of your Pro plan generations this month.",
            "proplus": "You've used all 100 of your Pro+ plan generations this month.",
        }
        message = plan_messages.get(
            user.plan.value,
            "Monthly generation limit reached. Please upgrade your plan.",
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "quota_exceeded",
                "message": message,
                "upgrade_url": "/pricing",
            },
        )
    return user
