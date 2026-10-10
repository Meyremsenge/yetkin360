"""
A2: admin write endpoints record the caller's IP in audit_events.actor_ip.

Before this, every admin audit row had actor_ip = NULL (hard-coded `None`).
Each write endpoint of app/api/admin.py is triggered directly; the row written
for that request must carry the client address.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.models import AuditEvent, FraudFlag, Organization, Skill, User


PEER_IP = "203.0.113.7"


class _PeerAddress:
    """ASGI wrapper that sets the connection's peer address."""

    def __init__(self, app, host: str):
        self.app = app
        self.host = host

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            scope = {**scope, "client": (self.host, 50000)}
        await self.app(scope, receive, send)


@pytest.fixture
def ip_client(client):
    """Same app and dependency overrides, but the peer is a real IP literal.

    Starlette's default peer is the string "testclient", which _client_ip()
    rightly refuses (audit_events.actor_ip is INET).
    """
    peer_client = TestClient(_PeerAddress(client.app, PEER_IP))
    # Same double-submit CSRF pair the shared `client` fixture sets by default.
    peer_client.cookies.set("csrf_token", "test-csrf-token")
    peer_client.headers.update({"X-CSRF-Token": "test-csrf-token"})
    return peer_client


@pytest.fixture
def admin(session):
    user = User(email="a2-admin@example.com", password_hash="h", is_platform_admin=True)
    session.add(user)
    session.flush()
    return user


def _h(user):
    return {"X-Debug-User-Id": str(user.id)}


def _skill(session, slug):
    skill = Skill(slug=slug, name_tr=slug, category="TOOL", status="ACTIVE")
    session.add(skill)
    session.flush()
    return skill


def _org(session, level="T2"):
    org = Organization(name="A2 A.S.", legal_id=f"L-{uuid.uuid4().hex[:10]}", verification_level=level)
    session.add(org)
    session.flush()
    return org


def _last_event(session, action, subject_id):
    return (
        session.query(AuditEvent)
        .filter_by(action=action, subject_id=subject_id)
        .order_by(AuditEvent.created_at.desc())
        .first()
    )


def _assert_ip(event):
    assert event is not None
    assert event.actor_ip is not None, "actor_ip must not be NULL for an admin write"
    assert str(event.actor_ip) == PEER_IP


def test_verification_level_records_ip(ip_client, session, admin):
    org = _org(session)
    r = ip_client.post(
        f"/admin/organizations/{org.id}/verification-level",
        headers=_h(admin),
        json={"verification_level": "T3"},
    )
    assert r.status_code == 200, r.text
    _assert_ip(_last_event(session, "ADMIN_SET_VERIFICATION_LEVEL", org.id))


def test_verification_reject_records_ip(ip_client, session, admin):
    org = _org(session)
    r = ip_client.post(f"/admin/organizations/{org.id}/verification-reject", headers=_h(admin), json={})
    assert r.status_code == 200, r.text
    _assert_ip(_last_event(session, "ADMIN_REJECT_VERIFICATION", org.id))


def test_skill_create_update_deprecate_records_ip(ip_client, session, admin):
    slug = f"a2-skill-{uuid.uuid4().hex[:8]}"
    r = ip_client.post(
        "/admin/skills",
        headers=_h(admin),
        json={"slug": slug, "name_tr": "A2 Yetkinlik", "category": "TOOL"},
    )
    assert r.status_code == 201, r.text
    skill_id = uuid.UUID(r.json()["id"])
    _assert_ip(_last_event(session, "ADMIN_CREATE_SKILL", skill_id))

    r = ip_client.patch(f"/admin/skills/{skill_id}", headers=_h(admin), json={"name_tr": "A2 Yeni Ad"})
    assert r.status_code == 200, r.text
    _assert_ip(_last_event(session, "ADMIN_UPDATE_SKILL", skill_id))

    r = ip_client.post(f"/admin/skills/{skill_id}/deprecate", headers=_h(admin))
    assert r.status_code == 200, r.text
    _assert_ip(_last_event(session, "ADMIN_DEPRECATE_SKILL", skill_id))


def test_skill_merge_records_ip(ip_client, session, admin):
    source = _skill(session, f"a2-src-{uuid.uuid4().hex[:8]}")
    target = _skill(session, f"a2-dst-{uuid.uuid4().hex[:8]}")
    r = ip_client.post(
        f"/admin/skills/{source.id}/merge",
        headers=_h(admin),
        json={"merged_into_id": str(target.id)},
    )
    assert r.status_code == 200, r.text
    _assert_ip(_last_event(session, "ADMIN_MERGE_SKILL", source.id))


def test_fraud_flag_resolve_records_ip(ip_client, session, admin):
    flag = FraudFlag(
        subject_type="ORGANIZATION",
        subject_id=uuid.uuid4(),
        reason="a2 test",
        confidence="LOW",
        model="rules-v1",
        status="PENDING",
    )
    session.add(flag)
    session.flush()
    r = ip_client.post(
        f"/admin/fraud-queue/{flag.id}/resolve",
        headers=_h(admin),
        json={"outcome": "DISMISSED"},
    )
    assert r.status_code == 200, r.text
    _assert_ip(_last_event(session, "ADMIN_RESOLVE_FRAUD_FLAG", flag.id))
