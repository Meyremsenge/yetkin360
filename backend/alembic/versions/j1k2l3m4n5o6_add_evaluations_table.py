"""add evaluations and evaluation_items tables

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-09-24 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'j1k2l3m4n5o6'
down_revision: Union[str, None] = 'i0j1k2l3m4n5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create evaluations table
    op.create_table(
        'evaluations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('engagement_id', sa.UUID(), nullable=False),
        sa.Column('evaluator_user_id', sa.UUID(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('private_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("direction IN ('ORG_TO_TALENT', 'TALENT_TO_ORG')", name='ck_evaluations_direction'),
        sa.ForeignKeyConstraint(['engagement_id'], ['engagements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evaluator_user_id'], ['users.id']),
        sa.UniqueConstraint('engagement_id', 'evaluator_user_id', 'direction', name='uq_evaluations_engagement_evaluator_direction'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evaluations_engagement_id', 'evaluations', ['engagement_id'])

    # Create evaluation_items table
    op.create_table(
        'evaluation_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('evaluation_id', sa.UUID(), nullable=False),
        sa.Column('skill_id', sa.UUID(), nullable=True),
        sa.Column('criterion', sa.String(), nullable=False),
        sa.Column('rating', sa.String(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.CheckConstraint("rating IN ('BELOW', 'MEETS', 'EXCEEDS', 'NOT_OBSERVED')", name='ck_evaluation_items_rating'),
        sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evaluation_items_evaluation_id', 'evaluation_items', ['evaluation_id'])


def downgrade() -> None:
    op.drop_index('ix_evaluation_items_evaluation_id')
    op.drop_table('evaluation_items')
    op.drop_index('ix_evaluations_engagement_id')
    op.drop_table('evaluations')
