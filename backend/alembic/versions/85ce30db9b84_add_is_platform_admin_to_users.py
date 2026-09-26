"""add is_platform_admin to users

Revision ID: 85ce30db9b84
Revises: m4n5o6p7q8r9
Create Date: 2026-09-26 23:24:19.988001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '85ce30db9b84'
down_revision: Union[str, None] = 'm4n5o6p7q8r9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_platform_admin', sa.Boolean(), server_default='false', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('users', 'is_platform_admin')
