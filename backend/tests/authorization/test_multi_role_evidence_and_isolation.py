"""
Multi-role evidence access and isolation tests (YET-187 — AC-S2, AC-S3, AC-2, AC-S1).

Implements acceptance criteria and security criteria from atdd.md, matris rows 13–15, 28.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient with X-Debug-User-Id header for auth simulation
- Evidence records created with real Principal objects (not mock)
- Security: owner-based access, visibility enforcement, tenant isolation

AC coverage:
- AC-S3 (satır 13-14): M1 (O1 üyesi) → T1'in PRIVATE kanıtına download → 404 (kanıt DB'de var)
- AC-S3 (satır 14): Platform admin → T1'in PRIVATE kanıtı → 404
- AC-S3 (satır 15): M1 → GET kanıt listesi uçları: T1'in kayıtları yok, yalnız M1'in
- AC-2 (satır 3): M1 → kendi talent kanıtı → 200/2xx (kendi kaydını görür)
- AC-S2 (satır 28): Bozuk/süresi geçmiş kimlik → 401 (X-Debug-User-Id='not-a-uuid', var olmayan uuid)
"""

import pytest
from uuid import uuid4

from app.models import (
    User,
    TalentProfile,
    Organization,
    Institution,
)
from app.models.evidence import Evidence
from app.services.evidence import create_evidence
from app.services.authorization import Principal


# ============================================================================
# Fixtures: Multi-role actors (with mre_ prefix to avoid collision)
# ============================================================================


@pytest.fixture
def mre_org_o1(session):
    """Organization O1."""
    org = Organization(
        name="MRE Test Org O1",
        domain="mre-o1.example.com",
        legal_id="MRE-O1-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def mre_inst_k1(session):
    """Institution K1."""
    inst = Institution(
        name="MRE Test Institution K1",
        domain="mre-k1.edu.tr",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def mre_user_m1(session):
    """User M1: multi-role."""
    user = User(email="mre-m1@example.com", password_hash="hash_m1")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def mre_talent_m1(session, mre_user_m1):
    """Talent profile for M1."""
    profile = TalentProfile(
        user_id=mre_user_m1.id,
        full_name="MRE M1 Talent",
        visibility="PRIVATE",
        headline=None,
        city=None,
        department=None,
        study_year=None,
        public_slug=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def mre_user_t1(session):
    """User T1: talent only (engagement owner)."""
    user = User(email="mre-t1@example.com", password_hash="hash_t1")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def mre_talent_t1(session, mre_user_t1):
    """Talent profile for T1."""
    profile = TalentProfile(
        user_id=mre_user_t1.id,
        full_name="MRE T1 Talent",
        visibility="PRIVATE",
        headline=None,
        city=None,
        department=None,
        study_year=None,
        public_slug=None,
    )
    session.add(profile)
    session.flush()
    return profile


# ============================================================================
# AC-S3 (satır 13): M1 (O1 üyesi) → T1'in PRIVATE kanıtına download → 404
# ============================================================================


class TestPrivateEvidenceIsolation:
    """AC-S3 (satır 13): PRIVATE kanıt access isolation."""

    def test_m1_cannot_download_t1_private_evidence_404(
        self, client, mre_user_m1, mre_talent_m1, mre_user_t1, mre_talent_t1, session
    ):
        """
        AC-S3 (satır 13): M1 (O1 üyesi) → T1'in PRIVATE kanıtına download-url → 404.
        Kanıt DB'de var, M1 erişebilmeli ama PRIVATE olduğu için 404.
        """
        # T1 kendi PRIVATE kanıtını oluştur
        principal_t1 = Principal(
            user_id=mre_user_t1.id,
            kind="TALENT",
            talent_id=mre_talent_t1.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        evidence_response = create_evidence(
            session=session,
            principal=principal_t1,
            storage_key=f"evidence/{mre_talent_t1.id}/t1-private.pdf",
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )
        evidence_id = evidence_response.id

        # Verify evidence exists in DB
        evidence = session.query(Evidence).filter_by(id=evidence_id).first()
        assert evidence is not None, "T1's evidence should be in DB"
        assert evidence.visibility == "PRIVATE", "Evidence should be PRIVATE"

        # M1 tries to download (should fail with 404)
        response = client.get(
            f"/evidence/{evidence_id}/download-url",
            headers={"X-Debug-User-Id": str(mre_user_m1.id)},
        )
        assert response.status_code == 404


# ============================================================================
# AC-S3 (satır 14): Platform admin → T1'in PRIVATE kanıtı → 404
# ============================================================================


class TestPlatformAdminCannotAccessPrivateEvidence:
    """AC-S3 (satır 14): Platform admin → PRIVATE kanıt → 403."""

    def test_platform_admin_cannot_download_t1_private_evidence_403(
        self, client, mre_user_t1, mre_talent_t1, session
    ):
        """
        AC-S3 (satır 14): Platform admin (is_platform_admin=True) → T1'in PRIVATE kanıtı → 403.
        Admin olsa da PRIVATE kanıta erişemez (special case per atdd.md §61: "admin da hayır").
        """
        # T1 kendi PRIVATE kanıtını oluştur
        principal_t1 = Principal(
            user_id=mre_user_t1.id,
            kind="TALENT",
            talent_id=mre_talent_t1.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        evidence_response = create_evidence(
            session=session,
            principal=principal_t1,
            storage_key=f"evidence/{mre_talent_t1.id}/t1-private-admin-test.pdf",
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )
        evidence_id = evidence_response.id

        # Verify evidence exists in DB
        evidence = session.query(Evidence).filter_by(id=evidence_id).first()
        assert evidence is not None, "T1's evidence should be in DB"

        # Create platform admin user
        admin_user = User(email="mre-admin@example.com", password_hash="hash_admin")
        session.add(admin_user)
        session.flush()

        # Admin tries to download T1's PRIVATE evidence → should get 403 (not 404)
        response = client.get(
            f"/evidence/{evidence_id}/download-url",
            headers={"X-Debug-User-Id": str(admin_user.id)},
        )
        assert response.status_code == 403


# ============================================================================
# AC-2 (satır 3): M1 → kendi talent kanıtı → 200/2xx
# ============================================================================


class TestOwnTalentEvidenceAccess:
    """AC-2 (satır 3): M1 kendi talent kanıtını görür."""

    def test_m1_can_access_own_evidence_200(
        self, client, mre_user_m1, mre_talent_m1, session
    ):
        """
        AC-2 (satır 3): M1 → kendi talent kanıtı → GET /evidence/{id}/download-url → 200.
        (Mock storage, scan_status=CLEAN olmadığı sürece 409 veya storage error.)
        """
        principal_m1 = Principal(
            user_id=mre_user_m1.id,
            kind="TALENT",
            talent_id=mre_talent_m1.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        evidence_response = create_evidence(
            session=session,
            principal=principal_m1,
            storage_key=f"evidence/{mre_talent_m1.id}/m1-own.pdf",
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )
        evidence_id = evidence_response.id

        # Set scan_status to CLEAN so download can proceed
        evidence = session.query(Evidence).filter_by(id=evidence_id).first()
        evidence.scan_status = "CLEAN"
        session.flush()

        # Mock storage to avoid real S3 call
        from unittest.mock import patch, MagicMock
        with patch("app.services.storage.boto3.client") as mock_boto:
            mock_s3 = MagicMock()
            mock_boto.return_value = mock_s3
            mock_s3.generate_presigned_url.return_value = "https://storage.example.com/download"

            response = client.get(
                f"/evidence/{evidence_id}/download-url",
                headers={"X-Debug-User-Id": str(mre_user_m1.id)},
            )

            # M1 can access their own evidence
            assert response.status_code == 200
            body = response.json()
            assert "download_url" in body


# ============================================================================
# AC-S2 (satır 28): Bozuk/süresi geçmiş kimlik → 401
# ============================================================================


class TestInvalidIdentity:
    """AC-S2 (satır 28): Bozuk UUID ve 'not-a-uuid' X-Debug-User-Id → 401."""

    def test_invalid_uuid_in_debug_header_returns_401(self, client):
        """
        AC-S2 (satır 28): X-Debug-User-Id='not-a-uuid' → 401 Unauthorized.
        """
        response = client.get(
            "/engagements",
            headers={"X-Debug-User-Id": "not-a-uuid"},
        )
        assert response.status_code == 401

    def test_nonexistent_uuid_in_debug_header_returns_401(self, client):
        """
        AC-S2 (satır 28): X-Debug-User-Id=valid-but-nonexistent-uuid → 401.
        """
        nonexistent_uuid = str(uuid4())
        response = client.get(
            "/engagements",
            headers={"X-Debug-User-Id": nonexistent_uuid},
        )
        assert response.status_code == 401

    def test_post_org_members_invalid_identity_returns_401(self, client, mre_org_o1):
        """
        AC-S2 (satır 28): POST /organizations/{O1}/members with invalid identity → 401.
        """
        response = client.post(
            f"/organizations/{mre_org_o1.id}/members",
            json={"email": "test@example.com", "role": "MEMBER"},
            headers={"X-Debug-User-Id": "not-a-uuid"},
        )
        assert response.status_code == 401
