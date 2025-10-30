"""add_verification_tokens_table

Revision ID: 1d2ddce749b2
Revises: b7606e665139
Create Date: 2025-10-27 13:09:36.789465

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg


# revision identifiers, used by Alembic.
revision: str = '1d2ddce749b2'
down_revision: Union[str, Sequence[str], None] = 'b7606e665139'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create verification_token table (idempotent)."""
    # Use raw SQL with IF NOT EXISTS to make the migration safe to re-run
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS verification_token (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            token VARCHAR(256) NOT NULL,
            token_type VARCHAR(64) NOT NULL DEFAULT 'email_verification',
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            is_used BOOLEAN NOT NULL DEFAULT false
        );
        """
    )

    # Create indexes and unique constraint if they don't exist
    op.execute("CREATE INDEX IF NOT EXISTS ix_verification_token_user_id ON verification_token (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_verification_token_token ON verification_token (token);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_verification_token_token ON verification_token (token);")


def downgrade() -> None:
    """Downgrade schema: drop verification_token table if exists."""
    # Drop the constraint/indexes if they exist, then drop the table
    op.execute("DROP INDEX IF EXISTS uq_verification_token_token;")
    op.execute("DROP INDEX IF EXISTS ix_verification_token_token;")
    op.execute("DROP INDEX IF EXISTS ix_verification_token_user_id;")
    op.execute("DROP TABLE IF EXISTS verification_token;")
