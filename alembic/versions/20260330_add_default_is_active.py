"""
Add default true for users.is_active (idempotent)

Revision ID: rev20260330b
Revises: rev20260330a
Create Date: 2026-03-29
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'rev20260330b'
down_revision = 'rev20260330a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgcrypto exists (safe if already present)
    # and set a default of TRUE for is_active to avoid future NotNullViolation
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("ALTER TABLE users ALTER COLUMN is_active SET DEFAULT true;")


def downgrade() -> None:
    # Remove the default only (keep extension if other parts use it)
    op.execute("ALTER TABLE users ALTER COLUMN is_active DROP DEFAULT;")
