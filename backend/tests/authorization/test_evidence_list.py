"""
YET-195: GET /evidence — the talent's own evidence list.

Unauthenticated → 401, no talent profile → 403, another talent's evidence is
never listed, soft-deleted rows are hidden.
"""

import uuid
from datetime import datetime, timezone

from app.models import User
from tests._evidence_api import add_evidence, login


class TestListEvidence:
    def test_unauthenticated_returns_401(self, evidence_api):
        assert evidence_api.get("/evidence").status_code == 401

    def test_user_without_talent_profile_returns_403(self, evidence_api, session):
        user = User(email="no-talent@example.com", password_hash="h")
        session.add(user)
        session.flush()
        login(evidence_api, user)
        response = evidence_api.get("/evidence")
        assert response.status_code == 403
        assert response.json()["code"] == "TALENT_PROFILE_REQUIRED"

    def test_lists_only_own_evidence_newest_first(self, evidence_api, session, user_talent_a, talent_a, talent_b):
        first = add_evidence(session, talent_a, scan_status="CLEAN")
        second = add_evidence(session, talent_a)
        theirs = add_evidence(session, talent_b)
        login(evidence_api, user_talent_a)

        response = evidence_api.get("/evidence")

        assert response.status_code == 200
        ids = [item["id"] for item in response.json()]
        assert ids == [str(second.id), str(first.id)]
        assert str(theirs.id) not in ids
        assert {item["owner_talent_id"] for item in response.json()} == {str(talent_a.id)}

    def test_other_talent_sees_none_of_it(self, evidence_api, session, talent_a, user_talent_b, talent_b):
        add_evidence(session, talent_a)
        login(evidence_api, user_talent_b)
        assert evidence_api.get("/evidence").json() == []

    def test_soft_deleted_evidence_is_excluded(self, evidence_api, session, user_talent_a, talent_a):
        add_evidence(session, talent_a, deleted_at=datetime.now(timezone.utc))
        kept = add_evidence(session, talent_a)
        login(evidence_api, user_talent_a)
        assert [i["id"] for i in evidence_api.get("/evidence").json()] == [str(kept.id)]

    def test_scan_status_is_reported(self, evidence_api, session, user_talent_a, talent_a):
        add_evidence(session, talent_a, scan_status="FAILED")
        login(evidence_api, user_talent_a)
        assert evidence_api.get("/evidence").json()[0]["scan_status"] == "FAILED"

    def test_foreign_deliverable_filter_returns_empty_not_error(self, evidence_api, user_talent_a, talent_a):
        login(evidence_api, user_talent_a)
        response = evidence_api.get("/evidence", params={"deliverable_id": str(uuid.uuid4())})
        assert response.status_code == 200 and response.json() == []

    def test_response_has_no_internal_fields(self, evidence_api, session, user_talent_a, talent_a):
        add_evidence(session, talent_a)
        login(evidence_api, user_talent_a)
        item = evidence_api.get("/evidence").json()[0]
        assert "content_hash" not in item and "deleted_at" not in item
