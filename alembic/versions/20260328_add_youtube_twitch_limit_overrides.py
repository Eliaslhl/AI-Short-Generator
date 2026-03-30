"""
NO-OP migration placeholder

This migration file previously attempted to add `youtube_limit_override` and
`twitch_limit_override` columns in a non-idempotent way which conflicted with
an idempotent migration introduced later. That caused failures when Alembic
re-ran migrations against databases where columns already existed.

Instead of deleting the revision file (which can be dangerous when a
revision may already exist in some databases), we keep a no-op migration with
the same revision id so that Alembic's history remains consistent and future
deploys won't attempt the conflicting ALTER again.

Revision ID: rev20260328b
Revises: rev20260328a
Create Date: 2026-03-28
"""

# revision identifiers, used by Alembic.
revision = 'rev20260328b'
down_revision = 'rev20260328a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # intentionally no-op: columns are handled idempotently in
    # 20260329_idempotent_add_plan_and_override_columns.py
    return


def downgrade() -> None:
    # no-op downgrade
    return
