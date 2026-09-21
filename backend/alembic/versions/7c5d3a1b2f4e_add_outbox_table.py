"""add outbox table

Revision ID: 7c5d3a1b2f4e
Revises: ffcf10979a51
Create Date: 2026-09-21 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '7c5d3a1b2f4e'
down_revision: Union[str, None] = 'ffcf10979a51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create outbox table (transactional outbox for async side effects)
    op.create_table(
        'outbox',
        sa.Column('id', sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column('topic', sa.Text(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create partial index for unprocessed rows (optimization for polling query)
    op.create_index(
        'ix_outbox_processed_at_null',
        'outbox',
        ['created_at'],
        postgresql_where=sa.text('processed_at IS NULL'),
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_outbox_processed_at_null', table_name='outbox')

    # Drop table
    op.drop_table('outbox')
