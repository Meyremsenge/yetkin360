"""add skill_id to engagement_tasks and deliverables tables

Revision ID: k2l3m4n5o6p7
Revises: f8g9h0i1j2k3
Create Date: 2026-09-24 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'k2l3m4n5o6p7'
down_revision: Union[str, None] = 'f8g9h0i1j2k3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add skill_id column to engagement_tasks table
    op.add_column(
        'engagement_tasks',
        sa.Column('skill_id', sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        'fk_engagement_tasks_skill_id',
        'engagement_tasks',
        'skills',
        ['skill_id'],
        ['id']
    )

    # Add skill_id column to deliverables table
    op.add_column(
        'deliverables',
        sa.Column('skill_id', sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        'fk_deliverables_skill_id',
        'deliverables',
        'skills',
        ['skill_id'],
        ['id']
    )


def downgrade() -> None:
    # Drop foreign key and column from deliverables
    op.drop_constraint('fk_deliverables_skill_id', 'deliverables', type_='foreignkey')
    op.drop_column('deliverables', 'skill_id')

    # Drop foreign key and column from engagement_tasks
    op.drop_constraint('fk_engagement_tasks_skill_id', 'engagement_tasks', type_='foreignkey')
    op.drop_column('engagement_tasks', 'skill_id')
