"""
Multi-role scope matrix tests (YET-187 — AC-S5, AC-S2, AC-S4, AC-2, AC-S3).

Implements specific acceptance criteria from atdd.md matris rows.
Scope: Rows 6, 9, 12, 15 only; other rows covered by other test files.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient with X-Debug-User-Id header for auth simulation
- Multi-role actors: each has overlapping organization/institution memberships
- Defense-in-depth: server-side authorization verification via scoped_*() and can()
- Tenant/user isolation: ensure client-provided IDs don't override server logic

Matris satırları (docstring'de AC + satır no):
- Satır 6 (AC-S5): yalnız INST_ADMIN kullanıcı → geçiş → reddedilir, DB değişmez
- Satır 9 (AC-S2): M3 (O1 MEMBER) → O3 kaynağı veya başka talent_id → 404
- Satır 12 (AC-S4): M2 → K1 ADMIN-only vs K2 COORDINATOR davranış izole
- Satır 15 (AC-S3): M1 (talent) → T1'in PRIVATE kanıtı → 404; liste uçlarında T1 kayıtları yok
"""

import pytest

from app.models import (
    User,
    TalentProfile,
    Organization,
    Institution,
    OrganizationMember,
    InstitutionMember,
    Engagement,
)
from app.models.evidence import Evidence


# ============================================================================
# Fixtures: Multi-role actors (msm_ prefix: multi-role scope matrix)
# ============================================================================


@pytest.fixture
def msm_org_o1(session):
    """Organization O1."""
    org = Organization(
        name="MSM Test Org O1",
        domain="msm-o1.example.com",
        legal_id="MSM-O1-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def msm_org_o2(session):
    """Organization O2."""
    org = Organization(
        name="MSM Test Org O2",
        domain="msm-o2.example.com",
        legal_id="MSM-O2-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def msm_org_o3(session):
    """Organization O3 (out-of-scope for M3)."""
    org = Organization(
        name="MSM Test Org O3",
        domain="msm-o3.example.com",
        legal_id="MSM-O3-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def msm_inst_k1(session):
    """Institution K1."""
    inst = Institution(
        name="MSM Test Institution K1",
        domain="msm-k1.edu.tr",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def msm_inst_k2(session):
    """Institution K2."""
    inst = Institution(
        name="MSM Test Institution K2",
        domain="msm-k2.edu.tr",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


# ============================================================================
# M2: K1 ADMIN + K2 COORDINATOR + talent (Satır 5-12)
# ============================================================================


@pytest.fixture
def msm_user_m2(session):
    """User M2: multi-role (K1 ADMIN, K2 COORDINATOR)."""
    user = User(email="msm-m2@example.com", password_hash="hash_m2")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def msm_talent_m2(session, msm_user_m2):
    """Talent profile for M2."""
    profile = TalentProfile(
        user_id=msm_user_m2.id,
        full_name="MSM M2 Talent",
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
def msm_m2_inst_k1_admin(session, msm_inst_k1, msm_user_m2):
    """M2 is ADMIN of K1."""
    member = InstitutionMember(
        institution_id=msm_inst_k1.id,
        user_id=msm_user_m2.id,
        role="ADMIN",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def msm_m2_inst_k2_coordinator(session, msm_inst_k2, msm_user_m2):
    """M2 is COORDINATOR of K2."""
    member = InstitutionMember(
        institution_id=msm_inst_k2.id,
        user_id=msm_user_m2.id,
        role="COORDINATOR",
    )
    session.add(member)
    session.flush()
    return member


# ============================================================================
# M3: O1 MEMBER + O2 ADMIN + talent (Satır 9, 12)
# ============================================================================


@pytest.fixture
def msm_user_m3(session):
    """User M3: multi-role (O1 MEMBER, O2 ADMIN)."""
    user = User(email="msm-m3@example.com", password_hash="hash_m3")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def msm_talent_m3(session, msm_user_m3):
    """Talent profile for M3."""
    profile = TalentProfile(
        user_id=msm_user_m3.id,
        full_name="MSM M3 Talent",
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
def msm_m3_org_o1_member(session, msm_org_o1, msm_user_m3):
    """M3 is MEMBER of O1."""
    member = OrganizationMember(
        organization_id=msm_org_o1.id,
        user_id=msm_user_m3.id,
        role="MEMBER",
        status="ACTIVE",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def msm_m3_org_o2_admin(session, msm_org_o2, msm_user_m3):
    """M3 is ADMIN of O2."""
    member = OrganizationMember(
        organization_id=msm_org_o2.id,
        user_id=msm_user_m3.id,
        role="ADMIN",
        status="ACTIVE",
    )
    session.add(member)
    session.flush()
    return member


# ============================================================================
# INST_ADMIN only user (Satır 6)
# ============================================================================


@pytest.fixture
def msm_user_inst_admin(session):
    """User: yalnız K1 INST_ADMIN (başka üyeliği yok)."""
    user = User(email="msm-inst-admin@example.com", password_hash="hash_admin")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def msm_inst_admin_k1_admin(session, msm_inst_k1, msm_user_inst_admin):
    """INST_ADMIN user is ADMIN of K1 (only membership)."""
    member = InstitutionMember(
        institution_id=msm_inst_k1.id,
        user_id=msm_user_inst_admin.id,
        role="ADMIN",
    )
    session.add(member)
    session.flush()
    return member


# ============================================================================
# T1: Talent only (Satır 15)
# ============================================================================


@pytest.fixture
def msm_user_t1(session):
    """User T1: talent only."""
    user = User(email="msm-t1@example.com", password_hash="hash_t1")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def msm_talent_t1(session, msm_user_t1):
    """Talent profile for T1."""
    profile = TalentProfile(
        user_id=msm_user_t1.id,
        full_name="MSM T1 Talent",
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
# Engagements
# ============================================================================


@pytest.fixture
def msm_engagement_m2_talent_k1(session, msm_talent_m2, msm_org_o1, msm_inst_k1):
    """Engagement: M2's own engagement in K1, PENDING_APPROVAL."""
    eng = Engagement(
        talent_id=msm_talent_m2.id,
        organization_id=msm_org_o1.id,
        institution_id=msm_inst_k1.id,
        kind="INTERNSHIP",
        title="M2 K1 Engagement",
        status="PENDING_APPROVAL",
        version=1,
        reason=None,
    )
    session.add(eng)
    session.flush()
    return eng


@pytest.fixture
def msm_engagement_t1_k1(session, msm_talent_t1, msm_org_o1, msm_inst_k1):
    """Engagement: T1's engagement in K1, PENDING_APPROVAL."""
    eng = Engagement(
        talent_id=msm_talent_t1.id,
        organization_id=msm_org_o1.id,
        institution_id=msm_inst_k1.id,
        kind="CAPSTONE",
        title="T1 K1 Engagement",
        status="PENDING_APPROVAL",
        version=1,
        reason=None,
    )
    session.add(eng)
    session.flush()
    return eng


# ============================================================================
# Satır 6 (AC-S5): yalnız INST_ADMIN kullanıcı → geçiş → 403, DB değişmez
# ============================================================================


class TestInstAdminTransitionForbidden:
    """
    AC-S5 (satır 6): Yalnız INST_ADMIN role'ü olan kullanıcı (başka üyeliği yok)
    PENDING_APPROVAL engagement'ında geçiş denediğinde reddedilir.

    INST_ADMIN'e geçiş yetkisi yalnız YET-190'a bırakılır; şu anda yalnız
    COORDINATOR rolü geçişi yapabilir.
    """

    def test_inst_admin_only_transition_engagement_403(
        self, client, msm_user_inst_admin, msm_inst_admin_k1_admin, msm_engagement_t1_k1, session
    ):
        """
        AC-S5 (satır 6): msm_user_inst_admin (yalnız K1 ADMIN) →
        PENDING_APPROVAL engagement'ında geçiş → 403, status ve version DB'de değişmez.
        """
        response = client.post(
            f"/engagements/{msm_engagement_t1_k1.id}/transitions",
            json={"to_status": "ACTIVE", "version": 1},
            headers={"X-Debug-User-Id": str(msm_user_inst_admin.id)},
        )
        # INST_ADMIN yetkisi yalnız ADMIN role'ü, ama geçiş COORDINATOR tarafından yapılır
        # Kullanıcı engagement'a erişebiliyor ama geçişi yapamıyor → 403
        assert response.status_code == 403

        # Verify DB unchanged
        session.expire_all()
        eng = session.query(Engagement).filter_by(id=msm_engagement_t1_k1.id).first()
        assert eng.status == "PENDING_APPROVAL"
        assert eng.version == 1


# ============================================================================
# Satır 9 (AC-S2): M3 (O1 MEMBER) → O3 kaynağı veya başka talent → 404
# ============================================================================


class TestBodyOrganizationIsolation:
    """
    AC-S2 (satır 9): M3 (O1 MEMBER, O2 ADMIN) engagement oluşturma kuralları:

    - M3 kendi talent_id'siyle ANY org için açabilir → 201 (mevcut sözleşme, YET-187 değiştirmez)
    - M3 org üyesi (org_ids'teki org) herhangi bir talent için açabilir → 201
    - M3 üyesi olmayan org + başka talent → 404

    Kaynak sahipliği URL'den değil, oturumdan (DB'den) çıkarılır. İstemci gönderdiği
    ID'ye güvenilmez.
    """

    def test_m3_post_engagement_o3_own_talent_201(
        self, client, msm_user_m3, msm_m3_org_o1_member, msm_m3_org_o2_admin,
        msm_org_o3, msm_talent_m3, session
    ):
        """
        AC-2 sonucu (bilinçli davranış değişikliği): her kullanıcının talent profili vardır;
        org üyesi talent kendi talent_id'siyle herhangi bir org'a engagement açabilir
        (saf talent'ın zaten yapabildiği).

        M3 (O1 MEMBER, O2 ADMIN) POST /engagements kendi talent_id'siyle
        organization_id=O3 (üyesi olmayan org) → 201.
        """
        initial_count = session.query(Engagement).count()

        response = client.post(
            "/engagements",
            json={
                "talent_id": str(msm_talent_m3.id),
                "organization_id": str(msm_org_o3.id),
                "kind": "INTERNSHIP",
                "title": "M3 Self O3 Engagement",
            },
            headers={"X-Debug-User-Id": str(msm_user_m3.id)},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["talent_id"] == str(msm_talent_m3.id)

        # Verify engagement created
        session.expire_all()
        final_count = session.query(Engagement).count()
        assert final_count == initial_count + 1

    def test_m3_post_engagement_o2_other_talent_201(
        self, client, msm_user_m3, msm_m3_org_o1_member, msm_m3_org_o2_admin,
        msm_org_o2, msm_talent_t1, session
    ):
        """
        AC-S2 (satır 9): M3 POST /engagements body'de talent_id=T1 (başka talent),
        organization_id=O2 (M3 ADMIN) → 201.

        Org üyesi (ADMIN) herhangi bir talent için engagement açabilir.
        """
        initial_count = session.query(Engagement).count()

        response = client.post(
            "/engagements",
            json={
                "talent_id": str(msm_talent_t1.id),
                "organization_id": str(msm_org_o2.id),
                "kind": "INTERNSHIP",
                "title": "M3 T1 O2 Engagement",
            },
            headers={"X-Debug-User-Id": str(msm_user_m3.id)},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["talent_id"] == str(msm_talent_t1.id)

        # Verify engagement created
        session.expire_all()
        final_count = session.query(Engagement).count()
        assert final_count == initial_count + 1

    def test_m3_post_engagement_other_talent_unowned_org_404(
        self, client, msm_user_m3, msm_m3_org_o1_member, msm_m3_org_o2_admin,
        msm_org_o3, msm_talent_m3, msm_talent_t1, session
    ):
        """
        AC-S2 (satır 9): M3 (O1 MEMBER, O2 ADMIN) POST /engagements body'de
        talent_id=T1 (başka talent), organization_id=O3 (M3 üyesi olmayan org) → 404.

        Kural: başka talent + üyesi olmayan org → OrganizationNotFoundError → 404.
        Yanıt: hata gövdesi biçimi {"code":..., "message":...}, O3/T1 sızmaz.
        DB: engagement sayısı değişmez.
        """
        initial_count = session.query(Engagement).count()

        response = client.post(
            "/engagements",
            json={
                "talent_id": str(msm_talent_t1.id),
                "organization_id": str(msm_org_o3.id),
                "kind": "INTERNSHIP",
                "title": "M3 T1 O3 Engagement (should fail)",
            },
            headers={"X-Debug-User-Id": str(msm_user_m3.id)},
        )
        assert response.status_code == 404

        body = response.json()
        assert "code" in body
        assert "message" in body

        # Verify no org/talent details leak in response
        response_str = str(body)
        assert str(msm_org_o3.id) not in response_str
        assert str(msm_talent_t1.id) not in response_str

        # Verify DB unchanged
        session.expire_all()
        final_count = session.query(Engagement).count()
        assert final_count == initial_count


# ============================================================================
# Satır 12 (AC-S4): M2 → K1 ADMIN vs K2 COORDINATOR roll isolation
# ============================================================================


class TestInstitutionRoleIsolation:
    """
    AC-S4 (satır 12): M2 (K1 ADMIN + K2 COORDINATOR) → roller kurum bazlı izole.

    K1'de yalnız ADMIN yetkisi, K2'de yalnız COORDINATOR yetkisi olması gerekir.
    Bir rolün yetkisi diğer kuruma sızmaz.
    """

    def test_m2_k1_admin_cannot_transition_k1_engagement_403(
        self, client, msm_user_m2, msm_talent_m2, msm_m2_inst_k1_admin, msm_m2_inst_k2_coordinator, msm_engagement_t1_k1, session
    ):
        """
        AC-S4 (satır 12): M2 is ADMIN of K1 (not COORDINATOR) →
        K1'deki PENDING_APPROVAL engagement'ı geçiştiremez → 403.

        Geçiş yetkisi yalnız COORDINATOR role'ünden gelir; ADMIN rolü yalnız K1'e aittir,
        K2 uçlarında sızmaz.
        """
        response = client.post(
            f"/engagements/{msm_engagement_t1_k1.id}/transitions",
            json={"to_status": "ACTIVE", "version": 1},
            headers={"X-Debug-User-Id": str(msm_user_m2.id)},
        )
        # M2 is K1 ADMIN (sees engagement) but not COORDINATOR (can't transition) → 403
        assert response.status_code == 403

        # Verify DB unchanged
        session.expire_all()
        eng = session.query(Engagement).filter_by(id=msm_engagement_t1_k1.id).first()
        assert eng.status == "PENDING_APPROVAL"
        assert eng.version == 1

    def test_m2_k2_coordinator_can_transition_k2_engagement_200(
        self, client, msm_user_m2, msm_talent_m2, msm_m2_inst_k1_admin, msm_m2_inst_k2_coordinator, msm_talent_t1,
        msm_org_o1, msm_inst_k2, session
    ):
        """
        AC-S4 (satır 12): M2 is COORDINATOR of K2 → K2'deki engagement'ı geçiştirebilir → 200.

        M2'nin K2 COORDINATOR rolü K2 engagement'larına uygulanır, K1'deki yetkisiz kalır.
        """
        # Create engagement in K2 owned by T1
        eng_k2 = Engagement(
            talent_id=msm_talent_t1.id,
            organization_id=msm_org_o1.id,
            institution_id=msm_inst_k2.id,
            kind="CAPSTONE",
            title="T1 K2 Engagement",
            status="PENDING_APPROVAL",
            version=1,
            reason=None,
        )
        session.add(eng_k2)
        session.flush()

        response = client.post(
            f"/engagements/{eng_k2.id}/transitions",
            json={"to_status": "ACTIVE", "version": 1},
            headers={"X-Debug-User-Id": str(msm_user_m2.id)},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ACTIVE"

        # Verify DB changed
        session.expire_all()
        eng = session.query(Engagement).filter_by(id=eng_k2.id).first()
        assert eng.status == "ACTIVE"
        assert eng.version == 2


# ============================================================================
# Satır 15 (AC-S3): M2 → T1'in PRIVATE kanıtına download → 404
# ============================================================================


class TestPrivateEvidenceAccessMatrix:
    """
    AC-S3 (satır 15): M2 (talent + org üyesi) → T1'in PRIVATE kanıtı erişimi.

    - M2 T1'in kanıtına download-url → 404 (kanıt DB'de var ama PRIVATE)
    """

    def test_m2_cannot_download_t1_private_evidence_404(
        self, client, msm_user_m2, msm_talent_m2, msm_m2_inst_k1_admin, msm_m2_inst_k2_coordinator, msm_user_t1, msm_talent_t1,
        msm_org_o1, session
    ):
        """
        AC-S3 (satır 15): T1 PRIVATE kanıt oluştur; M2 download-url dene → 404.
        Kanıt DB'de var, M2 O1 üyesi ama PRIVATE olduğu için erişemez.
        """
        # Add M2 to O1 as member/admin
        m2_membership = OrganizationMember(
            organization_id=msm_org_o1.id,
            user_id=msm_user_m2.id,
            role="ADMIN",
            status="ACTIVE",
        )
        session.add(m2_membership)
        session.flush()

        # T1 creates PRIVATE evidence
        from app.services.evidence import create_evidence
        from app.services.authorization import Principal

        principal_t1 = Principal(
            user_id=msm_user_t1.id,
            kind="TALENT",
            talent_id=msm_talent_t1.id,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        evidence_response = create_evidence(
            session=session,
            principal=principal_t1,
            storage_key=f"evidence/{msm_talent_t1.id}/t1-s15-private.pdf",
            kind="DOCUMENT",
            mime_type="application/pdf",
            size_bytes=1024,
        )
        evidence_id = evidence_response.id

        # Verify evidence exists in DB and is PRIVATE
        evidence = session.query(Evidence).filter_by(id=evidence_id).first()
        assert evidence is not None
        assert evidence.visibility == "PRIVATE"

        # M2 tries to download T1's PRIVATE evidence → 404
        response = client.get(
            f"/evidence/{evidence_id}/download-url",
            headers={"X-Debug-User-Id": str(msm_user_m2.id)},
        )
        assert response.status_code == 404
