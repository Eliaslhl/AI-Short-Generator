#!/usr/bin/env python3
"""
Reset test accounts to remove old overrides and reset counters.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select, update
from backend.database import AsyncSessionLocal
from backend.models.user import User, Plan

TEST_EMAILS = [
    "test.youtube.free@test.com",
    "test.youtube.standard@test.com",
    "test.youtube.pro@test.com",
    "test.youtube.proplus@test.com",
    "test.twitch.free@test.com",
    "test.twitch.standard@test.com",
    "test.twitch.pro@test.com",
    "test.twitch.proplus@test.com",
    "test.combo.standard@test.com",
    "test.combo.pro@test.com",
    "test.combo.proplus@test.com",
]

async def reset_test_accounts():
    """Remove overrides and reset generation counters for all test accounts."""
    async with AsyncSessionLocal() as session:
        print("\n" + "=" * 100)
        print("RESETTING TEST ACCOUNTS - REMOVING OVERRIDES & RESETTING COUNTERS")
        print("=" * 100 + "\n")
        
        for email in TEST_EMAILS:
            # Get user
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ {email:<40} NOT FOUND")
                continue
            
            # Before
            print(f"📝 Updating {email}")
            print(f"   BEFORE: youtube_limit_override={user.youtube_limit_override}, twitch_limit_override={user.twitch_limit_override}")
            print(f"           youtube_generations_month={user.youtube_generations_month}, twitch_generations_month={user.twitch_generations_month}")
            
            # Reset overrides to None (will use plan-based limits)
            user.youtube_limit_override = None
            user.twitch_limit_override = None
            
            # Reset counters to 0
            user.youtube_generations_month = 0
            user.twitch_generations_month = 0
            
            # After
            print(f"   AFTER:  youtube_limit_override={user.youtube_limit_override}, twitch_limit_override={user.twitch_limit_override}")
            print(f"           youtube_generations_month={user.youtube_generations_month}, twitch_generations_month={user.twitch_generations_month}")
            print(f"           → YouTube limit: {user.youtube_limit}, Twitch limit: {user.twitch_limit}")
            print()
        
        # Commit all changes
        await session.commit()
        print("=" * 100)
        print("✅ ALL TEST ACCOUNTS RESET SUCCESSFULLY")
        print("=" * 100 + "\n")

if __name__ == "__main__":
    asyncio.run(reset_test_accounts())
