"""fraud_flags tablosu eklendi

Revision ID: 86bf007a6b43
Revises: d85a0529f295
Create Date: 2026-10-10 10:35:37.171669

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '86bf007a6b43'
down_revision: Union[str, None] = 'd85a0529f295'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fraud_flags',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('subject_type', sa.String(length=50), nullable=False),
        sa.Column('subject_id', sa.UUID(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('confidence', sa.String(length=10), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('reviewed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("confidence IN ('LOW','MEDIUM','HIGH')", name='ck_fraud_flags_confidence'),
        sa.CheckConstraint("status IN ('PENDING','CONFIRMED','DISMISSED')", name='ck_fraud_flags_status'),
        sa.CheckConstraint("subject_type IN ('ATTESTATION')", name='ck_fraud_flags_subject_type'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_fraud_flags_status_created_at', 'fraud_flags', ['status', 'created_at'], unique=False)
    op.create_index('ix_fraud_flags_subject', 'fraud_flags', ['subject_type', 'subject_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_fraud_flags_subject', table_name='fraud_flags')
    op.drop_index('ix_fraud_flags_status_created_at', table_name='fraud_flags')
    op.drop_table('fraud_flags')
