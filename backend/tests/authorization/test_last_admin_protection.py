"""
YET-236 (L-01): an ADMIN must not be able to demote another ADMIN, demote themselves,
or leave an organization / institution without an administrator.

Evidence (probe, 2026-10-04): the membership surface has exactly one mutating route per
tenant type (POST .../members = invite). It never overwrites the role of an existing member
(YET-165/YET-180) and there is no remove/role-change route, so none of (a) sole admin
demotes self, (b) admin demotes another admin, (c) tenant left without admin is reachable.

These tests pin that state. If a role-change or remove route is ever added, the structural
guard below fails until last-admin protection (service layer, SELECT ... FOR UPDATE on the
member rows, 409) and its race test exist.
"""

import pytest
from sqlalchemy import select

from app.main import app
from app.models import InstitutionMember, OrganizationMember, TalentProfile, User

_TENANTS = {
    "organizations": (OrganizationMember, "organization_id", "MEMBER"),
    "institutions": (InstitutionMember, "institution_id", "COORDINATOR"),
}


def _h(user):
    return {"X-Debug-User-Id": str(user.id)}


def _user(session, email):
    user = User(email=email, password_hash="h")
    session.add(user)
    session.flush()
    session.add(TalentProfile(user_id=user.id, full_name=email.split("@")[0], visibility="PRIVATE"))
    session.flush()
    return user


def _strip(body):
    return {k: v for k, v in body.items() if k != "request_id"}


def _roles(session, model, fk, tenant_id):
    session.expire_all()
    rows = session.execute(select(model).where(getattr(model, fk) == tenant_id)).scalars().all()
    return {row.user_id: row.role for row in rows}


@pytest.fixture(params=sorted(_TENANTS))
def tenant(request, client, session):
    """Tenant with two ADMINs: the founder and a second admin invited through the real API."""
    kind = request.param
    model, fk, low_role = _TENANTS[kind]
    founder = _user(session, f"founder-{kind}@example.com")
    second = _user(session, f"second-{kind}@example.com")
    session.commit()

    r = client.post(f"/{kind}/", json={"name": f"Last Admin {kind}"}, headers=_h(founder))
    assert r.status_code == 201
    tenant_id = r.json()["id"]
    r = client.post(
        f"/{kind}/{tenant_id}/members",
        json={"email": second.email, "role": "ADMIN"},
        headers=_h(founder),
    )
    assert r.status_code == 202
    return kind, model, fk, low_role, tenant_id, founder, second


def test_admin_cannot_demote_another_admin_by_reinvite(client, session, tenant):
    kind, model, fk, low_role, tenant_id, founder, second = tenant
    r = client.post(
        f"/{kind}/{tenant_id}/members",
        json={"email": second.email, "role": low_role},
        headers=_h(founder),
    )
    assert r.status_code == 202
    assert _roles(session, model, fk, tenant_id)[second.id] == "ADMIN"


def test_sole_admin_cannot_demote_self_by_reinvite(client, session, tenant):
    kind, model, fk, low_role, tenant_id, founder, second = tenant
    # Make the founder the only admin by deleting the second admin row directly (setup only).
    session.execute(
        model.__table__.delete().where(
            getattr(model, fk) == tenant_id, model.user_id == second.id
        )
    )
    session.commit()

    r = client.post(
        f"/{kind}/{tenant_id}/members",
        json={"email": founder.email, "role": low_role},
        headers=_h(founder),
    )
    assert r.status_code == 202
    assert _roles(session, model, fk, tenant_id) == {founder.id: "ADMIN"}


def test_reinvite_response_is_uniform_with_unknown_email(client, tenant):
    """YET-180 contract must survive: existing member vs unknown e-mail look identical."""
    kind, model, fk, low_role, tenant_id, founder, second = tenant
    known = client.post(
        f"/{kind}/{tenant_id}/members",
        json={"email": second.email, "role": low_role},
        headers=_h(founder),
    )
    unknown = client.post(
        f"/{kind}/{tenant_id}/members",
        json={"email": "nobody-236@example.com", "role": low_role},
        headers=_h(founder),
    )
    assert known.status_code == unknown.status_code == 202
    assert _strip(known.json()) == _strip(unknown.json())


@pytest.mark.parametrize("method", ["patch", "put", "delete"])
def test_no_member_mutation_route_reachable(client, session, tenant, method):
    kind, model, fk, low_role, tenant_id, founder, second = tenant
    for path in (
        f"/{kind}/{tenant_id}/members",
        f"/{kind}/{tenant_id}/members/{second.id}",
        f"/{kind}/{tenant_id}/members/{founder.id}",
    ):
        r = client.request(method.upper(), path, json={"role": low_role}, headers=_h(founder))
        assert r.status_code in (404, 405), (method, path, r.status_code)
    assert set(_roles(session, model, fk, tenant_id).values()) == {"ADMIN"}


def test_structural_guard_no_member_role_change_or_remove_route():
    """Fails when someone adds a member remove/role-change route without last-admin protection."""
    mutating = {"put", "patch", "delete"}
    offenders = []
    for path, ops in app.openapi()["paths"].items():
        if not path.startswith(("/organizations/", "/institutions/")) or "member" not in path:
            continue
        offenders += [f"{op.upper()} {path}" for op in ops if op in mutating]
        # any extra POST under .../members/... (e.g. /members/{id}/role, /demote) is a mutation too
        if "post" in ops and path.rstrip("/").split("/members")[-1] not in ("", "/"):
            offenders.append(f"POST {path}")
    assert not offenders, (
        "Member mutation route added without YET-236 last-admin protection "
        f"(service-layer lock + 409 + race test): {offenders}"
    )
