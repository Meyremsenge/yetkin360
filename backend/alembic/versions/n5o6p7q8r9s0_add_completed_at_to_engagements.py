"""add completed_at to engagements

Revision ID: n5o6p7q8r9s0
Revises: m4n5o6p7q8r9
Create Date: 2026-10-03 00:00:00.000000

YET-7: Adds completed_at timestamptz field to engagements table for tracking completion time.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'n5o6p7q8r9s0'
down_revision: Union[str, None] = '85ce30db9b84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('engagements', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('engagements', 'completed_at')
