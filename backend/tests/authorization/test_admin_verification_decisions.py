"""
YET-198 (IS-11): admin verification queue decision semantics.

- "Reject" is now its own endpoint: the org leaves the queue, level and verified_at stay.
- verified_at/verified_by are touched only when the level is RAISED (same value / downgrade: untouched).
- The free-text `note` is never written to audit metadata (only its length).
- Unauthorized access is 404 (existing and unknown ids indistinguishable), anonymous is 401.
"""

import uuid

import pytest

from app.models import AuditEvent, Organization, User

NOTE = "ozel-red-gerekcesi-SIZINTI-KONTROLU"


@pytest.fixture
def admin(session):
    user = User(email="yet198-admin@example.com", password_hash="h", is_platform_admin=True)
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent(session):
    user = User(email="yet198-talent@example.com", password_hash="h")
    session.add(user)
    session.flush()
    return user


def _org(session, level="T2", name="YET198 A.S."):
    org = Organization(name=name, legal_id=f"L-{uuid.uuid4().hex[:10]}", verification_level=level)
    session.add(org)
    session.flush()
    return org


def _h(user):
    return {"X-Debug-User-Id": str(user.id)}


def _queue_ids(client, admin):
    r = client.get("/admin/verification-queue", headers=_h(admin))
    assert r.status_code == 200, r.text
    return {i["id"] for i in r.json()["items"]}


def _events(session, action, org):
    return session.query(AuditEvent).filter_by(action=action, subject_id=org.id).all()


class TestReject:
    def test_reject_removes_org_from_queue_and_keeps_level(self, client, session, admin):
        org = _org(session)
        other = _org(session, name="Baska")
        assert str(org.id) in _queue_ids(client, admin)

        r = client.post(
            f"/admin/organizations/{org.id}/verification-reject", headers=_h(admin), json={"note": NOTE}
        )
        assert r.status_code == 200, r.text
        assert r.json()["verification_level"] == "T2"
        assert r.json()["verified_at"] is None

        ids = _queue_ids(client, admin)
        assert str(org.id) not in ids
        assert str(other.id) in ids
        session.refresh(org)
        assert org.verification_level == "T2"
        assert org.verified_at is None
        assert org.verified_by_user_id is None
        assert org.verification_rejected_at is not None

    def test_reject_audit_has_no_free_text(self, client, session, admin):
        org = _org(session)
        client.post(f"/admin/organizations/{org.id}/verification-reject", headers=_h(admin), json={"note": NOTE})
        events = _events(session, "ADMIN_REJECT_VERIFICATION", org)
        assert len(events) == 1
        assert NOTE not in str(events[0].event_metadata)
        assert events[0].event_metadata.get("note_length") == len(NOTE)

    def test_reject_without_note_ok(self, client, session, admin):
        org = _org(session)
        r = client.post(f"/admin/organizations/{org.id}/verification-reject", headers=_h(admin), json={})
        assert r.status_code == 200, r.text

    def test_reject_unknown_org_404(self, client, admin):
        r = client.post(f"/admin/organizations/{uuid.uuid4()}/verification-reject", headers=_h(admin), json={})
        assert r.status_code == 404, r.text

    @pytest.mark.parametrize("level", ["T1", "T3"])
    def test_reject_non_pending_org_409(self, client, session, admin, level):
        org = _org(session, level=level)
        r = client.post(f"/admin/organizations/{org.id}/verification-reject", headers=_h(admin), json={})
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "NOT_PENDING"

    def test_reject_org_without_legal_id_409(self, client, session, admin):
        org = Organization(name="Basvurusuz", verification_level="T2")
        session.add(org)
        session.flush()
        r = client.post(f"/admin/organizations/{org.id}/verification-reject", headers=_h(admin), json={})
        assert r.status_code == 409, r.text

    def test_reject_twice_409_and_rejected_at_stable(self, client, session, admin):
        org = _org(session)
        client.post(f"/admin/organizations/{org.id}/verification-reject", headers=_h(admin), json={})
        session.refresh(org)
        first = org.verification_rejected_at
        r = client.post(f"/admin/organizations/{org.id}/verification-reject", headers=_h(admin), json={})
        assert r.status_code == 409, r.text
        session.refresh(org)
        assert org.verification_rejected_at == first

    def test_approve_after_reject_clears_rejection(self, client, session, admin):
        org = _org(session)
        client.post(f"/admin/organizations/{org.id}/verification-reject", headers=_h(admin), json={})
        r = client.post(
            f"/admin/organizations/{org.id}/verification-level", headers=_h(admin), json={"verification_level": "T3"}
        )
        assert r.status_code == 200, r.text
        session.refresh(org)
        assert org.verification_rejected_at is None
        assert org.verification_level == "T3"

    def test_queue_drains_after_decisions(self, client, session, admin):
        a, b = _org(session), _org(session)
        assert {str(a.id), str(b.id)} <= _queue_ids(client, admin)
        client.post(f"/admin/organizations/{a.id}/verification-reject", headers=_h(admin), json={})
        client.post(
            f"/admin/organizations/{b.id}/verification-level", headers=_h(admin), json={"verification_level": "T3"}
        )
        after = _queue_ids(client, admin)
        assert str(a.id) not in after and str(b.id) not in after


class TestSetLevelSemantics:
    def test_same_level_does_not_touch_verified_fields(self, client, session, admin):
        org = _org(session)
        r = client.post(
            f"/admin/organizations/{org.id}/verification-level", headers=_h(admin), json={"verification_level": "T2"}
        )
        assert r.status_code == 200, r.text
        assert r.json()["verified_at"] is None
        session.refresh(org)
        assert org.verified_at is None
        assert org.verified_by_user_id is None

    def test_upgrade_sets_verified_fields(self, client, session, admin):
        org = _org(session)
        r = client.post(
            f"/admin/organizations/{org.id}/verification-level", headers=_h(admin), json={"verification_level": "T3"}
        )
        assert r.status_code == 200, r.text
        session.refresh(org)
        assert org.verified_at is not None
        assert org.verified_by_user_id == admin.id

    def test_downgrade_keeps_verified_fields(self, client, session, admin):
        org = _org(session)
        client.post(
            f"/admin/organizations/{org.id}/verification-level", headers=_h(admin), json={"verification_level": "T3"}
        )
        session.refresh(org)
        stamp = org.verified_at
        r = client.post(
            f"/admin/organizations/{org.id}/verification-level", headers=_h(admin), json={"verification_level": "T1"}
        )
        assert r.status_code == 200, r.text
        session.refresh(org)
        assert org.verification_level == "T1"
        assert org.verified_at == stamp

    def test_set_level_audit_has_no_free_text(self, client, session, admin):
        org = _org(session)
        client.post(
            f"/admin/organizations/{org.id}/verification-level",
            headers=_h(admin),
            json={"verification_level": "T3", "note": NOTE},
        )
        events = _events(session, "ADMIN_SET_VERIFICATION_LEVEL", org)
        assert len(events) == 1
        assert NOTE not in str(events[0].event_metadata)
        assert events[0].event_metadata.get("note_length") == len(NOTE)
        assert events[0].event_metadata.get("verification_level") == "T3"


class TestRejectAuthorization:
    def test_non_admin_404_same_for_existing_and_unknown(self, client, session, talent):
        org = _org(session)
        r1 = client.post(f"/admin/organizations/{org.id}/verification-reject", headers=_h(talent), json={})
        r2 = client.post(f"/admin/organizations/{uuid.uuid4()}/verification-reject", headers=_h(talent), json={})
        assert r1.status_code == 404 and r2.status_code == 404
        assert {k: v for k, v in r1.json().items() if k != "request_id"} == {
            k: v for k, v in r2.json().items() if k != "request_id"
        }
        session.refresh(org)
        assert org.verification_rejected_at is None

    def test_anonymous_401(self, client, session):
        org = _org(session)
        r = client.post(f"/admin/organizations/{org.id}/verification-reject", json={})
        assert r.status_code == 401, r.text
