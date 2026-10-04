"""organizations: verification_rejected_at (YET-198 reject marks the application)

Revision ID: e2a7c4d91b38
Revises: d1f6a83c5b27
Create Date: 2026-10-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e2a7c4d91b38'
down_revision: Union[str, None] = 'd1f6a83c5b27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # YET-198: NULL = no rejection; set when an admin rejects a pending T3 application.
    op.add_column('organizations', sa.Column('verification_rejected_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('organizations', 'verification_rejected_at')
