"""add engagements table

Revision ID: g8h9i0j1k2l3
Revises: f7e8g9h0i1j2
Create Date: 2026-09-23 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'g8h9i0j1k2l3'
down_revision: Union[str, None] = 'f7e8g9h0i1j2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create engagements table
    op.create_table(
        'engagements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('talent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('supervisor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='DRAFT'),
        sa.Column('started_on', sa.Date(), nullable=True),
        sa.Column('ended_on', sa.Date(), nullable=True),
        sa.Column('confidential', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('INTERNSHIP','CAPSTONE','SHORT_PROJECT','PART_TIME')", name='ck_engagements_kind'),
        sa.CheckConstraint("status IN ('DRAFT','PENDING_APPROVAL','REJECTED','ACTIVE','CANCELLED','PENDING_EVALUATION','EVALUATED','VERIFIED','DISPUTED','RESOLVED')", name='ck_engagements_status'),
        sa.CheckConstraint("ended_on IS NULL OR started_on IS NULL OR ended_on >= started_on", name='ck_engagements_date_order'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], name='fk_engagements_institution_id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_engagements_organization_id'),
        sa.ForeignKeyConstraint(['supervisor_user_id'], ['users.id'], name='fk_engagements_supervisor_user_id'),
        sa.ForeignKeyConstraint(['talent_id'], ['talent_profiles.id'], name='fk_engagements_talent_id'),
        sa.PrimaryKeyConstraint('id', name='pk_engagements'),
    )

    # Create indexes as specified in DATABASE.md §2.3
    op.create_index('ix_engagements_organization_status', 'engagements', ['organization_id', 'status'])
    op.create_index('ix_engagements_talent_status', 'engagements', ['talent_id', 'status'])
    op.create_index('ix_engagements_institution_status', 'engagements', ['institution_id', 'status'])
    op.create_index('ix_engagements_status_pending_evaluation', 'engagements', ['status'], postgresql_where=sa.text("status = 'PENDING_EVALUATION'"))


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_engagements_status_pending_evaluation')
    op.drop_index('ix_engagements_institution_status')
    op.drop_index('ix_engagements_talent_status')
    op.drop_index('ix_engagements_organization_status')

    # Drop engagements table
    op.drop_table('engagements')
