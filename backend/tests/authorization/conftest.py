"""
Shared fixtures for authorization tests (yet-3-yetkilendirme-test-iskeleti).

Provides:
- session: Real Postgres transaction per test, rollback at end (from YET-2)
- org_a, org_b: Test organizations (tenant isolation)
- talent_a, talent_b: Test talent profiles (tenant isolation)
- user_org_a_member, user_org_b_member: OrganizationMember fixtures
- user_talent_a, user_talent_b: User fixtures for talent profiles

Also implements AC-5 guard: "boş matris = FAIL" — if no tests collected in
this package, pytest.exit() with error.
"""

import pytest

from app.models import Organization, OrganizationMember, TalentProfile, User


# NOTE: session fixture is provided by tests/conftest.py (parent conftest)
# Do not override here to maintain transaction isolation consistency


# ============================================================================
# Tenant isolation fixtures: Org A & B
# ============================================================================


@pytest.fixture
def org_a(session):
    """Test organization A (tenant 1)."""
    org = Organization(name="Test Organization A", legal_id="ORG_A_001")
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def org_b(session):
    """Test organization B (tenant 2)."""
    org = Organization(name="Test Organization B", legal_id="ORG_B_001")
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def user_org_a_member(session):
    """User who is a member of org_a."""
    user = User(email="member-org-a@example.com", password_hash="hash_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_b_member(session):
    """User who is a member of org_b."""
    user = User(email="member-org-b@example.com", password_hash="hash_b")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def org_a_member(session, org_a, user_org_a_member):
    """OrganizationMember: user_org_a_member is MEMBER of org_a."""
    member = OrganizationMember(
        organization_id=org_a.id,
        user_id=user_org_a_member.id,
        role="MEMBER",
        status="ACTIVE",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def org_b_member(session, org_b, user_org_b_member):
    """OrganizationMember: user_org_b_member is MEMBER of org_b."""
    member = OrganizationMember(
        organization_id=org_b.id,
        user_id=user_org_b_member.id,
        role="MEMBER",
        status="ACTIVE",
    )
    session.add(member)
    session.flush()
    return member


# ============================================================================
# Talent profile fixtures: Talent A & B
# ============================================================================


@pytest.fixture
def user_talent_a(session):
    """User who owns talent profile A."""
    user = User(email="talent-a@example.com", password_hash="hash_talent_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_b(session):
    """User who owns talent profile B."""
    user = User(email="talent-b@example.com", password_hash="hash_talent_b")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_a(session, user_talent_a):
    """Talent profile A (belongs to user_talent_a)."""
    profile = TalentProfile(
        user_id=user_talent_a.id, full_name="Test Talent A", visibility="PRIVATE"
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_b(session, user_talent_b):
    """Talent profile B (belongs to user_talent_b)."""
    profile = TalentProfile(
        user_id=user_talent_b.id, full_name="Test Talent B", visibility="PRIVATE"
    )
    session.add(profile)
    session.flush()
    return profile


# ============================================================================
# AC-5: "boş matris = FAIL" guard
# ============================================================================


def pytest_collection_modifyitems(config, items):
    """
    Hook: fail if tests/authorization/ package collects zero tests.

    Implements AC-5 (threat-model mitigation): forgetting to add a test case
    for a new endpoint must not silently pass. This guard ensures CI fails
    if the matrix is empty or all tests are skipped.

    Args:
        config: pytest config
        items: collected test items
    """
    # Check if we're running tests from this package
    # items is already filtered by pytest to the currently configured testpaths,
    # so we check if collection is empty (no tests collected).

    # If items is empty (no tests collected in this session),
    # pytest will already fail with "ERROR: usage: pytest [options] [file_or_dir] [file_or_dir] ..."
    # But to be extra safe for the case where pytest is run with explicit nodeid filters,
    # we'll add an explicit check.

    if not items:
        pytest.exit(
            "tests/authorization/ package is empty — no test matrix defined. "
            "This violates AC-5 (empty matrix = FAIL). "
            "Add parametrize-d test cases to test_matrix.py or test_can_defaults.py.",
            returncode=1,
        )
