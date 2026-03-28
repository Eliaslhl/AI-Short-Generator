"""
migrate_users_to_dual_plans.py – Migration script for existing users.

Migrates users from the legacy single-plan model (plan) to the new dual-plan model
(plan_youtube and plan_twitch).

Usage:
    python -m backend.scripts.migrate_users_to_dual_plans
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User, Plan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_users():
    """Migrate existing users to dual-plan model."""
    from backend.database import SessionLocal  # Import here to avoid circular deps
    
    async with SessionLocal() as session:
        # Get all users
        result = await session.execute(select(User))
        users = result.scalars().all()
        logger.info(f"Found {len(users)} users to migrate")

        updated = 0
        for user in users:
            # If plan_youtube is not set, use legacy plan value
            if not user.plan_youtube or user.plan_youtube.value == "free":
                user.plan_youtube = user.plan or Plan.FREE
                logger.info(
                    f"Set plan_youtube={user.plan_youtube} for {user.email} "
                    f"(was plan={user.plan})"
                )
                updated += 1

            # Initialize Twitch plan to FREE by default
            if not user.plan_twitch:
                user.plan_twitch = Plan.FREE
                logger.info(f"Set plan_twitch=FREE for {user.email}")

            # Initialize reset dates if not set
            if not user.youtube_plan_reset_date:
                user.youtube_plan_reset_date = datetime.now(timezone.utc)
            if not user.twitch_plan_reset_date:
                user.twitch_plan_reset_date = datetime.now(timezone.utc)

            # Set default subscription_type
            if not user.subscription_type:
                # Infer from legacy plan: if they have a paid plan, it's YouTube
                if user.plan and user.plan != Plan.FREE:
                    user.subscription_type = "youtube"
                else:
                    user.subscription_type = "none"

            # Initialize quota counters
            if user.youtube_generations_month is None:
                user.youtube_generations_month = user.generations_this_month or 0
            if user.twitch_generations_month is None:
                user.twitch_generations_month = 0

        # Commit changes
        await session.commit()
        logger.info(f"Migration complete: updated {updated} users")


async def main():
    """Run the migration."""
    try:
        await migrate_users()
        logger.info("✅ Migration successful")
    except Exception:
        logger.exception("❌ Migration failed")
        raise


if __name__ == "__main__":
    asyncio.run(main())
