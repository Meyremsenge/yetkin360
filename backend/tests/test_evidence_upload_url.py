"""
Integration tests for POST /evidence/upload-url endpoint.

PLAN 2.5 (YET-82, YET-83). Covers happy path and error handling:
- AC-1: Happy path — authenticated talent receives presigned URL
- AC-2: Unauthenticated → 401
- AC-3: Unsupported content_type → 422
- AC-4: File size > 10MB → 422
- AC-5: Invalid filename → 422
- AC-6: MinIO unavailable → 503
- AC-8: Presigned URL expires_in = 900 seconds

Integration tests use:
- Real PostgreSQL session (from conftest.py fixture)
- TestClient with dependency override for session
- Real access token cookies for auth (httpOnly)
- Mock MinIO client (patch) for failure scenarios
- Real schema validation (Pydantic)

Each test is independent and uses session fixture for isolation + rollback.
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.core.security import encode_access_token
from app.main import app
from app.models import User


@pytest.fixture
def client_with_db(session):
    """
    TestClient with session override + real access token cookies.
    Tests must call set_auth_cookies(client, user) to authenticate.
    """
    def override_get_session():
        return session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def set_auth_cookies(client: TestClient, user: User) -> None:
    """Set real access token + CSRF token cookies on client."""
    access_token = encode_access_token(user.id)
    client.cookies.set("access_token", access_token)
    # CSRF token: random value, must match X-CSRF-Token header in POST requests
    client.cookies.set("csrf_token", "test-csrf-token")


# ============================================================================
# AC-1: Happy Path — Authenticated Talent Receives Upload URL
# ============================================================================


class TestHappyPath:
    """AC-1: Valid request from authenticated talent returns 200 + presigned URL."""

    def test_happy_path_returns_upload_url(self, user_talent_a, talent_a, client_with_db):
        """
        AC-1: Authenticated talent posts valid request, receives:
        - HTTP 200
        - {upload_url: str, object_key: str, expires_in: 900}
        """
        set_auth_cookies(client_with_db, user_talent_a)
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "resume.pdf",
                "content_type": "application/pdf",
                "size_bytes": 2048,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 200
        body = response.json()

        # Verify response fields
        assert "upload_url" in body
        assert "object_key" in body
        assert "expires_in" in body

        # Verify types and values
        assert isinstance(body["upload_url"], str)
        assert isinstance(body["object_key"], str)
        assert isinstance(body["expires_in"], int)
        assert body["expires_in"] == 900

    def test_happy_path_object_key_format(self, user_talent_a, talent_a, client_with_db):
        """
        AC-1: object_key follows format evidence/{talent_id}/{uuid}.{ext}.
        """
        set_auth_cookies(client_with_db, user_talent_a)
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "document.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 200
        object_key = response.json()["object_key"]

        # Validate format
        parts = object_key.split("/")
        assert len(parts) == 3, f"Expected 3 parts, got {len(parts)}"
        assert parts[0] == "evidence"
        assert parts[1] == str(talent_a.id), f"Expected talent_a.id, got {parts[1]}"

        # Validate uuid.ext format
        filename_part = parts[2]
        assert filename_part.endswith(".pdf")
        uuid_part = filename_part.rsplit(".", 1)[0]
        try:
            uuid.UUID(uuid_part)
        except ValueError:
            pytest.fail(f"Expected UUID in {filename_part}")

    def test_happy_path_multiple_content_types(self, user_talent_a, talent_a, client_with_db):
        """AC-1: Happy path works for all allowed content types."""
        set_auth_cookies(client_with_db, user_talent_a)
        test_cases = [
            ("resume.pdf", "application/pdf", 1024),
            ("photo.jpeg", "image/jpeg", 512),
            ("screenshot.png", "image/png", 2048),
            ("document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 4096),
        ]

        for filename, content_type, size in test_cases:
            response = client_with_db.post(
                "/evidence/upload-url",
                json={
                    "filename": filename,
                    "content_type": content_type,
                    "size_bytes": size,
                },
                headers={"X-CSRF-Token": "test-csrf-token"},
            )
            assert response.status_code == 200, f"Failed for {content_type}"
            body = response.json()
            assert "upload_url" in body
            assert "object_key" in body


# ============================================================================
# AC-2: Unauthenticated Request → 401
# ============================================================================


class TestUnauthenticatedRequest:
    """AC-2: Request without auth cookie returns 401."""

    def test_no_auth_cookie_returns_401(self, client_with_db):
        """AC-2: Missing access_token cookie returns 401."""
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "document.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
        )
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client_with_db):
        """AC-2: Invalid access token returns 401."""
        client_with_db.cookies.set("access_token", "invalid-token-value")
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "document.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
        )
        assert response.status_code == 401


# ============================================================================
# AC-3: Content-Type Validation → 422 UNSUPPORTED_CONTENT_TYPE
# ============================================================================


class TestContentTypeValidation:
    """AC-3: Disallowed content types return 422 + UNSUPPORTED_CONTENT_TYPE."""

    @pytest.mark.parametrize("content_type", [
        "application/json",
        "text/plain",
        "text/html",
        "video/mp4",
        "application/x-executable",
        "image/gif",
        "application/zip",
    ])
    def test_unsupported_content_type_returns_422(self, user_talent_a, talent_a, client_with_db, content_type):
        """AC-3: Each disallowed content type returns 422."""
        set_auth_cookies(client_with_db, user_talent_a)
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "file.bin",
                "content_type": content_type,
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 422
        body = response.json()
        # Error response should have code field
        assert "code" in body or "error_code" in body


# ============================================================================
# AC-4: File Size Validation → 422 FILE_TOO_LARGE
# ============================================================================


class TestFileSizeValidation:
    """AC-4: size_bytes > 10485760 (10MB) returns 422 + FILE_TOO_LARGE."""

    def test_size_exactly_10mb_accepted(self, user_talent_a, talent_a, client_with_db):
        """AC-4: size_bytes = 10485760 is accepted (200)."""
        set_auth_cookies(client_with_db, user_talent_a)
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "large.pdf",
                "content_type": "application/pdf",
                "size_bytes": 10485760,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 200

    @pytest.mark.parametrize("size_bytes", [
        10485761,  # 10MB + 1
        15728640,  # 15MB
        104857600,  # 100MB
    ])
    def test_size_exceeds_10mb_returns_422(self, user_talent_a, talent_a, client_with_db, size_bytes):
        """AC-4: Each size > 10MB returns 422."""
        set_auth_cookies(client_with_db, user_talent_a)
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "huge.pdf",
                "content_type": "application/pdf",
                "size_bytes": size_bytes,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 422
        body = response.json()
        assert "code" in body or "error_code" in body


# ============================================================================
# AC-5: Filename Validation → 422 (Pydantic)
# ============================================================================


class TestFilenameValidation:
    """AC-5: Invalid filenames (empty or > 255 chars) return 422."""

    def test_empty_filename_returns_422(self, user_talent_a, talent_a, client_with_db):
        """AC-5: Empty filename returns 422."""
        set_auth_cookies(client_with_db, user_talent_a)
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 422

    def test_filename_too_long_returns_422(self, user_talent_a, talent_a, client_with_db):
        """AC-5: Filename > 255 characters returns 422."""
        set_auth_cookies(client_with_db, user_talent_a)
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "x" * 256,
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 422

    def test_filename_max_length_accepted(self, user_talent_a, talent_a, client_with_db):
        """AC-5: Filename with 255 characters is accepted."""
        set_auth_cookies(client_with_db, user_talent_a)
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "x" * 255,
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 200


# ============================================================================
# AC-6: Storage Unavailable → 503 STORAGE_UNAVAILABLE
# ============================================================================


class TestStorageUnavailable:
    """
    AC-6: When MinIO/S3 is unreachable, return 503 + STORAGE_UNAVAILABLE.

    This test mocks the storage service to simulate connection failure.
    """

    def test_minio_connection_error_returns_503(self, user_talent_a, talent_a, client_with_db):
        """
        AC-6: MinIO connection error is caught and converted to 503.

        Mock the storage service to raise a connection error.
        """
        set_auth_cookies(client_with_db, user_talent_a)
        with patch("app.api.evidence.generate_presigned_post") as mock_presigned:
            # Simulate MinIO connection error
            from botocore.exceptions import EndpointConnectionError
            mock_presigned.side_effect = EndpointConnectionError(endpoint_url="http://minio:9000")

            response = client_with_db.post(
                "/evidence/upload-url",
                json={
                    "filename": "document.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 1024,
                },
                headers={"X-CSRF-Token": "test-csrf-token"},
            )
            assert response.status_code == 503
            body = response.json()
            assert "code" in body
            assert body.get("code") == "STORAGE_UNAVAILABLE" or "UNAVAILABLE" in body.get("code", "")

    def test_minio_timeout_returns_503(self, user_talent_a, talent_a, client_with_db):
        """AC-6: MinIO timeout is converted to 503."""
        set_auth_cookies(client_with_db, user_talent_a)
        with patch("app.api.evidence.generate_presigned_post") as mock_presigned:
            from botocore.exceptions import ConnectTimeoutError
            mock_presigned.side_effect = ConnectTimeoutError(endpoint_url="http://minio:9000")

            response = client_with_db.post(
                "/evidence/upload-url",
                json={
                    "filename": "document.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 1024,
                },
                headers={"X-CSRF-Token": "test-csrf-token"},
            )
            assert response.status_code == 503


# ============================================================================
# AC-8: Presigned URL Expiration (TTL = 900 seconds)
# ============================================================================


class TestPresignedUrlTtl:
    """AC-8: Presigned URL includes expires_in = 900 seconds (15 minutes)."""

    def test_expires_in_is_900_seconds(self, user_talent_a, talent_a, client_with_db):
        """AC-8: Every successful response includes expires_in: 900."""
        set_auth_cookies(client_with_db, user_talent_a)
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "document.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["expires_in"] == 900


# ============================================================================
# AC-S4: Error Response Info Disclosure Prevention
# ============================================================================


class TestErrorResponseSafety:
    """
    AC-S4: Error responses must not leak MinIO details, buckets, endpoints,
    or internal stack traces. Only include 'code' and 'message'.
    """

    def test_error_response_has_required_fields(self, user_talent_a, talent_a, client_with_db):
        """AC-S4: Error responses include code, message, request_id."""
        set_auth_cookies(client_with_db, user_talent_a)
        # Trigger a 422 error
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "test.exe",
                "content_type": "application/x-executable",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 422
        body = response.json()

        # Verify structure: {code, message, request_id}
        assert "code" in body
        assert "message" in body
        assert "request_id" in body

    def test_error_response_no_minio_leakage(self, user_talent_a, talent_a, client_with_db):
        """AC-S4: Error responses do not expose MinIO internals."""
        set_auth_cookies(client_with_db, user_talent_a)
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "file.bin",
                "content_type": "application/octet-stream",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        body = response.json()
        response_text = str(body).lower()

        # Forbidden keywords in error messages
        forbidden = ["minio", "bucket", "endpoint", "traceback", "exception", "stack"]
        for keyword in forbidden:
            assert keyword not in response_text, \
                f"Error response leaked internal detail: {keyword}"

    def test_error_response_no_stack_trace(self, user_talent_a, talent_a, client_with_db):
        """AC-S4: Error responses do not include Python stack traces."""
        set_auth_cookies(client_with_db, user_talent_a)
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "file.bin",
                "content_type": "application/zip",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        body = response.json()
        response_text = str(body)

        # Stack trace patterns
        assert "Traceback" not in response_text
        assert ".py" not in response_text or "line" not in response_text


# ============================================================================
# AC-S1: Elevation Prevention (Talent Cannot Forge Another's Namespace)
# ============================================================================


class TestElevationPrevention:
    """
    AC-S1: Talent A's authentication context is used for object_key,
    not any talent_id in the request body (if it exists).
    """

    def test_object_key_uses_auth_context_talent_id(self, user_talent_a, talent_a, user_talent_b, talent_b, client_with_db):
        """
        AC-S1: object_key always uses authenticated user's talent_id,
        never from request body.
        """
        set_auth_cookies(client_with_db, user_talent_a)
        # Talent A makes request
        response = client_with_db.post(
            "/evidence/upload-url",
            json={
                "filename": "document.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 200
        object_key = response.json()["object_key"]

        # Verify it uses talent_a's ID
        assert str(talent_a.id) in object_key
        # Verify it does NOT use talent_b's ID
        assert str(talent_b.id) not in object_key
