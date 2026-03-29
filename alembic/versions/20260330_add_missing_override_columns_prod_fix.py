"""
Add missing youtube/twitch integer override columns (safe, idempotent)

Revision ID: rev20260330a
Revises: rev20260329a
Create Date: 2026-03-30
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'rev20260330a'
down_revision = 'rev20260329a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw SQL with IF NOT EXISTS to be robust in production
    # execute statements separately because asyncpg/psycopg prepared
    # statements do not accept multiple SQL commands in one execute call
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS youtube_limit_override integer;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS twitch_limit_override integer;")


def downgrade() -> None:
    # Safe rollback
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS twitch_limit_override;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS youtube_limit_override;")
