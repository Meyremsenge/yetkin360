"""
SPRINT D1 — approver (supervisor) on engagements.

- POST /engagements accepts supervisor_user_id only for an ACTIVE member of the
  same organization whose user is ACTIVE, and never the talent themselves;
  every other case is the same generic 404 and no engagement is written.
- GET /engagements?assigned=me&organization_id=... only narrows the scoped list.
- Detail shows the approver's name and unit; list and detail never carry an e-mail.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models import (
    AuditEvent,
    Engagement,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    TalentProfile,
    User,
)


def _user(session, email: str, status: str = "ACTIVE") -> User:
    user = User(email=email, password_hash="x", status=status)
    session.add(user)
    session.flush()
    return user


def _headers(user: User) -> dict:
    return {"X-Debug-User-Id": str(user.id)}


@pytest.fixture
def world(session):
    inst = Institution(name="Galata Teknik")
    org = Organization(name="Lale Yazılım")
    other_org = Organization(name="Başka A.Ş.")
    session.add_all([inst, org, other_org])
    session.flush()

    student = _user(session, "ogrenci@d1.test")
    approver = _user(session, "mehmet.kaya@d1.test")
    colleague = _user(session, "zeynep@d1.test")
    admin = _user(session, "admin@d1.test")
    foreigner = _user(session, "yabanci@d1.test")
    coordinator = _user(session, "koord@d1.test")
    talent = TalentProfile(user_id=student.id, full_name="Ayşe Yılmaz", institution_id=inst.id)
    session.add_all(
        [
            talent,
            TalentProfile(user_id=approver.id, full_name="Mehmet Kaya"),
            OrganizationMember(organization_id=org.id, user_id=approver.id, role="MEMBER", unit="Yazılım"),
            OrganizationMember(organization_id=org.id, user_id=colleague.id, role="MEMBER"),
            OrganizationMember(organization_id=org.id, user_id=admin.id, role="ADMIN"),
            OrganizationMember(organization_id=other_org.id, user_id=foreigner.id, role="ADMIN"),
            InstitutionMember(institution_id=inst.id, user_id=coordinator.id, role="COORDINATOR"),
        ]
    )
    session.flush()
    return {
        "inst": inst,
        "org": org,
        "other_org": other_org,
        "talent": talent,
        "student": student,
        "approver": approver,
        "colleague": colleague,
        "admin": admin,
        "foreigner": foreigner,
        "coordinator": coordinator,
    }


def _create(client, world, supervisor_user_id, actor=None):
    return client.post(
        "/engagements",
        json={
            "talent_id": str(world["talent"].id),
            "organization_id": str(world["org"].id),
            "institution_id": str(world["inst"].id),
            "kind": "INTERNSHIP",
            "title": "Yaz stajı",
            "supervisor_user_id": supervisor_user_id,
        },
        headers=_headers(actor or world["student"]),
    )


def _engagement_count(session) -> int:
    return session.execute(select(func.count()).select_from(Engagement)).scalar_one()


def test_create_with_supervisor_shows_approver_in_detail(client, session, world):
    """AC-1 + AC-S5: name and unit, never the e-mail."""
    response = _create(client, world, str(world["approver"].id))
    assert response.status_code == 201, response.text
    engagement_id = response.json()["id"]

    for viewer in ("student", "approver", "admin", "coordinator"):
        detail = client.get(f"/engagements/{engagement_id}", headers=_headers(world[viewer]))
        assert detail.status_code == 200
        assert detail.json()["supervisor"] == {
            "user_id": str(world["approver"].id),
            "display_name": "Mehmet Kaya",
            "unit": "Yazılım",
        }
        assert "mehmet.kaya@d1.test" not in detail.text


def test_create_without_supervisor_has_null_supervisor(client, session, world):
    response = _create(client, world, None)
    assert response.status_code == 201
    detail = client.get(f"/engagements/{response.json()['id']}", headers=_headers(world["student"]))
    assert detail.json()["supervisor"] is None


def test_audit_records_only_whether_a_supervisor_was_chosen(client, session, world):
    response = _create(client, world, str(world["approver"].id))
    assert response.status_code == 201
    event = session.execute(
        select(AuditEvent).where(AuditEvent.action == "ENGAGEMENT_CREATED").order_by(AuditEvent.id.desc())
    ).scalars().first()
    assert event.event_metadata["has_supervisor"] is True
    assert str(world["approver"].id) not in str(event.event_metadata)


@pytest.mark.parametrize(
    "case",
    ["other_org_member", "talent_self", "inactive_member", "suspended_user", "unknown_user", "bad_uuid"],
)
def test_invalid_supervisor_is_generic_404_and_writes_nothing(client, session, world, case):
    """AC-S1 (other org), AC-S2 (self), AC-S3 (inactive member / suspended user)."""
    if case == "other_org_member":
        supervisor = str(world["foreigner"].id)
    elif case == "talent_self":
        # The student is also a member of the organization: still refused.
        session.add(OrganizationMember(organization_id=world["org"].id, user_id=world["student"].id, role="MEMBER"))
        session.flush()
        supervisor = str(world["student"].id)
    elif case == "inactive_member":
        pending = _user(session, "pending@d1.test")
        session.add(
            OrganizationMember(organization_id=world["org"].id, user_id=pending.id, role="MEMBER", status="PENDING")
        )
        session.flush()
        supervisor = str(pending.id)
    elif case == "suspended_user":
        suspended = _user(session, "askida@d1.test", status="SUSPENDED")
        session.add(OrganizationMember(organization_id=world["org"].id, user_id=suspended.id, role="MEMBER"))
        session.flush()
        supervisor = str(suspended.id)
    elif case == "unknown_user":
        supervisor = "0190a1b2-c3d4-7e5f-8a9b-0c1d2e3f4a5b"
    else:
        supervisor = "not-a-uuid"

    before = _engagement_count(session)
    response = _create(client, world, supervisor)
    assert response.status_code == 404
    body = response.json()
    assert (body.get("detail") or body)["code"] == "NOT_FOUND"
    assert _engagement_count(session) == before


def _seed_engagement(session, world, organization, supervisor=None, talent=None) -> Engagement:
    engagement = Engagement(
        talent_id=(talent or world["talent"]).id,
        organization_id=organization.id,
        institution_id=world["inst"].id,
        kind="INTERNSHIP",
        title=f"Staj {organization.name}",
        status="DRAFT",
        supervisor_user_id=supervisor.id if supervisor else None,
        updated_at=datetime.now(timezone.utc),
    )
    session.add(engagement)
    session.flush()
    return engagement


def test_assigned_me_lists_only_mine(client, session, world):
    """AC-2."""
    mine = _seed_engagement(session, world, world["org"], supervisor=world["approver"])
    _seed_engagement(session, world, world["org"], supervisor=world["colleague"])
    _seed_engagement(session, world, world["org"])

    items = client.get("/engagements?assigned=me", headers=_headers(world["approver"])).json()["items"]
    assert [item["id"] for item in items] == [str(mine.id)]
    assert items[0]["supervisor_user_id"] == str(world["approver"].id)
    assert items[0]["institution_name"] == "Galata Teknik"

    all_items = client.get("/engagements", headers=_headers(world["approver"])).json()["items"]
    assert len(all_items) == 3


def test_organization_filter_lists_only_that_organization(client, session, world):
    """AC-2: a student with engagements in two organizations."""
    in_org = _seed_engagement(session, world, world["org"])
    _seed_engagement(session, world, world["other_org"])

    items = client.get(
        f"/engagements?organization_id={world['org'].id}", headers=_headers(world["student"])
    ).json()["items"]
    assert [item["id"] for item in items] == [str(in_org.id)]


def test_filters_never_widen_scope(client, session, world):
    """AC-S4: an organization I am not in gives 200 [] — not 404, not its engagements."""
    _seed_engagement(session, world, world["other_org"], supervisor=world["foreigner"])

    response = client.get(
        f"/engagements?assigned=me&organization_id={world['other_org'].id}",
        headers=_headers(world["approver"]),
    )
    assert response.status_code == 200
    assert response.json() == {"items": []}

    # The foreign org's admin assigned there still cannot see our org's engagements via the filter.
    _seed_engagement(session, world, world["org"], supervisor=world["foreigner"])
    response = client.get(
        f"/engagements?assigned=me&organization_id={world['org'].id}",
        headers=_headers(world["foreigner"]),
    )
    assert response.json() == {"items": []}


def test_invalid_filter_values_are_rejected(client, session, world):
    for query in ("assigned=someone", "organization_id=not-a-uuid"):
        response = client.get(f"/engagements?{query}", headers=_headers(world["student"]))
        assert response.status_code == 422


def test_list_never_contains_email(client, session, world):
    """AC-S5."""
    _seed_engagement(session, world, world["org"], supervisor=world["approver"])
    response = client.get("/engagements", headers=_headers(world["admin"]))
    assert response.status_code == 200
    assert "@d1.test" not in response.text
