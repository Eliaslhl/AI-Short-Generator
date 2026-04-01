"""
EMERGENCY HOTFIX: Create or fix plan ENUM type + cast string to enum

This migration ensures the 'plan' ENUM type exists and is properly configured.
PostgreSQL requires explicit casting when inserting enum values from strings.

Revision ID: rev20260401_emergency_enum_fix
Revises: rev20260330b
Create Date: 2026-04-01
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'rev20260401_emergency_enum_fix'
down_revision = 'rev20260401_fix_plan'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    1. Create the 'plan' ENUM type if it doesn't exist
    2. Add server default to users.plan column
    3. Ensure the column accepts enum values
    """
    conn = op.get_bind()
    
    # Step 1: Create enum type if missing
    op.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'plan') THEN
                CREATE TYPE plan AS ENUM ('free', 'standard', 'pro', 'proplus');
            END IF;
        END$$;
    """))
    
    # Step 2: Ensure users.plan has the correct type
    # If the column exists but has wrong type, we need to fix it
    op.execute(text("""
        DO $$
        BEGIN
            -- Check if users table exists and plan column exists
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'plan'
            ) THEN
                -- Attempt to set the correct type and default
                -- Use USING clause to cast existing text values to enum
                EXECUTE 'ALTER TABLE users ALTER COLUMN plan TYPE plan USING plan::text::plan';
            ELSE
                -- If plan column doesn't exist, create it
                EXECUTE 'ALTER TABLE users ADD COLUMN plan plan DEFAULT ''free''::plan NOT NULL';
            END IF;
        END$$;
    """))
    
    # Step 3: Ensure default is set
    op.execute(text("""
        ALTER TABLE users
        ALTER COLUMN plan SET DEFAULT 'free'::plan;
    """))


def downgrade() -> None:
    """Downgrade: remove default from plan column"""
    op.execute(text("""
        ALTER TABLE users
        ALTER COLUMN plan DROP DEFAULT;
    """))
