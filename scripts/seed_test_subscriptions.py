#!/usr/bin/env python3
"""scripts/seed_test_subscriptions.py

Creates test user accounts for YouTube, Twitch and Combo subscriptions.
Idempotent: updates existing users if present.

Usage:
    python scripts/seed_test_subscriptions.py

Credentials created:
  youtube.standard@test.com    / Test1234!
  youtube.pro@test.com         / Test1234!
  twitch.standard@test.com     / Test1234!
  twitch.pro@test.com          / Test1234!
  combo.pro@test.com           / Test1234!

Notes:
- Sets platform-specific fields: plan_youtube / plan_twitch / subscription_type
- Marks accounts as is_active and is_verified
"""

import asyncio
import sys
import os

# allow importing backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import select
from backend.database import AsyncSessionLocal, create_tables
from backend.models.user import Plan, User

TEST_ACCOUNTS = [
    # YouTube plans
    {
        "email": "test.youtube.free@test.com",
        "password": "Test1234!",
        "full_name": "YT Free",
        "platform": "youtube",
        "plan_youtube": Plan.FREE,
        "plan_twitch": None,
        "subscription_type": "youtube",
    },
    {
        "email": "test.youtube.standard@test.com",
        "password": "Test1234!",
        "full_name": "YT Standard",
        "platform": "youtube",
        "plan_youtube": Plan.STANDARD,
        "plan_twitch": None,
        "subscription_type": "youtube",
    },
    {
        "email": "test.youtube.pro@test.com",
        "password": "Test1234!",
        "full_name": "YT Pro",
        "platform": "youtube",
        "plan_youtube": Plan.PRO,
        "plan_twitch": None,
        "subscription_type": "youtube",
    },
    {
        "email": "test.youtube.proplus@test.com",
        "password": "Test1234!",
        "full_name": "YT Pro+",
        "platform": "youtube",
        "plan_youtube": Plan.PROPLUS,
        "plan_twitch": None,
        "subscription_type": "youtube",
    },
    # Twitch plans
    {
        "email": "test.twitch.free@test.com",
        "password": "Test1234!",
        "full_name": "Twitch Free",
        "platform": "twitch",
        "plan_youtube": None,
        "plan_twitch": Plan.FREE,
        "subscription_type": "twitch",
    },
    {
        "email": "test.twitch.standard@test.com",
        "password": "Test1234!",
        "full_name": "Twitch Standard",
        "platform": "twitch",
        "plan_youtube": None,
        "plan_twitch": Plan.STANDARD,
        "subscription_type": "twitch",
    },
    {
        "email": "test.twitch.pro@test.com",
        "password": "Test1234!",
        "full_name": "Twitch Pro",
        "platform": "twitch",
        "plan_youtube": None,
        "plan_twitch": Plan.PRO,
        "subscription_type": "twitch",
    },
    {
        "email": "test.twitch.proplus@test.com",
        "password": "Test1234!",
        "full_name": "Twitch Pro+",
        "platform": "twitch",
        "plan_youtube": None,
        "plan_twitch": Plan.PROPLUS,
        "subscription_type": "twitch",
    },
    # Combo plans
    {
        "email": "test.combo.standard@test.com",
        "password": "Test1234!",
        "full_name": "Combo Standard",
        "platform": "combo",
        "plan_youtube": Plan.STANDARD,
        "plan_twitch": Plan.STANDARD,
        "subscription_type": "combo",
    },
    {
        "email": "test.combo.pro@test.com",
        "password": "Test1234!",
        "full_name": "Combo Pro",
        "platform": "combo",
        "plan_youtube": Plan.PRO,
        "plan_twitch": Plan.PRO,
        "subscription_type": "combo",
    },
    {
        "email": "test.combo.proplus@test.com",
        "password": "Test1234!",
        "full_name": "Combo Pro+",
        "platform": "combo",
        "plan_youtube": Plan.PROPLUS,
        "plan_twitch": Plan.PROPLUS,
        "subscription_type": "combo",
    },
]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def seed():
    await create_tables()

    async with AsyncSessionLocal() as session:
        for account in TEST_ACCOUNTS:
            result = await session.execute(select(User).where(User.email == account["email"]))
            existing = result.scalar_one_or_none()

            if existing:
                # update platform-specific plan fields
                if account.get("plan_youtube") is not None:
                    existing.plan_youtube = account["plan_youtube"]
                    # initialize youtube counters/reset date so limits apply
                    existing.youtube_generations_month = 0
                    existing.youtube_plan_reset_date = datetime.now(timezone.utc)
                if account.get("plan_twitch") is not None:
                    existing.plan_twitch = account["plan_twitch"]
                    # initialize twitch counters/reset date so limits apply
                    existing.twitch_generations_month = 0
                    existing.twitch_plan_reset_date = datetime.now(timezone.utc)
                existing.subscription_type = account["subscription_type"]
                existing.is_active = True
                existing.is_verified = True
                print(f"  ↻  {account['email']}  (already exists, updated platform plans)")
            else:
                user = User(
                    email=account["email"],
                    hashed_password=hash_password(account["password"]),
                    full_name=account["full_name"],
                    is_active=True,
                    is_verified=True,
                    plan=Plan.FREE,
                    plan_youtube=account.get("plan_youtube") or Plan.FREE,
                    plan_twitch=account.get("plan_twitch") or Plan.FREE,
                    # initialize monthly counters and reset dates so limits apply immediately
                    youtube_generations_month=0,
                    youtube_plan_reset_date=datetime.now(timezone.utc),
                    twitch_generations_month=0,
                    twitch_plan_reset_date=datetime.now(timezone.utc),
                    subscription_type=account.get("subscription_type"),
                )
                session.add(user)
                print(f"  ✓  {account['email']}  platform={account['platform']} plan_youtube={user.plan_youtube} plan_twitch={user.plan_twitch}")

        await session.commit()

    print("\n✅ Done! Test subscription accounts ready:")
    print("─" * 60)
    print(f"  {'Email':<35} {'Password':<12} Platform  YT-plan  TW-plan  subscription_type")
    print("─" * 60)
    for a in TEST_ACCOUNTS:
        yt = a.get("plan_youtube") or '-' 
        tw = a.get("plan_twitch") or '-'
        print(f"  {a['email']:<35} {a['password']:<12} {a['platform']:<8} {yt:<7} {tw:<7} {a['subscription_type']}")
    print("─" * 60)


if __name__ == '__main__':
    asyncio.run(seed())
