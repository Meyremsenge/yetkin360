"""evidence: UNIQUE storage_key + storage_etag (TOCTOU re-check)

Revision ID: d1f6a83c5b27
Revises: c9e4b7a21d03
Create Date: 2026-10-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd1f6a83c5b27'
down_revision: Union[str, None] = 'c9e4b7a21d03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # YET-184: one evidence record per stored object, enforced by the database.
    op.create_unique_constraint('uq_evidence_storage_key', 'evidence', ['storage_key'])
    # YET-195 follow-up: ETag the scan saw; nullable (NULL = never scanned / pre-migration row).
    op.add_column('evidence', sa.Column('storage_etag', sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column('evidence', 'storage_etag')
    op.drop_constraint('uq_evidence_storage_key', 'evidence', type_='unique')
