"""fraud_flags: kurulus/kurum ozneleri ve signal alani eklendi

Revision ID: e7b1d9a3c604
Revises: c4e8a1f7b352
Create Date: 2026-10-10 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7b1d9a3c604'
down_revision: Union[str, None] = 'c4e8a1f7b352'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('fraud_flags', sa.Column('signal', sa.String(length=50), nullable=True))
    op.drop_constraint('ck_fraud_flags_subject_type', 'fraud_flags', type_='check')
    op.create_check_constraint(
        'ck_fraud_flags_subject_type',
        'fraud_flags',
        "subject_type IN ('ATTESTATION','ORGANIZATION','INSTITUTION')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_fraud_flags_subject_type', 'fraud_flags', type_='check')
    # Organization/institution flags can't satisfy the old constraint and have
    # no meaning without it — a review-queue table, so removing rows is allowed.
    op.execute("DELETE FROM fraud_flags WHERE subject_type <> 'ATTESTATION'")
    op.create_check_constraint(
        'ck_fraud_flags_subject_type', 'fraud_flags', "subject_type IN ('ATTESTATION')"
    )
    op.drop_column('fraud_flags', 'signal')
