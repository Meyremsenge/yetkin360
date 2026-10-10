"""
CertificateCheck model: öğrencinin açık rızasıyla tetiklenen sertifika
çıkarım/kontrol kaydı (PLAN 3.55 — Udemy/Coursera sertifikaları).

AI burada hiçbir zaman "doğrulandı" kararı vermez (final-analiz §11.4.2/§39:
AI'nin evidence gerçekliğini değerlendirmesi kesinlikle yasak). AI sadece
sertifikadaki metni/QR'ı çıkarır (dönüştürme, üretim değil) — isim eşleşmesi
DETERMİNİSTİK bir string karşılaştırmasıyla koddan hesaplanır, AI'nin
görüşü değildir. Nihai karar (CONFIRMED/REJECTED) her zaman koordinatör/
supervisor'dan gelir — fraud_flags ile aynı felsefe.

Bu tablo append-only DEĞİL (fraud_flags gibi bir inceleme kuyruğu satırı,
kanıtın kendisi değil) — mutable, organizations.verification_level ile
aynı desen.

Schema:
  - id: UUIDv7 PK
  - evidence_id: FK evidence.id, UNIQUE (bir evidence için tek kayıt)
  - requested_by_talent_at: timestamptz, öğrencinin açık rızasının zaman damgası
  - status: PENDING/DONE/FAILED (çıkarım süreci durumu)
  - provider: UDEMY/COURSERA/BTK/UNKNOWN (AI'nin çıkardığı, metne göre)
  - credential_id: nullable text (çıkarılan kimlik/sertifika numarası)
  - verify_url: nullable text (QR'dan veya metinden çıkarılan resmi doğrulama linki)
  - qr_raw_data: nullable text (QR'dan deterministik olarak çözülen ham veri)
  - extracted_name: nullable text (sertifikada yazılı isim, AI'nin okuduğu)
  - name_match: nullable bool (extracted_name ile talent profilinin full_name'i
    arasında DETERMİNİSTİK string karşılaştırması — AI kararı değil)
  - page_name / page_match: resmi doğrulama sayfasındaki ad ve karşılaştırması
  - extracted_course_name / page_course_name / course_match: sertifikadaki ve
    resmi sayfadaki kurs adı ile deterministik karşılaştırması (AI kararı değil)
  - model: text, kullanılan görsel model slug'ı
  - decision: PENDING/CONFIRMED/REJECTED (koordinatör kararı — AI asla set etmez)
  - decided_by_user_id: FK users.id, nullable
  - decided_at: nullable timestamptz
  - created_at: timestamptz
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid7_default


class CertificateCheck(Base):
    """Öğrenci rızasıyla tetiklenen sertifika çıkarımı + koordinatör kararı."""

    __tablename__ = "certificate_checks"
    __table_args__ = (
        UniqueConstraint("evidence_id", name="uq_certificate_checks_evidence_id"),
        CheckConstraint("status IN ('PENDING','DONE','FAILED')", name="ck_certificate_checks_status"),
        CheckConstraint(
            "provider IS NULL OR provider IN ('UDEMY','COURSERA','BTK','UNKNOWN')",
            name="ck_certificate_checks_provider",
        ),
        CheckConstraint(
            "decision IN ('PENDING','CONFIRMED','REJECTED')", name="ck_certificate_checks_decision"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False
    )

    requested_by_talent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PENDING")

    provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    credential_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    verify_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_raw_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    name_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # PLAN 3.55b: resmi doğrulama sayfasından (Coursera ve BTK Akademi — Udemy Cloudflare
    # bot korumasının arkasında, otomatik erişilemez) deterministik olarak
    # çekilen ad ve sertifikadaki adla karşılaştırması. AI karar vermez; bu da
    # düz string karşılaştırması (bkz. _names_match) — yalnız bir öneridir.
    page_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Sertifikada yazılı kurs adı (AI'nin okuduğu), resmi sayfadaki kurs adı
    # (Coursera ve BTK Akademi) ve ikisinin aynı deterministik karşılaştırması.
    extracted_course_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_course_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    course_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    decision: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PENDING")
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
