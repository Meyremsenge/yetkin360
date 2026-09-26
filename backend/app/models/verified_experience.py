"""
VerifiedExperience model: snapshot of engagement state at T8 attestation.

PLAN 2.8 (YET-70, YET-88): VerifiedExperience schema.
Implements snapshot semantics — field values (organization name, role, dates, institution) are copied
at attestation time and never update, providing a historical record of what was verified.

Schema:
  - id: UUIDv7 PK
  - talent_id: FK to talent_profiles.id, NOT NULL
  - engagement_id: FK to engagements.id, NOT NULL (for referential integrity and audit trail)
  - organization_name_snapshot: text, NOT NULL (copied from Organization.name at attestation time)
  - role_snapshot: text, NOT NULL (copied from Engagement.title at attestation time)
  - started_on_snapshot: date, nullable (copied from Engagement.started_on)
  - ended_on_snapshot: date, nullable (copied from Engagement.ended_on)
  - institution_name_snapshot: text, nullable (copied from Institution.name if institution_id IS NOT NULL)
  - claim_type: CHECK IN (PARTICIPATION, CONTRIBUTION, COMPETENCE, CONDUCT), NOT NULL (final claim_type from Attestation)
  - visibility: CHECK IN (PRIVATE, INSTITUTION, ORGANIZATIONS, PUBLIC), mutable (D6 change-visibility uç, future)
  - public_token: text, unique, nullable (YET-106, paylaşılabilir doğrulama linki için rastgele token)
  - created_at: timestamptz (append-only)
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid7_default


class VerifiedExperience(Base):
    """VerifiedExperience: snapshot of engagement state at attestation time (T8 transition)."""

    __tablename__ = "verified_experiences"
    __table_args__ = (
        # Enum constraints
        CheckConstraint(
            "claim_type IN ('PARTICIPATION','CONTRIBUTION','COMPETENCE','CONDUCT')",
            name="ck_verified_experiences_claim_type",
        ),
        CheckConstraint(
            "visibility IN ('PRIVATE','INSTITUTION','ORGANIZATIONS','PUBLIC')",
            name="ck_verified_experiences_visibility",
        ),
        # Indexes
        Index("ix_verified_experiences_talent_id", "talent_id"),
        Index("ix_verified_experiences_engagement_id", "engagement_id"),
    )

    # Primary key: UUIDv7
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)

    # Foreign keys
    talent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("talent_profiles.id"), nullable=False
    )

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False
    )

    # Snapshots: copied at attestation time (no live FK, intentionally denormalized)
    organization_name_snapshot: Mapped[str] = mapped_column(String, nullable=False)
    role_snapshot: Mapped[str] = mapped_column(String, nullable=False)
    started_on_snapshot: Mapped[date | None] = mapped_column(nullable=True)
    ended_on_snapshot: Mapped[date | None] = mapped_column(nullable=True)
    institution_name_snapshot: Mapped[str | None] = mapped_column(String, nullable=True)

    # Verification context
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False)  # COMPETENCE, PARTICIPATION, etc.

    # Visibility: mutable (DOMAIN.md D6, future uç for private → public transitions)
    visibility: Mapped[str] = mapped_column(String(50), nullable=False, server_default="PRIVATE")

    # Public verification link token (YET-106)
    public_token: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)

    # Timestamps (append-only: no updated_at, except visibility changes which happen via separate mechanism)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
