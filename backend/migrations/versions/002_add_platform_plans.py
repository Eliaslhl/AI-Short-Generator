"""Add YouTube and Twitch separated plans to User model.

Revision ID: 002_add_platform_plans
Revises: 001_initial
Create Date: 2026-03-28 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_platform_plans'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        # YouTube plan and quota
        batch_op.add_column(
            sa.Column('plan_youtube', sa.Enum('free', 'standard', 'pro', 'proplus'), nullable=True, server_default='free')
        )
        batch_op.add_column(
            sa.Column('youtube_generations_month', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('youtube_plan_reset_date', sa.DateTime(timezone=True), nullable=True)
        )
        
        # Twitch plan and quota
        batch_op.add_column(
            sa.Column('plan_twitch', sa.Enum('free', 'standard', 'pro', 'proplus'), nullable=True, server_default='free')
        )
        batch_op.add_column(
            sa.Column('twitch_generations_month', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('twitch_plan_reset_date', sa.DateTime(timezone=True), nullable=True)
        )
        
        # Subscription type and second Stripe subscription
        batch_op.add_column(
            sa.Column('subscription_type', sa.String(50), nullable=True, server_default='none')
        )
        batch_op.add_column(
            sa.Column('stripe_subscription_id_twitch', sa.String(255), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('stripe_subscription_id_twitch')
        batch_op.drop_column('subscription_type')
        batch_op.drop_column('twitch_plan_reset_date')
        batch_op.drop_column('twitch_generations_month')
        batch_op.drop_column('plan_twitch')
        batch_op.drop_column('youtube_plan_reset_date')
        batch_op.drop_column('youtube_generations_month')
        batch_op.drop_column('plan_youtube')
