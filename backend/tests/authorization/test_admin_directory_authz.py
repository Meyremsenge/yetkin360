"""
Admin directory authorization tests (U1, U2, O1, O4, I1 — admin-kullanici-kurulus-kurum-yonetimi).

- Role x endpoint matrix: talent, org ADMIN, institution coordinator -> 404; anonymous -> 401;
  a suspended former platform admin (real access token, real get_current_user) -> 401.
- Combinations: own account / last active admin -> 409 LAST_ADMIN_PROTECTED; one of two admins
  suspends the other -> 200.
- AC-S6: target from the path only, actor from the session only; suspended user's access and
  refresh tokens stop working. AC-S7: audit row per real change, no e-mail/free text.
  AC-S8: no secret fields in the user list. AC-11: audit failure rolls the status change back.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.deps import get_current_user as core_get_current_user
from app.core.security import encode_access_token, hash_refresh_token
from app.main import app
from app.models import (
    AuditEvent,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    RefreshToken,
    TalentProfile,
    User,
)

ENVELOPE_KEYS = {"items", "has_more", "limit", "offset"}
USER_ITEM_KEYS = {"id", "email", "status", "is_platform_admin", "email_verified", "created_at"}


def _h(user):
    return {"X-Debug-User-Id": str(user.id)}


def _user(session, email, **fields):
    user = User(email=email, password_hash="hash", **fields)
    session.add(user)
    session.flush()
    return user


def _audit_count(session, action, subject_id):
    return session.execute(
        select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action == action, AuditEvent.subject_id == subject_id
        )
    ).scalar_one()


@pytest.fixture
def admin(session):
    return _user(session, "dir-admin@example.com", is_platform_admin=True)


@pytest.fixture
def second_admin(session):
    return _user(session, "dir-admin-2@example.com", is_platform_admin=True)


@pytest.fixture
def target_user(session):
    return _user(session, "dir-target@example.com")


@pytest.fixture
def org(session):
    o = Organization(name="Dizin Kuruluşu A.Ş.", legal_id="DIR-ORG-1", domain="dizin-org.example.com")
    session.add(o)
    session.flush()
    return o


@pytest.fixture
def institution(session):
    i = Institution(name="Dizin Üniversitesi", domain="dizin-uni.example.edu")
    session.add(i)
    session.flush()
    return i


@pytest.fixture
def actors(session, org, institution):
    """Non-admin principals: talent, organization ADMIN, institution coordinator."""
    talent = _user(session, "dir-talent@example.com")
    session.add(TalentProfile(user_id=talent.id, full_name="Dir Talent", visibility="PRIVATE"))
    org_admin = _user(session, "dir-org-admin@example.com")
    session.add(OrganizationMember(organization_id=org.id, user_id=org_admin.id, role="ADMIN"))
    coordinator = _user(session, "dir-coord@example.com")
    session.add(InstitutionMember(institution_id=institution.id, user_id=coordinator.id, role="COORDINATOR"))
    session.flush()
    return {"talent": talent, "org_admin": org_admin, "coordinator": coordinator}


def _cases(target_user, org, institution):
    return [
        ("GET", "/admin/users?limit=1&offset=0", None),
        ("POST", f"/admin/users/{target_user.id}/suspend", {}),
        ("POST", f"/admin/users/{target_user.id}/reactivate", {}),
        ("GET", "/admin/organizations?limit=1&offset=0", None),
        ("POST", f"/admin/organizations/{org.id}/suspend", {}),
        ("POST", f"/admin/organizations/{org.id}/reactivate", {}),
        ("GET", "/admin/institutions?limit=1&offset=0", None),
        ("POST", f"/admin/institutions/{institution.id}/verification-level", {"verification_level": "T3"}),
        ("POST", f"/admin/institutions/{institution.id}/suspend", {}),
        ("POST", f"/admin/institutions/{institution.id}/reactivate", {}),
    ]


# ============================================================================
# Role x endpoint matrix
# ============================================================================


@pytest.mark.parametrize("role", ["talent", "org_admin", "coordinator"])
def test_non_admin_roles_get_404_on_every_directory_endpoint(
    client, session, actors, target_user, org, institution, role
):
    for method, path, body in _cases(target_user, org, institution):
        response = client.request(method, path, json=body, headers=_h(actors[role]))
        assert response.status_code == 404, (role, method, path, response.text)
        assert response.json()["code"] == "NOT_FOUND"
        assert not ENVELOPE_KEYS & set(response.json()), (method, path)
    session.expire_all()
    assert session.get(User, target_user.id).status == "ACTIVE"
    assert session.get(Organization, org.id).status == "ACTIVE"
    assert session.get(Institution, institution.id).verification_level == "T1"


def test_anonymous_gets_401_on_every_directory_endpoint(client, target_user, org, institution):
    for method, path, body in _cases(target_user, org, institution):
        response = client.request(method, path, json=body)
        assert response.status_code == 401, (method, path)


def test_suspended_former_admin_gets_401_with_real_token(client, session, target_user, org, institution):
    former = _user(session, "dir-former-admin@example.com", is_platform_admin=True, status="SUSPENDED")
    app.dependency_overrides.pop(core_get_current_user, None)
    client.cookies.set("access_token", encode_access_token(former.id))
    for method, path, body in _cases(target_user, org, institution):
        response = client.request(method, path, json=body)
        assert response.status_code == 401, (method, path, response.text)
        assert not ENVELOPE_KEYS & set(response.json())


def test_platform_admin_reaches_every_list(client, admin, target_user, org, institution):
    for path in ("/admin/users", "/admin/organizations", "/admin/institutions"):
        response = client.get(f"{path}?limit=50&offset=0", headers=_h(admin))
        assert response.status_code == 200, response.text
        body = response.json()
        assert set(body) == ENVELOPE_KEYS
        assert body["limit"] == 50 and body["offset"] == 0


# ============================================================================
# U1 — user list
# ============================================================================


def test_user_list_item_has_no_secret_fields(client, admin, target_user):
    response = client.get("/admin/users?q=dir-target", headers=_h(admin))
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [i["email"] for i in items] == ["dir-target@example.com"]
    assert set(items[0]) == USER_ITEM_KEYS
    for forbidden in ("password_hash", "failed_login_count", "locked_until", "token"):
        assert forbidden not in response.text


def test_user_list_has_more_uses_limit_plus_one(client, session, admin):
    for n in range(3):
        _user(session, f"dir-page-{n}@example.com")
    first = client.get("/admin/users?q=dir-page-&limit=2&offset=0", headers=_h(admin)).json()
    assert len(first["items"]) == 2 and first["has_more"] is True
    second = client.get("/admin/users?q=dir-page-&limit=2&offset=2", headers=_h(admin)).json()
    assert len(second["items"]) == 1 and second["has_more"] is False
    assert {i["id"] for i in first["items"]}.isdisjoint({i["id"] for i in second["items"]})


def test_user_list_status_filter_and_empty_result(client, session, admin):
    _user(session, "dir-susp@example.com", status="SUSPENDED")
    body = client.get("/admin/users?status=SUSPENDED&q=dir-susp", headers=_h(admin)).json()
    assert [i["email"] for i in body["items"]] == ["dir-susp@example.com"]
    empty = client.get("/admin/users?q=no-such-user-xyz", headers=_h(admin)).json()
    assert empty == {"items": [], "limit": 50, "offset": 0, "has_more": False}


def test_user_list_q_wildcards_are_literal(client, session, admin):
    _user(session, "dir-wild@example.com")
    body = client.get("/admin/users?q=%25", headers=_h(admin)).json()
    assert body["items"] == []


@pytest.mark.parametrize("path", ["/admin/users", "/admin/organizations", "/admin/institutions"])
@pytest.mark.parametrize("query", ["limit=0", "limit=201", "offset=-1", "limit=abc"])
def test_list_pagination_bounds_422(client, admin, path, query):
    response = client.get(f"{path}?{query}", headers=_h(admin))
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "path", ["/admin/users?status=BANNED", "/admin/organizations?verification_level=T9", "/admin/organizations?status=X"]
)
def test_list_invalid_filter_422(client, admin, path):
    assert client.get(path, headers=_h(admin)).status_code == 422


# ============================================================================
# U2 — suspend / reactivate user
# ============================================================================


def test_admin_suspends_user_and_audit_written(client, session, admin, target_user):
    response = client.post(f"/admin/users/{target_user.id}/suspend", json={}, headers=_h(admin))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "SUSPENDED"
    session.expire_all()
    assert session.get(User, target_user.id).status == "SUSPENDED"
    event = session.execute(
        select(AuditEvent).where(AuditEvent.action == "ADMIN_SUSPEND_USER", AuditEvent.subject_id == target_user.id)
    ).scalar_one()
    assert event.actor_user_id == admin.id
    assert "@" not in str(event.event_metadata or {})


def test_suspend_is_idempotent_without_new_audit(client, session, admin, target_user):
    client.post(f"/admin/users/{target_user.id}/suspend", json={}, headers=_h(admin))
    again = client.post(f"/admin/users/{target_user.id}/suspend", json={}, headers=_h(admin))
    assert again.status_code == 200
    assert again.json()["status"] == "SUSPENDED"
    assert _audit_count(session, "ADMIN_SUSPEND_USER", target_user.id) == 1


def test_reactivate_restores_active_and_is_idempotent(client, session, admin, target_user):
    client.post(f"/admin/users/{target_user.id}/suspend", json={}, headers=_h(admin))
    response = client.post(f"/admin/users/{target_user.id}/reactivate", json={}, headers=_h(admin))
    assert response.status_code == 200 and response.json()["status"] == "ACTIVE"
    again = client.post(f"/admin/users/{target_user.id}/reactivate", json={}, headers=_h(admin))
    assert again.status_code == 200 and again.json()["status"] == "ACTIVE"
    assert _audit_count(session, "ADMIN_REACTIVATE_USER", target_user.id) == 1


@pytest.mark.parametrize("action", ["suspend", "reactivate"])
def test_unknown_or_deleted_user_404(client, session, admin, action):
    deleted = _user(session, "dir-deleted@example.com", status="DELETED")
    for target in (uuid.uuid4(), deleted.id):
        response = client.post(f"/admin/users/{target}/{action}", json={}, headers=_h(admin))
        assert response.status_code == 404, response.text
    assert _audit_count(session, f"ADMIN_{action.upper()}_USER", deleted.id) == 0


def test_admin_cannot_suspend_self_409(client, session, admin, second_admin):
    response = client.post(f"/admin/users/{admin.id}/suspend", json={}, headers=_h(admin))
    assert response.status_code == 409
    assert response.json()["code"] == "LAST_ADMIN_PROTECTED"
    session.expire_all()
    assert session.get(User, admin.id).status == "ACTIVE"


def test_sole_admin_cannot_suspend_self_409(client, admin):
    response = client.post(f"/admin/users/{admin.id}/suspend", json={}, headers=_h(admin))
    assert response.status_code == 409
    assert response.json()["code"] == "LAST_ADMIN_PROTECTED"


def test_one_of_two_admins_suspends_the_other(client, session, admin, second_admin):
    response = client.post(f"/admin/users/{second_admin.id}/suspend", json={}, headers=_h(admin))
    assert response.status_code == 200, response.text
    session.expire_all()
    assert session.get(User, second_admin.id).status == "SUSPENDED"
    assert session.get(User, admin.id).status == "ACTIVE"


def test_last_active_admin_protected_at_service_layer(session, admin, second_admin):
    """Race outcome: the acting admin was suspended concurrently -> the other is now the last active admin."""
    from app.services.admin_directory import LastAdminProtectedError, set_user_suspended
    from app.services.authorization import Principal

    admin.status = "SUSPENDED"
    session.flush()
    principal = Principal(
        user_id=admin.id, kind="USER", talent_id=None, org_ids=[], org_admin_ids=[],
        institution_ids=[], is_platform_admin=True, is_suspended=False,
    )
    with pytest.raises(LastAdminProtectedError):
        set_user_suspended(session, principal, second_admin.id, suspended=True)
    assert second_admin.status == "ACTIVE"


def test_body_cannot_redirect_target_or_actor(client, session, admin, second_admin, target_user):
    """AC-S6: only the path id is acted on; actor comes from the session."""
    response = client.post(
        f"/admin/users/{target_user.id}/suspend",
        json={"id": str(second_admin.id), "actor_id": str(second_admin.id), "status": "ACTIVE", "is_platform_admin": True},
        headers=_h(admin),
    )
    assert response.status_code == 200
    session.expire_all()
    assert session.get(User, target_user.id).status == "SUSPENDED"
    assert session.get(User, target_user.id).is_platform_admin is False
    assert session.get(User, second_admin.id).status == "ACTIVE"
    event = session.execute(
        select(AuditEvent).where(AuditEvent.action == "ADMIN_SUSPEND_USER", AuditEvent.subject_id == target_user.id)
    ).scalar_one()
    assert event.actor_user_id == admin.id


def test_suspended_user_tokens_stop_working(client, session, admin, target_user):
    """AC-S6: next request with the old access token -> 401; refresh tokens revoked."""
    token = RefreshToken(
        user_id=target_user.id,
        family_id=uuid.uuid4(),
        token_hash=hash_refresh_token("dir-refresh-raw"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    session.add(token)
    session.flush()

    assert client.post(f"/admin/users/{target_user.id}/suspend", json={}, headers=_h(admin)).status_code == 200
    session.expire_all()
    assert session.get(RefreshToken, token.id).revoked_at is not None

    app.dependency_overrides.pop(core_get_current_user, None)
    client.cookies.set("access_token", encode_access_token(target_user.id))
    assert client.get("/me").status_code == 401
    client.cookies.set("refresh_token", "dir-refresh-raw")
    assert client.post("/auth/refresh").status_code == 401


def test_audit_failure_rolls_back_suspension(client, session, admin, target_user, monkeypatch):
    """AC-11: status change and audit are one transaction."""
    import app.services.admin_directory as svc

    def boom(*args, **kwargs):
        raise RuntimeError("audit down")

    monkeypatch.setattr(svc, "log_audit_event", boom)
    with pytest.raises(RuntimeError):
        client.post(f"/admin/users/{target_user.id}/suspend", json={}, headers=_h(admin))
    session.expire_all()
    assert session.get(User, target_user.id).status == "ACTIVE"


# ============================================================================
# O1 / O4 — organizations
# ============================================================================


def test_organization_list_filters_and_null_fields(client, session, admin, org):
    bare = Organization(name="Dizin Boş Ltd.")
    session.add(bare)
    session.flush()
    body = client.get("/admin/organizations?q=Dizin&verification_level=T1", headers=_h(admin)).json()
    items = {i["id"]: i for i in body["items"]}
    assert str(org.id) in items and str(bare.id) in items
    assert items[str(bare.id)]["legal_id"] is None
    assert items[str(bare.id)]["domain"] is None
    assert set(items[str(org.id)]) == {
        "id", "name", "legal_id", "domain", "verification_level", "verified_at", "status", "created_at"
    }


def test_organization_list_hides_soft_deleted(client, session, admin):
    gone = Organization(name="Dizin Silinmiş", deleted_at=datetime.now(timezone.utc))
    session.add(gone)
    session.flush()
    body = client.get("/admin/organizations?q=Dizin Silinmiş", headers=_h(admin)).json()
    assert body["items"] == []


def test_admin_suspends_and_reactivates_organization(client, session, admin, org):
    r = client.post(f"/admin/organizations/{org.id}/suspend", json={}, headers=_h(admin))
    assert r.status_code == 200 and r.json()["status"] == "SUSPENDED"
    again = client.post(f"/admin/organizations/{org.id}/suspend", json={}, headers=_h(admin))
    assert again.status_code == 200
    assert _audit_count(session, "ADMIN_SUSPEND_ORGANIZATION", org.id) == 1
    filtered = client.get("/admin/organizations?status=SUSPENDED&q=Dizin Kuruluşu", headers=_h(admin)).json()
    assert [i["id"] for i in filtered["items"]] == [str(org.id)]
    r = client.post(f"/admin/organizations/{org.id}/reactivate", json={}, headers=_h(admin))
    assert r.status_code == 200 and r.json()["status"] == "ACTIVE"
    assert _audit_count(session, "ADMIN_REACTIVATE_ORGANIZATION", org.id) == 1


def test_suspended_organization_leaves_the_directory(client, session, admin, org, actors):
    client.post(f"/admin/organizations/{org.id}/suspend", json={}, headers=_h(admin))
    response = client.get("/organizations/?q=Dizin", headers=_h(actors["talent"]))
    assert response.status_code == 200, response.text
    assert str(org.id) not in response.text


@pytest.mark.parametrize("action", ["suspend", "reactivate"])
def test_unknown_or_deleted_organization_404(client, session, admin, action):
    gone = Organization(name="Dizin Gitti", deleted_at=datetime.now(timezone.utc))
    session.add(gone)
    session.flush()
    for target in (uuid.uuid4(), gone.id):
        assert client.post(f"/admin/organizations/{target}/{action}", json={}, headers=_h(admin)).status_code == 404


# ============================================================================
# I1 — institutions
# ============================================================================


def test_institution_list_and_verification_level(client, session, admin, institution):
    body = client.get("/admin/institutions?q=Dizin", headers=_h(admin)).json()
    assert [i["id"] for i in body["items"]] == [str(institution.id)]
    assert set(body["items"][0]) == {"id", "name", "domain", "verification_level", "status", "created_at"}

    r = client.post(
        f"/admin/institutions/{institution.id}/verification-level",
        json={"verification_level": "T3", "note": "YÖK listesinde"},
        headers=_h(admin),
    )
    assert r.status_code == 200 and r.json()["verification_level"] == "T3"
    same = client.post(
        f"/admin/institutions/{institution.id}/verification-level",
        json={"verification_level": "T3"},
        headers=_h(admin),
    )
    assert same.status_code == 200
    events = session.execute(
        select(AuditEvent).where(
            AuditEvent.action == "ADMIN_SET_INSTITUTION_VERIFICATION_LEVEL", AuditEvent.subject_id == institution.id
        )
    ).scalars().all()
    assert len(events) == 1
    assert "YÖK" not in str(events[0].event_metadata)


def test_institution_verification_level_invalid_and_unknown(client, admin, institution):
    bad = client.post(
        f"/admin/institutions/{institution.id}/verification-level", json={"verification_level": "T9"}, headers=_h(admin)
    )
    assert bad.status_code == 422
    missing = client.post(
        f"/admin/institutions/{uuid.uuid4()}/verification-level", json={"verification_level": "T2"}, headers=_h(admin)
    )
    assert missing.status_code == 404


def test_admin_suspends_and_reactivates_institution(client, session, admin, institution):
    r = client.post(f"/admin/institutions/{institution.id}/suspend", json={}, headers=_h(admin))
    assert r.status_code == 200 and r.json()["status"] == "SUSPENDED"
    assert client.post(f"/admin/institutions/{institution.id}/suspend", json={}, headers=_h(admin)).status_code == 200
    assert _audit_count(session, "ADMIN_SUSPEND_INSTITUTION", institution.id) == 1
    r = client.post(f"/admin/institutions/{institution.id}/reactivate", json={}, headers=_h(admin))
    assert r.status_code == 200 and r.json()["status"] == "ACTIVE"
    assert client.post(f"/admin/institutions/{uuid.uuid4()}/suspend", json={}, headers=_h(admin)).status_code == 404
