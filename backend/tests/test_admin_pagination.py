"""Admin list endpoints: {items, limit, offset, has_more} envelope (admin-sayfalama-ve-kabuk)."""

import uuid

import pytest

from app.models import FraudFlag, Organization, Skill, User
from app.services.fraud_flag import list_fraud_queue
from app.services.organization import list_verification_queue
from app.services.skill import list_all_skills

ENVELOPE_KEYS = {"items", "limit", "offset", "has_more"}


@pytest.fixture
def admin(session):
    user = User(email="pag-admin@example.com", password_hash="h", is_platform_admin=True)
    session.add(user)
    session.flush()
    return user


def _h(user):
    return {"X-Debug-User-Id": str(user.id)}


def _seed_orgs(session, n):
    for i in range(n):
        session.add(Organization(name=f"Org {i:03d}", legal_id=f"LID-{i:03d}", verification_level="T2"))
    session.flush()


def _seed_skills(session, n):
    for i in range(n):
        session.add(Skill(slug=f"pag-skill-{i:03d}", name_tr=f"Skill {i:03d}", category="TOOL"))
    session.flush()


def _seed_flags(session, n):
    for _ in range(n):
        session.add(
            FraudFlag(
                subject_type="ATTESTATION",
                subject_id=uuid.uuid4(),
                reason="r",
                confidence="LOW",
                model="rules-v1",
            )
        )
    session.flush()


SEEDERS = {
    "/admin/verification-queue": _seed_orgs,
    "/admin/skills": _seed_skills,
    "/admin/fraud-queue": _seed_flags,
}


class TestServiceHasMore:
    def test_verification_queue_limit_plus_one(self, session):
        _seed_orgs(session, 4)
        rows, has_more = list_verification_queue(session, limit=3, offset=0)
        assert len(rows) == 3 and has_more is True

    def test_verification_queue_exact_limit(self, session):
        _seed_orgs(session, 3)
        rows, has_more = list_verification_queue(session, limit=3, offset=0)
        assert len(rows) == 3 and has_more is False

    def test_skills_limit_plus_one_and_last_page(self, session):
        _seed_skills(session, 4)
        rows, has_more = list_all_skills(session, limit=3, offset=0)
        assert len(rows) == 3 and has_more is True
        rows, has_more = list_all_skills(session, limit=3, offset=3)
        assert len(rows) == 1 and has_more is False

    def test_fraud_queue_limit_plus_one_and_exact(self, session):
        _seed_flags(session, 4)
        rows, has_more = list_fraud_queue(session, limit=3, offset=0)
        assert len(rows) == 3 and has_more is True
        rows, has_more = list_fraud_queue(session, limit=4, offset=0)
        assert len(rows) == 4 and has_more is False


@pytest.mark.parametrize("path", list(SEEDERS))
class TestEnvelopeEndpoints:
    def test_limit_plus_one_not_silently_truncated(self, client, session, admin, path):
        SEEDERS[path](session, 51)
        body = client.get(f"{path}?limit=50&offset=0", headers=_h(admin)).json()
        assert set(body) == ENVELOPE_KEYS
        assert len(body["items"]) == 50
        assert body["has_more"] is True and body["limit"] == 50 and body["offset"] == 0

        second = client.get(f"{path}?limit=50&offset=50", headers=_h(admin)).json()
        assert len(second["items"]) == 1  # the 51st record is reachable
        assert second["has_more"] is False and second["offset"] == 50

    def test_exact_limit_has_more_false(self, client, session, admin, path):
        SEEDERS[path](session, 50)
        body = client.get(f"{path}?limit=50&offset=0", headers=_h(admin)).json()
        assert len(body["items"]) == 50 and body["has_more"] is False

    def test_max_limit_never_exceeds_200(self, client, session, admin, path):
        SEEDERS[path](session, 250)
        body = client.get(f"{path}?limit=200", headers=_h(admin)).json()
        assert len(body["items"]) == 200 and body["has_more"] is True

    def test_empty_envelope(self, client, admin, path):
        response = client.get(path, headers=_h(admin))
        assert response.status_code == 200
        body = response.json()
        default_limit = 200 if path == "/admin/skills" else 50
        assert body == {"items": [], "limit": default_limit, "offset": 0, "has_more": False}


def test_item_schemas_unchanged(client, session, admin):
    _seed_orgs(session, 1)
    _seed_skills(session, 1)
    _seed_flags(session, 1)
    org = client.get("/admin/verification-queue", headers=_h(admin)).json()["items"][0]
    assert set(org) == {
        "id", "name", "legal_id", "domain", "verification_level", "created_at", "upheld_complaint_count",
    }
    assert org["upheld_complaint_count"] == 0
    skill = client.get("/admin/skills", headers=_h(admin)).json()["items"][0]
    assert set(skill) == {
        "id", "slug", "name_tr", "name_en", "category", "parent_id", "status", "merged_into_id",
    }
    flag = client.get("/admin/fraud-queue", headers=_h(admin)).json()["items"][0]
    assert set(flag) == {
        "id", "subject_type", "subject_id", "subject_label", "signal",
        "reason", "confidence", "model", "created_at",
    }
