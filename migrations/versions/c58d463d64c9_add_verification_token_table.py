"""Add verification_token table

Revision ID: c58d463d64c9
Revises: bfaf29d53bbe
Create Date: 2026-02-05 12:02:10.206545

"""
from typing import Sequence, Union

import sqlmodel
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c58d463d64c9'
down_revision: Union[str, Sequence[str], None] = 'bfaf29d53bbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'verification_token',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('token_type', sa.String(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('expires_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('used_at', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')),
        sa.ForeignKeyConstraint(['user_id'], ['utilisateur.id'])
    )
    op.create_index(op.f('ix_verification_token_token'), 'verification_token', ['token'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_verification_token_token'), table_name='verification_token')
    op.drop_table('verification_token')
