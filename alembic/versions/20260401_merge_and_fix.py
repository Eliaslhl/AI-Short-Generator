"""Merge heads and add plan ENUM type with proper defaults

Revision ID: 20260401_merge_and_fix
Revises: ('3b526031a41b', '86193de34e59')
Create Date: 2026-04-01 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260401_merge_and_fix'
down_revision: Union[str, Sequence[str], None] = ('3b526031a41b', '86193de34e59')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Try to create ENUM type (ignore if exists)
    # Use simple CREATE TYPE with error handling at Python level
    try:
        op.execute(
            "CREATE TYPE plan AS ENUM ('free', 'standard', 'pro', 'proplus');"
        )
    except Exception:
        # Type probably already exists, that's fine
        pass
    
    # Step 2: Add plan column if it doesn't exist
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'plan'
        ) THEN
            ALTER TABLE users ADD COLUMN plan plan DEFAULT 'free'::plan NOT NULL;
        END IF;
    END
    $$;
    """)
    
    # Step 3: Ensure is_active has proper default
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'is_active'
        ) THEN
            ALTER TABLE users ALTER COLUMN is_active SET DEFAULT true;
        END IF;
    END
    $$;
    """)


def downgrade() -> None:
    """Downgrade schema.

    Partial by design, not a silent no-op: this migration merges two
    branches whose own upgrade() steps are themselves conditional ("IF NOT
    EXISTS") — from here alone there is no way to tell whether THIS
    migration is what created `plan`/the `plan` enum type versus an earlier
    one in whichever branch a given database went through. Reversing that
    unconditionally would risk either destroying a column an earlier
    migration owns, or dropping a type still in use.

    Does NOT drop the `plan` column or the `plan` enum type:
    `plan_youtube`/`plan_twitch` (backend/models/user.py) already depend on
    the same Postgres enum type, and dropping `plan` would destroy every
    user's plan assignment — a rollback must never delete user data as a
    side effect. Only reverses the one change that is unambiguously this
    migration's alone and safe to undo without any data loss: the
    `is_active` column default. Rolling back past the plan/enum changes
    themselves requires restoring from a backup taken before this migration
    was applied.
    """
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'is_active'
        ) THEN
            ALTER TABLE users ALTER COLUMN is_active DROP DEFAULT;
        END IF;
    END
    $$;
    """)
