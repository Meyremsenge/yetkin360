"""
FraudFlag model: AI-generated fraud/suspicious-content flag for admin review.

PLAN 3.54 — faz 1: attestation.statement metnini outbox worker'da OpenRouter'a
gönderip şüpheli paternleri işaretler. AI hiçbir zaman karar vermez — sadece
flag üretir (subject_type/subject_id + reason + confidence), nihai karar
(CONFIRMED/DISMISSED) admin tarafından verilir ve bu tabloya yazılır.

attestations gibi append-only DEĞİL: admin incelemesi status'ü günceller
(review akışı organizations.verification_level ile aynı desen — mutable bir
kuyruk satırı, kanıtın kendisi değil).

Schema:
  - id: UUIDv7 PK
  - subject_type: CHECK IN ('ATTESTATION','ORGANIZATION','INSTITUTION')
  - signal: nullable text — işareti üreten kuralın/kontrolün kodu (PLAN 3.56;
    3.54'ün tanıklık metni işaretlerinde NULL). Aynı (özne, sinyal) için
    tekrar satır üretmemek ve admin ekranında etiketlemek için.
  - subject_id: UUID, nullable=False
  - reason: text, AI'nin ürettiği gerekçe (serbest metin ama AI kaynaklı, PII değil)
  - confidence: CHECK IN ('LOW','MEDIUM','HIGH')
  - model: text, kullanılan model slug'ı (örn. "anthropic/claude-haiku-4.5")
  - status: CHECK IN ('PENDING','CONFIRMED','DISMISSED'), default PENDING
  - reviewed_by_user_id: FK users.id, nullable (admin karar verene kadar null)
  - reviewed_at: nullable timestamptz
  - created_at: timestamptz
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid7_default


class FraudFlag(Base):
    """AI tarafından üretilen sahtekarlık/şüpheli-içerik işareti (karar admin'de)."""

    __tablename__ = "fraud_flags"
    __table_args__ = (
        CheckConstraint(
            "subject_type IN ('ATTESTATION','ORGANIZATION','INSTITUTION')", name="ck_fraud_flags_subject_type"
        ),
        CheckConstraint("confidence IN ('LOW','MEDIUM','HIGH')", name="ck_fraud_flags_confidence"),
        CheckConstraint("status IN ('PENDING','CONFIRMED','DISMISSED')", name="ck_fraud_flags_status"),
        Index("ix_fraud_flags_subject", "subject_type", "subject_id"),
        Index("ix_fraud_flags_status_created_at", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)

    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    signal: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PENDING")
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
