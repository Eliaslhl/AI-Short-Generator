"""
auth/dependencies.py – FastAPI dependencies for authenticated routes.
"""

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.user import User
from backend.auth.jwt import decode_token

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the Bearer token, return the User object."""
    payload = decode_token(credentials.credentials)
    user_id: str = payload["sub"]

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

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
