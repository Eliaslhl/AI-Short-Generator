"""remove_unique_constraint_email_confirmation_tokens_email

Revision ID: remove_email_unique_constraint
Revises: 87c202bdd72d
Create Date: 2026-04-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_email_unique_constraint'
down_revision: Union[str, Sequence[str], None] = '87c202bdd72d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove unique constraint from email_confirmation_tokens.email"""
    # Drop unique constraint if it exists (PostgreSQL)
    with op.batch_alter_table('email_confirmation_tokens', schema=None) as batch_op:
        batch_op.drop_constraint('email_confirmation_tokens_email_key', type_='unique')
        # Note: Index ix_email_confirmation_tokens_email may already exist
        # so we don't recreate it


def downgrade() -> None:
    """Restore unique constraint on email_confirmation_tokens.email"""
    with op.batch_alter_table('email_confirmation_tokens', schema=None) as batch_op:
        # Note: We don't need to drop the index as it will be replaced by the unique constraint
        batch_op.create_unique_constraint('email_confirmation_tokens_email_key', ['email'])
