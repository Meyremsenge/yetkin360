"""complaints tablosu eklendi

Revision ID: aeb03da96da1
Revises: 53d336a5a854
Create Date: 2026-10-10 18:47:18.348536

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'aeb03da96da1'
down_revision: Union[str, None] = '53d336a5a854'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'complaints',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('engagement_id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('talent_id', sa.UUID(), nullable=False),
        sa.Column('created_by_user_id', sa.UUID(), nullable=False),
        sa.Column('category', sa.String(length=30), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='OPEN', nullable=False),
        sa.Column('decision_note', sa.Text(), nullable=True),
        sa.Column('decided_by_user_id', sa.UUID(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "category IN ('TASK_APPROVAL','CERTIFICATE_APPROVAL','PERSONAL')", name='ck_complaints_category'
        ),
        sa.CheckConstraint("status IN ('OPEN','UPHELD','DISMISSED')", name='ck_complaints_status'),
        sa.CheckConstraint(
            "(status = 'OPEN') = (decided_at IS NULL)", name='ck_complaints_decided_at_matches_status'
        ),
        sa.CheckConstraint(
            '(decided_at IS NULL) = (decided_by_user_id IS NULL)', name='ck_complaints_decision_has_admin'
        ),
        sa.CheckConstraint('char_length(btrim(description)) > 0', name='ck_complaints_description_not_blank'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['decided_by_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['engagement_id'], ['engagements.id']),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['talent_id'], ['talent_profiles.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_complaints_organization_status', 'complaints', ['organization_id', 'status'], unique=False)
    op.create_index('ix_complaints_status_created_at', 'complaints', ['status', 'created_at'], unique=False)
    op.create_index(
        'uq_complaints_one_open_per_engagement',
        'complaints',
        ['engagement_id'],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN'"),
    )


def downgrade() -> None:
    op.drop_index('uq_complaints_one_open_per_engagement', table_name='complaints')
    op.drop_index('ix_complaints_status_created_at', table_name='complaints')
    op.drop_index('ix_complaints_organization_status', table_name='complaints')
    op.drop_table('complaints')
