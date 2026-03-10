"""
scripts/seed_test_accounts.py
──────────────────────────────────────────────────────────────
Creates one test account per plan (free / standard / pro / pro+).
Idempotent: skips an account if the email already exists.

Usage:
    python scripts/seed_test_accounts.py

Credentials created:
    test.free@test.com       / Test1234!   → plan: free
    test.standard@test.com   / Test1234!   → plan: standard
    test.pro@test.com        / Test1234!   → plan: pro
    test.proplus@test.com    / Test1234!   → plan: proplus
"""

import asyncio
import sys
import os

# Make sure we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import bcrypt
from sqlalchemy import select
from backend.database import AsyncSessionLocal, create_tables
from backend.models.user import Plan, User

TEST_ACCOUNTS = [
    {
        "email":     "test.free@test.com",
        "password":  "Test1234!",
        "full_name": "Test Free",
        "plan":      Plan.FREE,
    },
    {
        "email":     "test.standard@test.com",
        "password":  "Test1234!",
        "full_name": "Test Standard",
        "plan":      Plan.STANDARD,
    },
    {
        "email":     "test.pro@test.com",
        "password":  "Test1234!",
        "full_name": "Test Pro",
        "plan":      Plan.PRO,
    },
    {
        "email":     "test.proplus@test.com",
        "password":  "Test1234!",
        "full_name": "Test Pro+",
        "plan":      Plan.PROPLUS,
    },
]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def seed():
    await create_tables()

    async with AsyncSessionLocal() as session:
        for account in TEST_ACCOUNTS:
            result = await session.execute(
                select(User).where(User.email == account["email"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update plan in case it changed
                existing.plan = account["plan"]
                print(f"  ↻  {account['email']}  (already exists, plan updated to {account['plan']})")
            else:
                user = User(
                    email=account["email"],
                    hashed_password=hash_password(account["password"]),
                    full_name=account["full_name"],
                    plan=account["plan"],
                    is_active=True,
                    is_verified=True,
                )
                session.add(user)
                print(f"  ✓  {account['email']}  plan={account['plan']}")

        await session.commit()

    print("\n✅ Done! Test accounts ready:")
    print("─" * 52)
    print(f"  {'Email':<30} {'Password':<12} Plan")
    print("─" * 52)
    for a in TEST_ACCOUNTS:
        print(f"  {a['email']:<30} {a['password']:<12} {a['plan']}")
    print("─" * 52)


if __name__ == "__main__":
    asyncio.run(seed())
