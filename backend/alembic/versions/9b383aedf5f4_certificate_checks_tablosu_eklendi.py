"""certificate_checks tablosu eklendi

Revision ID: 9b383aedf5f4
Revises: 86bf007a6b43
Create Date: 2026-10-10 11:38:38.100096

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '9b383aedf5f4'
down_revision: Union[str, None] = '86bf007a6b43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'certificate_checks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('evidence_id', sa.UUID(), nullable=False),
        sa.Column('requested_by_talent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=True),
        sa.Column('credential_id', sa.Text(), nullable=True),
        sa.Column('verify_url', sa.Text(), nullable=True),
        sa.Column('qr_raw_data', sa.Text(), nullable=True),
        sa.Column('extracted_name', sa.Text(), nullable=True),
        sa.Column('name_match', sa.Boolean(), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('decision', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('decided_by_user_id', sa.UUID(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("decision IN ('PENDING','CONFIRMED','REJECTED')", name='ck_certificate_checks_decision'),
        sa.CheckConstraint("provider IS NULL OR provider IN ('UDEMY','COURSERA','UNKNOWN')", name='ck_certificate_checks_provider'),
        sa.CheckConstraint("status IN ('PENDING','DONE','FAILED')", name='ck_certificate_checks_status'),
        sa.ForeignKeyConstraint(['decided_by_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('evidence_id', name='uq_certificate_checks_evidence_id'),
    )


def downgrade() -> None:
    op.drop_table('certificate_checks')
