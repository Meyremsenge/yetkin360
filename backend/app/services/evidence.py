"""
Evidence service: core business logic for evidence creation and download URL generation.

PLAN 2.6 (YET-84, YET-85): Manages evidence lifecycle.
- AC-1: Create evidence record with outbox message + audit event (single transaction)
- AC-5: Generate download URL with ownership + scan_status checks
- AC-S1: Storage key prefix validation (elevation defense)
- AC-S6/AC-S7: Audit logging for creation + download
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.models import Evidence, Outbox, Deliverable, Engagement
from app.schemas.evidence import EvidenceResponse, EvidenceDownloadUrlResponse
from app.services.authorization import Principal, scoped_evidence, get_scoped_or_404
from app.services.audit import log_audit_event
from app.services.storage import generate_presigned_get_url


# Evidence kind allowlist (AC-8)
ALLOWED_EVIDENCE_KINDS = {"REPOSITORY", "DOCUMENT", "IMAGE", "LINK", "CERTIFICATE"}


def create_evidence(
    session: Session,
    principal: Principal,
    storage_key: str,
    kind: str,
    mime_type: str,
    size_bytes: int,
    deliverable_id: uuid.UUID | None = None,
) -> EvidenceResponse:
    """
    AC-1, AC-S1, AC-S7, AC-4: Create an evidence record and enqueue scanning.

    Validates storage_key prefix (elevation defense), checks deliverable ownership (AC-4),
    creates evidence record, writes outbox message for worker scanning, and logs audit event.
    All writes within a single transaction (atomic).

    Args:
        session: SQLAlchemy Session
        principal: Authenticated user context (must be TALENT with talent_id)
        storage_key: MinIO object key (must start with evidence/{principal.talent_id}/)
        kind: Evidence type (REPOSITORY/DOCUMENT/IMAGE/LINK/CERTIFICATE)
        mime_type: File MIME type
        size_bytes: File size in bytes
        deliverable_id: Optional UUID of related Deliverable (AC-4: ownership chain check)

    Returns:
        EvidenceResponse: Created evidence record

    Raises:
        ApiError(422, "INVALID_STORAGE_KEY") if storage_key prefix doesn't match principal.talent_id
        ApiError(403, "TALENT_PROFILE_REQUIRED") if principal.talent_id is None
        ApiError(404, "NOT_FOUND") if deliverable_id provided but ownership check fails (AC-4)
    """
    # Authorization checks (same order as PLAN 2.5 upload-url for consistency)
    if principal.talent_id is None:
        raise ApiError(403, "TALENT_PROFILE_REQUIRED", "Bu işlem için talent profili gereklidir.")

    # AC-S1: Validate storage_key prefix (elevation defense)
    expected_prefix = f"evidence/{principal.talent_id}/"
    if not storage_key.startswith(expected_prefix):
        raise ApiError(
            422,
            "INVALID_STORAGE_KEY",
            "Kanıt referansı geçersiz. Başka bir kullanıcının dosyasını kullanmaya çalışıyorsunuz.",
        )

    # AC-8: Validate kind allowlist
    if kind not in ALLOWED_EVIDENCE_KINDS:
        raise ApiError(422, "INVALID_KIND", "Geçersiz kanıt türü.")

    # AC-4: Validate deliverable ownership (if provided)
    if deliverable_id is not None:
        stmt = (
            select(Deliverable, Engagement)
            .join(Engagement, Deliverable.engagement_id == Engagement.id)
            .where(Deliverable.id == deliverable_id)
        )
        result = session.execute(stmt).first()
        if result is None or result[1].talent_id != principal.talent_id:
            raise ApiError(404, "NOT_FOUND", "Kanıt bulunamadı.")

    # AC-1: Create evidence record
    evidence = Evidence(
        owner_talent_id=principal.talent_id,
        kind=kind,
        provenance="SELF_UPLOADED",
        visibility="PRIVATE",
        scan_status="PENDING",
        storage_key=storage_key,
        mime_type=mime_type,
        size_bytes=size_bytes,
        deliverable_id=deliverable_id,
    )
    session.add(evidence)
    session.flush()  # Generate ID for outbox reference

    # AC-1: Write outbox message for worker to scan evidence
    outbox_record = Outbox(
        topic="evidence.scan_requested",
        payload={
            "evidence_id": str(evidence.id),
            "storage_key": storage_key,
            "bucket": settings.s3_bucket,
        },
    )
    session.add(outbox_record)

    # AC-S7: Log creation audit event
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,  # IP passed from endpoint layer if available
        action="evidence.created",
        subject_type="evidence",
        subject_id=evidence.id,
        result="SUCCESS",
    )

    # Single transaction commit in endpoint layer
    response = EvidenceResponse(
        id=evidence.id,
        owner_talent_id=evidence.owner_talent_id,
        kind=evidence.kind,
        provenance=evidence.provenance,
        storage_key=evidence.storage_key,
        mime_type=evidence.mime_type,
        size_bytes=evidence.size_bytes,
        scan_status=evidence.scan_status,
        visibility=evidence.visibility,
        deliverable_id=evidence.deliverable_id,
        created_at=evidence.created_at,
    )

    return response


def list_evidence(
    session: Session,
    principal: Principal,
    deliverable_id: uuid.UUID | None = None,
) -> list[EvidenceResponse]:
    """
    YET-195: The talent's own (non-deleted) evidence, newest first.

    Scoped by scoped_evidence (owner only; PRIVATE evidence is closed to admins too).
    A principal without a talent profile gets 403 TALENT_PROFILE_REQUIRED, same as
    the other evidence endpoints.
    """
    if principal.talent_id is None:
        raise ApiError(403, "TALENT_PROFILE_REQUIRED", "Bu işlem için talent profili gereklidir.")

    query = scoped_evidence(session, principal).where(Evidence.deleted_at.is_(None))
    if deliverable_id is not None:
        query = query.where(Evidence.deliverable_id == deliverable_id)
    rows = session.execute(query.order_by(Evidence.created_at.desc(), Evidence.id.desc())).scalars().all()
    return [
        EvidenceResponse(
            id=e.id,
            owner_talent_id=e.owner_talent_id,
            kind=e.kind,
            provenance=e.provenance,
            storage_key=e.storage_key,
            mime_type=e.mime_type,
            size_bytes=e.size_bytes,
            scan_status=e.scan_status,
            visibility=e.visibility,
            deliverable_id=e.deliverable_id,
            created_at=e.created_at,
        )
        for e in rows
    ]


def get_download_url(
    session: Session,
    principal: Principal,
    evidence_id: uuid.UUID,
) -> EvidenceDownloadUrlResponse:
    """
    AC-5, AC-6, AC-7, AC-S6: Generate presigned download URL with authorization checks.

    Validates ownership (via scoped_evidence), checks scan_status (must be CLEAN),
    and generates short-lived presigned URL (300 seconds).
    Logs audit event on success.

    AC-S2/AC-S3: Ownership/scan_status checks must be done BEFORE returning URL
    or error. Never leak scan_status/visibility info to non-owners.

    Args:
        session: SQLAlchemy Session
        principal: Authenticated user context
        evidence_id: Evidence UUID to download

    Returns:
        EvidenceDownloadUrlResponse: Presigned download URL

    Raises:
        ApiError(404) if evidence not found or not in scope (ownership/visibility check)
        ApiError(403) if principal is admin trying to download PRIVATE evidence
        ApiError(409, "SCAN_NOT_CLEAN") if scan_status is not CLEAN
        ApiError(503, "STORAGE_UNAVAILABLE") if MinIO unreachable
    """
    # AC-6, AC-S2: Get evidence, scoped to principal (ownership check)
    # scoped_evidence returns empty query for non-talent kinds (including admin)
    scoped_query = scoped_evidence(session, principal).where(Evidence.id == evidence_id)
    evidence = get_scoped_or_404(scoped_query, session)

    # AC-S3: Special case — platform admin requesting PRIVATE evidence → 403 (not 404)
    if evidence is None:
        if principal.is_platform_admin:
            # Admin requesting non-owned PRIVATE evidence: verify it exists (without scoped check)
            admin_check_stmt = select(Evidence).where(Evidence.id == evidence_id)
            evidence_exists = session.execute(admin_check_stmt).scalars().first()
            if evidence_exists is not None and evidence_exists.visibility == "PRIVATE":
                raise ApiError(
                    403,
                    "FORBIDDEN",
                    "Erişim reddedildi.",
                )
        # Regular 404 for everyone else (non-owners, non-admins)
        raise ApiError(404, "NOT_FOUND", "Kanıt bulunamadı.")

    # AC-7: Scan status must be CLEAN before download
    if evidence.scan_status != "CLEAN":
        raise ApiError(
            409,
            "SCAN_NOT_CLEAN",
            f"Dosya taranıyor veya kanıt kullanılamaz. Durum: {evidence.scan_status}",
        )

    # AC-5, AC-10, AC-11: Generate presigned GET URL (300 seconds TTL)
    # generate_presigned_get_url handles storage errors internally (ApiError 503)
    download_url = generate_presigned_get_url(
        bucket=settings.s3_bucket,
        object_key=evidence.storage_key,
        ttl=settings.evidence_download_url_ttl_seconds,
    )

    # AC-S6: Log download audit event
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,  # IP passed from endpoint layer if available
        action="evidence.downloaded",
        subject_type="evidence",
        subject_id=evidence.id,
        result="SUCCESS",
    )

    return EvidenceDownloadUrlResponse(
        download_url=download_url,
        expires_in=settings.evidence_download_url_ttl_seconds,
    )
