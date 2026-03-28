# Fichier supprimé pour régénération du schéma initial

"""add youtube/twitch plan columns to users

Revision ID: 20260328_add_youtube_twitch_plan_columns
Revises: 3b526031a41b
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260328_add_youtube_twitch_plan_columns'
down_revision = '3b526031a41b'
branch_labels = None
depends_on = None

plan_enum = postgresql.ENUM('free', 'standard', 'pro', 'proplus', name='plan')

def upgrade():
    # Add new columns for YouTube/Twitch plans and quotas
    op.add_column('users', sa.Column('plan_youtube', plan_enum, nullable=True))
    op.add_column('users', sa.Column('plan_twitch', plan_enum, nullable=True))
    op.add_column('users', sa.Column('subscription_type', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('youtube_generations_month', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('youtube_plan_reset_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('twitch_generations_month', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('twitch_plan_reset_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('stripe_subscription_id_twitch', sa.String(length=255), nullable=True))

def downgrade():
    op.drop_column('users', 'stripe_subscription_id_twitch')
    op.drop_column('users', 'twitch_plan_reset_date')
    op.drop_column('users', 'twitch_generations_month')
    op.drop_column('users', 'youtube_plan_reset_date')
    op.drop_column('users', 'youtube_generations_month')
    op.drop_column('users', 'subscription_type')
    op.drop_column('users', 'plan_twitch')
    op.drop_column('users', 'plan_youtube')
