#!/usr/bin/env python3
"""
Inspect the production database to check schema status
"""
import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import text, inspect, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
if not DATABASE_URL:
    print("❌ DATABASE_URL not set!")
    exit(1)

async def main():
    print(f"📡 Connecting to: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'unknown'}")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # 1. Check if ENUM type exists
        print("\n1️⃣  Checking ENUM type 'plan'...")
        result = await conn.execute(
            text("SELECT typname FROM pg_type WHERE typname = 'plan'")
        )
        enum_type = result.scalar()
        if enum_type:
            print(f"   ✅ ENUM type 'plan' exists")
            # List enum values
            result = await conn.execute(
                text("SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'plan')")
            )
            values = [row[0] for row in result.fetchall()]
            print(f"   📋 Enum values: {values}")
        else:
            print("   ❌ ENUM type 'plan' DOES NOT EXIST")
        
        # 2. Check if users table exists
        print("\n2️⃣  Checking 'users' table...")
        result = await conn.execute(
            text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='users')")
        )
        table_exists = result.scalar()
        if table_exists:
            print("   ✅ users table exists")
            
            # Check column types
            result = await conn.execute(
                text("""
                SELECT column_name, data_type, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY ordinal_position
                """)
            )
            columns = result.fetchall()
            print(f"   📋 Columns ({len(columns)}):")
            for col_name, data_type, default, nullable in columns:
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                default_str = f"DEFAULT {default}" if default else ""
                print(f"      - {col_name}: {data_type} {nullable_str} {default_str}")
            
            # Specifically check plan column
            result = await conn.execute(
                text("""
                SELECT data_type, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'plan'
                """)
            )
            plan_col = result.fetchone()
            if plan_col:
                print(f"\n   🎯 'plan' column details:")
                print(f"      - Type: {plan_col[0]}")
                print(f"      - Default: {plan_col[1]}")
                print(f"      - Nullable: {plan_col[2]}")
            else:
                print(f"   ❌ 'plan' column DOES NOT EXIST")
            
            # Check row count
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            print(f"   📊 Total rows: {count}")
        else:
            print("   ❌ users table DOES NOT EXIST")
        
        # 3. Check alembic_version
        print("\n3️⃣  Checking Alembic migrations...")
        result = await conn.execute(
            text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='alembic_version')")
        )
        alembic_exists = result.scalar()
        if alembic_exists:
            result = await conn.execute(
                text("SELECT version_num FROM alembic_version ORDER BY version_num")
            )
            versions = [row[0] for row in result.fetchall()]
            print(f"   ✅ alembic_version table exists with {len(versions)} migrations")
            for v in versions:
                print(f"      - {v}")
        else:
            print("   ❌ alembic_version table DOES NOT EXIST")
        
        # 4. Check for any other types or constraints
        print("\n4️⃣  Checking constraints on 'users' table...")
        result = await conn.execute(
            text("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = 'users'
            """)
        )
        constraints = result.fetchall()
        if constraints:
            for name, ctype in constraints:
                print(f"   - {name}: {ctype}")
        else:
            print("   (no constraints found)")
        
        # 5. Try a simple query
        print("\n5️⃣  Testing simple queries...")
        try:
            result = await conn.execute(text("SELECT 1"))
            print("   ✅ Simple SELECT works")
        except Exception as e:
            print(f"   ❌ Simple SELECT failed: {e}")
        
        try:
            result = await conn.execute(text("SELECT * FROM users LIMIT 1"))
            print("   ✅ SELECT from users works")
        except Exception as e:
            print(f"   ❌ SELECT from users failed: {e}")
    
    await engine.dispose()
    print("\n✅ Inspection complete!")

if __name__ == "__main__":
    asyncio.run(main())
