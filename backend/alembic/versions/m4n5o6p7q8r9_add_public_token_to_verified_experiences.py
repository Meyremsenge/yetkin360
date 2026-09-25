"""add public_token to verified_experiences

Revision ID: m4n5o6p7q8r9
Revises: l3m4n5o6p7q8
Create Date: 2026-09-25 10:00:00.000000

YET-106, PLAN 3.2: public verification link
Adds public_token (nullable, unique) to verified_experiences for shareable verification links.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'm4n5o6p7q8r9'
down_revision: Union[str, None] = 'l3m4n5o6p7q8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('verified_experiences', sa.Column('public_token', sa.String(), nullable=True))
    op.create_unique_constraint('uq_verified_experiences_public_token', 'verified_experiences', ['public_token'])
    op.create_index('ix_verified_experiences_public_token', 'verified_experiences', ['public_token'])


def downgrade() -> None:
    op.drop_index('ix_verified_experiences_public_token', table_name='verified_experiences')
    op.drop_constraint('uq_verified_experiences_public_token', 'verified_experiences', type_='unique')
    op.drop_column('verified_experiences', 'public_token')
