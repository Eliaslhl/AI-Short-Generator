"""
merge heads to resolve branching in versions

Revision ID: 20260328_merge_heads_86193de34e59
Revises: 86193de34e59, 20260328_add_youtube_twitch_limit_overrides
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260328_merge_heads_86193de34e59'
down_revision = ('86193de34e59', '20260328_add_youtube_twitch_limit_overrides')
branch_labels = None
depends_on = None


def upgrade():
    # Merge migration - no DB changes, just unify heads.
    pass


def downgrade():
    pass
