"""
PortfolioItem model: a talent's self-declared certificate or work shown on the profile.

docs/arastirma-ogrenci-profili.md §4.2. A portfolio item is a CLAIM (final analiz
§7.1), not evidence and not an attestation: title/issuer/date are typed by the
student. An optional evidence_id links the uploaded file, which stays PRIVATE —
the evidence row's own visibility CHECK is untouched, the file never goes public.

The public badge is never stored here: it is derived on read. Only when the
linked evidence has a certificate_checks row with decision=CONFIRMED (a
coordinator's decision) is the item shown as "coordinator confirmed"; everything
else is "self declared".

Schema:
  - id: UUIDv7 PK
  - talent_id: FK talent_profiles.id, NOT NULL (owner, taken from the session)
  - kind: CERTIFICATE / WORK
  - title (1-120), issuer (<=120), issued_on, credential_id (<=100)
  - external_url: https only (<=500)
  - evidence_id: FK evidence.id, nullable, UNIQUE (one showcase row per file)
  - show_on_profile: explicit consent to list it on /p/[slug], default false
  - deleted_at: soft delete (the linked evidence is not affected)
  - created_at, updated_at: TimestampMixin
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class PortfolioItem(Base, TimestampMixin):
    """Self-declared certificate/work; consent-gated on the public profile."""

    __tablename__ = "portfolio_items"
    __table_args__ = (
        UniqueConstraint("evidence_id", name="uq_portfolio_items_evidence_id"),
        CheckConstraint("kind IN ('CERTIFICATE','WORK')", name="ck_portfolio_items_kind"),
        CheckConstraint("char_length(title) BETWEEN 1 AND 120", name="ck_portfolio_items_title_length"),
        CheckConstraint(
            "issuer IS NULL OR char_length(issuer) <= 120", name="ck_portfolio_items_issuer_length"
        ),
        CheckConstraint(
            "credential_id IS NULL OR char_length(credential_id) <= 100",
            name="ck_portfolio_items_credential_id_length",
        ),
        CheckConstraint(
            "external_url IS NULL OR (external_url LIKE 'https://%' AND char_length(external_url) <= 500)",
            name="ck_portfolio_items_external_url_https",
        ),
        Index(
            "ix_portfolio_items_talent_not_deleted",
            "talent_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
    talent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("talent_profiles.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(120))
    issued_on: Mapped[date | None] = mapped_column(Date)
    credential_id: Mapped[str | None] = mapped_column(String(100))
    external_url: Mapped[str | None] = mapped_column(String(500))
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("evidence.id"))
    show_on_profile: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
