import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid7_default

if TYPE_CHECKING:
    from app.models.skill import Skill


class SkillSignal(Base):
    """
    Skill signal: evidence of competency from various sources (SELF_CLAIM, DELIVERABLE, etc.).

    AC-1 through AC-6 from YET-104 (skillsignal-self-claim-uretimi).
    Append-only table (per DOMAIN.md §3.14): no UPDATE/DELETE allowed.
    No updated_at field — append-only means no mutations, only created_at.
    """
    __tablename__ = "skill_signals"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('SELF_CLAIM','DELIVERABLE','TASK','EVALUATION','ATTESTATION','EXTERNAL')",
            name="ck_skill_signals_source_type",
        ),
        CheckConstraint(
            "strength IN ('NONE','WEAK','MODERATE','STRONG')",
            name="ck_skill_signals_strength",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    talent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("talent_profiles.id"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    strength: Mapped[str] = mapped_column(String, nullable=False)
    attested_by_org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skill_signals.id")
    )

    skill: Mapped["Skill"] = relationship("Skill")
