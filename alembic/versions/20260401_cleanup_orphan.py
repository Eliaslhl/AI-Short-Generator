"""
CLEANUP: Remove orphaned migration reference from DB history

Some databases have a stale entry in alembic_version pointing to a migration
file name instead of a revision ID. This migration stamps over it.

Revision ID: rev20260401_cleanup_orphan
Revises: rev20260401_merge_all_heads
Create Date: 2026-04-01
"""

# revision identifiers, used by Alembic.
revision = 'rev20260401_cleanup_orphan'
down_revision = 'rev20260401_merge_all_heads'
branch_labels = None
depends_on = None


def upgrade():
    # This migration does nothing to the schema
    # It exists to:
    # 1. Mark that we've processed all previous migrations
    # 2. Provide a clean, single head going forward
    # 3. Allow Alembic to move past any orphaned revision entries
    pass


def downgrade():
    # No-op downgrade
    pass
