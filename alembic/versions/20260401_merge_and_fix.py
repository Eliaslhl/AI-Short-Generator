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
    # Create ENUM type if it doesn't exist
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_type WHERE typname = 'plan'
        ) THEN
            CREATE TYPE plan AS ENUM ('free', 'standard', 'pro', 'proplus');
        END IF;
    END
    $$;
    """)
    
    # Ensure plan column exists with correct type and default
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'plan'
        ) THEN
            ALTER TABLE users ADD COLUMN plan plan DEFAULT 'free'::plan NOT NULL;
        ELSE
            -- Column exists, ensure it's the right type and has default
            ALTER TABLE users ALTER COLUMN plan SET DEFAULT 'free'::plan;
            ALTER TABLE users ALTER COLUMN plan SET NOT NULL;
        END IF;
    END
    $$;
    """)
    
    # Ensure is_active has proper default
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
    """Downgrade schema."""
    pass
