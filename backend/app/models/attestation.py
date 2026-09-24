"""
Attestation model: third-party testimony to validate competency claims.

PLAN 2.8 (YET-70, YET-88, YET-89, YET-90): Attestation (tanıklık) schema.
Implements T8 transition (EVALUATED → VERIFIED) with SkillSignal/VerifiedExperience/AuditEvent in single transaction.

Schema:
  - id: UUIDv7 PK
  - engagement_id: FK to engagements.id, NOT NULL
  - talent_id: FK to talent_profiles.id (denormalized from Engagement.talent_id for CHECK constraint), NOT NULL
  - subject_type: CHECK IN (ENGAGEMENT, EVIDENCE, DELIVERABLE, SKILL_CLAIM), NOT NULL
  - subject_id: UUID (typically engagement_id when subject_type=ENGAGEMENT), nullable
  - claim_type: CHECK IN (PARTICIPATION, CONTRIBUTION, COMPETENCE, CONDUCT), NOT NULL (actual granted)
  - requested_claim_type: same CHECK, the client's request (may differ if downgraded)
  - attestor_user_id: FK to users.id, NOT NULL (from authenticated principal, NOT from request body)
  - attestor_org_id: FK to organizations.id, nullable (attestor's organization)
  - skill_id: FK to skills.id, nullable
  - statement: nullable text (additional justification)
  - downgrade_reasons: JSONB list of codes (["NO_DELIVERABLE", ...]), empty if not downgraded
  - revoked_at: nullable timestamptz (future use, YET-93/94 revoke uç)
  - revoke_reason: nullable text
  - created_at: timestamptz (append-only, no updated_at)
  - CHECK(attestor_user_id != talent_id) — self-attestation forbidden
  - UNIQUE(engagement_id, attestor_user_id, subject_type) — one attestation per attestor+subject per engagement
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid7_default


class Attestation(Base):
    """Attestation record: third-party testimony to verify competency claim."""

    __tablename__ = "attestations"
    __table_args__ = (
        # Enum constraints
        CheckConstraint(
            "subject_type IN ('ENGAGEMENT','EVIDENCE','DELIVERABLE','SKILL_CLAIM')",
            name="ck_attestations_subject_type",
        ),
        CheckConstraint(
            "claim_type IN ('PARTICIPATION','CONTRIBUTION','COMPETENCE','CONDUCT')",
            name="ck_attestations_claim_type",
        ),
        CheckConstraint(
            "requested_claim_type IN ('PARTICIPATION','CONTRIBUTION','COMPETENCE','CONDUCT')",
            name="ck_attestations_requested_claim_type",
        ),
        # Self-attestation prevention (PLAN 2.8 §2)
        CheckConstraint(
            "attestor_user_id != talent_id",
            name="ck_attestations_no_self_attestation",
        ),
        # Uniqueness: only one attestation per attestor+subject+engagement
        UniqueConstraint(
            "engagement_id",
            "attestor_user_id",
            "subject_type",
            name="uq_attestations_engagement_attestor_subject",
        ),
        # Indexes
        Index("ix_attestations_engagement_id", "engagement_id"),
        Index("ix_attestations_talent_id", "talent_id"),
        Index("ix_attestations_attestor_user_id", "attestor_user_id"),
        Index("ix_attestations_skill_id", "skill_id"),
    )

    # Primary key: UUIDv7
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)

    # Foreign keys
    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False
    )

    # Denormalized talent_id (from Engagement.talent_id) for CHECK constraint
    talent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("talent_profiles.id"), nullable=False
    )

    # Subject being attested
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Claim types: requested vs. granted (may differ due to downgrade)
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Final, after downgrade logic
    requested_claim_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Original request

    # Attestor context (from authenticated principal)
    attestor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    attestor_org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )

    # Optional skill reference
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), nullable=True
    )

    # Additional context
    statement: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Downgrade tracking (PLAN 2.8 §3.11)
    downgrade_reasons: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, default=list  # ["NO_DELIVERABLE", ...]
    )

    # Revocation (future use, YET-93/94)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps (append-only: no updated_at)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
