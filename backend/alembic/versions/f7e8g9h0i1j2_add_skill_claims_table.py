"""add skill_claims table

Revision ID: f7e8g9h0i1j2
Revises: 045883d11996
Create Date: 2026-09-22 14:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f7e8g9h0i1j2'
down_revision: Union[str, None] = '045883d11996'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create skill_claims table
    op.create_table(
        'skill_claims',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('talent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claimed_level', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=False, server_default='MANUAL'),
        sa.Column('confirmed_by_user_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("claimed_level IS NULL OR claimed_level IN ('BEGINNER','INTERMEDIATE','ADVANCED')", name='ck_skill_claims_claimed_level'),
        sa.CheckConstraint("source IN ('MANUAL','AI_EXTRACTED')", name='ck_skill_claims_source'),
        sa.CheckConstraint("source <> 'AI_EXTRACTED' OR confirmed_by_user_at IS NOT NULL", name='ck_skill_claims_ai_requires_confirmation'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], name='fk_skill_claims_skill_id'),
        sa.ForeignKeyConstraint(['talent_id'], ['talent_profiles.id'], name='fk_skill_claims_talent_id'),
        sa.PrimaryKeyConstraint('id', name='pk_skill_claims'),
        sa.UniqueConstraint('talent_id', 'skill_id', name='uq_skill_claims_talent_skill'),
    )


def downgrade() -> None:
    # Drop skill_claims table
    op.drop_table('skill_claims')
