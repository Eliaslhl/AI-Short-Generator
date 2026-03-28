#!/usr/bin/env python3
"""Rotate test account passwords to 24-character random secrets.

Usage:
    python scripts/rotate_test_passwords.py

This will find all users whose email starts with 'test.' or 'test@' or contains 'test.' and
set a new random 24-character password for each. It prints the new credentials to stdout.
"""
import os
import sys
import secrets

# Ensure repo import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import bcrypt
from sqlalchemy import select
from backend.database import AsyncSessionLocal, create_tables
from backend.models.user import User

TARGET_PREFIXES = ['test.', 'test@', 'test.youtube', 'test.twitch', 'test.combo', 'test+']

async def rotate():
    await create_tables()
    updated = []
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        # fetch id and email as raw rows to avoid ORM Enum mapping issues
        res = await session.execute(text("SELECT id, email FROM users WHERE email LIKE :p"), {"p": "%test%"})
        rows = res.fetchall()
        for row in rows:
            user_id = row[0]
            email = row[1]
            pwd = secrets.token_urlsafe(32)[:24]
            hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
            await session.execute(text("UPDATE users SET hashed_password = :h WHERE id = :id"), {"h": hashed, "id": user_id})
            updated.append((email, pwd))
        await session.commit()
    if updated:
        print('\nUpdated test account passwords:')
        print('─' * 60)
        print(f"  {'Email':<40} {'Password (24 chars)'}")
        print('─' * 60)
        for em, pw in updated:
            print(f"  {em:<40} {pw}")
        print('─' * 60)
    else:
        print('No test accounts found to update.')

if __name__ == '__main__':
    import asyncio
    asyncio.run(rotate())
