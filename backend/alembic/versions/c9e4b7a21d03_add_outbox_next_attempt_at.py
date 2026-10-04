"""add outbox.next_attempt_at (retry backoff + claim lease)

Revision ID: c9e4b7a21d03
Revises: 85ce30db9b84
Create Date: 2026-10-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9e4b7a21d03'
down_revision: Union[str, None] = '85ce30db9b84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable on purpose: NULL means "eligible now", so existing rows need no
    # backfill and old code keeps working (add-then-use, backwards compatible).
    op.add_column(
        'outbox',
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('outbox', 'next_attempt_at')
