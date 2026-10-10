"""engagement_tasks: olusturan ve dogrulama alanlari eklendi

Revision ID: a9d2f4c7e815
Revises: e7b1d9a3c604
Create Date: 2026-10-10 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a9d2f4c7e815'
down_revision: Union[str, None] = 'e7b1d9a3c604'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'engagement_tasks',
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        'engagement_tasks',
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'engagement_tasks',
        sa.Column('verified_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_engagement_tasks_created_by_user_id', 'engagement_tasks', 'users',
        ['created_by_user_id'], ['id'],
    )
    op.create_foreign_key(
        'fk_engagement_tasks_verified_by_user_id', 'engagement_tasks', 'users',
        ['verified_by_user_id'], ['id'],
    )
    # Every existing task was created by an organization member or coordinator
    # (talents could not create tasks), so it counts as verified from the start.
    op.execute("UPDATE engagement_tasks SET verified_at = created_at")
    op.create_check_constraint(
        'ck_engagement_tasks_verifier_needs_verified_at',
        'engagement_tasks',
        "verified_by_user_id IS NULL OR verified_at IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint('ck_engagement_tasks_verifier_needs_verified_at', 'engagement_tasks', type_='check')
    op.drop_constraint('fk_engagement_tasks_verified_by_user_id', 'engagement_tasks', type_='foreignkey')
    op.drop_constraint('fk_engagement_tasks_created_by_user_id', 'engagement_tasks', type_='foreignkey')
    op.drop_column('engagement_tasks', 'verified_by_user_id')
    op.drop_column('engagement_tasks', 'verified_at')
    op.drop_column('engagement_tasks', 'created_by_user_id')
