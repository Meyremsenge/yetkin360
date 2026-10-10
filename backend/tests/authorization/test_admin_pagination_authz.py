"""AC-S1/AC-S2/AC-4: paginated admin list endpoints x role matrix (admin-sayfalama-ve-kabuk)."""

import pytest

from app.models import Institution, InstitutionMember, Organization, OrganizationMember, User

PATHS = [
    "/admin/verification-queue?limit=1&offset=0",
    "/admin/skills?limit=1&offset=0",
    "/admin/fraud-queue?limit=1&offset=0",
]
LEAK_KEYS = {"items", "has_more", "limit", "offset"}


def _user(session, email, **kw):
    user = User(email=email, password_hash="h", **kw)
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def roles(session):
    talent = _user(session, "pg-talent@example.com")
    org_admin = _user(session, "pg-orgadmin@example.com")
    coordinator = _user(session, "pg-coord@example.com")
    org = Organization(name="Pg Org", verification_level="T1")
    inst = Institution(name="Pg Inst", domain="pg-inst.edu.tr", verification_level="T1", status="ACTIVE")
    session.add_all([org, inst])
    session.flush()
    session.add(OrganizationMember(organization_id=org.id, user_id=org_admin.id, role="ADMIN", status="ACTIVE"))
    session.add(InstitutionMember(institution_id=inst.id, user_id=coordinator.id, role="COORDINATOR"))
    session.flush()
    return {"talent": talent, "org_admin": org_admin, "coordinator": coordinator}


@pytest.mark.parametrize("role", ["talent", "org_admin", "coordinator"])
@pytest.mark.parametrize("path", PATHS)
def test_non_admin_gets_404_without_envelope(client, roles, role, path):
    response = client.get(path, headers={"X-Debug-User-Id": str(roles[role].id)})
    assert response.status_code == 404, response.text
    body = response.json()
    assert not (LEAK_KEYS & set(body))
    assert body["code"] == "NOT_FOUND"


@pytest.mark.parametrize("path", PATHS)
def test_anonymous_gets_401(client, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("base", ["/admin/verification-queue", "/admin/skills", "/admin/fraud-queue"])
@pytest.mark.parametrize("query", ["limit=201", "limit=100000", "limit=0", "offset=-1", "offset=abc"])
def test_admin_invalid_pagination_422(client, session, base, query):
    admin = _user(session, "pg-admin422@example.com", is_platform_admin=True)
    response = client.get(f"{base}?{query}", headers={"X-Debug-User-Id": str(admin.id)})
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "VALIDATION_ERROR"
