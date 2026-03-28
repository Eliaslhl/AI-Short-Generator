"""
platform_dependencies.py – Platform-specific auth checks for YouTube and Twitch.

Provides dependencies to check if a user can generate content on YouTube or Twitch,
respecting the new dual-plan model (plan_youtube and plan_twitch).
"""

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.user import User
from backend.auth.dependencies import get_current_user


def _needs_monthly_reset(reset_date: datetime | None) -> bool:
    """Check if we're in a new month compared to reset_date."""
    if not reset_date:
        return True
    now = datetime.now(timezone.utc)
    if reset_date.tzinfo is None:
        reset_date = reset_date.replace(tzinfo=timezone.utc)
    return (now.year, now.month) > (reset_date.year, reset_date.month)


async def require_can_generate_youtube(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that checks if user can generate on YouTube.
    
    Lazy resets the monthly YouTube quota on first call after month change.
    """
    now = datetime.now(timezone.utc)

    # Lazy monthly reset
    if _needs_monthly_reset(user.youtube_plan_reset_date):
        user.youtube_generations_month = 0
        user.youtube_plan_reset_date = now
        await db.commit()
        await db.refresh(user)

    # Check quota
    youtube_limit = user.youtube_limit
    if (user.youtube_generations_month or 0) >= youtube_limit:
        plan_messages = {
            "free": "You've used your 2 free YouTube generations this month. Upgrade to Standard or Pro.",
            "standard": "You've used all 20 YouTube Standard plan generations this month.",
            "pro": "You've used all 50 YouTube Pro plan generations this month.",
            "proplus": "You've used all 100 YouTube Pro+ plan generations this month.",
        }
        plan_val = (user.plan_youtube or user.plan).value if user.plan_youtube else "free"
        message = plan_messages.get(
            plan_val,
            "Monthly YouTube generation limit reached.",
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "youtube_quota_exceeded",
                "message": message,
                "platform": "youtube",
            },
        )
    return user


async def require_can_generate_twitch(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that checks if user can generate on Twitch.
    
    Lazy resets the monthly Twitch quota on first call after month change.
    """
    now = datetime.now(timezone.utc)

    # Lazy monthly reset
    if _needs_monthly_reset(user.twitch_plan_reset_date):
        user.twitch_generations_month = 0
        user.twitch_plan_reset_date = now
        await db.commit()
        await db.refresh(user)

    # Check quota
    twitch_limit = user.twitch_limit
    if (user.twitch_generations_month or 0) >= twitch_limit:
        plan_messages = {
            "free": "You've used your 2 free Twitch generations this month. Upgrade to Standard or Pro.",
            "standard": "You've used all 20 Twitch Standard plan generations this month.",
            "pro": "You've used all 50 Twitch Pro plan generations this month.",
            "proplus": "You've used all 100 Twitch Pro+ plan generations this month.",
        }
        plan_val = (user.plan_twitch).value if user.plan_twitch else "free"
        message = plan_messages.get(
            plan_val,
            "Monthly Twitch generation limit reached.",
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "twitch_quota_exceeded",
                "message": message,
                "platform": "twitch",
            },
        )
    return user


# Backward compatibility: keep the old require_can_generate pointing to YouTube
require_can_generate = require_can_generate_youtube
