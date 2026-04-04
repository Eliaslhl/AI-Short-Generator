"""fix_email_unique_constraint_migration

Revision ID: 20260404_fix_email_unique_constraint
Revises: remove_email_unique_constraint
Create Date: 2026-04-04 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260404_fix_email_unique_constraint'
down_revision: Union[str, Sequence[str], None] = 'remove_email_unique_constraint'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure unique constraint is removed if the previous migration failed"""
    # This migration is a safety net in case the previous migration failed partially
    # We'll try to drop the constraint if it still exists
    try:
        with op.batch_alter_table('email_confirmation_tokens', schema=None) as batch_op:
            batch_op.drop_constraint('email_confirmation_tokens_email_key', type_='unique')
    except Exception:
        # Constraint might already be dropped
        pass


def downgrade() -> None:
    """Restore unique constraint"""
    try:
        with op.batch_alter_table('email_confirmation_tokens', schema=None) as batch_op:
            batch_op.create_unique_constraint('email_confirmation_tokens_email_key', ['email'])
    except Exception:
        # Constraint might already exist
        pass
