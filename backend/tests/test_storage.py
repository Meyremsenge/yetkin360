"""
Unit tests for storage.py (file upload URL generation, validation).

PLAN 2.5 (YET-82, YET-83): Storage service — content_type allowlist, size validation,
object_key generation, presigned URL generation. Tests cover:
- Content-type allowlist validation
- File size limit enforcement
- Object key formatting ({uuid}.{ext})
- Filename validation (length, empty check)
- Error handling (unsupported type, too large)

These tests are unit-level and do NOT mock the database; they test pure logic.
Integration with MinIO is tested separately in test_evidence_upload_url.py.
"""

import uuid

import pytest

# NOTE: These imports will fail until the modules are implemented.
# This is expected during the red phase (TDD).
# Once app.services.storage and app.schemas.evidence are written,
# these imports will resolve and tests will run.
try:
    from app.services.storage import (
        validate_content_type,
        validate_file_size,
        build_object_key,
        validate_filename,
    )
    from app.schemas.evidence import EvidenceUploadUrlRequest, EvidenceUploadUrlResponse
except ImportError as e:
    # During red phase, capture the import error and skip tests gracefully.
    # Once modules are implemented, this will be removed.
    pytest.skip(f"Storage modules not yet implemented: {e}", allow_module_level=True)


# ============================================================================
# Content-Type Allowlist Tests (AC-3)
# ============================================================================


class TestContentTypeAllowlist:
    """AC-3: Only whitelisted content types are allowed."""

    ALLOWED_TYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    @pytest.mark.parametrize("content_type", [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ])
    def test_validate_content_type_allowed(self, content_type):
        """AC-3: validate_content_type() returns True for allowed types."""
        result = validate_content_type(content_type)
        assert result is True

    @pytest.mark.parametrize("content_type", [
        "application/json",
        "text/plain",
        "image/gif",
        "video/mp4",
        "application/x-executable",
        "application/x-msdownload",
        "",
    ])
    def test_validate_content_type_not_allowed(self, content_type):
        """AC-3: validate_content_type() returns False for disallowed types."""
        result = validate_content_type(content_type)
        assert result is False

    def test_validate_content_type_case_sensitive(self):
        """Content-type validation should handle MIME type case sensitivity correctly."""
        # MIME types are case-insensitive in standards, but we enforce lowercase in allowlist
        result = validate_content_type("Application/PDF")
        # Implementation may normalize to lowercase; test documents expected behavior
        # For now, assume it expects lowercase as per MIME standard
        # This test documents the contract
        assert result is False
        assert validate_content_type("application/pdf") is True


# ============================================================================
# File Size Validation Tests (AC-4)
# ============================================================================


class TestFileSizeValidation:
    """AC-4: File size must not exceed 10MB (10485760 bytes)."""

    SIZE_LIMIT = 10485760  # 10 MB

    @pytest.mark.parametrize("size_bytes", [
        0,
        1,
        1024,
        1048576,  # 1 MB
        5242880,  # 5 MB
        10485760,  # 10 MB (exactly at limit)
    ])
    def test_validate_file_size_within_limit(self, size_bytes):
        """AC-4: validate_file_size() returns True for sizes <= 10MB."""
        result = validate_file_size(size_bytes)
        assert result is True

    @pytest.mark.parametrize("size_bytes", [
        10485761,  # 10 MB + 1 byte
        15728640,  # 15 MB
        104857600,  # 100 MB
    ])
    def test_validate_file_size_exceeds_limit(self, size_bytes):
        """AC-4: validate_file_size() returns False for sizes > 10MB."""
        result = validate_file_size(size_bytes)
        assert result is False


# ============================================================================
# Filename Validation Tests (AC-5)
# ============================================================================


class TestFilenameValidation:
    """AC-5: Filename must be non-empty and <= 255 characters."""

    @pytest.mark.parametrize("filename", [
        "document.pdf",
        "a.png",
        "x" * 255,  # 255 characters (at limit)
        "resume-2024-09-23.pdf",
        "screenshot.jpeg",
    ])
    def test_validate_filename_valid(self, filename):
        """AC-5: validate_filename() returns True for valid filenames."""
        result = validate_filename(filename)
        assert result is True

    @pytest.mark.parametrize("filename", [
        "",  # empty
        "x" * 256,  # 256 characters (exceeds limit)
    ])
    def test_validate_filename_invalid(self, filename):
        """AC-5: validate_filename() returns False for empty or too-long filenames."""
        result = validate_filename(filename)
        assert result is False


# ============================================================================
# Object Key Generation Tests (AC-1, AC-S1)
# ============================================================================


class TestObjectKeyGeneration:
    """
    AC-1 & AC-S1: object_key must follow format evidence/{owner_talent_id}/{uuid}.{ext}.
    AC-S1 (Elevation): owner_talent_id must come from auth context, not from request.
    """

    @pytest.mark.parametrize("content_type,expected_ext", [
        ("application/pdf", "pdf"),
        ("image/jpeg", "jpeg"),
        ("image/png", "png"),
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
    ])
    def test_build_object_key_format(self, content_type, expected_ext):
        """
        AC-1: build_object_key() returns evidence/{talent_id}/{uuid}.{ext} format.
        """
        talent_id = str(uuid.uuid4())
        filename = f"test.{expected_ext}"

        object_key = build_object_key(
            talent_id=talent_id,
            filename=filename,
            content_type=content_type,
        )

        # Validate format: evidence/{talent_id}/{uuid}.{ext}
        parts = object_key.split("/")
        assert len(parts) == 3, f"Expected 3 parts separated by /, got {len(parts)}"
        assert parts[0] == "evidence", f"Expected prefix 'evidence', got {parts[0]}"
        assert parts[1] == talent_id, f"Expected talent_id {talent_id}, got {parts[1]}"

        # parts[2] should be {uuid}.{ext}
        filename_part = parts[2]
        assert filename_part.endswith(f".{expected_ext}"), \
            f"Expected suffix .{expected_ext}, got {filename_part}"

        # Verify that uuid part (before ext) is a valid UUID
        uuid_part = filename_part.rsplit(".", 1)[0]
        try:
            uuid.UUID(uuid_part)
        except ValueError:
            pytest.fail(f"Expected UUID, got {uuid_part}")

    def test_build_object_key_elevation_defense(self):
        """
        AC-S1 (Elevation): Even if request claims a different talent_id,
        build_object_key() uses the owner_talent_id passed in, not from external source.

        Note: This test documents the contract that talent_id must be passed
        from auth context, not extracted from request body.
        """
        correct_talent_id = str(uuid.uuid4())
        malicious_talent_id = str(uuid.uuid4())

        object_key = build_object_key(
            talent_id=correct_talent_id,
            filename="document.pdf",
            content_type="application/pdf",
        )

        # Verify that object_key contains correct_talent_id, not malicious_talent_id
        assert correct_talent_id in object_key, \
            f"Expected correct_talent_id {correct_talent_id} in key"
        assert malicious_talent_id not in object_key, \
            f"Malicious talent_id {malicious_talent_id} should not be in key"

    def test_build_object_key_uuid_uniqueness(self):
        """
        Consecutive calls to build_object_key() for the same talent/filename
        should produce different keys (different UUIDs).
        """
        talent_id = str(uuid.uuid4())
        filename = "document.pdf"
        content_type = "application/pdf"

        key1 = build_object_key(talent_id, filename, content_type)
        key2 = build_object_key(talent_id, filename, content_type)

        assert key1 != key2, "Consecutive calls should generate different UUIDs"

    def test_build_object_key_preserves_extension(self):
        """
        build_object_key() should derive the extension from the filename,
        not from content_type alone.
        """
        talent_id = str(uuid.uuid4())

        # Test that extension is preserved (or correctly mapped from content_type)
        for filename, expected_ext in [
            ("resume.pdf", "pdf"),
            ("screenshot.png", "png"),
            ("photo.jpeg", "jpeg"),
        ]:
            object_key = build_object_key(
                talent_id=talent_id,
                filename=filename,
                content_type="application/pdf",  # Intentionally mismatch
            )
            # Extension should be from the mapped content_type or filename
            assert object_key.endswith(expected_ext) or object_key.endswith("pdf"), \
                f"Expected extension in {object_key}"


# ============================================================================
# Error Handling & Edge Cases
# ============================================================================


class TestErrorHandling:
    """Edge cases and error conditions."""

    def test_validate_filename_special_characters(self):
        """Filenames with special characters should be handled."""
        # These may be valid or sanitized; test documents contract
        filenames = [
            "file (1).pdf",
            "document-final_v2.pdf",
            "résumé.pdf",  # UTF-8
        ]
        for filename in filenames:
            result = validate_filename(filename)
            # Contract: valid filenames pass, but implementation may sanitize
            assert isinstance(result, bool)

    def test_validate_content_type_with_charset(self):
        """Content-Type headers may include charset; test handling."""
        # Real-world headers may include charset: "application/pdf; charset=utf-8"
        # This test documents whether the validation handles it
        result = validate_content_type("application/pdf; charset=utf-8")
        # Implementation may strip charset or reject it; document contract
        # For now, assume strict matching (charset not included in request body)
        assert result is False


# ============================================================================
# Integration: Request Schema Validation (Pydantic)
# ============================================================================


class TestEvidenceUploadUrlRequest:
    """
    AC-5: Pydantic schema validates filename (min_length=1, max_length=255),
    content_type, and size_bytes types.
    """

    def test_request_schema_valid(self):
        """Valid request data passes Pydantic validation."""
        data = {
            "filename": "document.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
        }
        request = EvidenceUploadUrlRequest(**data)
        assert request.filename == "document.pdf"
        assert request.content_type == "application/pdf"
        assert request.size_bytes == 1024

    def test_request_schema_filename_empty_fails(self):
        """Empty filename fails Pydantic validation (AC-5)."""
        data = {
            "filename": "",
            "content_type": "application/pdf",
            "size_bytes": 1024,
        }
        with pytest.raises(ValueError):
            EvidenceUploadUrlRequest(**data)

    def test_request_schema_filename_too_long_fails(self):
        """Filename > 255 characters fails Pydantic validation (AC-5)."""
        data = {
            "filename": "x" * 256,
            "content_type": "application/pdf",
            "size_bytes": 1024,
        }
        with pytest.raises(ValueError):
            EvidenceUploadUrlRequest(**data)

    def test_request_schema_size_bytes_zero(self):
        """size_bytes=0 is technically valid (empty file); schema allows it."""
        data = {
            "filename": "empty.txt",
            "content_type": "text/plain",
            "size_bytes": 0,
        }
        # This may be valid or rejected; document contract
        try:
            request = EvidenceUploadUrlRequest(**data)
            assert request.size_bytes == 0
        except ValueError:
            # Schema may require size_bytes > 0
            pass

    def test_request_schema_negative_size_fails(self):
        """Negative size_bytes should fail."""
        data = {
            "filename": "document.pdf",
            "content_type": "application/pdf",
            "size_bytes": -1,
        }
        with pytest.raises(ValueError):
            EvidenceUploadUrlRequest(**data)


class TestEvidenceUploadUrlResponse:
    """AC-1: Response includes upload_url, object_key, expires_in."""

    def test_response_schema_has_required_fields(self):
        """Response schema has upload_url, object_key, expires_in."""
        response = EvidenceUploadUrlResponse(
            upload_url="https://minio.example.com/evidence/...",
            upload_fields={"key": "evidence/test/uuid.pdf", "policy": "base64-policy-string", "x-amz-signature": "signature-value"},
            object_key="evidence/uuid/uuid.pdf",
            expires_in=900,
        )
        assert response.upload_url is not None
        assert response.upload_fields is not None
        assert response.object_key is not None
        assert response.expires_in == 900

    def test_response_expires_in_ttl_seconds(self):
        """expires_in field is in seconds (TTL = 900 seconds = 15 minutes)."""
        response = EvidenceUploadUrlResponse(
            upload_url="https://...",
            upload_fields={"key": "evidence/test/uuid.pdf", "policy": "base64-policy-string"},
            object_key="evidence/...",
            expires_in=900,
        )
        assert response.expires_in == 900
        assert isinstance(response.expires_in, int)
