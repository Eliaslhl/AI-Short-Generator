"""
idempotent: add youtube/twitch plan and override columns

Revision ID: 20260329_idempotent_add_plan_and_override_columns
Revises: 0831864a2940
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260329_idempotent_add_plan_and_override_columns'
down_revision = '0831864a2940'
branch_labels = None
depends_on = None


def _column_exists(conn, table: str, column: str) -> bool:
    dialect = conn.engine.dialect.name
    if dialect in ("postgresql", "postgres"):
        q = text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column LIMIT 1")
        return conn.execute(q, {"table": table, "column": column}).first() is not None
    else:
        # sqlite
        q = text("PRAGMA table_info(%s)" % table)
        rows = conn.execute(q).fetchall()
        for r in rows:
            # pragma returns (cid,name,type,notnull,dflt_value,pk)
            if r[1] == column:
                return True
        return False


def _ensure_plan_enum(conn):
    # Ensure the 'plan' enum exists in Postgres
    dialect = conn.engine.dialect.name
    if dialect in ("postgresql", "postgres"):
        conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'plan') THEN
                CREATE TYPE plan AS ENUM ('free','standard','pro','proplus');
            END IF;
        END$$;
        """))


def upgrade() -> None:
    conn = op.get_bind()
    _ensure_plan_enum(conn)

    # Add plan columns if they don't exist
    if not _column_exists(conn, 'users', 'plan_youtube'):
        op.add_column('users', sa.Column('plan_youtube', postgresql.ENUM('free','standard','pro','proplus', name='plan'), nullable=True))
    if not _column_exists(conn, 'users', 'plan_twitch'):
        op.add_column('users', sa.Column('plan_twitch', postgresql.ENUM('free','standard','pro','proplus', name='plan'), nullable=True))

    # Other plan related columns
    if not _column_exists(conn, 'users', 'subscription_type'):
        op.add_column('users', sa.Column('subscription_type', sa.String(length=50), nullable=True))
    if not _column_exists(conn, 'users', 'youtube_generations_month'):
        op.add_column('users', sa.Column('youtube_generations_month', sa.Integer(), nullable=True, server_default='0'))
    if not _column_exists(conn, 'users', 'youtube_plan_reset_date'):
        op.add_column('users', sa.Column('youtube_plan_reset_date', sa.DateTime(timezone=True), nullable=True))
    if not _column_exists(conn, 'users', 'twitch_generations_month'):
        op.add_column('users', sa.Column('twitch_generations_month', sa.Integer(), nullable=True, server_default='0'))
    if not _column_exists(conn, 'users', 'twitch_plan_reset_date'):
        op.add_column('users', sa.Column('twitch_plan_reset_date', sa.DateTime(timezone=True), nullable=True))
    if not _column_exists(conn, 'users', 'stripe_subscription_id_twitch'):
        op.add_column('users', sa.Column('stripe_subscription_id_twitch', sa.String(length=255), nullable=True))

    # Add the integer override columns
    if not _column_exists(conn, 'users', 'youtube_limit_override'):
        op.add_column('users', sa.Column('youtube_limit_override', sa.Integer(), nullable=True))
    if not _column_exists(conn, 'users', 'twitch_limit_override'):
        op.add_column('users', sa.Column('twitch_limit_override', sa.Integer(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    # Drop columns only if they exist
    if _column_exists(conn, 'users', 'twitch_limit_override'):
        op.drop_column('users', 'twitch_limit_override')
    if _column_exists(conn, 'users', 'youtube_limit_override'):
        op.drop_column('users', 'youtube_limit_override')

    if _column_exists(conn, 'users', 'stripe_subscription_id_twitch'):
        op.drop_column('users', 'stripe_subscription_id_twitch')
    if _column_exists(conn, 'users', 'twitch_plan_reset_date'):
        op.drop_column('users', 'twitch_plan_reset_date')
    if _column_exists(conn, 'users', 'twitch_generations_month'):
        op.drop_column('users', 'twitch_generations_month')
    if _column_exists(conn, 'users', 'youtube_plan_reset_date'):
        op.drop_column('users', 'youtube_plan_reset_date')
    if _column_exists(conn, 'users', 'youtube_generations_month'):
        op.drop_column('users', 'youtube_generations_month')
    if _column_exists(conn, 'users', 'subscription_type'):
        op.drop_column('users', 'subscription_type')
    if _column_exists(conn, 'users', 'plan_twitch'):
        op.drop_column('users', 'plan_twitch')
    if _column_exists(conn, 'users', 'plan_youtube'):
        op.drop_column('users', 'plan_youtube')
