"""Institution link requests table (AC-3, AC-3b)

Revision ID: c5d6e7f8g9h0
Revises: a1b2c3d4e5f6
Create Date: 2026-09-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c5d6e7f8g9h0"
down_revision: Union[str, None] = "7c5d3a1b2f4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create institution_link_requests table
    op.create_table(
        "institution_link_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("talent_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED')",
            name="ck_institution_link_requests_status",
        ),
        sa.ForeignKeyConstraint(
            ["talent_profile_id"],
            ["talent_profiles.id"],
            name="fk_institution_link_requests_talent_profile_id",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_institution_link_requests_institution_id",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_user_id"],
            ["users.id"],
            name="fk_institution_link_requests_decided_by_user_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_institution_link_requests"),
    )

    # Create partial unique index for PENDING status
    op.create_index(
        "uq_institution_link_requests_talent_institution_pending",
        "institution_link_requests",
        ["talent_profile_id", "institution_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
    )


def downgrade() -> None:
    op.drop_index("uq_institution_link_requests_talent_institution_pending", "institution_link_requests")
    op.drop_table("institution_link_requests")
