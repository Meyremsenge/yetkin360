"""
Fixed-window request counters for the identity endpoints (YET-186, GUV-11).

One row per (bucket, key_hash, window_start). `key_hash` is an HMAC of the
client IP or the submitted e-mail, never the raw value, so the table holds no
PII. Rows are disposable counters, not facts: they are deleted once their
window is long past (see app/services/rate_limit.py), so this table is not
append-only.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"
    __table_args__ = (
        CheckConstraint("count >= 0", name="ck_auth_rate_limits_count_nonneg"),
        Index("ix_auth_rate_limits_window_start", "window_start"),
    )

    bucket: Mapped[str] = mapped_column(Text, primary_key=True)
    key_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
