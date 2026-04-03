#!/usr/bin/env python3
"""
Test script to verify all seeded test accounts have correct quotas and plan fields.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select
from backend.database import AsyncSessionLocal
from backend.models.user import User, Plan

EXPECTED = {
    "test.youtube.free@test.com": {
        "plan_youtube": Plan.FREE,
        "plan_twitch": Plan.FREE,
        "subscription_type": "youtube",
        "youtube_limit": 1,  # FREE tier
        "twitch_limit": 1,   # FREE tier
    },
    "test.youtube.standard@test.com": {
        "plan_youtube": Plan.STANDARD,
        "plan_twitch": Plan.FREE,
        "subscription_type": "youtube",
        "youtube_limit": 10,
        "twitch_limit": 1,
    },
    "test.youtube.pro@test.com": {
        "plan_youtube": Plan.PRO,
        "plan_twitch": Plan.FREE,
        "subscription_type": "youtube",
        "youtube_limit": 25,
        "twitch_limit": 1,
    },
    "test.youtube.proplus@test.com": {
        "plan_youtube": Plan.PROPLUS,
        "plan_twitch": Plan.FREE,
        "subscription_type": "youtube",
        "youtube_limit": 50,
        "twitch_limit": 1,
    },
    "test.twitch.free@test.com": {
        "plan_youtube": Plan.FREE,
        "plan_twitch": Plan.FREE,
        "subscription_type": "twitch",
        "youtube_limit": 1,
        "twitch_limit": 1,
    },
    "test.twitch.standard@test.com": {
        "plan_youtube": Plan.FREE,
        "plan_twitch": Plan.STANDARD,
        "subscription_type": "twitch",
        "youtube_limit": 1,
        "twitch_limit": 10,
    },
    "test.twitch.pro@test.com": {
        "plan_youtube": Plan.FREE,
        "plan_twitch": Plan.PRO,
        "subscription_type": "twitch",
        "youtube_limit": 1,
        "twitch_limit": 25,
    },
    "test.twitch.proplus@test.com": {
        "plan_youtube": Plan.FREE,
        "plan_twitch": Plan.PROPLUS,
        "subscription_type": "twitch",
        "youtube_limit": 1,
        "twitch_limit": 50,
    },
    "test.combo.standard@test.com": {
        "plan_youtube": Plan.STANDARD,
        "plan_twitch": Plan.STANDARD,
        "subscription_type": "combo",
        "youtube_limit": 10,
        "twitch_limit": 10,
    },
    "test.combo.pro@test.com": {
        "plan_youtube": Plan.PRO,
        "plan_twitch": Plan.PRO,
        "subscription_type": "combo",
        "youtube_limit": 25,
        "twitch_limit": 25,
    },
    "test.combo.proplus@test.com": {
        "plan_youtube": Plan.PROPLUS,
        "plan_twitch": Plan.PROPLUS,
        "subscription_type": "combo",
        "youtube_limit": 50,
        "twitch_limit": 50,
    },
}

def get_generation_limit(plan, platform):
    """Determine max monthly generations based on plan and platform."""
    if plan == Plan.FREE:
        return 1
    elif plan == Plan.STANDARD:
        return 10 if platform == "youtube" else 10
    elif plan == Plan.PRO:
        return 25 if platform == "youtube" else 25
    elif plan == Plan.PROPLUS:
        return 50 if platform == "youtube" else 50
    return 1

async def test_accounts():
    async with AsyncSessionLocal() as session:
        print("\n" + "=" * 100)
        print("TEST ACCOUNT QUOTA VERIFICATION")
        print("=" * 100)
        
        all_passed = True
        for email, expected in EXPECTED.items():
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"✗ {email:<40} NOT FOUND IN DB")
                all_passed = False
                continue
            
            # Calculate limits based on plan
            youtube_limit = get_generation_limit(user.plan_youtube, "youtube")
            twitch_limit = get_generation_limit(user.plan_twitch, "twitch")
            
            errors = []
            if user.plan_youtube != expected["plan_youtube"]:
                errors.append(f"plan_youtube: {user.plan_youtube} != {expected['plan_youtube']}")
            if user.plan_twitch != expected["plan_twitch"]:
                errors.append(f"plan_twitch: {user.plan_twitch} != {expected['plan_twitch']}")
            if user.subscription_type != expected["subscription_type"]:
                errors.append(f"subscription_type: {user.subscription_type} != {expected['subscription_type']}")
            if youtube_limit != expected["youtube_limit"]:
                errors.append(f"youtube_limit: {youtube_limit} != {expected['youtube_limit']}")
            if twitch_limit != expected["twitch_limit"]:
                errors.append(f"twitch_limit: {twitch_limit} != {expected['twitch_limit']}")
            
            if errors:
                print(f"✗ {email:<40} FAILED")
                for err in errors:
                    print(f"    {err}")
                all_passed = False
            else:
                yt_plan = str(user.plan_youtube).split('.')[-1]
                tw_plan = str(user.plan_twitch).split('.')[-1]
                print(f"✓ {email:<40} YT:{yt_plan:<8} TW:{tw_plan:<8} YT-limit:{youtube_limit:<3} TW-limit:{twitch_limit:<3}")
        
        print("=" * 100)
        if all_passed:
            print("✅ ALL TESTS PASSED!")
        else:
            print("❌ SOME TESTS FAILED - see above")
        print("=" * 100 + "\n")
        
        return all_passed

if __name__ == "__main__":
    result = asyncio.run(test_accounts())
    sys.exit(0 if result else 1)
