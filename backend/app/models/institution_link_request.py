"""Institution link request model (student → institution binding)."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class InstitutionLinkRequest(Base, TimestampMixin):
    """
    Student request to link their TalentProfile to an Institution.

    AC-3, AC-3b: Student creates PENDING request. Coordinator/Admin approves
    to set TalentProfile.institution_id (D10 workflow: explicit request + explicit approval).

    Status: PENDING (awaiting coordinator approval) → APPROVED or REJECTED.
    UNIQUE constraint ensures only one PENDING request per (talent_profile, institution).
    """

    __tablename__ = "institution_link_requests"
    __table_args__ = (
        Index(
            "uq_institution_link_requests_talent_institution_pending",
            "talent_profile_id",
            "institution_id",
            unique=True,
            postgresql_where=text("status = 'PENDING'"),
        ),
        CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED')",
            name="ck_institution_link_requests_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    talent_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("talent_profiles.id"), nullable=False
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="PENDING")
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
