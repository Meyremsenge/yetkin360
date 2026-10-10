"""
Role x endpoint matrix for GET /admin/audit-events (A1) and GET /admin/fraud-flags/history (F2).

Non-admin roles get 404 with no list envelope in the body; anonymous gets 401;
platform admin gets 200. The audit response must not leak e-mails or free text.
"""

import uuid
from datetime import datetime, timezone

import pytest

from app.models import (
    AuditEvent,
    FraudFlag,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    User,
)
from app.services.audit import log_audit_event

ENDPOINTS = ["/admin/audit-events?limit=1", "/admin/fraud-flags/history?limit=1"]
ENVELOPE_KEYS = ("items", "has_more", "limit", "offset")


def _user(session, email, **kw):
    user = User(email=email, password_hash="hash", **kw)
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def admin(session):
    return _user(session, "aud-admin@example.com", is_platform_admin=True)


@pytest.fixture
def talent(session):
    return _user(session, "aud-talent@example.com")


@pytest.fixture
def org_admin(session):
    user = _user(session, "aud-orgadmin@example.com")
    org = Organization(name="Aud Org", verification_level="T1")
    session.add(org)
    session.flush()
    session.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="ADMIN", status="ACTIVE"))
    session.flush()
    return user


@pytest.fixture
def coordinator(session):
    user = _user(session, "aud-coord@example.com")
    inst = Institution(name="Aud Inst", domain="aud-inst.edu.tr", verification_level="T1", status="ACTIVE")
    session.add(inst)
    session.flush()
    session.add(InstitutionMember(institution_id=inst.id, user_id=user.id, role="COORDINATOR"))
    session.flush()
    return user


def _h(user):
    return {"X-Debug-User-Id": str(user.id)}


class TestRoleMatrix:
    @pytest.mark.parametrize("url", ENDPOINTS)
    @pytest.mark.parametrize("who", ["talent", "org_admin", "coordinator"])
    def test_non_admin_gets_404_without_envelope(self, request, client, url, who):
        user = request.getfixturevalue(who)
        response = client.get(url, headers=_h(user))
        assert response.status_code == 404, response.text
        body = response.json()
        assert body["code"] == "NOT_FOUND"
        for key in ENVELOPE_KEYS:
            assert key not in body

    @pytest.mark.parametrize("url", ENDPOINTS)
    def test_anonymous_gets_401(self, client, url):
        assert client.get(url).status_code == 401

    @pytest.mark.parametrize("url", ENDPOINTS)
    def test_platform_admin_gets_200_with_envelope(self, client, admin, url):
        response = client.get(url, headers=_h(admin))
        assert response.status_code == 200, response.text
        body = response.json()
        for key in ENVELOPE_KEYS:
            assert key in body

    @pytest.mark.parametrize("url", ["/admin/audit-events", "/admin/fraud-flags/history"])
    @pytest.mark.parametrize("query", ["limit=201", "limit=0", "limit=100000", "offset=-1", "offset=abc"])
    def test_invalid_paging_is_422(self, client, admin, url, query):
        response = client.get(f"{url}?{query}", headers=_h(admin))
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "VALIDATION_ERROR"

    def test_invalid_history_status_is_422(self, client, admin):
        assert client.get("/admin/fraud-flags/history?status=PENDING", headers=_h(admin)).status_code == 422


class TestAuditEvents:
    def _seed(self, session, n, action="A1_TEST_ACTION", actor=None, metadata=None):
        for _ in range(n):
            log_audit_event(
                session=session,
                actor_user_id=actor.id if actor else None,
                actor_ip="203.0.113.7",
                action=action,
                subject_type="a1_test",
                subject_id=uuid.uuid4(),
                result="SUCCESS",
                metadata=metadata,
            )

    def test_envelope_newest_first_and_has_more(self, client, session, admin):
        self._seed(session, 3)
        page1 = client.get("/admin/audit-events?action=A1_TEST_ACTION&limit=2", headers=_h(admin)).json()
        assert len(page1["items"]) == 2
        assert page1["has_more"] is True
        assert page1["limit"] == 2 and page1["offset"] == 0
        ids = [i["id"] for i in page1["items"]]
        assert ids == sorted(ids, reverse=True)
        page2 = client.get("/admin/audit-events?action=A1_TEST_ACTION&limit=2&offset=2", headers=_h(admin)).json()
        assert len(page2["items"]) == 1
        assert page2["has_more"] is False

    def test_exact_limit_has_more_false(self, client, session, admin):
        self._seed(session, 2)
        body = client.get("/admin/audit-events?action=A1_TEST_ACTION&limit=2", headers=_h(admin)).json()
        assert len(body["items"]) == 2 and body["has_more"] is False

    def test_empty_result_is_200_envelope(self, client, admin):
        body = client.get("/admin/audit-events?action=NOPE_NOPE", headers=_h(admin)).json()
        assert body == {"items": [], "limit": 50, "offset": 0, "has_more": False}

    def test_filters_by_actor_and_subject_type(self, client, session, admin, talent):
        self._seed(session, 1, actor=talent)
        self._seed(session, 1, actor=admin)
        body = client.get(
            f"/admin/audit-events?actor_user_id={talent.id}&subject_type=a1_test", headers=_h(admin)
        ).json()
        assert len(body["items"]) == 1
        assert body["items"][0]["actor_user_id"] == str(talent.id)
        assert body["items"][0]["actor_ip"] == "203.0.113.7"

    def test_response_leaks_no_email_or_free_text(self, client, session, admin, talent):
        self._seed(
            session,
            1,
            actor=talent,
            metadata={
                "verification_level": "T3",
                "name": "Gizli Kurulus AS",
                "legal_id": "1234567890",
                "title": "ozel calisma basligi",
                "free_note": "x" * 50,
                "reason": "y" * 500,
                "nested": {"hint": "a-b"},
            },
        )
        response = client.get("/admin/audit-events?action=A1_TEST_ACTION", headers=_h(admin))
        text = response.text
        for forbidden in ("@", "password", "token", "Gizli Kurulus", "1234567890", "ozel calisma", "free_note"):
            assert forbidden not in text, forbidden
        item = response.json()["items"][0]
        assert item["metadata"] == {"verification_level": "T3"}
        assert "actor_email" not in item and "email" not in item

    def test_endpoint_does_not_write_audit_rows(self, client, session, admin):
        before = session.query(AuditEvent).count()
        client.get("/admin/audit-events", headers=_h(admin))
        assert session.query(AuditEvent).count() == before


class TestFraudHistory:
    def _flag(self, session, status, reviewer=None):
        flag = FraudFlag(
            subject_type="ATTESTATION",
            subject_id=uuid.uuid4(),
            reason="Kural gerekcesi",
            confidence="HIGH",
            model="rules-v1",
            status=status,
            reviewed_by_user_id=reviewer.id if reviewer else None,
            reviewed_at=datetime.now(timezone.utc) if reviewer else None,
        )
        session.add(flag)
        session.flush()
        return flag

    def test_only_reviewed_flags_with_reviewer_fields(self, client, session, admin):
        pending = self._flag(session, "PENDING")
        confirmed = self._flag(session, "CONFIRMED", admin)
        dismissed = self._flag(session, "DISMISSED", admin)
        body = client.get("/admin/fraud-flags/history", headers=_h(admin)).json()
        by_id = {i["id"]: i for i in body["items"]}
        assert str(pending.id) not in by_id
        assert by_id[str(confirmed.id)]["status"] == "CONFIRMED"
        assert by_id[str(confirmed.id)]["reviewed_by_user_id"] == str(admin.id)
        assert by_id[str(dismissed.id)]["reviewed_at"] is not None

    def test_status_filter_and_pagination(self, client, session, admin):
        for _ in range(3):
            self._flag(session, "DISMISSED", admin)
        self._flag(session, "CONFIRMED", admin)
        body = client.get("/admin/fraud-flags/history?status=DISMISSED&limit=2", headers=_h(admin)).json()
        assert len(body["items"]) == 2 and body["has_more"] is True
        assert all(i["status"] == "DISMISSED" for i in body["items"])
        body2 = client.get("/admin/fraud-flags/history?status=DISMISSED&limit=2&offset=2", headers=_h(admin)).json()
        assert len(body2["items"]) == 1 and body2["has_more"] is False
