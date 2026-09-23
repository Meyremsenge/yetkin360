"""add skill_signals table and immutability trigger

Revision ID: 53299629ffe0
Revises: i0j1k2l3m4n5
Create Date: 2026-09-23 23:31:51.034577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '53299629ffe0'
down_revision: Union[str, None] = 'i0j1k2l3m4n5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create skill_signals table (append-only, YET-104)
    op.create_table(
        'skill_signals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('talent_id', sa.UUID(), nullable=False),
        sa.Column('skill_id', sa.UUID(), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=True),
        sa.Column('strength', sa.String(), nullable=False),
        sa.Column('attested_by_org_id', sa.UUID(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('superseded_by_id', sa.UUID(), nullable=True),
        sa.CheckConstraint("source_type IN ('SELF_CLAIM','DELIVERABLE','TASK','EVALUATION','ATTESTATION','EXTERNAL')", name='ck_skill_signals_source_type'),
        sa.CheckConstraint("strength IN ('NONE','WEAK','MODERATE','STRONG')", name='ck_skill_signals_strength'),
        sa.ForeignKeyConstraint(['attested_by_org_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id']),
        sa.ForeignKeyConstraint(['superseded_by_id'], ['skill_signals.id']),
        sa.ForeignKeyConstraint(['talent_id'], ['talent_profiles.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create immutability trigger (append-only): BEFORE UPDATE OR DELETE
    op.execute("""
        CREATE FUNCTION skill_signals_before_update_delete() RETURNS TRIGGER AS $$
        BEGIN
          RAISE EXCEPTION 'skill_signals is append-only (immutable trigger)'
            USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER skill_signals_immutable
          BEFORE UPDATE OR DELETE ON skill_signals
          FOR EACH ROW
          EXECUTE FUNCTION skill_signals_before_update_delete();
    """)

    # Create composite index for profile page query (talent_id, skill_id, occurred_at DESC)
    op.create_index(
        'ix_skill_signals_talent_skill_occurred',
        'skill_signals',
        ['talent_id', 'skill_id', sa.text('occurred_at DESC')],
    )


def downgrade() -> None:
    # Drop index first
    op.drop_index('ix_skill_signals_talent_skill_occurred', table_name='skill_signals', if_exists=True)

    # Drop trigger and function (in reverse order)
    op.execute("DROP TRIGGER IF EXISTS skill_signals_immutable ON skill_signals")
    op.execute("DROP FUNCTION IF EXISTS skill_signals_before_update_delete()")

    # Drop table
    op.drop_table('skill_signals')
