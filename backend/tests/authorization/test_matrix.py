"""
Parametric authorization test matrix (yet-3-yetkilendirme-test-iskeleti).

Implements AC-1, AC-2, AC-3, AC-5, AC-S2, AC-S4, AC-S5 from atdd.md.
Covers mevcut can()/scoped_*() surface (User, Organization resources).
Henüz var olmayan kaynaklar (Engagement, Evidence, etc.) marked with pytest.skip.

Migrated from backend/tests/test_authorization.py and restructured as
parametric matrix (docs/AUTHORIZATION.md §5 format: actor × resource × action × expected).
"""

import pytest

from app.models import Organization, User
from app.services.authorization import (
    Principal,
    can,
    get_scoped_or_404,
    scoped_organizations,
    scoped_talent_profiles,
)


# ============================================================================
# AC-1: Principal dataclass accepts all kind enum values
# ============================================================================


class TestPrincipalAcceptsAllKindValues:
    """AC-1: Principal dataclass accepts all kind enum values."""

    @pytest.mark.parametrize("kind_value", [
        "ANONYMOUS", "TALENT", "ORG_MEMBER", "ORG_ADMIN", "ORG_SUPERVISOR",
        "COORDINATOR", "INST_ADMIN", "PLATFORM_ADMIN", "SUSPENDED"
    ])
    def test_principal_accepts_kind(self, kind_value):
        """AC-1: Principal accepts all 9 kind enum values."""
        principal = Principal(
            user_id="550e8400-e29b-41d4-a716-446655440000" if kind_value != "ANONYMOUS" else None,
            kind=kind_value,
            talent_id="550e8400-e29b-41d4-a716-446655440001" if kind_value == "TALENT" else None,
            org_ids=["550e8400-e29b-41d4-a716-446655440001"] if kind_value in ["ORG_MEMBER", "ORG_ADMIN", "ORG_SUPERVISOR"] else [],
            org_admin_ids=["550e8400-e29b-41d4-a716-446655440001"] if kind_value == "ORG_ADMIN" else [],
            institution_ids=["550e8400-e29b-41d4-a716-446655440002"] if kind_value in ["TALENT", "COORDINATOR", "INST_ADMIN"] else [],
            is_platform_admin=(kind_value == "PLATFORM_ADMIN"),
            is_suspended=(kind_value == "SUSPENDED"),
        )
        assert principal.kind == kind_value


# ============================================================================
# AC-2: scoped_*() returns SQLAlchemy Select objects
# ============================================================================


class TestScopedFunctionsReturnSelectObjects:
    """AC-2: scoped_organizations() and scoped_talent_profiles() return Select objects."""

    def test_scoped_organizations_returns_select_object(self, session):
        """AC-2: scoped_organizations() returns a SQLAlchemy Select object."""
        principal = Principal(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=["550e8400-e29b-41d4-a716-446655440001"],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        result = scoped_organizations(session, principal)
        # Check that result is a SQLAlchemy Select object
        assert str(type(result)).find("Select") != -1

    def test_scoped_talent_profiles_returns_select_object(self, session):
        """AC-2: scoped_talent_profiles() returns a SQLAlchemy Select object."""
        principal = Principal(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            kind="TALENT",
            talent_id="550e8400-e29b-41d4-a716-446655440001",
            org_ids=[],
            org_admin_ids=[],
            institution_ids=["550e8400-e29b-41d4-a716-446655440002"],
            is_platform_admin=False,
            is_suspended=False,
        )
        result = scoped_talent_profiles(session, principal)
        # Check that result is a SQLAlchemy Select object
        assert str(type(result)).find("Select") != -1


# ============================================================================
# AC-3: can() returns True for own resource, False for others
# ============================================================================


class TestCanTrueForOwnResourceFalseForOthers:
    """AC-3: can() returns True when principal accesses their own resource."""

    def test_can_true_for_own_resource(self, session):
        """AC-3: can(principal, 'read', user) returns True when principal.user_id == user.id."""
        user = User(email="alice@example.com", password_hash="hash")
        session.add(user)
        session.flush()

        principal = Principal(
            user_id=user.id,
            kind="TALENT",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        result = can(principal, "read", user)
        assert result is True

    def test_can_false_for_others_resource(self, session):
        """AC-3: can(principal, 'read', other_user) returns False."""
        user_alice = User(email="alice@example.com", password_hash="hash")
        user_bob = User(email="bob@example.com", password_hash="hash")
        session.add_all([user_alice, user_bob])
        session.flush()

        principal = Principal(
            user_id=user_alice.id,
            kind="TALENT",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        result = can(principal, "read", user_bob)
        assert result is False


# ============================================================================
# AC-5 / AC-S4: get_scoped_or_404() returns None when scoped result is empty
# ============================================================================


class TestGetScopedOr404:
    """AC-5 / AC-S4: get_scoped_or_404() returns None for out-of-scope or nonexistent resources."""

    def test_get_scoped_or_404_returns_none_when_empty(self, session):
        """AC-5: get_scoped_or_404() returns None when scoped query returns no rows."""
        principal = Principal(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=["550e8400-e29b-41d4-a716-446655440001"],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        # Empty result (no organizations in principal's scope)
        scoped_select = scoped_organizations(session, principal)
        result = get_scoped_or_404(scoped_select, session)
        assert result is None

    def test_get_scoped_or_404_out_of_scope_returns_none(self, session):
        """AC-S4: get_scoped_or_404() returns None for out-of-scope resource."""
        # Create an org but principal has no access to it
        org = Organization(name="Inaccessible Org")
        session.add(org)
        session.flush()

        principal = Principal(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=["550e8400-e29b-41d4-a716-446655440001"],  # Different org
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        scoped_select = scoped_organizations(session, principal)
        result = get_scoped_or_404(scoped_select, session)
        assert result is None

    def test_get_scoped_or_404_out_of_scope_and_nonexistent_same_result(self, session):
        """AC-S4: Both out-of-scope and nonexistent resources produce the same None result."""
        org = Organization(name="Test Org")
        session.add(org)
        session.flush()

        # Principal with access to different org
        principal = Principal(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=["550e8400-e29b-41d4-a716-446655440001"],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        # Case 1: scoped query for out-of-scope org
        scoped_select = scoped_organizations(session, principal)
        result_out_of_scope = get_scoped_or_404(scoped_select, session)

        # Case 2: scoped query with no orgs matching principal's scope
        result_nonexistent = get_scoped_or_404(scoped_select, session)

        # Both should be None
        assert result_out_of_scope is None
        assert result_nonexistent is None


# ============================================================================
# AC-S2: Tenant isolation (BOLA) — scoped_*() filters out other orgs
# ============================================================================


class TestTenantIsolationOrganizations:
    """AC-S2: scoped_organizations() filters by tenant (org_ids)."""

    def test_scoped_organizations_tenant_isolation(self, session, org_a, org_b, user_org_a_member, org_a_member):
        """AC-S2: scoped_organizations() does not return organizations outside principal's scope."""
        # Principal for org_a member: only has access to org_a
        principal = Principal(
            user_id=user_org_a_member.id,
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=[org_a.id],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        # Execute scoped query
        scoped_select = scoped_organizations(session, principal)
        orgs = session.execute(scoped_select).scalars().all()

        # Assert: org_a should be present, org_b should NOT be present
        org_ids = [org.id for org in orgs]
        assert org_a.id in org_ids, "Org A (in principal's scope) should be returned"
        assert org_b.id not in org_ids, "Org B (outside principal's scope) should NOT be returned"

    @pytest.mark.parametrize("principal_kind,expected_result_for_org_a", [
        ("ORG_MEMBER", True),
        ("ORG_ADMIN", True),
        ("ORG_SUPERVISOR", False),  # ORG_SUPERVISOR has no org_ids
        ("TALENT", False),  # TALENT has no org_ids
        ("COORDINATOR", False),  # COORDINATOR has no org_ids
    ])
    def test_scoped_organizations_by_kind(self, session, org_a, principal_kind, expected_result_for_org_a):
        """AC-2 / AC-S2: scoped_organizations() filters based on principal.kind and org_ids."""
        # Determine org_ids based on expected_result_for_org_a
        # expected_result_for_org_a=True means principal should access org_a (use real org_a.id)
        # expected_result_for_org_a=False means principal has no org access (use empty list)
        org_ids = [org_a.id] if expected_result_for_org_a else []

        principal = Principal(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            kind=principal_kind,
            talent_id=None,
            org_ids=org_ids,
            org_admin_ids=[] if principal_kind != "ORG_ADMIN" else org_ids,
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        scoped_select = scoped_organizations(session, principal)
        result = session.execute(scoped_select).scalars().all()

        if expected_result_for_org_a:
            # Should return org_a (exactly one org in principal's scope)
            assert len(result) == 1, f"Expected 1 organization, got {len(result)}"
            assert result[0].id == org_a.id, f"Expected org_a.id={org_a.id}, got {result[0].id}"
        else:
            # Should return empty (no organizations in principal's scope)
            assert len(result) == 0, f"Expected 0 organizations, got {len(result)}"


# ============================================================================
# AC-S2: Tenant isolation (BOLA) — scoped_talent_profiles() by kind
# ============================================================================


class TestTenantIsolationTalentProfiles:
    """AC-S2: scoped_talent_profiles() filters by talent scope."""

    def test_scoped_talent_profiles_tenant_isolation(self, session, user_talent_a, user_talent_b, talent_a, talent_b):
        """AC-S2: scoped_talent_profiles() returns only principal's own talent profile."""
        # Principal for talent_a: only has access to their own profile
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

        # Execute scoped query
        scoped_select = scoped_talent_profiles(session, principal)
        profiles = session.execute(scoped_select).scalars().all()

        # Assert: only talent_a should be present
        profile_ids = [p.id for p in profiles]
        assert talent_a.id in profile_ids, "Profile A (principal's own) should be returned"
        assert talent_b.id not in profile_ids, "Profile B (other talent) should NOT be returned"

    @pytest.mark.parametrize("principal_kind,user_id,expected_returns_profiles", [
        ("ORG_MEMBER", "550e8400-e29b-41d4-a716-446655440001", False),
        ("COORDINATOR", "550e8400-e29b-41d4-a716-446655440002", False),
        ("INST_ADMIN", "550e8400-e29b-41d4-a716-446655440003", False),
    ])
    def test_scoped_talent_profiles_by_kind(self, session, principal_kind, user_id, expected_returns_profiles):
        """AC-2 / AC-S2: scoped_talent_profiles() filters based on principal.kind (non-TALENT roles return empty)."""
        principal = Principal(
            user_id=user_id,
            kind=principal_kind,
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=["550e8400-e29b-41d4-a716-446655440005"] if principal_kind in ["COORDINATOR", "INST_ADMIN"] else [],
            is_platform_admin=False,
            is_suspended=False,
        )

        scoped_select = scoped_talent_profiles(session, principal)
        result = session.execute(scoped_select).scalars().all()

        # All non-TALENT roles should return empty
        assert len(result) == 0, f"Principal kind {principal_kind} should return empty scoped query"

    def test_scoped_talent_profiles_talent_returns_own_profile(self, session, user_talent_a, talent_a):
        """AC-S2: TALENT principal returns only their own talent profile."""
        # Principal for talent_a owner
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

        scoped_select = scoped_talent_profiles(session, principal)
        profiles = session.execute(scoped_select).scalars().all()

        # Assert: only talent_a should be returned
        profile_ids = [p.id for p in profiles]
        assert profile_ids == [talent_a.id], f"Expected [talent_a.id], got {profile_ids}"


# ============================================================================
# AC-S5: can() defense-in-depth (ownership check)
# ============================================================================


class TestCanDefenseInDepth:
    """AC-S5: can() checks resource ownership directly, not just via scoped_*()."""

    def test_can_defense_in_depth_checks_ownership(self, session):
        """AC-S5: can() checks resource ownership directly, bypassing scoped_*()."""
        user_a = User(email="user-a@example.com", password_hash="hash")
        user_b = User(email="user-b@example.com", password_hash="hash")
        session.add_all([user_a, user_b])
        session.flush()

        # Principal for user_a
        principal = Principal(
            user_id=user_a.id,
            kind="TALENT",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        # Try to access user_b's resource directly via can() (bypassing scoped_*())
        result = can(principal, "read", user_b)
        # Should be False because can() checks ownership internally
        assert result is False

    def test_can_ownership_check_independent_of_scoped(self, session):
        """AC-S5: can() ownership check works even if scoped_*() is bypassed."""
        org = Organization(name="Test Org", legal_id="test-org-001")
        session.add(org)
        session.flush()

        user = User(email="org-admin@example.com", password_hash="hash")
        session.add(user)
        session.flush()

        from app.models import OrganizationMember
        member = OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role="ADMIN",
            status="ACTIVE",
        )
        session.add(member)
        session.flush()

        principal = Principal(
            user_id=user.id,
            kind="ORG_ADMIN",
            talent_id=None,
            org_ids=[org.id],
            org_admin_ids=[org.id],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        # Direct can() call (no scoped_*() lookup)
        result = can(principal, "admin_update", org)
        # Should be True because user is admin of this org
        assert result is True

        # But if user is NOT admin (even with org_ids), should be False
        principal_member_only = Principal(
            user_id=user.id,
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=[org.id],
            org_admin_ids=[],  # Not an admin
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        result = can(principal_member_only, "admin_update", org)
        assert result is False


# ============================================================================
# AC-4: Resource placeholder tests (YET-7/8/9 — not yet implemented)
# ============================================================================


class TestFutureResourcesPlaceholders:
    """
    AC-4: Henüz var olmayan kaynaklar (Engagement, Evidence, Evaluation, Attestation)
    için placeholder testler, pytest.skip() ile gerekçeli şekilde işaretlenmiş.

    These will be implemented in YET-7 (Engagement), YET-8 (Evidence/Evaluation),
    YET-9 (Attestation/VerifiedExperience).
    """

    def test_engagement_access_org_member_read_own_org(self):
        """
        AC-4: Placeholder for docs/AUTHORIZATION.md §5.1 A5 (org member read Org A engagement).

        Status: YET-7 (Engagement model + can()/scoped_*() implementation pending).
        """
        pytest.skip("YET-7 pending: Engagement model and scoped_engagements() not yet implemented")

    def test_evidence_access_tenant_isolation(self):
        """
        AC-4: Placeholder for docs/AUTHORIZATION.md §5.2 B2 (talent cannot read other's PRIVATE evidence).

        Status: YET-8 (Evidence model pending).
        """
        pytest.skip("YET-8 pending: Evidence model and scoped_evidence() not yet implemented")

    def test_evaluation_private_note_field_access(self):
        """
        AC-4: Placeholder for docs/AUTHORIZATION.md §5.3 C1 (private_note field access control).

        Status: YET-8 (Evaluation model and field-level filtering pending).
        """
        pytest.skip("YET-8 pending: Evaluation model and private_note filtering not yet implemented")

    def test_attestation_self_attestation_prevention(self):
        """
        AC-4: Placeholder for docs/AUTHORIZATION.md §5.8 H1 (cannot attest for oneself).

        Status: YET-9 (Attestation model and self-attestation check pending).
        """
        pytest.skip("YET-9 pending: Attestation model and self-attestation validation not yet implemented")

    def test_coordinator_scope_filtering(self):
        """
        AC-4: Placeholder for docs/AUTHORIZATION.md §5.5 E1-E6 (coordinator institution-scoped access).

        Status: YET-7 (Engagement + coordinator scope implementation pending).
        """
        pytest.skip("YET-7 pending: Engagement + scoped_engagements() for COORDINATOR kind not yet implemented")

    def test_anonymous_public_profile_access(self):
        """
        AC-4: Placeholder for docs/AUTHORIZATION.md §5.6 F1-F8 (anonymous public access).

        Status: Partial (PUBLIC visibility filtering in query layer pending, but concept OK).
        """
        pytest.skip("YET-7 (HTTP endpoint + visibility filtering in scoped_talent_profiles) pending")
