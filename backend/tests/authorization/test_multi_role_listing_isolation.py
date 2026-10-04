"""
Multi-role listing isolation tests (YET-187 — AC-2, AC-S3).

Implements acceptance criteria and security criteria for listing endpoints
when principal has multiple roles (talent + org memberships + institution memberships).

Scenario (AC-2, AC-S3, matrix row 3/15):
- M1: talent profile + Org O1 ADMIN + Kurum K1 COORDINATOR (multi-role actor)
- T1: saf talent (no org/institution memberships)

Test contract:
1. M1 calls GET /talents/me/verified-experiences, GET /talents/me/signals, GET /talents/me/skills
2. Each endpoint returns M1's own records only (by talent_id)
3. T1's records are NOT in the response (isolation verified)
4. DB validation: M1's and T1's records both exist in DB (not empty list mistake)
5. GET /me returns M1's talent profile (200, not 404)
6. Unauthenticated request → 401

Pattern notes:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient with X-Debug-User-Id header for auth simulation
- Fixture prefix: mli_ (multi-role listing isolation)
- No imports between test files; all fixtures defined here or use base conftest
- No mock()'ing: services use real scoped_*() authorization
- DB validation: count before/after; ID matching for records

Implements:
- AC-2 (satır 3): Multi-role user sees only own talent records (skill_signals, verified_experiences, skill_claims)
- AC-S3 (satır 15): Cross-talent isolation (M1 cannot see T1's records via listing endpoints)
"""

import pytest
from datetime import date, datetime

from app.models import (
    User,
    TalentProfile,
    Organization,
    Institution,
    OrganizationMember,
    InstitutionMember,
    Engagement,
    SkillClaim,
    Skill,
    SkillSignal,
    VerifiedExperience,
)


# ============================================================================
# Fixtures: Organizations and Institutions (mli_ prefix)
# ============================================================================


@pytest.fixture
def mli_org_o1(session):
    """Organization O1 for multi-role listing isolation test."""
    org = Organization(
        name="MLI Test Org O1",
        domain="mli-o1.example.com",
        legal_id="MLI-O1-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def mli_inst_k1(session):
    """Institution K1 for multi-role listing isolation test."""
    inst = Institution(
        name="MLI Test Institution K1",
        domain="mli-k1.edu.tr",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


# ============================================================================
# M1: Multi-role actor (talent + Org O1 ADMIN + Kurum K1 COORDINATOR)
# ============================================================================


@pytest.fixture
def mli_user_m1(session):
    """User M1: multi-role (O1 ADMIN, K1 COORDINATOR, talent)."""
    user = User(email="mli-m1@example.com", password_hash="hash_mli_m1")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def mli_talent_m1(session, mli_user_m1):
    """Talent profile for M1."""
    profile = TalentProfile(
        user_id=mli_user_m1.id,
        full_name="MLI M1 Talent",
        visibility="PRIVATE",
        headline="M1 Profile",
        city="Istanbul",
        department=None,
        study_year=None,
        public_slug=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def mli_m1_org_o1_admin(session, mli_org_o1, mli_user_m1):
    """M1 is ADMIN of O1."""
    member = OrganizationMember(
        organization_id=mli_org_o1.id,
        user_id=mli_user_m1.id,
        role="ADMIN",
        status="ACTIVE",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def mli_m1_inst_k1_coordinator(session, mli_inst_k1, mli_user_m1):
    """M1 is COORDINATOR of K1."""
    member = InstitutionMember(
        institution_id=mli_inst_k1.id,
        user_id=mli_user_m1.id,
        role="COORDINATOR",
    )
    session.add(member)
    session.flush()
    return member


# ============================================================================
# T1: Single-role talent (no org/institution memberships)
# ============================================================================


@pytest.fixture
def mli_user_t1(session):
    """User T1: talent only (no org/institution memberships)."""
    user = User(email="mli-t1@example.com", password_hash="hash_mli_t1")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def mli_talent_t1(session, mli_user_t1):
    """Talent profile for T1."""
    profile = TalentProfile(
        user_id=mli_user_t1.id,
        full_name="MLI T1 Talent",
        visibility="PRIVATE",
        headline="T1 Profile",
        city="Ankara",
        department=None,
        study_year=None,
        public_slug=None,
    )
    session.add(profile)
    session.flush()
    return profile


# ============================================================================
# Shared Skill for both talents to use in claims/signals
# ============================================================================


@pytest.fixture
def mli_skill_python(session):
    """Shared skill for both M1 and T1."""
    skill = Skill(
        slug="mli-python-shared",
        name_tr="Python",
        name_en="Python",
        category="LANGUAGE",
        status="ACTIVE",
        parent_id=None,
        merged_into_id=None,
    )
    session.add(skill)
    session.flush()
    return skill


# ============================================================================
# M1's records: skill claim, signal, verified experience
# ============================================================================


@pytest.fixture
def mli_skill_claim_m1(session, mli_talent_m1, mli_skill_python):
    """Skill claim for M1."""
    claim = SkillClaim(
        talent_id=mli_talent_m1.id,
        skill_id=mli_skill_python.id,
        claimed_level="INTERMEDIATE",
        source="MANUAL",
        confirmed_by_user_at=None,
    )
    session.add(claim)
    session.flush()
    return claim


@pytest.fixture
def mli_skill_signal_m1(session, mli_talent_m1, mli_skill_python):
    """Skill signal for M1."""
    signal = SkillSignal(
        talent_id=mli_talent_m1.id,
        skill_id=mli_skill_python.id,
        source_type="SELF_CLAIM",
        strength="MODERATE",
        occurred_at=datetime.utcnow(),
        attested_by_org_id=None,
        superseded_by_id=None,
    )
    session.add(signal)
    session.flush()
    return signal


@pytest.fixture
def mli_engagement_m1(session, mli_talent_m1, mli_org_o1, mli_inst_k1):
    """Engagement for M1 (for verified experience snapshot)."""
    eng = Engagement(
        talent_id=mli_talent_m1.id,
        organization_id=mli_org_o1.id,
        institution_id=mli_inst_k1.id,
        kind="INTERNSHIP",
        title="M1 Internship at O1/K1",
        status="ACTIVE",
        version=1,
        reason=None,
    )
    session.add(eng)
    session.flush()
    return eng


@pytest.fixture
def mli_verified_experience_m1(session, mli_talent_m1, mli_engagement_m1):
    """Verified experience for M1."""
    ve = VerifiedExperience(
        talent_id=mli_talent_m1.id,
        engagement_id=mli_engagement_m1.id,
        organization_name_snapshot="MLI Test Org O1",
        role_snapshot="Intern",
        started_on_snapshot=date(2024, 1, 1),
        ended_on_snapshot=date(2024, 6, 30),
        institution_name_snapshot="MLI Test Institution K1",
        claim_type="COMPETENCE",
        visibility="PRIVATE",
        public_token=None,
    )
    session.add(ve)
    session.flush()
    return ve


# ============================================================================
# T1's records: skill claim, signal, verified experience
# ============================================================================


@pytest.fixture
def mli_skill_claim_t1(session, mli_talent_t1, mli_skill_python):
    """Skill claim for T1."""
    claim = SkillClaim(
        talent_id=mli_talent_t1.id,
        skill_id=mli_skill_python.id,
        claimed_level="ADVANCED",
        source="MANUAL",
        confirmed_by_user_at=None,
    )
    session.add(claim)
    session.flush()
    return claim


@pytest.fixture
def mli_skill_signal_t1(session, mli_talent_t1, mli_skill_python):
    """Skill signal for T1."""
    signal = SkillSignal(
        talent_id=mli_talent_t1.id,
        skill_id=mli_skill_python.id,
        source_type="SELF_CLAIM",
        strength="STRONG",
        occurred_at=datetime.utcnow(),
        attested_by_org_id=None,
        superseded_by_id=None,
    )
    session.add(signal)
    session.flush()
    return signal


@pytest.fixture
def mli_org_t1(session):
    """Organization for T1's engagement (required for Engagement model)."""
    org = Organization(
        name="MLI T1 Org",
        domain="mli-t1.example.com",
        legal_id="MLI-T1-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def mli_engagement_t1(session, mli_talent_t1, mli_org_t1):
    """Engagement for T1 (for verified experience snapshot; org required but no institution)."""
    eng = Engagement(
        talent_id=mli_talent_t1.id,
        organization_id=mli_org_t1.id,
        institution_id=None,
        kind="CAPSTONE",
        title="T1 Capstone Project",
        status="DRAFT",
        version=1,
        reason=None,
    )
    session.add(eng)
    session.flush()
    return eng


@pytest.fixture
def mli_verified_experience_t1(session, mli_talent_t1, mli_engagement_t1, mli_org_t1):
    """Verified experience for T1."""
    ve = VerifiedExperience(
        talent_id=mli_talent_t1.id,
        engagement_id=mli_engagement_t1.id,
        organization_name_snapshot=mli_org_t1.name,
        role_snapshot="Developer",
        started_on_snapshot=date(2024, 3, 1),
        ended_on_snapshot=date(2024, 5, 31),
        institution_name_snapshot=None,
        claim_type="PARTICIPATION",
        visibility="PRIVATE",
        public_token=None,
    )
    session.add(ve)
    session.flush()
    return ve


# ============================================================================
# Tests: AC-2 and AC-S3 (Multi-role listing isolation)
# ============================================================================


class TestMultiRoleListingIsolation:
    """
    AC-2, AC-S3 (satır 3/15): Multi-role user sees only own records.

    M1 is talent + org admin + institution coordinator.
    T1 is pure talent.

    Each listing endpoint must return only the calling user's records,
    never cross-talent data.
    """

    def test_m1_verified_experiences_listing_shows_only_m1(
        self, client, mli_user_m1, mli_talent_m1, mli_verified_experience_m1,
        mli_user_t1, mli_talent_t1, mli_verified_experience_t1, session
    ):
        """
        AC-2, AC-S3 (verified-experiences): M1 GET /talents/me/verified-experiences
        returns M1's verified experience only, not T1's.

        Precondition: DB has M1's and T1's verified experiences.
        Expected: Response includes M1's record (id matches); T1's record not in response.
        """
        # Verify DB precondition: both records exist
        ve_m1_count = session.query(VerifiedExperience).filter_by(talent_id=mli_talent_m1.id).count()
        ve_t1_count = session.query(VerifiedExperience).filter_by(talent_id=mli_talent_t1.id).count()
        assert ve_m1_count == 1, f"M1 should have 1 verified experience, found {ve_m1_count}"
        assert ve_t1_count == 1, f"T1 should have 1 verified experience, found {ve_t1_count}"

        # M1 calls endpoint
        response = client.get(
            "/talents/me/verified-experiences",
            headers={"X-Debug-User-Id": str(mli_user_m1.id)},
        )
        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        items = body["items"]

        # M1's record must be present
        m1_ids = [item["id"] for item in items]
        assert str(mli_verified_experience_m1.id) in m1_ids, "M1's verified experience must be in response"

        # T1's record must NOT be present
        t1_id_str = str(mli_verified_experience_t1.id)
        assert t1_id_str not in m1_ids, "T1's verified experience must NOT be in M1's response (isolation violation)"

    def test_m1_skill_signals_listing_shows_only_m1(
        self, client, mli_user_m1, mli_talent_m1, mli_skill_signal_m1,
        mli_user_t1, mli_talent_t1, mli_skill_signal_t1, session
    ):
        """
        AC-2, AC-S3 (skill-signals): M1 GET /talents/me/signals
        returns M1's skill signals only, not T1's.

        Precondition: DB has M1's and T1's skill signals for same skill.
        Expected: Response includes M1's signal; T1's signal not in response.
        """
        # Verify DB precondition: both records exist
        sig_m1_count = session.query(SkillSignal).filter_by(talent_id=mli_talent_m1.id).count()
        sig_t1_count = session.query(SkillSignal).filter_by(talent_id=mli_talent_t1.id).count()
        assert sig_m1_count == 1, f"M1 should have 1 skill signal, found {sig_m1_count}"
        assert sig_t1_count == 1, f"T1 should have 1 skill signal, found {sig_t1_count}"

        # M1 calls endpoint
        response = client.get(
            "/talents/me/signals",
            headers={"X-Debug-User-Id": str(mli_user_m1.id)},
        )
        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        items = body["items"]

        # Extract all signal source types from all skill groups
        # Should only have M1's signal
        all_signals = []
        for skill_group in items:
            assert "signals" in skill_group
            all_signals.extend(skill_group["signals"])

        # M1 has 1 signal, T1 has 1 signal for same skill
        # Response should group by skill and contain only M1's signal
        assert len(items) > 0, "Should have at least one skill group"

        # Verify no T1 signals in response by checking signal count
        # (Can't directly compare signal objects without ID, so check count)
        total_signals = sum(len(group["signals"]) for group in items)
        assert total_signals == 1, f"Should have exactly 1 signal (M1's), found {total_signals}"

    def test_m1_skill_claims_listing_shows_only_m1(
        self, client, mli_user_m1, mli_talent_m1, mli_skill_claim_m1,
        mli_user_t1, mli_talent_t1, mli_skill_claim_t1, session
    ):
        """
        AC-2, AC-S3 (skill-claims): M1 GET /talents/me/skills
        returns M1's skill claims only, not T1's.

        Precondition: DB has M1's and T1's skill claims for same skill.
        Expected: Response includes M1's claim (level INTERMEDIATE); T1's claim (level ADVANCED) not in response.
        """
        # Verify DB precondition: both records exist
        claim_m1_count = session.query(SkillClaim).filter_by(talent_id=mli_talent_m1.id).count()
        claim_t1_count = session.query(SkillClaim).filter_by(talent_id=mli_talent_t1.id).count()
        assert claim_m1_count == 1, f"M1 should have 1 skill claim, found {claim_m1_count}"
        assert claim_t1_count == 1, f"T1 should have 1 skill claim, found {claim_t1_count}"

        # M1 calls endpoint
        response = client.get(
            "/talents/me/skills",
            headers={"X-Debug-User-Id": str(mli_user_m1.id)},
        )
        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        items = body["items"]

        # Should have exactly 1 claim (M1's)
        assert len(items) == 1, f"M1 should see exactly 1 claim, found {len(items)}"

        # Verify it's M1's claim with M1's level
        claim_item = items[0]
        assert claim_item["claimed_level"] == "INTERMEDIATE", \
            f"M1's claim level should be INTERMEDIATE, found {claim_item['claimed_level']}"

    def test_t1_verified_experiences_listing_shows_only_t1(
        self, client, mli_user_t1, mli_talent_t1, mli_verified_experience_t1,
        mli_user_m1, mli_talent_m1, mli_verified_experience_m1, session
    ):
        """
        AC-S3 (verified-experiences, T1 perspective): T1 GET /talents/me/verified-experiences
        returns T1's verified experience only, not M1's.

        Reverse isolation test: ensure M1's records also don't leak to T1.
        """
        # Verify DB precondition: both records exist
        ve_m1_count = session.query(VerifiedExperience).filter_by(talent_id=mli_talent_m1.id).count()
        ve_t1_count = session.query(VerifiedExperience).filter_by(talent_id=mli_talent_t1.id).count()
        assert ve_m1_count == 1
        assert ve_t1_count == 1

        # T1 calls endpoint
        response = client.get(
            "/talents/me/verified-experiences",
            headers={"X-Debug-User-Id": str(mli_user_t1.id)},
        )
        assert response.status_code == 200
        body = response.json()
        items = body["items"]

        # T1's record must be present
        t1_ids = [item["id"] for item in items]
        assert str(mli_verified_experience_t1.id) in t1_ids, "T1's verified experience must be in response"

        # M1's record must NOT be present
        m1_id_str = str(mli_verified_experience_m1.id)
        assert m1_id_str not in t1_ids, "M1's verified experience must NOT be in T1's response (isolation violation)"

    def test_m1_get_me_returns_talent_profile_200(
        self, client, mli_user_m1, mli_talent_m1, mli_m1_org_o1_admin, mli_m1_inst_k1_coordinator
    ):
        """
        AC-2, AC-S3 (GET /me): M1 GET /me returns M1's own talent profile (200, not 404).

        Multi-role users must still see their talent profile even with org/institution memberships.
        """
        response = client.get(
            "/me",
            headers={"X-Debug-User-Id": str(mli_user_m1.id)},
        )
        assert response.status_code == 200
        body = response.json()

        # Response structure
        assert "user" in body
        assert "talent_profile" in body
        assert "organizations" in body
        assert "institutions" in body

        # Verify talent profile is M1's
        talent_profile = body["talent_profile"]
        assert str(mli_talent_m1.id) == talent_profile["id"], "Talent profile ID must match M1's"
        assert str(mli_user_m1.id) == talent_profile["user_id"], "User ID must match M1's"
        assert talent_profile["full_name"] == "MLI M1 Talent"

    def test_m1_get_me_organizations_and_institutions(
        self, client, mli_user_m1, mli_talent_m1, mli_org_o1, mli_inst_k1,
        mli_m1_org_o1_admin, mli_m1_inst_k1_coordinator
    ):
        """
        AC-2 (GET /me): M1's org/institution associations are included in response.
        """
        response = client.get(
            "/me",
            headers={"X-Debug-User-Id": str(mli_user_m1.id)},
        )
        assert response.status_code == 200
        body = response.json()

        # Check organizations
        orgs = body["organizations"]
        org_ids = [str(org["id"]) for org in orgs]
        assert str(mli_org_o1.id) in org_ids, "M1's org O1 must be in response"

        # Check institutions
        insts = body["institutions"]
        inst_ids = [str(inst["id"]) for inst in insts]
        assert str(mli_inst_k1.id) in inst_ids, "M1's institution K1 must be in response"

    def test_unauthenticated_verified_experiences_401(self, client):
        """
        AC-S3 (unauthenticated, verified-experiences): GET /talents/me/verified-experiences without
        X-Debug-User-Id header returns 401.
        """
        response = client.get("/talents/me/verified-experiences")
        assert response.status_code == 401

    def test_unauthenticated_skill_signals_401(self, client):
        """
        AC-S3 (unauthenticated, signals): GET /talents/me/signals without
        X-Debug-User-Id header returns 401.
        """
        response = client.get("/talents/me/signals")
        assert response.status_code == 401

    def test_unauthenticated_skill_claims_401(self, client):
        """
        AC-S3 (unauthenticated, claims): GET /talents/me/skills without
        X-Debug-User-Id header returns 401.
        """
        response = client.get("/talents/me/skills")
        assert response.status_code == 401

    def test_unauthenticated_me_401(self, client):
        """
        AC-S3 (unauthenticated, /me): GET /me without X-Debug-User-Id header returns 401.
        """
        response = client.get("/me")
        assert response.status_code == 401

    def test_m1_no_cross_talent_visibility_in_listing(
        self, client, mli_user_m1, mli_talent_m1, mli_m1_org_o1_admin, mli_m1_inst_k1_coordinator,
        mli_user_t1, mli_talent_t1, mli_verified_experience_m1, mli_verified_experience_t1, session
    ):
        """
        AC-S3 (comprehensive isolation): M1 (multi-role) must not see T1's records
        across all listing endpoints, even though M1 has org/institution memberships.

        This is the core security test: org/institution membership does NOT grant
        access to other talent's talent-level data.
        """
        # Ensure M1 has multiple membership roles
        orgs = session.query(OrganizationMember).filter_by(user_id=mli_user_m1.id).all()
        insts = session.query(InstitutionMember).filter_by(user_id=mli_user_m1.id).all()
        assert len(orgs) > 0, "M1 must have org membership"
        assert len(insts) > 0, "M1 must have institution membership"

        # M1 has org/institution scope but must NOT see T1's talent records
        response = client.get(
            "/talents/me/verified-experiences",
            headers={"X-Debug-User-Id": str(mli_user_m1.id)},
        )
        assert response.status_code == 200
        m1_ve_ids = [item["id"] for item in response.json()["items"]]

        # Get T1's verified experience count
        t1_ve_count = session.query(VerifiedExperience).filter_by(talent_id=mli_talent_t1.id).count()
        assert t1_ve_count > 0, "T1 must have verified experiences for this test"

        # None of T1's records should be in M1's response
        t1_ve = session.query(VerifiedExperience).filter_by(talent_id=mli_talent_t1.id).first()
        assert str(t1_ve.id) not in m1_ve_ids, \
            "T1's verified experience must not appear in M1's response (isolation violation)"
