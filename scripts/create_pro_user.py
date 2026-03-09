"""
scripts/create_pro_user.py
--------------------------
Creates (or upgrades) a test Pro user in the local SQLite database.

Usage:
    python -m scripts.create_pro_user
    python -m scripts.create_pro_user --email me@example.com --password secret123
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Make sure the project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from sqlalchemy import select

from backend.database import create_tables, AsyncSessionLocal
from backend.models.user import Plan, User

DEFAULT_EMAIL    = "pro@test.com"
DEFAULT_PASSWORD = "prouser123"
DEFAULT_NAME     = "Pro Tester"


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def seed(email: str, password: str, full_name: str) -> None:
    await create_tables()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            # Upgrade existing user to Pro
            user.plan = Plan.PRO
            user.hashed_password = _hash(password)
            user.full_name = full_name
            user.is_active = True
            user.is_verified = True
            user.generations_this_month = 0
            await session.commit()
            print(f"✅  Existing user upgraded to Pro: {email}")
        else:
            # Create brand-new Pro user
            user = User(
                email=email,
                hashed_password=_hash(password),
                full_name=full_name,
                plan=Plan.PRO,
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"✅  New Pro user created: {email}")

        print(f"   ID       : {user.id}")
        print(f"   Email    : {user.email}")
        print(f"   Password : {password}")
        print(f"   Plan     : {user.plan.value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create/upgrade a Pro test user")
    parser.add_argument("--email",    default=DEFAULT_EMAIL,    help="User email")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="User password")
    parser.add_argument("--name",     default=DEFAULT_NAME,     help="Display name")
    args = parser.parse_args()

    asyncio.run(seed(args.email, args.password, args.name))


if __name__ == "__main__":
    main()
