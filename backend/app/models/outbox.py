"""
Outbox model: transactional outbox pattern for async email delivery.

Implements AC-1, AC-2, AC-4, AC-5 (mutable model, no immutability trigger).
Used for enqueueing side effects (email, SMS, webhooks) safely within a transaction,
then processing them asynchronously by the worker without blocking the transaction.

Schema:
  - id: BigInteger PK (autoincrement bigserial)
  - topic: text, NOT NULL (e.g., "email.duplicate_registration_attempt")
  - payload: JSONB, NOT NULL (context for the handler)
  - created_at: timestamptz, NOT NULL, server default (when row was enqueued)
  - processed_at: timestamptz, nullable (NULL until handler succeeds)
  - attempts: int, NOT NULL, default 0 (retry counter, incremented on failure)

Mutable (unlike audit_events): processed_at and attempts are updated by the worker.
No immutability trigger.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func

from app.models.base import Base


class Outbox(Base):
    """Transactional outbox for async side effects."""

    __tablename__ = "outbox"
    __table_args__ = (
        Index(
            "ix_outbox_processed_at_null",
            "created_at",
            postgresql_where=text("processed_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(nullable=False, default=0)
