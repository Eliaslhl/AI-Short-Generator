"""Add single-use OAuth transaction state.

Revision ID: 20260726_add_oauth_transactions
Revises: 20260726_add_auth_sessions
"""
from alembic import op
import sqlalchemy as sa

revision = "20260726_add_oauth_transactions"
down_revision = "20260726_add_auth_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_transactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("redirect_uri", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_oauth_transactions_state_hash", "oauth_transactions", ["state_hash"], unique=True)
    op.create_index("ix_oauth_transactions_expires_at", "oauth_transactions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_oauth_transactions_expires_at", table_name="oauth_transactions")
    op.drop_index("ix_oauth_transactions_state_hash", table_name="oauth_transactions")
    op.drop_table("oauth_transactions")
