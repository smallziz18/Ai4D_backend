"""add_agent_contexts_table

Revision ID: 08b12c31a836
Revises: 1d2ddce749b2
Create Date: 2025-11-22 10:50:19.074139

"""
from typing import Sequence, Union
import sqlmodel
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08b12c31a836'
down_revision: Union[str, Sequence[str], None] = '1d2ddce749b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'agent_contexts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('current_state', sa.String(), nullable=True, server_default='idle'),
        sa.Column('current_agent', sa.String(), nullable=True),
        sa.Column('context_data', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('conversation_history', sa.JSON(), nullable=True, server_default='[]'),
        sa.Column('total_interactions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('meta_data', sa.JSON(), nullable=True, server_default='{}'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_contexts_user_id', 'agent_contexts', ['user_id'])
    op.create_index('ix_agent_contexts_session_id', 'agent_contexts', ['session_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_agent_contexts_session_id', table_name='agent_contexts')
    op.drop_index('ix_agent_contexts_user_id', table_name='agent_contexts')
    op.drop_table('agent_contexts')

