"""add audit_events table and immutability trigger

Revision ID: a1b2c3d4e5f6
Revises: b82aa928fbd2
Create Date: 2026-09-19 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'b82aa928fbd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create audit_events table (append-only audit log)
    op.create_table(
        'audit_events',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('actor_user_id', sa.UUID(), nullable=True),
        sa.Column('actor_ip', postgresql.INET(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('subject_type', sa.String(), nullable=False),
        sa.Column('subject_id', sa.UUID(), nullable=True),
        sa.Column('result', sa.String(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("result IN ('SUCCESS','DENIED','ERROR')", name='ck_audit_events_result'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create immutability trigger (append-only): BEFORE UPDATE OR DELETE
    op.execute("""
        CREATE FUNCTION audit_events_before_update_delete() RETURNS TRIGGER AS $$
        BEGIN
          RAISE EXCEPTION 'audit_events is append-only'
            USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER audit_events_immutable
          BEFORE UPDATE OR DELETE ON audit_events
          FOR EACH ROW
          EXECUTE FUNCTION audit_events_before_update_delete();
    """)


def downgrade() -> None:
    # Drop trigger and function (in reverse order)
    op.execute("DROP TRIGGER IF EXISTS audit_events_immutable ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_before_update_delete()")

    # Drop table
    op.drop_table('audit_events')
