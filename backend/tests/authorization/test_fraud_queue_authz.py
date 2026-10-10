"""
Fraud flag queue authorization tests (PLAN 3.54 — faz 1).

- Yalnız platform admin erişebilir: GET /admin/fraud-queue, POST
  /admin/fraud-queue/{id}/resolve — non-admin 404 (CLAUDE.md: 403 kaynağın
  varlığını sızdırır), anonim 401 (auth katmanında, admin kontrolünden önce).
- Pozitif: admin kuyruğu görür, CONFIRMED/DISMISSED ile çözer, audit_events'e
  yazılır, ikinci çözüm denemesi 409 (zaten incelenmiş — tekrar inceleme yok).
"""

import uuid

import pytest

from app.models import AuditEvent, FraudFlag, User


@pytest.fixture
def platform_admin_ff(session):
    user = User(email="platform-admin-ff@example.com", password_hash="hash_admin", is_platform_admin=True)
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def non_admin_talent_ff(session):
    user = User(email="non-admin-talent-ff@example.com", password_hash="hash_talent")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def pending_flag(session):
    flag = FraudFlag(
        subject_type="ATTESTATION",
        subject_id=uuid.uuid4(),
        reason="Şablon ifade paterni tespit edildi.",
        confidence="HIGH",
        model="anthropic/claude-haiku-4.5",
    )
    session.add(flag)
    session.flush()
    return flag


class TestFraudQueueAdminOnlyAccess:
    def test_non_admin_cannot_list_fraud_queue_404(self, client, non_admin_talent_ff):
        response = client.get(
            "/admin/fraud-queue",
            headers={"X-Debug-User-Id": str(non_admin_talent_ff.id)},
        )
        assert response.status_code == 404, response.text

    def test_non_admin_cannot_resolve_fraud_flag_404(self, client, non_admin_talent_ff, pending_flag):
        response = client.post(
            f"/admin/fraud-queue/{pending_flag.id}/resolve",
            headers={"X-Debug-User-Id": str(non_admin_talent_ff.id)},
            json={"outcome": "DISMISSED"},
        )
        assert response.status_code == 404, response.text

    def test_anonymous_gets_401_not_404(self, client):
        response = client.get("/admin/fraud-queue")
        assert response.status_code == 401, response.text


class TestFraudQueuePositive:
    def test_admin_sees_pending_flag(self, client, platform_admin_ff, pending_flag):
        response = client.get(
            "/admin/fraud-queue",
            headers={"X-Debug-User-Id": str(platform_admin_ff.id)},
        )
        assert response.status_code == 200, response.text
        ids = {item["id"] for item in response.json()["items"]}
        assert str(pending_flag.id) in ids

    def test_admin_confirms_flag_and_audit_logged(self, client, session, platform_admin_ff, pending_flag):
        response = client.post(
            f"/admin/fraud-queue/{pending_flag.id}/resolve",
            headers={"X-Debug-User-Id": str(platform_admin_ff.id)},
            json={"outcome": "CONFIRMED"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["id"] == str(pending_flag.id)

        session.refresh(pending_flag)
        assert pending_flag.status == "CONFIRMED"
        assert pending_flag.reviewed_by_user_id == platform_admin_ff.id
        assert pending_flag.reviewed_at is not None

        event = (
            session.query(AuditEvent)
            .filter_by(action="ADMIN_RESOLVE_FRAUD_FLAG", subject_id=pending_flag.id)
            .first()
        )
        assert event is not None

    def test_admin_dismisses_flag(self, client, session, platform_admin_ff, pending_flag):
        response = client.post(
            f"/admin/fraud-queue/{pending_flag.id}/resolve",
            headers={"X-Debug-User-Id": str(platform_admin_ff.id)},
            json={"outcome": "DISMISSED"},
        )
        assert response.status_code == 200, response.text
        session.refresh(pending_flag)
        assert pending_flag.status == "DISMISSED"

    def test_resolved_flag_disappears_from_queue(self, client, session, platform_admin_ff, pending_flag):
        client.post(
            f"/admin/fraud-queue/{pending_flag.id}/resolve",
            headers={"X-Debug-User-Id": str(platform_admin_ff.id)},
            json={"outcome": "DISMISSED"},
        )
        response = client.get(
            "/admin/fraud-queue",
            headers={"X-Debug-User-Id": str(platform_admin_ff.id)},
        )
        ids = {item["id"] for item in response.json()["items"]}
        assert str(pending_flag.id) not in ids

    def test_resolving_an_already_resolved_flag_returns_409(self, client, platform_admin_ff, pending_flag):
        client.post(
            f"/admin/fraud-queue/{pending_flag.id}/resolve",
            headers={"X-Debug-User-Id": str(platform_admin_ff.id)},
            json={"outcome": "CONFIRMED"},
        )
        response = client.post(
            f"/admin/fraud-queue/{pending_flag.id}/resolve",
            headers={"X-Debug-User-Id": str(platform_admin_ff.id)},
            json={"outcome": "DISMISSED"},
        )
        assert response.status_code == 409, response.text

    def test_resolving_unknown_flag_returns_404(self, client, platform_admin_ff):
        response = client.post(
            f"/admin/fraud-queue/{uuid.uuid4()}/resolve",
            headers={"X-Debug-User-Id": str(platform_admin_ff.id)},
            json={"outcome": "CONFIRMED"},
        )
        assert response.status_code == 404, response.text

    def test_invalid_outcome_returns_422(self, client, platform_admin_ff, pending_flag):
        response = client.post(
            f"/admin/fraud-queue/{pending_flag.id}/resolve",
            headers={"X-Debug-User-Id": str(platform_admin_ff.id)},
            json={"outcome": "MAYBE"},
        )
        assert response.status_code == 422, response.text
