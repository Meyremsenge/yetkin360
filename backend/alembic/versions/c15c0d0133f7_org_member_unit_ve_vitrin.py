"""organization member unit label and organization showcase switch

Revision ID: c15c0d0133f7
Revises: 53d336a5a854
Create Date: 2026-10-10 23:00:00.000000

SPRINT M0: additive, backward compatible.
  - organization_members.unit: optional team/unit label (1-60 chars, not blank)
  - organizations.showcase_public: public showcase switch, off by default
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c15c0d0133f7'
down_revision: Union[str, Sequence[str], None] = '53d336a5a854'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('organization_members', sa.Column('unit', sa.String(length=60), nullable=True))
    op.create_check_constraint(
        'ck_organization_members_unit_length',
        'organization_members',
        'unit IS NULL OR char_length(btrim(unit)) BETWEEN 1 AND 60',
    )
    op.add_column(
        'organizations',
        sa.Column('showcase_public', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('organizations', 'showcase_public')
    op.drop_constraint('ck_organization_members_unit_length', 'organization_members', type_='check')
    op.drop_column('organization_members', 'unit')
