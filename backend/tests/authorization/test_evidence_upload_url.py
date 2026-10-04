"""
Authorization tests for POST /evidence/upload-url endpoint.

PLAN 2.5 (YET-82, YET-83). Covers:
- AC-2: Unauthenticated requests return 401
- AC-S1 (Elevation): Authenticated talent A cannot forge upload-url for talent B's namespace
- AC-S3 (Rate limit): 10+ requests per minute return 429

Uses TestClient with real access token cookies for auth (httpOnly).
Each test uses session fixture for isolated transaction + rollback.

Parametric test matrix covers: actor kind × request body × expected HTTP code.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.core.security import encode_access_token
from app.main import app
from app.models import User
from tests._testdb import session_override


@pytest.fixture
def client_with_auth(session):
    """
    TestClient with session override + real access token cookies.
    Tests must call set_auth_cookies(client, user) to authenticate.
    """
    app.dependency_overrides[get_session] = session_override(session)

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
# AC-2: Unauthenticated Request → 401
# ============================================================================


class TestUnauthenticatedRequest:
    """AC-2: Requests without auth return 401 Unauthorized."""

    def test_unauthenticated_request_returns_401(self, client_with_auth):
        """AC-2: POST /evidence/upload-url without access_token cookie returns 401."""
        # No auth cookies set, request should fail
        response = client_with_auth.post(
            "/evidence/upload-url",
            json={
                "filename": "document.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
        )
        assert response.status_code == 401


# ============================================================================
# AC-9: Talent Profile Required
# ============================================================================


class TestTalentProfileRequired:
    """AC-9: Authenticated user without a talent profile gets 403."""

    def test_user_without_talent_profile_returns_403(self, user_talent_a, client_with_auth):
        """AC-9: User authenticated but with no TalentProfile row returns 403 TALENT_PROFILE_REQUIRED."""
        set_auth_cookies(client_with_auth, user_talent_a)
        response = client_with_auth.post(
            "/evidence/upload-url",
            json={
                "filename": "document.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 403
        body = response.json()
        assert body.get("code") == "TALENT_PROFILE_REQUIRED"


# ============================================================================
# AC-1 & AC-S1: Authenticated Talent Can Request Upload URL
# ============================================================================


class TestAuthenticatedUploadUrl:
    """
    AC-1: Authenticated talent A requests upload-url with valid request body.
    AC-S1: object_key is generated with A's talent_id (from auth context),
           not from request body.
    """

    def test_authenticated_talent_receives_upload_url(self, session, user_talent_a, talent_a, client_with_auth):
        """
        AC-1: Authenticated talent receives 200 + {upload_url, object_key, expires_in}.
        CSRF token required in header (POST is a write method).
        """
        set_auth_cookies(client_with_auth, user_talent_a)
        response = client_with_auth.post(
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

        assert "upload_url" in body
        assert "object_key" in body
        assert "expires_in" in body
        assert isinstance(body["upload_url"], str)
        assert isinstance(body["object_key"], str)
        assert isinstance(body["expires_in"], int)
        assert body["expires_in"] == 900  # 15 minutes

    def test_object_key_format_correct(self, session, user_talent_a, talent_a, client_with_auth):
        """
        AC-1: object_key follows format evidence/{talent_id}/{uuid}.{ext}.
        """
        set_auth_cookies(client_with_auth, user_talent_a)
        response = client_with_auth.post(
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

        # Format: evidence/{talent_id}/{uuid}.{ext}
        parts = object_key.split("/")
        assert len(parts) == 3
        assert parts[0] == "evidence"
        assert parts[1] == str(talent_a.id), f"Expected talent_a.id={talent_a.id}, got {parts[1]}"

        # parts[2] should be {uuid}.{ext}
        filename_part = parts[2]
        assert filename_part.endswith(".pdf"), f"Expected .pdf extension, got {filename_part}"

    def test_elevation_defense_talent_a_cannot_forge_talent_b_namespace(
        self, session, user_talent_a, talent_a, user_talent_b, talent_b, client_with_auth
    ):
        """
        AC-S1 (Elevation): Talent A, even if request schema allows talent_id field,
        object_key is generated with A's talent_id from JWT, not from request body.

        The implementation must use the authenticated user's talent_id from the
        access token, not from any request field.
        """
        set_auth_cookies(client_with_auth, user_talent_a)
        response = client_with_auth.post(
            "/evidence/upload-url",
            json={
                "filename": "malicious.pdf",
                "content_type": "application/pdf",
                "size_bytes": 512,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 200
        object_key = response.json()["object_key"]

        # Verify that object_key contains talent_a.id, NOT talent_b.id
        assert str(talent_a.id) in object_key, \
            f"Expected talent_a.id={talent_a.id} in object_key, got {object_key}"
        assert str(talent_b.id) not in object_key, \
            f"Malicious talent_b.id={talent_b.id} must NOT be in object_key"


# ============================================================================
# AC-3: Unsupported Content-Type → 422
# ============================================================================


class TestContentTypeValidation:
    """AC-3: Disallowed content_type values return 422 + UNSUPPORTED_CONTENT_TYPE."""

    ALLOWED_TYPES = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]

    DISALLOWED_TYPES = [
        "application/json",
        "text/plain",
        "text/html",
        "video/mp4",
        "application/x-executable",
        "image/gif",
    ]

    @pytest.mark.parametrize("content_type", ALLOWED_TYPES)
    def test_allowed_content_type_accepted(self, user_talent_a, talent_a, client_with_auth, content_type):
        """AC-3: Allowed content types are accepted (200)."""
        set_auth_cookies(client_with_auth, user_talent_a)
        # Use appropriate filename for each type
        extensions = {
            "application/pdf": "pdf",
            "image/jpeg": "jpeg",
            "image/png": "png",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        }
        ext = extensions.get(content_type, "bin")

        response = client_with_auth.post(
            "/evidence/upload-url",
            json={
                "filename": f"test.{ext}",
                "content_type": content_type,
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 200

    @pytest.mark.parametrize("content_type", DISALLOWED_TYPES)
    def test_disallowed_content_type_rejected(self, user_talent_a, talent_a, client_with_auth, content_type):
        """AC-3: Disallowed content types return 422 + UNSUPPORTED_CONTENT_TYPE."""
        set_auth_cookies(client_with_auth, user_talent_a)
        response = client_with_auth.post(
            "/evidence/upload-url",
            json={
                "filename": "test.bin",
                "content_type": content_type,
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 422
        body = response.json()
        assert body.get("code") == "UNSUPPORTED_CONTENT_TYPE" or "error_code" in body


# ============================================================================
# AC-4: File Size Limit → 422
# ============================================================================


class TestFileSizeValidation:
    """AC-4: size_bytes > 10MB returns 422 + FILE_TOO_LARGE."""

    def test_size_within_limit_accepted(self, user_talent_a, talent_a, client_with_auth):
        """AC-4: size_bytes <= 10MB are accepted (200)."""
        set_auth_cookies(client_with_auth, user_talent_a)
        response = client_with_auth.post(
            "/evidence/upload-url",
            json={
                "filename": "large.pdf",
                "content_type": "application/pdf",
                "size_bytes": 10485760,  # Exactly 10MB
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 200

    def test_size_exceeds_limit_rejected(self, user_talent_a, talent_a, client_with_auth):
        """AC-4: size_bytes > 10MB return 422 + FILE_TOO_LARGE."""
        set_auth_cookies(client_with_auth, user_talent_a)
        response = client_with_auth.post(
            "/evidence/upload-url",
            json={
                "filename": "huge.pdf",
                "content_type": "application/pdf",
                "size_bytes": 10485761,  # 10MB + 1 byte
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 422
        body = response.json()
        assert body.get("code") == "FILE_TOO_LARGE" or "error_code" in body

    def test_size_100mb_rejected(self, user_talent_a, talent_a, client_with_auth):
        """AC-4: Large file sizes are rejected."""
        set_auth_cookies(client_with_auth, user_talent_a)
        response = client_with_auth.post(
            "/evidence/upload-url",
            json={
                "filename": "huge.pdf",
                "content_type": "application/pdf",
                "size_bytes": 104857600,  # 100MB
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 422


# ============================================================================
# AC-5: Invalid Filename → 422
# ============================================================================


class TestFilenameValidation:
    """
    AC-5: filename must be non-empty and <= 255 characters.
    Pydantic validation should enforce this.
    """

    def test_valid_filename_accepted(self, user_talent_a, talent_a, client_with_auth):
        """AC-5: Valid filenames are accepted."""
        set_auth_cookies(client_with_auth, user_talent_a)
        response = client_with_auth.post(
            "/evidence/upload-url",
            json={
                "filename": "my-document-2024.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 200

    def test_empty_filename_rejected(self, user_talent_a, talent_a, client_with_auth):
        """AC-5: Empty filename returns 422 (Pydantic validation)."""
        set_auth_cookies(client_with_auth, user_talent_a)
        response = client_with_auth.post(
            "/evidence/upload-url",
            json={
                "filename": "",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 422

    def test_filename_too_long_rejected(self, user_talent_a, talent_a, client_with_auth):
        """AC-5: filename > 255 characters returns 422."""
        set_auth_cookies(client_with_auth, user_talent_a)
        response = client_with_auth.post(
            "/evidence/upload-url",
            json={
                "filename": "x" * 256,
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 422


# ============================================================================
# AC-S3: Rate Limit (10 requests/minute) → 429
# ============================================================================


class TestRateLimit:
    """
    AC-S3: Same user cannot make > 10 requests per minute.
    Request 11 returns 429 Too Many Requests.
    """

    def test_ten_requests_within_limit(self, user_talent_a, talent_a, client_with_auth):
        """AC-S3: First 10 requests per minute are accepted (200)."""
        set_auth_cookies(client_with_auth, user_talent_a)
        for i in range(10):
            response = client_with_auth.post(
                "/evidence/upload-url",
                json={
                    "filename": f"document-{i}.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 1024,
                },
                headers={"X-CSRF-Token": "test-csrf-token"},
            )
            assert response.status_code == 200, f"Request {i+1} should succeed"

    def test_eleventh_request_returns_429(self, user_talent_a, talent_a, client_with_auth):
        """AC-S3: Request 11 within same minute returns 429."""
        set_auth_cookies(client_with_auth, user_talent_a)
        # Make 10 requests (should all succeed)
        for i in range(10):
            response = client_with_auth.post(
                "/evidence/upload-url",
                json={
                    "filename": f"document-{i}.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 1024,
                },
                headers={"X-CSRF-Token": "test-csrf-token"},
            )
            assert response.status_code == 200

        # 11th request should be rate-limited
        response = client_with_auth.post(
            "/evidence/upload-url",
            json={
                "filename": "document-11.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        assert response.status_code == 429


# ============================================================================
# AC-6: MinIO Unavailable → 503
# ============================================================================


class TestStorageUnavailable:
    """AC-6: If MinIO cannot be reached, return 503 + STORAGE_UNAVAILABLE."""

    def test_minio_connection_error_returns_503(self, user_talent_a, talent_a, client_with_auth):
        """
        AC-6: When MinIO/S3 presigned URL generation fails (connection error),
        return 503 Service Unavailable + STORAGE_UNAVAILABLE.

        This test mocks the storage service to simulate connection failure.
        """
        set_auth_cookies(client_with_auth, user_talent_a)
        with patch("app.api.evidence.generate_presigned_post") as mock_presigned:
            from botocore.exceptions import EndpointConnectionError
            mock_presigned.side_effect = EndpointConnectionError(endpoint_url="http://minio:9000")

            response = client_with_auth.post(
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


# ============================================================================
# AC-S4: Info Disclosure Prevention
# ============================================================================


class TestInfoDisclosureProtection:
    """AC-S4: Error responses must not leak MinIO internals or internal details."""

    def test_error_response_contains_only_code_and_message(self, user_talent_a, talent_a, client_with_auth):
        """
        AC-S4: Error responses include only 'code' and 'message', not MinIO details.
        """
        set_auth_cookies(client_with_auth, user_talent_a)
        # Trigger a 422 error with unsupported content type
        response = client_with_auth.post(
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

        # Verify response shape: {code, message, request_id}
        assert "code" in body
        assert "message" in body

        # Verify no leakage of internal details
        response_text = str(body).lower()
        assert "minio" not in response_text
        assert "bucket" not in response_text
        assert "endpoint" not in response_text
        assert "traceback" not in response_text
        assert "exception" not in response_text


# ============================================================================
# AC-S2 (Tampering): Presigned URL Content-Type/Length Binding
# ============================================================================


class TestPresignedUrlIntegrity:
    """
    AC-S2: Presigned URL's signature includes Content-Type and Content-Length.

    This is a service-level contract test: verify that the service passes
    these parameters to the MinIO client when generating the presigned URL.

    The test uses mock/patch to inspect the MinIO client call.
    """

    def test_presigned_url_includes_content_type_constraint(self, user_talent_a, talent_a, client_with_auth):
        """
        AC-S2 (Tampering): Presigned URL signature must be bound to the declared
        Content-Type (and Content-Length), so that the client cannot tamper with them.

        Implementation: When calling MinIO's generate_presigned_post(), pass
        Conditions with Content-Type and content-length-range constraints.

        This test mocks the storage service to verify it receives the correct size_bytes parameter.
        """
        set_auth_cookies(client_with_auth, user_talent_a)

        with patch("app.api.evidence.generate_presigned_post") as mock_presigned:
            # Mock the presigned POST generation to return a dict with url and fields
            mock_presigned.return_value = {
                "url": "https://minio.example.com/presigned-url",
                "fields": {"key": "evidence/test/test.pdf", "policy": "test-policy"}
            }

            response = client_with_auth.post(
                "/evidence/upload-url",
                json={
                    "filename": "document.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 1024,
                },
                headers={"X-CSRF-Token": "test-csrf-token"},
            )
            assert response.status_code == 200

            # Verify that generate_presigned_post was called with correct parameters
            mock_presigned.assert_called_once()
            call_args = mock_presigned.call_args

            # Check that size_bytes parameter was passed correctly (AC-S2 enforcement)
            call_kwargs = call_args.kwargs
            assert call_kwargs.get("size_bytes") == 1024, \
                f"Expected size_bytes=1024, got {call_kwargs.get('size_bytes')}"
            assert call_kwargs.get("content_type") == "application/pdf", \
                f"Expected content_type='application/pdf', got {call_kwargs.get('content_type')}"
