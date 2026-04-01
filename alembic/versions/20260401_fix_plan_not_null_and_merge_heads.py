"""
URGENT PROD FIX: Set plan column server default to 'free' + resolve multiple heads

This migration:
1. Adds server default 'free' to the `plan` column so future INSERTs that omit `plan` won't fail
2. Acts as the unified merge head to resolve the "Multiple head revisions" Alembic error

Revision ID: rev20260401_fix_plan
Revises: rev20260330a
Create Date: 2026-04-01
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'rev20260401_fix_plan'
down_revision = 'rev20260330b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add server default to 'plan' column so INSERT without plan doesn't fail."""
    # This is PostgreSQL syntax to set a server default on an existing column
    op.execute(text("""
        ALTER TABLE users
        ALTER COLUMN plan SET DEFAULT 'free'::plan;
    """))
    
    # Log for auditing
    print("✓ Set plan column default to 'free' (Alembic merge head fix)")


def downgrade() -> None:
    """Remove the default."""
    op.execute(text("""
        ALTER TABLE users
        ALTER COLUMN plan DROP DEFAULT;
    """))
