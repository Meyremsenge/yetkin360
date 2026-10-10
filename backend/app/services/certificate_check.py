"""
Certificate check service (PLAN 3.55 — faz 2 kanıt/sertifika kontrolü).

Öğrenci açık rızasıyla tetikler (KVKK: üçüncü taraf AI sağlayıcısına gönderim
için ayrı rıza gerekir, final-analiz §11.2) → outbox worker OpenRouter'a
sorar, QR'ı deterministik (OpenCV) çözer → sonuç (extracted_name, name_match,
credential_id, verify_url) engagement'ın koordinatör/supervisor'una gösterilir
→ nihai CONFIRMED/REJECTED kararını koordinatör verir. AI hiçbir zaman karar
vermez (final-analiz §11.4.2/§39).

Yetkilendirme istisnası: scoped_evidence() evidence'ı sadece sahibine açar
(final-analiz §21.2). Bu modül, SADECE CertificateCheck özetini (ham dosyayı
DEĞİL) ilgili engagement'ın koordinatör/supervisor'una açan kasıtlı ve dar bir
istisnadır — docs/API.md'de kayıtlıdır.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CertificateCheck, Deliverable, Engagement, Evidence, Outbox
from app.services.authorization import Principal, engagement_relation, get_scoped_or_404, scoped_evidence


class EvidenceNotFoundError(Exception):
    """Evidence yok veya principal'ın scope'unda değil (404)."""


class NotCertificateKindError(Exception):
    """Evidence CERTIFICATE türünde değil (422)."""


class EvidenceNotCleanError(Exception):
    """Evidence henüz CLEAN değil (virüs taraması bekliyor/başarısız) (409)."""


class CheckAlreadyRequestedError(Exception):
    """Bu evidence için zaten bir CertificateCheck var (409)."""


class CheckNotFoundError(Exception):
    """CertificateCheck yok veya principal erişemiyor (404)."""


class CheckNotPendingError(Exception):
    """Karar zaten verilmiş (409) — tekrar inceleme yok."""


def request_certificate_check(session: Session, principal: Principal, evidence_id: uuid.UUID) -> CertificateCheck:
    """Öğrencinin kendi CERTIFICATE türü, CLEAN durumundaki evidence'ı için açık
    rızayla AI çıkarımı talep eder. Yalnız sahibi çağırabilir (scoped_evidence)."""
    evidence = get_scoped_or_404(scoped_evidence(session, principal).where(Evidence.id == evidence_id), session)
    if evidence is None:
        raise EvidenceNotFoundError(str(evidence_id))
    if evidence.kind != "CERTIFICATE":
        raise NotCertificateKindError(str(evidence_id))
    if evidence.scan_status != "CLEAN":
        raise EvidenceNotCleanError(str(evidence_id))

    check = CertificateCheck(evidence_id=evidence_id, requested_by_talent_at=datetime.now(timezone.utc))
    session.add(check)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        if "uq_certificate_checks_evidence_id" not in str(exc.orig):
            raise
        raise CheckAlreadyRequestedError(str(evidence_id)) from exc

    session.add(
        Outbox(topic="evidence.certificate_check_requested", payload={"certificate_check_id": str(check.id)})
    )
    return check


def _principal_can_view_check(session: Session, principal: Principal, check: CertificateCheck) -> bool:
    """Evidence sahibi (talent, kendi talebinin sonucunu görür) VEYA ilişkili
    engagement'ın koordinatör/supervisor'u (org_admin/coordinator) — scoped_evidence'a
    kasıtlı, dar istisna (bkz. modül docstring'i)."""
    evidence = session.get(Evidence, check.evidence_id)
    if evidence is None:
        return False
    if principal.talent_id is not None and evidence.owner_talent_id == principal.talent_id:
        return True
    if evidence.deliverable_id is None:
        return False
    row = session.execute(
        select(Engagement).join(Deliverable, Deliverable.engagement_id == Engagement.id)
        .where(Deliverable.id == evidence.deliverable_id)
    ).scalars().first()
    if row is None:
        return False
    rel = engagement_relation(principal, row)
    return rel.is_org_admin or rel.is_coordinator


def get_certificate_check_for_evidence(
    session: Session, principal: Principal, evidence_id: uuid.UUID
) -> CertificateCheck | None:
    """Talent kendi talebinin sonucunu görmek için (profil/çalışma ekranı)."""
    check = session.execute(select(CertificateCheck).where(CertificateCheck.evidence_id == evidence_id)).scalars().first()
    if check is None or not _principal_can_view_check(session, principal, check):
        return None
    return check


def list_certificate_checks_for_engagement(
    session: Session, principal: Principal, engagement_id: uuid.UUID
) -> list[CertificateCheck]:
    """Bir engagement'a bağlı (deliverable üzerinden) tüm CertificateCheck'ler.

    Çağıran API katmanında zaten scoped_engagements()/get_scoped_or_404 ile
    404 kontrolü yapılmış olmalı (bu fonksiyon yalnız "scope içindeyim ama bu
    özel görünüme yetkim yok" durumunu [] ile ayırt eder — plain ORG_MEMBER
    gibi). Yalnız ilgili talent veya koordinatör/supervisor (org_admin) görür.
    """
    engagement = session.get(Engagement, engagement_id)
    if engagement is None:
        return []
    rel = engagement_relation(principal, engagement)
    if not (rel.is_subject or rel.is_org_admin or rel.is_coordinator):
        return []

    rows = session.execute(
        select(CertificateCheck)
        .join(Evidence, Evidence.id == CertificateCheck.evidence_id)
        .join(Deliverable, Deliverable.id == Evidence.deliverable_id)
        .where(Deliverable.engagement_id == engagement_id)
        .order_by(CertificateCheck.created_at.asc())
    ).scalars().all()
    return list(rows)


def resolve_certificate_check(
    session: Session, principal: Principal, check_id: uuid.UUID, decision: str, decided_by_user_id: uuid.UUID | None
) -> CertificateCheck:
    """Koordinatör/supervisor kararı — CONFIRMED veya REJECTED. AI bu kararı asla vermez."""
    check = session.get(CertificateCheck, check_id)
    if check is None or not _principal_can_view_check(session, principal, check):
        raise CheckNotFoundError(str(check_id))

    evidence = session.get(Evidence, check.evidence_id)
    assert evidence is not None  # _principal_can_view_check already resolved it
    row = session.execute(
        select(Engagement).join(Deliverable, Deliverable.engagement_id == Engagement.id)
        .where(Deliverable.id == evidence.deliverable_id)
    ).scalars().first()
    if row is None:
        raise CheckNotFoundError(str(check_id))
    rel = engagement_relation(principal, row)
    if not (rel.is_org_admin or rel.is_coordinator):
        raise CheckNotFoundError(str(check_id))

    if check.decision != "PENDING":
        raise CheckNotPendingError(str(check_id))

    check.decision = decision
    check.decided_by_user_id = decided_by_user_id
    check.decided_at = datetime.now(timezone.utc)
    session.flush()
    return check
