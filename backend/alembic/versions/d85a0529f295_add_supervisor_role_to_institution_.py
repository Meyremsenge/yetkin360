"""add SUPERVISOR role to institution_members

Revision ID: d85a0529f295
Revises: n5o6p7q8r9s0
Create Date: 2026-10-04 20:55:17.886223

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'd85a0529f295'
down_revision: Union[str, None] = 'n5o6p7q8r9s0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update institution_members role constraint to include SUPERVISOR
    op.drop_constraint('ck_institution_members_role', 'institution_members', type_='check')
    op.create_check_constraint(
        'ck_institution_members_role',
        'institution_members',
        "role IN ('ADMIN','COORDINATOR','SUPERVISOR')"
    )


def downgrade() -> None:
    # Revert institution_members role constraint back to original (without SUPERVISOR)
    op.drop_constraint('ck_institution_members_role', 'institution_members', type_='check')
    op.create_check_constraint(
        'ck_institution_members_role',
        'institution_members',
        "role IN ('ADMIN','COORDINATOR')"
    )
