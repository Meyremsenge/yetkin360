"""certificate_checks kurs adi alanlari + BTK saglayicisi eklendi

Revision ID: c4e8a1f7b352
Revises: 237dbae3e129
Create Date: 2026-10-10 15:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4e8a1f7b352'
down_revision: Union[str, None] = '237dbae3e129'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('certificate_checks', sa.Column('extracted_course_name', sa.Text(), nullable=True))
    op.add_column('certificate_checks', sa.Column('page_course_name', sa.Text(), nullable=True))
    op.add_column('certificate_checks', sa.Column('course_match', sa.Boolean(), nullable=True))
    op.drop_constraint('ck_certificate_checks_provider', 'certificate_checks', type_='check')
    op.create_check_constraint(
        'ck_certificate_checks_provider',
        'certificate_checks',
        "provider IS NULL OR provider IN ('UDEMY','COURSERA','BTK','UNKNOWN')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_certificate_checks_provider', 'certificate_checks', type_='check')
    # BTK rows can't satisfy the old constraint — fold them back to UNKNOWN first.
    op.execute("UPDATE certificate_checks SET provider = 'UNKNOWN' WHERE provider = 'BTK'")
    op.create_check_constraint(
        'ck_certificate_checks_provider',
        'certificate_checks',
        "provider IS NULL OR provider IN ('UDEMY','COURSERA','UNKNOWN')",
    )
    op.drop_column('certificate_checks', 'course_match')
    op.drop_column('certificate_checks', 'page_course_name')
    op.drop_column('certificate_checks', 'extracted_course_name')
