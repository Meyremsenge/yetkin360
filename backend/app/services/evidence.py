"""
Evidence service: core business logic for evidence creation and download URL generation.

PLAN 2.6 (YET-84, YET-85): Manages evidence lifecycle.
- AC-1: Create evidence record with outbox message + audit event (single transaction)
- AC-5: Generate download URL with ownership + scan_status checks
- AC-S1: Storage key prefix validation (elevation defense)
- AC-S6/AC-S7: Audit logging for creation + download
"""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.models import Evidence, Outbox, Deliverable, Engagement
from app.schemas.evidence import EvidenceResponse, EvidenceDownloadUrlResponse
from app.services.authorization import Principal, scoped_evidence, get_scoped_or_404
from app.services.audit import log_audit_event
from app.services.storage import (
    CONTENT_TYPE_TO_EXT,
    generate_presigned_get_url,
    head_object_etag,
    validate_content_type,
    validate_file_size,
)


_UUID_RE = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

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
        ApiError(404, "NOT_FOUND") if storage_key is not under the principal's own prefix
            (someone else's object — never confirm it exists)
        ApiError(422, "INVALID_STORAGE_KEY") if the key is under the own prefix but malformed
        ApiError(409, "EVIDENCE_ALREADY_REGISTERED") if the object already has an evidence record
        ApiError(403, "TALENT_PROFILE_REQUIRED") if principal.talent_id is None
        ApiError(404, "NOT_FOUND") if deliverable_id provided but ownership check fails (AC-4)
    """
    # Authorization checks (same order as PLAN 2.5 upload-url for consistency)
    if principal.talent_id is None:
        raise ApiError(403, "TALENT_PROFILE_REQUIRED", "Bu işlem için talent profili gereklidir.")

    # AC-S1: Validate storage_key prefix (elevation defense). A key outside the caller's
    # own prefix is someone else's (or no) object: 404, same as any unauthorized access,
    # so the response never confirms whether the object exists.
    expected_prefix = f"evidence/{principal.talent_id}/"
    if not storage_key.startswith(expected_prefix):
        raise ApiError(404, "NOT_FOUND", "Kanıt bulunamadı.")

    # YET-184: key must be exactly evidence/{talent_id}/{uuid}.{ext} as built by
    # build_object_key — no nested paths, no client-chosen names — and the
    # extension must match the declared mime type.
    if not validate_content_type(mime_type):
        raise ApiError(422, "UNSUPPORTED_CONTENT_TYPE", "Desteklenmeyen dosya türü. İzin verilen türler: PDF, JPEG, PNG, DOCX.")
    if not validate_file_size(size_bytes):
        raise ApiError(422, "FILE_TOO_LARGE", "Dosya çok büyük.")
    key_pattern = rf"{re.escape(expected_prefix)}{_UUID_RE}\.{re.escape(CONTENT_TYPE_TO_EXT[mime_type])}"
    if not re.fullmatch(key_pattern, storage_key):
        raise ApiError(422, "INVALID_STORAGE_KEY", "Kanıt referansı geçersiz.")

    # YET-184: one evidence record per stored object.
    already_registered = get_scoped_or_404(
        scoped_evidence(session, principal).where(Evidence.storage_key == storage_key), session
    )
    if already_registered is not None:
        raise ApiError(409, "EVIDENCE_ALREADY_REGISTERED", "Bu dosya zaten kanıt olarak kaydedilmiş.")

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
    try:
        # Savepoint: a losing concurrent registration must not poison the outer transaction.
        with session.begin_nested():
            session.flush()  # Generate ID for outbox reference
    except IntegrityError as exc:
        # The pre-check above is racy; the UNIQUE constraint is the real guard (YET-184).
        if "uq_evidence_storage_key" not in str(exc.orig):
            raise
        raise ApiError(409, "EVIDENCE_ALREADY_REGISTERED", "Bu dosya zaten kanıt olarak kaydedilmiş.") from exc

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
        ApiError(409, "EVIDENCE_CONTENT_CHANGED") if the stored object's ETag differs from
            the one recorded by the scan (or none was recorded)
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

    return issue_download_url(session, principal.user_id, evidence)


def issue_download_url(
    session: Session,
    actor_user_id: uuid.UUID | None,
    evidence: Evidence,
    audit_action: str = "evidence.downloaded",
    audit_metadata: dict | None = None,
) -> EvidenceDownloadUrlResponse:
    """
    Issue a short-lived download URL for an evidence the caller has ALREADY been
    authorized for. Enforces what holds for every reader: the scan must be CLEAN
    and the stored object must still be the one that was scanned; the download is
    audited.

    Raises ApiError 409 SCAN_NOT_CLEAN / EVIDENCE_CONTENT_CHANGED, 503 STORAGE_UNAVAILABLE.
    """
    # AC-7: Scan status must be CLEAN before download
    if evidence.scan_status != "CLEAN":
        raise ApiError(
            409,
            "SCAN_NOT_CLEAN",
            f"Dosya taranıyor veya kanıt kullanılamaz. Durum: {evidence.scan_status}",
        )

    # TOCTOU defence: the object must still be the one the scan inspected. Capture what
    # we need and end the read transaction first — the HEAD is a network call and must
    # not run inside an open transaction.
    evidence_pk, storage_key, scanned_etag = evidence.id, evidence.storage_key, evidence.storage_etag
    session.commit()
    current_etag = head_object_etag(settings.s3_bucket, storage_key)
    if scanned_etag is None or current_etag != scanned_etag:
        log_audit_event(
            session=session,
            actor_user_id=actor_user_id,
            actor_ip=None,
            action="evidence.download_blocked",
            subject_type="evidence",
            subject_id=evidence_pk,
            result="DENIED",
            metadata={"reason": "content_changed_since_scan", **(audit_metadata or {})},
        )
        session.commit()  # the 409 below would otherwise roll the audit row back
        raise ApiError(
            409,
            "EVIDENCE_CONTENT_CHANGED",
            "Dosya içeriği taramadan sonra değişmiş. Dosyayı yeniden yükleyip kanıt olarak kaydedin.",
        )

    # AC-5, AC-10, AC-11: Generate presigned GET URL (300 seconds TTL)
    # generate_presigned_get_url handles storage errors internally (ApiError 503)
    download_url = generate_presigned_get_url(
        bucket=settings.s3_bucket,
        object_key=storage_key,
        ttl=settings.evidence_download_url_ttl_seconds,
    )

    # AC-S6: Log download audit event
    log_audit_event(
        session=session,
        actor_user_id=actor_user_id,
        actor_ip=None,  # IP passed from endpoint layer if available
        action=audit_action,
        subject_type="evidence",
        subject_id=evidence_pk,
        result="SUCCESS",
        metadata=audit_metadata,
    )

    return EvidenceDownloadUrlResponse(
        download_url=download_url,
        expires_in=settings.evidence_download_url_ttl_seconds,
    )
