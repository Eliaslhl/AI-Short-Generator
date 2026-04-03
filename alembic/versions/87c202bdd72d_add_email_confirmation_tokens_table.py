"""add_email_confirmation_tokens_table

Revision ID: 87c202bdd72d
Revises: 20260401_merge_and_fix
Create Date: 2026-04-03 23:55:06.688425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '87c202bdd72d'
down_revision: Union[str, Sequence[str], None] = '20260401_merge_and_fix'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'email_confirmation_tokens',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('token', sa.String(64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('token'),
    )
    op.create_index('ix_email_confirmation_tokens_email', 'email_confirmation_tokens', ['email'], unique=True)
    op.create_index('ix_email_confirmation_tokens_token', 'email_confirmation_tokens', ['token'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_email_confirmation_tokens_token', table_name='email_confirmation_tokens')
    op.drop_index('ix_email_confirmation_tokens_email', table_name='email_confirmation_tokens')
    op.drop_table('email_confirmation_tokens')
