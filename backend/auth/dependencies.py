"""
auth/dependencies.py – FastAPI dependencies for authenticated routes.
"""

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.user import User
from backend.auth.origin_policy import require_trusted_origin_for_cookie_auth
from backend.auth.session_cookie import (
    read_session_cookie,
    reject_ambiguous_session_cookie,
    session_cookie_present,
)
from backend.services.session_service import session_service

def _authentication_failed() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )


async def resolve_user_from_session_cookie(request: Request, db: AsyncSession) -> User:
    """Resolve a cookie session or return one opaque authentication failure."""
    auth_session = await session_service.get_valid_session(db, read_session_cookie(request))
    if auth_session is None or auth_session.user is None or not auth_session.user.is_active:
        raise _authentication_failed()
    return auth_session.user


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve an active user exclusively from one opaque session cookie."""
    reject_ambiguous_session_cookie(request)
    if not session_cookie_present(request):
        raise _authentication_failed()
    user = await resolve_user_from_session_cookie(request, db)
    require_trusted_origin_for_cookie_auth(request)
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
