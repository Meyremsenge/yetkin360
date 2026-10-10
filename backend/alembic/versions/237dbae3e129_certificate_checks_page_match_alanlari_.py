"""certificate_checks page_match alanlari eklendi

Revision ID: 237dbae3e129
Revises: 9b383aedf5f4
Create Date: 2026-10-10 12:14:00.059249

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '237dbae3e129'
down_revision: Union[str, None] = '9b383aedf5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('certificate_checks', sa.Column('page_name', sa.Text(), nullable=True))
    op.add_column('certificate_checks', sa.Column('page_match', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('certificate_checks', 'page_match')
    op.drop_column('certificate_checks', 'page_name')
