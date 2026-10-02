"""
Talent's own institution link request history (YET-197/IS-10).

GET /talents/me/institution-link-requests → talent's own requests, all statuses,
newest first, with institution_name.
"""

import pytest

from app.models import Institution, InstitutionLinkRequest, TalentProfile, User


@pytest.fixture
def user_student(session):
    user = User(email="link-history-student@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent(session, user_student):
    profile = TalentProfile(user_id=user_student.id, full_name="Link History Student", visibility="PRIVATE")
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def institution_x(session):
    inst = Institution(name="Institution X", domain="x.edu.tr", verification_level="T1", status="ACTIVE")
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_y(session):
    inst = Institution(name="Institution Y", domain="y.edu.tr", verification_level="T1", status="ACTIVE")
    session.add(inst)
    session.flush()
    return inst


class TestMyLinkRequestsHistory:
    """GET /talents/me/institution-link-requests — talent's own request history."""

    def test_talent_lists_own_requests_all_statuses_newest_first(self, session, user_student, talent, institution_x, institution_y, client):
        """
        AC: all statuses returned (PENDING/APPROVED/REJECTED), ordered newest first,
        each item carries institution_name.
        """
        import datetime as dt

        older = InstitutionLinkRequest(
            talent_profile_id=talent.id, institution_id=institution_x.id, status="REJECTED",
            requested_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
        )
        newer = InstitutionLinkRequest(
            talent_profile_id=talent.id, institution_id=institution_y.id, status="PENDING",
            requested_at=dt.datetime(2026, 2, 1, tzinfo=dt.timezone.utc),
        )
        session.add_all([older, newer])
        session.flush()

        response = client.get("/talents/me/institution-link-requests", headers={"X-Debug-User-Id": str(user_student.id)})

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        items = response.json()["items"]
        assert len(items) == 2
        # newest first
        assert items[0]["id"] == str(newer.id)
        assert items[0]["status"] == "PENDING"
        assert items[0]["institution_name"] == "Institution Y"
        assert items[1]["id"] == str(older.id)
        assert items[1]["status"] == "REJECTED"
        assert items[1]["institution_name"] == "Institution X"

    def test_talent_with_no_requests_returns_empty_list(self, user_student, talent, client):
        response = client.get("/talents/me/institution-link-requests", headers={"X-Debug-User-Id": str(user_student.id)})

        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_response_includes_institution_name(self, session, user_student, talent, institution_x, client):
        """institution_name field resolves to the real Institution.name, not just the id."""
        link_req = InstitutionLinkRequest(talent_profile_id=talent.id, institution_id=institution_x.id, status="PENDING")
        session.add(link_req)
        session.flush()

        response = client.get("/talents/me/institution-link-requests", headers={"X-Debug-User-Id": str(user_student.id)})

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["institution_id"] == str(institution_x.id)
        assert item["institution_name"] == institution_x.name
