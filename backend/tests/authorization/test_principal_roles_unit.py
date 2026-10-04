"""
Unit tests for Principal derived properties and engagement_relation (AC-5, AC-S1, AC-S4).

Tests coordinator_institution_ids property, engagement_relation masking,
scoped_*() query compilation for multi-role union, and AC-S3 privacy enforcement.

Migrated from yet-187-coklu-rol task specification.
"""

import uuid
from types import SimpleNamespace


from app.models import (
    Institution, Organization
)
from app.services.authorization import (
    Principal, engagement_relation,
    scoped_engagements, scoped_evidence, scoped_organizations, scoped_institutions,
    can
)


# Helper UUIDs
UUID_USER_000 = uuid.UUID("550e8400-0000-0000-0000-000000000000")
UUID_TALENT_A = uuid.UUID("00000000-0000-0000-0000-000000000010")
UUID_TALENT_B = uuid.UUID("00000000-0000-0000-0000-000000000011")
UUID_ORG_A = uuid.UUID("00000000-0000-0000-0000-000000000020")
UUID_ORG_B = uuid.UUID("00000000-0000-0000-0000-000000000021")
UUID_INST_A = uuid.UUID("00000000-0000-0000-0000-000000000030")
UUID_INST_B = uuid.UUID("00000000-0000-0000-0000-000000000031")


# ============================================================================
# AC-5: Principal.coordinator_institution_ids property
# ============================================================================


class TestCoordinatorInstitutionIds:
    """AC-5, AC-S4: coordinator_institution_ids excludes admin institutions."""

    def test_coordinator_ids_pure_coordinator(self):
        """AC-5: pure COORDINATOR returns all institutions in institution_ids."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="COORDINATOR",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[UUID_INST_A, UUID_INST_B],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        assert principal.coordinator_institution_ids == [UUID_INST_A, UUID_INST_B]

    def test_coordinator_ids_pure_admin_only(self):
        """AC-S4: pure INST_ADMIN returns empty list."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="INST_ADMIN",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[UUID_INST_A],
            institution_admin_ids=[UUID_INST_A],
            is_platform_admin=False,
            is_suspended=False,
        )
        assert principal.coordinator_institution_ids == []

    def test_coordinator_ids_mixed_coordinator_and_admin(self):
        """AC-S4: mixed role returns only coordinator institutions."""
        inst_3 = uuid.UUID("00000000-0000-0000-0000-000000000032")
        principal = Principal(
            user_id=UUID_USER_000,
            kind="INST_ADMIN",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[UUID_INST_A, UUID_INST_B, inst_3],
            institution_admin_ids=[UUID_INST_A],
            is_platform_admin=False,
            is_suspended=False,
        )
        expected = [UUID_INST_B, inst_3]
        assert principal.coordinator_institution_ids == expected

    def test_coordinator_ids_empty_both_lists(self):
        """AC-5: empty lists return empty coordinator_ids."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="USER",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        assert principal.coordinator_institution_ids == []

    def test_coordinator_ids_order_preserved(self):
        """AC-5: order from institution_ids is preserved."""
        inst_3 = uuid.UUID("00000000-0000-0000-0000-000000000033")
        inst_1 = uuid.UUID("00000000-0000-0000-0000-000000000031")
        inst_2 = uuid.UUID("00000000-0000-0000-0000-000000000032")

        principal = Principal(
            user_id=UUID_USER_000,
            kind="COORDINATOR",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[inst_3, inst_1, inst_2],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        assert principal.coordinator_institution_ids == [inst_3, inst_1, inst_2]


# ============================================================================
# AC-S1, AC-S4: engagement_relation masking and membership
# ============================================================================


class TestEngagementRelation:
    """AC-S1, AC-S4: engagement_relation enforces self-dealing masking."""

    def test_engagement_relation_pure_talent_is_subject(self):
        """AC-5: pure talent (subject=True), no org side link."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="TALENT",
            talent_id=UUID_TALENT_A,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        engagement = SimpleNamespace(
            talent_id=UUID_TALENT_A,
            organization_id=UUID_ORG_A,
            institution_id=None,
        )
        rel = engagement_relation(principal, engagement)
        assert rel.is_subject is True
        assert rel.is_org_member is False
        assert rel.is_org_admin is False
        assert rel.is_coordinator is False
        assert rel.has_org_side_link is False

    def test_engagement_relation_pure_org_member(self):
        """AC-5: pure org member (not subject), member=True, admin=False."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        engagement = SimpleNamespace(
            talent_id=UUID_TALENT_A,
            organization_id=UUID_ORG_A,
            institution_id=None,
        )
        rel = engagement_relation(principal, engagement)
        assert rel.is_subject is False
        assert rel.is_org_member is True
        assert rel.is_org_admin is False
        assert rel.is_coordinator is False
        assert rel.has_org_side_link is True

    def test_engagement_relation_org_admin(self):
        """AC-5, AC-S4: org admin has member=True, admin=True."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_ADMIN",
            talent_id=None,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[UUID_ORG_A],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        engagement = SimpleNamespace(
            talent_id=UUID_TALENT_A,
            organization_id=UUID_ORG_A,
            institution_id=None,
        )
        rel = engagement_relation(principal, engagement)
        assert rel.is_subject is False
        assert rel.is_org_member is True
        assert rel.is_org_admin is True
        assert rel.is_coordinator is False
        assert rel.has_org_side_link is True

    def test_engagement_relation_coordinator(self):
        """AC-S1, AC-S4: coordinator (not admin) has is_coordinator=True."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="COORDINATOR",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[UUID_INST_A],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        engagement = SimpleNamespace(
            talent_id=UUID_TALENT_A,
            organization_id=None,
            institution_id=UUID_INST_A,
        )
        rel = engagement_relation(principal, engagement)
        assert rel.is_subject is False
        assert rel.is_org_member is False
        assert rel.is_org_admin is False
        assert rel.is_coordinator is True
        assert rel.has_org_side_link is True

    def test_engagement_relation_inst_admin(self):
        """AC-S4: INST_ADMIN (not coordinator)."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="INST_ADMIN",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[UUID_INST_A],
            institution_admin_ids=[UUID_INST_A],
            is_platform_admin=False,
            is_suspended=False,
        )
        engagement = SimpleNamespace(
            talent_id=UUID_TALENT_A,
            organization_id=None,
            institution_id=UUID_INST_A,
        )
        rel = engagement_relation(principal, engagement)
        assert rel.is_subject is False
        assert rel.is_coordinator is False
        assert rel.has_org_side_link is True

    def test_engagement_relation_talent_and_org_admin_is_subject_masks_org(self):
        """AC-S1: talent + org admin of same engagement masks org flags."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_ADMIN",
            talent_id=UUID_TALENT_A,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[UUID_ORG_A],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        engagement = SimpleNamespace(
            talent_id=UUID_TALENT_A,
            organization_id=UUID_ORG_A,
            institution_id=None,
        )
        rel = engagement_relation(principal, engagement)
        assert rel.is_subject is True
        assert rel.is_org_member is False
        assert rel.is_org_admin is False
        assert rel.has_org_side_link is True

    def test_engagement_relation_talent_of_different_engagement(self):
        """AC-5: talent+org admin in different engagement (not subject here)."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_ADMIN",
            talent_id=UUID_TALENT_A,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[UUID_ORG_A],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        engagement = SimpleNamespace(
            talent_id=UUID_TALENT_B,
            organization_id=UUID_ORG_A,
            institution_id=None,
        )
        rel = engagement_relation(principal, engagement)
        assert rel.is_subject is False
        assert rel.is_org_member is True
        assert rel.is_org_admin is True

    def test_engagement_relation_no_org_link(self):
        """AC-5: engagement with organization_id None."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="TALENT",
            talent_id=UUID_TALENT_A,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        engagement = SimpleNamespace(
            talent_id=UUID_TALENT_A,
            organization_id=None,
            institution_id=None,
        )
        rel = engagement_relation(principal, engagement)
        assert rel.is_subject is True
        assert rel.has_org_side_link is False

    def test_engagement_relation_no_talent_id_principal(self):
        """AC-5: principal with talent_id=None."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        engagement = SimpleNamespace(
            talent_id=UUID_TALENT_A,
            organization_id=UUID_ORG_A,
            institution_id=None,
        )
        rel = engagement_relation(principal, engagement)
        assert rel.is_subject is False
        assert rel.is_org_member is True

    def test_engagement_relation_cross_tenant(self):
        """AC-S2: different org/institution returns all False."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[],
            institution_ids=[UUID_INST_A],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        engagement = SimpleNamespace(
            talent_id=UUID_TALENT_A,
            organization_id=UUID_ORG_B,
            institution_id=UUID_INST_B,
        )
        rel = engagement_relation(principal, engagement)
        assert rel.is_subject is False
        assert rel.is_org_member is False
        assert rel.is_org_admin is False
        assert rel.is_coordinator is False
        assert rel.has_org_side_link is False


# ============================================================================
# AC-5: scoped_engagements union compilation
# ============================================================================


class TestScopedEngagements:
    """AC-5: scoped_engagements compiles OR union for talent+org+institution."""

    def test_scoped_engagements_talent_only(self, session):
        """AC-5: talent path only."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="TALENT",
            talent_id=UUID_TALENT_A,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        stmt = scoped_engagements(session, principal)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "talent_id" in sql.lower()

    def test_scoped_engagements_org_only(self, session):
        """AC-5: org ids path only."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        stmt = scoped_engagements(session, principal)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "IN" in sql or "in" in sql

    def test_scoped_engagements_talent_and_org(self, session):
        """AC-5: talent + org paths use OR."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_MEMBER",
            talent_id=UUID_TALENT_A,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        stmt = scoped_engagements(session, principal)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert " OR " in sql.upper()

    def test_scoped_engagements_talent_org_institution(self, session):
        """AC-5: all three pathways use OR union."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="INST_ADMIN",
            talent_id=UUID_TALENT_A,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[],
            institution_ids=[UUID_INST_A],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        stmt = scoped_engagements(session, principal)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert " OR " in sql.upper()

    def test_scoped_engagements_empty_principal(self, session):
        """AC-5: empty principal (no memberships) returns no engagements."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="USER",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        stmt = scoped_engagements(session, principal)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        # SQLAlchemy renders empty IN as IN (NULL) AND (1 != 1) for safety
        assert "IN (NULL)" in sql and "(1 != 1)" in sql

    def test_scoped_engagements_no_kind_in_where(self, session):
        """AC-6: WHERE clause does not reference 'kind' field."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_ADMIN",
            talent_id=UUID_TALENT_A,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[UUID_ORG_A],
            institution_ids=[UUID_INST_A],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        stmt = scoped_engagements(session, principal)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        where_clause = sql.split("WHERE", 1)[1] if "WHERE" in sql else ""
        assert "kind" not in where_clause.lower()

    def test_scoped_engagements_same_sql_for_user_and_talent(self, session):
        """AC-6: kind="USER" vs kind="TALENT" with same lists produce same SQL."""
        org_list = [UUID_ORG_A]
        talent_id = UUID_TALENT_A

        principal_user = Principal(
            user_id=UUID_USER_000,
            kind="USER",
            talent_id=talent_id,
            org_ids=org_list,
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        principal_talent = Principal(
            user_id=UUID_USER_000,
            kind="TALENT",
            talent_id=talent_id,
            org_ids=org_list,
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        stmt_user = scoped_engagements(session, principal_user)
        stmt_talent = scoped_engagements(session, principal_talent)
        sql_user = str(stmt_user.compile(compile_kwargs={"literal_binds": True}))
        sql_talent = str(stmt_talent.compile(compile_kwargs={"literal_binds": True}))
        assert sql_user.replace(" ", "") == sql_talent.replace(" ", "")


# ============================================================================
# AC-5, AC-S3: scoped_evidence (talent_id only, no org)
# ============================================================================


class TestScopedEvidence:
    """AC-5, AC-S3: scoped_evidence filters by talent_id only."""

    def test_scoped_evidence_talent_has_access(self, session):
        """AC-S3: talent sees own evidence."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="TALENT",
            talent_id=UUID_TALENT_A,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        stmt = scoped_evidence(session, principal)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "owner_talent_id" in sql

    def test_scoped_evidence_org_no_access(self, session):
        """AC-S3: org member does not see evidence via org."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        stmt = scoped_evidence(session, principal)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        # SQLAlchemy renders empty IN as IN (NULL) AND (1 != 1) for safety
        assert "IN (NULL)" in sql and "(1 != 1)" in sql

    def test_scoped_evidence_talent_and_org_still_talent_id_only(self, session):
        """AC-S3: talent+org principal sees evidence only via talent_id."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_MEMBER",
            talent_id=UUID_TALENT_A,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        stmt = scoped_evidence(session, principal)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "owner_talent_id" in sql
        assert "organization" not in sql.lower()


# ============================================================================
# AC-2, AC-7: scoped_organizations and scoped_institutions
# ============================================================================


class TestScopedOrganizations:
    """AC-2, AC-7: scoped_organizations filters by org_ids."""

    def test_scoped_organizations_member(self, session):
        """AC-2: org member sees their org."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        stmt = scoped_organizations(session, principal)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "IN" in sql or "in" in sql

    def test_scoped_organizations_empty_principal(self, session):
        """AC-7: non-member principal sees no orgs."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="TALENT",
            talent_id=UUID_TALENT_A,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        stmt = scoped_organizations(session, principal)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        # SQLAlchemy renders empty IN as IN (NULL) AND (1 != 1) for safety
        assert "IN (NULL)" in sql and "(1 != 1)" in sql


class TestScopedInstitutions:
    """AC-2, AC-7: scoped_institutions filters by institution_ids."""

    def test_scoped_institutions_coordinator(self, session):
        """AC-2: coordinator sees their institution."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="COORDINATOR",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[UUID_INST_A],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        stmt = scoped_institutions(session, principal)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "IN" in sql or "in" in sql

    def test_scoped_institutions_empty(self, session):
        """AC-7: non-associated principal sees no institutions."""
        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=[UUID_ORG_A],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )
        stmt = scoped_institutions(session, principal)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        # SQLAlchemy renders empty IN as IN (NULL) AND (1 != 1) for safety
        assert "IN (NULL)" in sql and "(1 != 1)" in sql


# ============================================================================
# AC-S2, AC-S4: can() resource ownership (Organization, Institution)
# ============================================================================


class TestCanOrganization:
    """AC-S2, AC-S4: can() checks org_admin_ids for Organization."""

    def test_can_admin_update_org_authorized(self, session):
        """AC-S4: org admin can admin_update own org."""
        org = Organization(name="Test Org", legal_id="ORG_001")
        session.add(org)
        session.flush()

        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_ADMIN",
            talent_id=None,
            org_ids=[org.id],
            org_admin_ids=[org.id],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        result = can(principal, "admin_update", org)
        assert result is True

    def test_can_admin_update_org_unauthorized(self, session):
        """AC-S4: non-admin cannot admin_update org."""
        org = Organization(name="Test Org", legal_id="ORG_001")
        session.add(org)
        session.flush()

        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_MEMBER",
            talent_id=None,
            org_ids=[org.id],
            org_admin_ids=[],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        result = can(principal, "admin_update", org)
        assert result is False

    def test_can_admin_update_org_cross_tenant(self, session):
        """AC-S2: admin of another org cannot admin_update this org."""
        org_a = Organization(name="Org A", legal_id="ORG_A_001")
        org_b = Organization(name="Org B", legal_id="ORG_B_001")
        session.add(org_a)
        session.add(org_b)
        session.flush()

        principal = Principal(
            user_id=UUID_USER_000,
            kind="ORG_ADMIN",
            talent_id=None,
            org_ids=[org_a.id, org_b.id],
            org_admin_ids=[org_a.id],
            institution_ids=[],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        assert can(principal, "admin_update", org_a) is True
        assert can(principal, "admin_update", org_b) is False


class TestCanInstitution:
    """AC-S2, AC-S4: can() checks institution_admin_ids for Institution."""

    def test_can_admin_update_institution_authorized(self, session):
        """AC-S4: institution admin can admin_update own institution."""
        inst = Institution(name="Test Institution", domain="inst-001.edu.tr")
        session.add(inst)
        session.flush()

        principal = Principal(
            user_id=UUID_USER_000,
            kind="INST_ADMIN",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[inst.id],
            institution_admin_ids=[inst.id],
            is_platform_admin=False,
            is_suspended=False,
        )

        result = can(principal, "admin_update", inst)
        assert result is True

    def test_can_admin_update_institution_unauthorized(self, session):
        """AC-S4: coordinator cannot admin_update institution."""
        inst = Institution(name="Test Institution", domain="inst-002.edu.tr")
        session.add(inst)
        session.flush()

        principal = Principal(
            user_id=UUID_USER_000,
            kind="COORDINATOR",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[inst.id],
            institution_admin_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        result = can(principal, "admin_update", inst)
        assert result is False

    def test_can_admin_update_institution_cross_tenant(self, session):
        """AC-S2: admin of another institution cannot admin_update this one."""
        inst_a = Institution(name="Institution A", domain="inst-a.edu.tr")
        inst_b = Institution(name="Institution B", domain="inst-b.edu.tr")
        session.add(inst_a)
        session.add(inst_b)
        session.flush()

        principal = Principal(
            user_id=UUID_USER_000,
            kind="INST_ADMIN",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[inst_a.id, inst_b.id],
            institution_admin_ids=[inst_a.id],
            is_platform_admin=False,
            is_suspended=False,
        )

        assert can(principal, "admin_update", inst_a) is True
        assert can(principal, "admin_update", inst_b) is False
