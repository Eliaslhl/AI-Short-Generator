"""remove_email_unique_constraint_v2

Revision ID: 20260404_remove_email_constraint
Revises: 87c202bdd72d
Create Date: 2026-04-04 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '20260404_remove_email_constraint'
down_revision: Union[str, Sequence[str], None] = '87c202bdd72d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove unique constraint from email_confirmation_tokens.email"""
    # Simply drop the constraint - it should exist from the previous migration
    op.execute('ALTER TABLE email_confirmation_tokens DROP CONSTRAINT IF EXISTS email_confirmation_tokens_email_key CASCADE')


def downgrade() -> None:
    """Restore unique constraint on email_confirmation_tokens.email"""
    op.execute('ALTER TABLE email_confirmation_tokens ADD CONSTRAINT email_confirmation_tokens_email_key UNIQUE (email)')
