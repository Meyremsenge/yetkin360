"""Add attestations and verified_experiences tables.

PLAN 2.8 (YET-70): Attestation + VerifiedExperience schema for T8 transition (EVALUATED → VERIFIED).

Revision ID: f8g9h0i1j2k3
Revises: ee96f63a4231
Create Date: 2026-09-24

- attestations: append-only table, talent_id denormalized for CHECK constraint
- verified_experiences: snapshot fields (no live FKs), mutable visibility only
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f8g9h0i1j2k3'
down_revision: Union[str, None] = 'ee96f63a4231'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create attestations and verified_experiences tables."""
    # attestations table
    op.create_table(
        "attestations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("engagement_id", sa.UUID(), nullable=False),
        sa.Column("talent_id", sa.UUID(), nullable=False),
        sa.Column("subject_type", sa.String(length=50), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=True),
        sa.Column("claim_type", sa.String(length=50), nullable=False),
        sa.Column("requested_claim_type", sa.String(length=50), nullable=False),
        sa.Column("attestor_user_id", sa.UUID(), nullable=False),
        sa.Column("attestor_org_id", sa.UUID(), nullable=True),
        sa.Column("skill_id", sa.UUID(), nullable=True),
        sa.Column("statement", sa.Text(), nullable=True),
        sa.Column("downgrade_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "subject_type IN ('ENGAGEMENT','EVIDENCE','DELIVERABLE','SKILL_CLAIM')",
            name="ck_attestations_subject_type",
        ),
        sa.CheckConstraint(
            "claim_type IN ('PARTICIPATION','CONTRIBUTION','COMPETENCE','CONDUCT')",
            name="ck_attestations_claim_type",
        ),
        sa.CheckConstraint(
            "requested_claim_type IN ('PARTICIPATION','CONTRIBUTION','COMPETENCE','CONDUCT')",
            name="ck_attestations_requested_claim_type",
        ),
        sa.CheckConstraint(
            "attestor_user_id != talent_id",
            name="ck_attestations_no_self_attestation",
        ),
        sa.ForeignKeyConstraint(["attestor_org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["attestor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["engagement_id"], ["engagements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.ForeignKeyConstraint(["talent_id"], ["talent_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "engagement_id",
            "attestor_user_id",
            "subject_type",
            name="uq_attestations_engagement_attestor_subject",
        ),
    )
    op.create_index("ix_attestations_attestor_user_id", "attestations", ["attestor_user_id"])
    op.create_index("ix_attestations_engagement_id", "attestations", ["engagement_id"])
    op.create_index("ix_attestations_skill_id", "attestations", ["skill_id"])
    op.create_index("ix_attestations_talent_id", "attestations", ["talent_id"])

    # verified_experiences table
    op.create_table(
        "verified_experiences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("talent_id", sa.UUID(), nullable=False),
        sa.Column("engagement_id", sa.UUID(), nullable=False),
        sa.Column("organization_name_snapshot", sa.String(), nullable=False),
        sa.Column("role_snapshot", sa.String(), nullable=False),
        sa.Column("started_on_snapshot", sa.Date(), nullable=True),
        sa.Column("ended_on_snapshot", sa.Date(), nullable=True),
        sa.Column("institution_name_snapshot", sa.String(), nullable=True),
        sa.Column("claim_type", sa.String(length=50), nullable=False),
        sa.Column("visibility", sa.String(length=50), server_default="PRIVATE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "claim_type IN ('PARTICIPATION','CONTRIBUTION','COMPETENCE','CONDUCT')",
            name="ck_verified_experiences_claim_type",
        ),
        sa.CheckConstraint(
            "visibility IN ('PRIVATE','INSTITUTION','ORGANIZATIONS','PUBLIC')",
            name="ck_verified_experiences_visibility",
        ),
        sa.ForeignKeyConstraint(["engagement_id"], ["engagements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["talent_id"], ["talent_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verified_experiences_engagement_id", "verified_experiences", ["engagement_id"])
    op.create_index("ix_verified_experiences_talent_id", "verified_experiences", ["talent_id"])


def downgrade() -> None:
    """Drop attestations and verified_experiences tables."""
    op.drop_index("ix_verified_experiences_talent_id", table_name="verified_experiences")
    op.drop_index("ix_verified_experiences_engagement_id", table_name="verified_experiences")
    op.drop_table("verified_experiences")

    op.drop_index("ix_attestations_skill_id", table_name="attestations")
    op.drop_index("ix_attestations_talent_id", table_name="attestations")
    op.drop_index("ix_attestations_engagement_id", table_name="attestations")
    op.drop_index("ix_attestations_attestor_user_id", table_name="attestations")
    op.drop_table("attestations")
