# Fichier supprimé pour régénération du schéma initial

"""add youtube/twitch plan columns to users

Revision ID: 20260328_add_youtube_twitch_plan_columns
Revises: 3b526031a41b
Create Date: 2026-03-28
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260328_add_youtube_twitch_plan_columns'
down_revision = '3b526031a41b'
branch_labels = None
depends_on = None

# plan enum will be created idempotently via raw SQL in upgrade()


def upgrade():
    # Make this migration idempotent in production: create enum if missing, then add columns using
    # ALTER TABLE ... ADD COLUMN IF NOT EXISTS so repeated runs don't fail with DuplicateColumnError.
    # Create enum type if not exists (Postgres-only)
    op.execute(text("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'plan') THEN
            CREATE TYPE plan AS ENUM ('free','standard','pro','proplus');
        END IF;
    END$$;
    """))

    # Add columns idempotently
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_youtube plan;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_twitch plan;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_type varchar(50);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS youtube_generations_month integer DEFAULT 0;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS youtube_plan_reset_date timestamptz;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS twitch_generations_month integer DEFAULT 0;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS twitch_plan_reset_date timestamptz;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id_twitch varchar(255);")


def downgrade():
    # Safe rollback with IF EXISTS
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS stripe_subscription_id_twitch;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS twitch_plan_reset_date;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS twitch_generations_month;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS youtube_plan_reset_date;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS youtube_generations_month;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS subscription_type;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS plan_twitch;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS plan_youtube;")
