"""
add youtube/twitch limit override columns to users

Revision ID: rev20260328b
Revises: rev20260328a
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'rev20260328b'
down_revision = 'rev20260328a'
branch_labels = None
depends_on = None


def upgrade():
    # Add integer override columns for per-user limits
    op.add_column('users', sa.Column('youtube_limit_override', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('twitch_limit_override', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('users', 'twitch_limit_override')
    op.drop_column('users', 'youtube_limit_override')
