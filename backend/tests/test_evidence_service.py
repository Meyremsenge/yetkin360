"""
Unit tests for services/evidence.py and services/storage.py (GET URL generation).

PLAN 2.6 (YET-84, YET-85): Evidence record creation and download URL generation.
Tests cover:
- AC-1: Evidence creation with transaction (evidence + outbox + audit)
- AC-3, AC-S1: Storage key prefix validation (elevation defense)
- AC-5, AC-10: Download URL generation and TTL (300 seconds)
- AC-7: Scan status validation (PENDING/INFECTED/FAILED → 409)
- AC-8: Kind allowlist validation
- AC-11: MinIO unavailability → 503
- AC-S6, AC-S7: Audit event logging (creation + download)

These tests are unit-level: they test pure service logic without mocking
the database (using real/test PostgreSQL, isolated transactions).

Storage service tests for presigned GET URL generation follow the same
pattern as presigned POST tests (PLAN 2.5, test_storage.py).
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import EndpointConnectionError, ConnectTimeoutError
from sqlalchemy import select
from sqlalchemy.orm import Session

# NOTE: These imports will fail during red phase (TDD) and cause collection error (FAILED).
# This is expected and correct — tests must show red (FAILED), not SKIP.
# Once app.services.evidence, app.models.evidence, and app.schemas.evidence
# are implemented, these imports will resolve and tests will run normally.
from app.core.errors import ApiError
from app.models.evidence import Evidence
from app.models.outbox import Outbox
from app.models.audit import AuditEvent
from app.services.evidence import create_evidence, get_download_url
from app.services.storage import generate_presigned_get_url
from app.services.authorization import Principal, scoped_evidence
from app.schemas.evidence import EvidenceCreateRequest, EvidenceResponse, EvidenceDownloadUrlResponse


# ============================================================================
# AC-1: Evidence Creation — Transaction Test (evidence + outbox + audit)
# ============================================================================


class TestEvidenceCreation:
    """AC-1: Evidence creation writes evidence + outbox + audit in single transaction."""

    def test_create_evidence_success_returns_response(self, session, user_talent_a, talent_a):
        """
        AC-1: create_evidence() returns EvidenceResponse with id, owner_talent_id,
        kind, provenance=SELF_UPLOADED, storage_key, mime_type, size_bytes,
        scan_status=PENDING, visibility=PRIVATE, created_at.
        """
        principal = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        storage_key = f"evidence/{talent_a.id}/test-uuid.pdf"
        response = create_evidence(
            session=session,
            principal=principal,
            storage_key=storage_key,
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        assert isinstance(response, EvidenceResponse)
        assert response.id is not None
        assert response.owner_talent_id == talent_a.id
        assert response.kind == "DOCUMENT"
        assert response.provenance == "SELF_UPLOADED"
        assert response.storage_key == storage_key
        assert response.mime_type == "application/pdf"
        assert response.size_bytes == 1024
        assert response.scan_status == "PENDING"
        assert response.visibility == "PRIVATE"
        assert response.created_at is not None

    def test_create_evidence_writes_evidence_record(self, session, user_talent_a, talent_a):
        """
        AC-1: Evidence record is written to DB with correct fields.
        """
        principal = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        storage_key = f"evidence/{talent_a.id}/test-uuid.pdf"
        response = create_evidence(
            session=session,
            principal=principal,
            storage_key=storage_key,
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=2048,
        )

        # Verify DB record exists
        evidence = session.query(Evidence).filter_by(id=response.id).first()
        assert evidence is not None
        assert evidence.owner_talent_id == talent_a.id
        assert evidence.kind == "DOCUMENT"
        assert evidence.provenance == "SELF_UPLOADED"
        assert evidence.storage_key == storage_key
        assert evidence.visibility == "PRIVATE"
        assert evidence.scan_status == "PENDING"
        assert evidence.deleted_at is None

    def test_create_evidence_writes_outbox_record(self, session, user_talent_a, talent_a):
        """
        AC-1: Outbox record is written with topic=evidence.scan_requested
        and payload containing evidence_id, storage_key, bucket.
        """
        principal = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        storage_key = f"evidence/{talent_a.id}/test-uuid.pdf"
        response = create_evidence(
            session=session,
            principal=principal,
            storage_key=storage_key,
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        # Verify outbox record
        outbox = session.query(Outbox).filter_by(topic="evidence.scan_requested").first()
        assert outbox is not None
        assert outbox.processed_at is None  # Not yet processed by worker
        assert outbox.payload["evidence_id"] == str(response.id)
        assert outbox.payload["storage_key"] == storage_key
        assert "bucket" in outbox.payload

    def test_create_evidence_writes_audit_event(self, session, user_talent_a, talent_a):
        """
        AC-S7: Audit event is written with action=evidence.created,
        subject_type=evidence, subject_id=evidence_id, result=SUCCESS.
        """
        principal = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        storage_key = f"evidence/{talent_a.id}/test-uuid.pdf"
        response = create_evidence(
            session=session,
            principal=principal,
            storage_key=storage_key,
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        # Verify audit event
        audit = session.query(AuditEvent).filter_by(
            action="evidence.created",
            subject_type="evidence"
        ).first()
        assert audit is not None
        assert audit.subject_id == response.id
        assert audit.result == "SUCCESS"
        assert audit.actor_user_id == user_talent_a.id


# ============================================================================
# AC-3, AC-S1: Storage Key Prefix Validation (Elevation Defense)
# ============================================================================


class TestStorageKeyValidation:
    """AC-3, AC-S1: Storage key must start with evidence/{principal.talent_id}/."""

    def test_storage_key_valid_prefix_accepted(self, session, user_talent_a, talent_a):
        """
        AC-3, AC-S1: Storage key with correct talent_id prefix is accepted.
        """
        principal = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        storage_key = f"evidence/{talent_a.id}/valid-uuid.pdf"
        response = create_evidence(
            session=session,
            principal=principal,
            storage_key=storage_key,
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        assert response.id is not None
        assert response.storage_key == storage_key

    def test_storage_key_invalid_prefix_raises_error(self, session, user_talent_a, talent_a, user_talent_b, talent_b):
        """
        AC-S1 (Elevation): Storage key with different talent_id prefix
        returns 422 + INVALID_STORAGE_KEY.
        """
        principal = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        # Try to use talent_b's prefix while authenticated as talent_a
        malicious_storage_key = f"evidence/{talent_b.id}/evil-uuid.pdf"

        with pytest.raises(ApiError) as exc_info:
            create_evidence(
                session=session,
                principal=principal,
                storage_key=malicious_storage_key,
                kind="DOCUMENT",
                mime_type="application/pdf",
                size_bytes=1024,
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "INVALID_STORAGE_KEY"

    def test_storage_key_no_prefix_raises_error(self, session, user_talent_a, talent_a):
        """
        AC-S1: Storage key without evidence/ prefix returns 422 + INVALID_STORAGE_KEY.
        """
        principal = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        with pytest.raises(ApiError) as exc_info:
            create_evidence(
                session=session,
                principal=principal,
                storage_key="random-key.pdf",
                kind="DOCUMENT",
                mime_type="application/pdf",
                size_bytes=1024,
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "INVALID_STORAGE_KEY"


# ============================================================================
# AC-8: Kind Allowlist Validation
# ============================================================================


class TestKindAllowlist:
    """AC-8: Kind must be in allowlist (REPOSITORY, DOCUMENT, IMAGE, LINK, CERTIFICATE)."""

    ALLOWED_KINDS = ["REPOSITORY", "DOCUMENT", "IMAGE", "LINK", "CERTIFICATE"]
    DISALLOWED_KINDS = ["VIDEO", "EXECUTABLE", "ARCHIVE", "INVALID"]

    @pytest.mark.parametrize("kind", ALLOWED_KINDS)
    def test_allowed_kind_accepted(self, session, user_talent_a, talent_a, kind):
        """
        AC-8: Allowed kind values are accepted (200).
        """
        principal = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        storage_key = f"evidence/{talent_a.id}/test-uuid.pdf"
        response = create_evidence(
            session=session,
            principal=principal,
            storage_key=storage_key,
            kind=kind,
            mime_type="application/pdf",
            size_bytes=1024,
        )

        assert response.kind == kind

    @pytest.mark.parametrize("kind", DISALLOWED_KINDS)
    def test_disallowed_kind_raises_error(self, session, user_talent_a, talent_a, kind):
        """
        AC-8: Disallowed kind values return 422 (Pydantic/CHECK constraint).
        """
        principal = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        with pytest.raises((ApiError, ValueError)):
            create_evidence(
                session=session,
                principal=principal,
                storage_key=f"evidence/{talent_a.id}/test-uuid.pdf",
                kind=kind,
                mime_type="application/pdf",
                size_bytes=1024,
            )


# ============================================================================
# AC-5, AC-10: Download URL Generation and TTL
# ============================================================================


class TestDownloadUrlGeneration:
    """AC-5, AC-10: Download URL expires_in is always 300 seconds (5 minutes)."""

    def test_generate_presigned_get_url_ttl_300_seconds(self):
        """
        AC-10: generate_presigned_get_url() with ttl=300 returns presigned URL
        valid for 300 seconds (different from upload's 900 seconds).
        """
        # Mock boto3 S3 client
        with patch("app.services.storage.boto3.client") as mock_boto:
            mock_s3 = MagicMock()
            mock_boto.return_value = mock_s3
            mock_s3.generate_presigned_url.return_value = "https://minio.example.com/download-url"

            url = generate_presigned_get_url(
                bucket="yetkin360",
                object_key="evidence/uuid/test.pdf",
                ttl=300,
            )

            assert url == "https://minio.example.com/download-url"
            # Verify that generate_presigned_url was called with ttl=300
            mock_s3.generate_presigned_url.assert_called_once()
            call_kwargs = mock_s3.generate_presigned_url.call_args.kwargs
            assert call_kwargs.get("ExpiresIn") == 300

    def test_download_url_response_schema(self):
        """
        AC-5, AC-10: EvidenceDownloadUrlResponse includes download_url and expires_in=300.
        """
        response = EvidenceDownloadUrlResponse(
            download_url="https://minio.example.com/presigned",
            expires_in=300,
        )
        assert response.download_url == "https://minio.example.com/presigned"
        assert response.expires_in == 300


# ============================================================================
# AC-7: Scan Status Validation (PENDING/INFECTED/FAILED → 409)
# ============================================================================


class TestScanStatusValidation:
    """
    AC-7: If scan_status is PENDING, INFECTED, or FAILED, download raises 409 Conflict.
    """

    @pytest.mark.parametrize("scan_status", ["PENDING", "INFECTED", "FAILED"])
    def test_get_download_url_non_clean_scan_status_returns_409(
        self, session, user_talent_a, talent_a, scan_status
    ):
        """
        AC-7: get_download_url() when scan_status != CLEAN returns 409 + SCAN_NOT_CLEAN.
        """
        principal = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        # Create evidence with specific scan_status (use direct DB update if needed)
        storage_key = f"evidence/{talent_a.id}/test-uuid.pdf"
        response = create_evidence(
            session=session,
            principal=principal,
            storage_key=storage_key,
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        # Manually set scan_status (in real scenario, worker updates this)
        evidence = session.query(Evidence).filter_by(id=response.id).first()
        evidence.scan_status = scan_status
        session.flush()

        with pytest.raises(ApiError) as exc_info:
            get_download_url(
                session=session,
                principal=principal,
                evidence_id=response.id,
            )

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["code"] == "SCAN_NOT_CLEAN"
        # Verify scan_status is in the error message (not as separate field)
        error_message = str(exc_info.value)
        assert scan_status in error_message


# ============================================================================
# AC-11: MinIO Unavailability → 503
# ============================================================================


class TestStorageUnavailable:
    """AC-11: MinIO connection error returns 503 + STORAGE_UNAVAILABLE."""

    def test_generate_presigned_get_url_connection_error_returns_503(self):
        """
        AC-11: generate_presigned_get_url() with MinIO connection error raises 503.
        """
        with patch("app.services.storage.boto3.client") as mock_boto:
            mock_s3 = MagicMock()
            mock_boto.return_value = mock_s3
            mock_s3.generate_presigned_url.side_effect = EndpointConnectionError(
                endpoint_url="http://minio:9000"
            )

            with pytest.raises(ApiError) as exc_info:
                generate_presigned_get_url(
                    bucket="yetkin360",
                    object_key="evidence/uuid/test.pdf",
                    ttl=300,
                )

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["code"] == "STORAGE_UNAVAILABLE"

    def test_generate_presigned_get_url_timeout_returns_503(self):
        """
        AC-11: generate_presigned_get_url() with timeout raises 503.
        """
        with patch("app.services.storage.boto3.client") as mock_boto:
            mock_s3 = MagicMock()
            mock_boto.return_value = mock_s3
            mock_s3.generate_presigned_url.side_effect = ConnectTimeoutError(
                endpoint_url="http://minio:9000"
            )

            with pytest.raises(ApiError) as exc_info:
                generate_presigned_get_url(
                    bucket="yetkin360",
                    object_key="evidence/uuid/test.pdf",
                    ttl=300,
                )

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["code"] == "STORAGE_UNAVAILABLE"


# ============================================================================
# AC-S6: Audit Event for Download
# ============================================================================


class TestDownloadAudit:
    """AC-S6: get_download_url() writes audit_events record with action=evidence.downloaded."""

    def test_get_download_url_writes_audit_event(self, session, user_talent_a, talent_a):
        """
        AC-S6: get_download_url() writes audit event with action=evidence.downloaded.
        """
        principal = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        # Create evidence
        storage_key = f"evidence/{talent_a.id}/test-uuid.pdf"
        response = create_evidence(
            session=session,
            principal=principal,
            storage_key=storage_key,
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        # Manually set scan_status to CLEAN (simulating worker processing)
        evidence = session.query(Evidence).filter_by(id=response.id).first()
        evidence.scan_status = "CLEAN"
        session.flush()

        # Mock MinIO
        with patch("app.services.storage.boto3.client") as mock_boto:
            mock_s3 = MagicMock()
            mock_boto.return_value = mock_s3
            mock_s3.generate_presigned_url.return_value = "https://minio.example.com/download"

            # Get download URL
            download_response = get_download_url(
                session=session,
                principal=principal,
                evidence_id=response.id,
            )

            assert download_response.download_url is not None

        # Verify audit event (audit_events is append-only, filter by specific evidence_id)
        audit = session.query(AuditEvent).filter_by(
            action="evidence.downloaded",
            subject_type="evidence",
            subject_id=response.id
        ).first()
        assert audit is not None
        assert audit.result == "SUCCESS"


# ============================================================================
# scoped_evidence() Authorization Scoping
# ============================================================================


class TestScopedEvidenceAuthorization:
    """scoped_evidence() implements default-deny for PRIVATE evidence."""

    def test_scoped_evidence_talent_sees_own(self, session, user_talent_a, talent_a):
        """
        Talent A can see own evidence via scoped_evidence().
        """
        principal = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        # Create evidence
        storage_key = f"evidence/{talent_a.id}/test-uuid.pdf"
        response = create_evidence(
            session=session,
            principal=principal,
            storage_key=storage_key,
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        # Query via scoped_evidence
        query = scoped_evidence(session, principal)
        results = session.execute(query).scalars().all()

        assert len(results) == 1
        assert results[0].id == response.id

    def test_scoped_evidence_talent_cannot_see_other(
        self, session, user_talent_a, talent_a, user_talent_b, talent_b
    ):
        """
        Talent A cannot see Talent B's PRIVATE evidence via scoped_evidence().
        """
        # Create evidence for talent_a
        principal_a = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        storage_key_a = f"evidence/{talent_a.id}/test-uuid-a.pdf"
        create_evidence(
            session=session,
            principal=principal_a,
            storage_key=storage_key_a,
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        # Create evidence for talent_b
        principal_b = Principal(
            user_id=user_talent_b.id,
            kind="TALENT",
            talent_id=talent_b.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        storage_key_b = f"evidence/{talent_b.id}/test-uuid-b.pdf"
        response_b = create_evidence(
            session=session,
            principal=principal_b,
            storage_key=storage_key_b,
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        # Talent A queries evidence
        query = scoped_evidence(session, principal_a)
        results = session.execute(query).scalars().all()

        # Talent A should only see their own evidence
        assert len(results) == 1
        assert results[0].id != response_b.id

    def test_scoped_evidence_admin_cannot_see_private(
        self, session, user_talent_a, talent_a
    ):
        """
        AC-S3: Admin (is_platform_admin=True) cannot see PRIVATE evidence via scoped_evidence().
        """
        # Create evidence for talent_a
        principal_a = Principal(
            user_id=user_talent_a.id,
            kind="TALENT",
            talent_id=talent_a.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        storage_key = f"evidence/{talent_a.id}/test-uuid.pdf"
        create_evidence(
            session=session,
            principal=principal_a,
            storage_key=storage_key,
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        # Admin queries evidence
        admin_principal = Principal(
            user_id=uuid.uuid4(),
            kind="ADMIN",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=True,
            is_suspended=False,
        )

        query = scoped_evidence(session, admin_principal)
        results = session.execute(query).scalars().all()

        # Admin should see empty result (PRIVATE evidence excluded)
        assert len(results) == 0
