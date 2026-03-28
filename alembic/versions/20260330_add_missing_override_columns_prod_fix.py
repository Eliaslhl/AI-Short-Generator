"""
Add missing youtube/twitch integer override columns (safe, idempotent)

Revision ID: 20260330_add_missing_override_columns_prod_fix
Revises: 20260329_idempotent_add_plan_and_override_columns
Create Date: 2026-03-30
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '20260330_add_missing_override_columns_prod_fix'
down_revision = '20260329_idempotent_add_plan_and_override_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw SQL with IF NOT EXISTS to be robust in production
    op.execute("""
    ALTER TABLE users
      ADD COLUMN IF NOT EXISTS youtube_limit_override integer;
    ALTER TABLE users
      ADD COLUMN IF NOT EXISTS twitch_limit_override integer;
    """)


def downgrade() -> None:
    # Safe rollback
    op.execute("""
    ALTER TABLE users
      DROP COLUMN IF EXISTS twitch_limit_override;
    ALTER TABLE users
      DROP COLUMN IF EXISTS youtube_limit_override;
    """)
