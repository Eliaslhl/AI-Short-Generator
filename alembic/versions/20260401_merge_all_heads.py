"""
Merge all divergent heads into single unified timeline

Revision ID: rev20260401_merge_all_heads
Revises: rev20260401_emergency_enum_fix, 3b526031a41b
Create Date: 2026-04-01
"""

# revision identifiers, used by Alembic.
revision = 'rev20260401_merge_all_heads'
down_revision = ('rev20260401_emergency_enum_fix', '3b526031a41b')
branch_labels = None
depends_on = None


def upgrade():
    # Merge migration - no DB changes, just unify heads
    pass


def downgrade():
    pass
