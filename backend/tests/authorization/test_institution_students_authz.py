"""
GET /institutions/{id}/students — coordinator panel student list (authorization).

Who may list: members of THE institution (COORDINATOR, ADMIN). Everyone else gets 404
(not 403): another institution's coordinator, a talent, an organization member, an
unknown institution id. Unauthenticated → 401.

What is listed: students whose link to the institution was approved
(TalentProfile.institution_id) and whose visibility is not PRIVATE. Counts only cover
engagements of this institution. Email never appears; public_slug only for PUBLIC.
"""

import uuid

import pytest

from app.models import (
    Engagement,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    TalentProfile,
    User,
)


def _user(session, email: str) -> User:
    user = User(email=email, password_hash="hash")
    session.add(user)
    session.flush()
    return user


def _institution(session, name: str) -> Institution:
    inst = Institution(name=name, verification_level="T1", status="ACTIVE")
    session.add(inst)
    session.flush()
    return inst


def _member(session, institution: Institution, email: str, role: str) -> User:
    user = _user(session, email)
    session.add(InstitutionMember(institution_id=institution.id, user_id=user.id, role=role))
    session.flush()
    return user


def _student(
    session,
    email: str,
    full_name: str,
    institution: Institution | None,
    visibility: str,
    public_slug: str | None = None,
) -> TalentProfile:
    user = _user(session, email)
    profile = TalentProfile(
        user_id=user.id,
        full_name=full_name,
        department="Bilgisayar Mühendisliği",
        study_year=3,
        visibility=visibility,
        public_slug=public_slug,
        institution_id=institution.id if institution else None,
    )
    session.add(profile)
    session.flush()
    return profile


def _engagement(session, talent: TalentProfile, org: Organization, institution: Institution | None, status: str):
    eng = Engagement(
        talent_id=talent.id,
        organization_id=org.id,
        institution_id=institution.id if institution else None,
        kind="INTERNSHIP",
        title=f"Staj {status}",
        status=status,
    )
    session.add(eng)
    session.flush()
    return eng


def _get(client, institution_id, user: User | None):
    headers = {"X-Debug-User-Id": str(user.id)} if user else {}
    return client.get(f"/institutions/{institution_id}/students", headers=headers)


@pytest.fixture
def world(session):
    inst_a = _institution(session, "Kurum A")
    inst_b = _institution(session, "Kurum B")
    org = Organization(name="Staj Kuruluşu", legal_id=f"ORG-{uuid.uuid4().hex[:8]}")
    session.add(org)
    session.flush()

    linked = _student(session, "linked@example.com", "Ayşe Bağlı", inst_a, "INSTITUTION")
    public = _student(session, "public@example.com", "Can Herkese", inst_a, "PUBLIC", "can-herkese")
    private = _student(session, "private@example.com", "Gizli Öğrenci", inst_a, "PRIVATE")
    unlinked = _student(session, "unlinked@example.com", "Bağsız Öğrenci", None, "PUBLIC")
    other = _student(session, "other@example.com", "Başka Kurumlu", inst_b, "INSTITUTION")

    # linked: 1 verified + 1 in progress in A; 1 verified with B (must not count for A).
    _engagement(session, linked, org, inst_a, "VERIFIED")
    _engagement(session, linked, org, inst_a, "ACTIVE")
    _engagement(session, linked, org, inst_b, "VERIFIED")
    _engagement(session, linked, org, None, "VERIFIED")

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "org": org,
        "linked": linked,
        "public": public,
        "private": private,
        "unlinked": unlinked,
        "other": other,
        "coord_a": _member(session, inst_a, "coord-a@example.com", "COORDINATOR"),
        "admin_a": _member(session, inst_a, "admin-a@example.com", "ADMIN"),
        "coord_b": _member(session, inst_b, "coord-b@example.com", "COORDINATOR"),
    }


class TestInstitutionStudentsPositive:
    @pytest.mark.parametrize("actor", ["coord_a", "admin_a"])
    def test_member_lists_linked_non_private_students(self, client, world, actor):
        response = _get(client, world["inst_a"].id, world[actor])

        assert response.status_code == 200
        items = response.json()["items"]
        names = [item["full_name"] for item in items]
        assert names == ["Ayşe Bağlı", "Can Herkese"]  # ordered by name

        body = response.text
        for hidden in ("Gizli Öğrenci", "Bağsız Öğrenci", "Başka Kurumlu"):
            assert hidden not in body
        assert "@example.com" not in body  # no email, ever

    def test_counts_cover_only_this_institution(self, client, world):
        items = _get(client, world["inst_a"].id, world["coord_a"]).json()["items"]
        linked = next(item for item in items if item["full_name"] == "Ayşe Bağlı")

        assert linked["verified_count"] == 1
        assert linked["in_progress_count"] == 1
        assert linked["total_count"] == 2

        public = next(item for item in items if item["full_name"] == "Can Herkese")
        assert (public["verified_count"], public["in_progress_count"], public["total_count"]) == (0, 0, 0)

    def test_public_slug_only_for_public_profiles(self, client, session, world):
        world["linked"].public_slug = "ayse-bagli"
        session.flush()

        items = _get(client, world["inst_a"].id, world["coord_a"]).json()["items"]
        slugs = {item["full_name"]: item["public_slug"] for item in items}

        assert slugs["Can Herkese"] == "can-herkese"
        assert slugs["Ayşe Bağlı"] is None  # INSTITUTION visibility: slug not exposed

    def test_suspended_student_not_listed(self, client, session, world):
        user = session.get(User, world["public"].user_id)
        user.status = "SUSPENDED"
        session.flush()

        names = [i["full_name"] for i in _get(client, world["inst_a"].id, world["coord_a"]).json()["items"]]
        assert "Can Herkese" not in names


class TestInstitutionStudentsNegative:
    def test_other_institution_coordinator_gets_404(self, client, world):
        response = _get(client, world["inst_a"].id, world["coord_b"])

        assert response.status_code == 404
        assert "Ayşe Bağlı" not in response.text

    def test_talent_gets_404(self, client, session, world):
        student_user = session.get(User, world["linked"].user_id)
        response = _get(client, world["inst_a"].id, student_user)

        assert response.status_code == 404
        assert "Can Herkese" not in response.text

    def test_organization_member_gets_404(self, client, session, world):
        org_user = _user(session, "org-member@example.com")
        session.add(OrganizationMember(organization_id=world["org"].id, user_id=org_user.id, role="ADMIN"))
        session.flush()

        response = _get(client, world["inst_a"].id, org_user)
        assert response.status_code == 404

    def test_unknown_institution_gets_404(self, client, world):
        response = _get(client, uuid.uuid4(), world["coord_a"])
        assert response.status_code == 404

    def test_unauthenticated_gets_401(self, client, world):
        response = _get(client, world["inst_a"].id, None)
        assert response.status_code == 401
