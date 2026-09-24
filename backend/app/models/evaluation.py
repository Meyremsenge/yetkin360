"""
Evaluation model: stores structured evaluations for engagements.

PLAN 2.7 (YET-69, YET-86, YET-87): Evaluation form schema with direction, items, private_note.
Implements append-only semantics — no UPDATE/DELETE on evaluations/evaluation_items.

Schema:
  - id: UUIDv7 PK
  - engagement_id: FK to engagements.id, NOT NULL
  - evaluator_user_id: FK to users.id, NOT NULL (authenticated principal)
  - direction: CHECK IN ORG_TO_TALENT/TALENT_TO_ORG
  - submitted_at: timestamptz, satır oluşturulduğu an (NOT NULL)
  - private_note: nullable text (org/admin tarafından, talent'a asla dönmez)
  - UNIQUE(engagement_id, evaluator_user_id, direction) — aynı evaluator bir yönde yalnız bir kere değerlendirme gönderebilir
  - TimestampMixin (created_at/updated_at)

evaluation_items:
  - id: UUIDv7 PK
  - evaluation_id: FK evaluations.id, ON DELETE CASCADE
  - skill_id: FK skills.id, nullable (yetkinlikle ilişkili değerlendirme optional)
  - criterion: text NOT NULL, min_length=1 (boş string yasak)
  - rating: CHECK IN BELOW/MEETS/EXCEEDS/NOT_OBSERVED
  - comment: nullable text
  - TimestampMixin sahip değil (sadece evaluation_id ile referanslanır)
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    DateTime,
    String,
    Text,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid7_default


class Evaluation(Base, TimestampMixin):
    """Evaluation record: structured tanıklık (kurumun veya talent'ın değerlendirmesi)."""

    __tablename__ = "evaluations"
    __table_args__ = (
        # Direction: ORG_TO_TALENT (kurumdan stajyere) veya TALENT_TO_ORG (stajyerden kuruluşa)
        CheckConstraint(
            "direction IN ('ORG_TO_TALENT', 'TALENT_TO_ORG')",
            name="ck_evaluations_direction",
        ),
        # UNIQUE constraint: aynı evaluator bir yönde yalnız bir kere değerlendirme gönderebilir
        UniqueConstraint(
            "engagement_id",
            "evaluator_user_id",
            "direction",
            name="uq_evaluations_engagement_evaluator_direction",
        ),
        # Index for scope queries
        Index(
            "ix_evaluations_engagement_id",
            "engagement_id",
        ),
    )

    # Primary key: UUIDv7
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7_default)

    # Foreign keys
    engagement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False
    )

    evaluator_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    # Evaluation metadata
    direction: Mapped[str] = mapped_column(String(50), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    private_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship to evaluation items
    evaluation_items: Mapped[list["EvaluationItem"]] = relationship(
        "EvaluationItem", back_populates="evaluation", cascade="all, delete-orphan"
    )


class EvaluationItem(Base):
    """Individual evaluation criterion and rating (yetkinlik veya davranış kriteri)."""

    __tablename__ = "evaluation_items"
    __table_args__ = (
        # Rating allowlist
        CheckConstraint(
            "rating IN ('BELOW', 'MEETS', 'EXCEEDS', 'NOT_OBSERVED')",
            name="ck_evaluation_items_rating",
        ),
        # Index for evaluation lookup
        Index(
            "ix_evaluation_items_evaluation_id",
            "evaluation_id",
        ),
    )

    # Primary key: UUIDv7
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7_default)

    # Foreign key to Evaluation (CASCADE delete)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False
    )

    # Optional FK to skill (yetkinlikle ilişkili değerlendirme)
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("skills.id"), nullable=True
    )

    # Criterion text (min_length=1)
    criterion: Mapped[str] = mapped_column(String, nullable=False)

    # Rating value
    rating: Mapped[str] = mapped_column(String(50), nullable=False)

    # Optional comment
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship back to evaluation
    evaluation: Mapped["Evaluation"] = relationship(
        "Evaluation", back_populates="evaluation_items"
    )
