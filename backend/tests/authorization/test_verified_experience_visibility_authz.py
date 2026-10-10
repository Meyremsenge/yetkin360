"""
Authorization tests for PATCH /talents/me/verified-experiences/{id}/visibility.

D6 change-visibility: visibility is the only mutable column of the append-only
verified_experiences table. Only the owner may change it; ownership comes from
the session principal. Unknown id, another talent's record and a talent-less
caller must all answer an identical 404 (no existence leak).
"""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models import Engagement, Organization, User, VerifiedExperience
from app.models.audit import AuditEvent


def _url(experience_id) -> str:
    return f"/talents/me/verified-experiences/{experience_id}/visibility"


def _auth(user) -> dict:
    return {"X-Debug-User-Id": str(user.id)}


@pytest.fixture
def org(session):
    organization = Organization(name="Visibility Test Org")
    session.add(organization)
    session.flush()
    return organization


def _make_experience(session, talent, org, visibility: str, token: str) -> VerifiedExperience:
    engagement = Engagement(
        id=uuid4(),
        kind="INTERNSHIP",
        talent_id=talent.id,
        organization_id=org.id,
        institution_id=None,
        title=f"Role {token}",
        started_on=date(2026, 1, 1),
        ended_on=date(2026, 3, 1),
        status="VERIFIED",
    )
    session.add(engagement)
    session.flush()
    ve = VerifiedExperience(
        id=uuid4(),
        talent_id=talent.id,
        engagement_id=engagement.id,
        organization_name_snapshot=org.name,
        role_snapshot=engagement.title,
        started_on_snapshot=engagement.started_on,
        ended_on_snapshot=engagement.ended_on,
        institution_name_snapshot=None,
        claim_type="CONTRIBUTION",
        visibility=visibility,
        public_token=token,
        created_at=datetime.now(timezone.utc),
    )
    session.add(ve)
    session.flush()
    return ve


@pytest.fixture
def exp_a_private(session, talent_a, org):
    return _make_experience(session, talent_a, org, "PRIVATE", "vis-token-a")


@pytest.fixture
def exp_b_private(session, talent_b, org):
    return _make_experience(session, talent_b, org, "PRIVATE", "vis-token-b")


# ---------------------------------------------------------------------------
# Positive
# ---------------------------------------------------------------------------


def test_owner_can_publish_own_experience(client, session, user_talent_a, talent_a, exp_a_private):
    response = client.patch(_url(exp_a_private.id), json={"visibility": "PUBLIC"}, headers=_auth(user_talent_a))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(exp_a_private.id)
    assert body["visibility"] == "PUBLIC"
    session.refresh(exp_a_private)
    assert exp_a_private.visibility == "PUBLIC"


def test_published_experience_becomes_publicly_verifiable(client, user_talent_a, talent_a, exp_a_private):
    assert client.get("/public/v/vis-token-a").status_code == 404

    client.patch(_url(exp_a_private.id), json={"visibility": "PUBLIC"}, headers=_auth(user_talent_a))
    assert client.get("/public/v/vis-token-a").status_code == 200

    client.patch(_url(exp_a_private.id), json={"visibility": "PRIVATE"}, headers=_auth(user_talent_a))
    assert client.get("/public/v/vis-token-a").status_code == 404


def test_visibility_change_is_audited(client, session, user_talent_a, talent_a, exp_a_private):
    client.patch(_url(exp_a_private.id), json={"visibility": "PUBLIC"}, headers=_auth(user_talent_a))

    events = session.execute(
        select(AuditEvent).where(
            AuditEvent.action == "VERIFIED_EXPERIENCE_VISIBILITY_CHANGED",
            AuditEvent.subject_id == exp_a_private.id,
        )
    ).scalars().all()
    assert len(events) == 1
    assert events[0].actor_user_id == user_talent_a.id
    assert events[0].event_metadata == {"from": "PRIVATE", "to": "PUBLIC"}


# ---------------------------------------------------------------------------
# Negative — identical 404, record untouched
# ---------------------------------------------------------------------------


def test_other_talent_cannot_change_visibility(client, session, user_talent_a, talent_a, exp_b_private):
    response = client.patch(_url(exp_b_private.id), json={"visibility": "PUBLIC"}, headers=_auth(user_talent_a))

    assert response.status_code == 404
    assert response.json()["code"] == "VERIFIED_EXPERIENCE_NOT_FOUND"
    session.refresh(exp_b_private)
    assert exp_b_private.visibility == "PRIVATE"


def test_foreign_and_unknown_ids_are_indistinguishable(client, user_talent_a, talent_a, exp_b_private):
    foreign = client.patch(_url(exp_b_private.id), json={"visibility": "PUBLIC"}, headers=_auth(user_talent_a))
    unknown = client.patch(_url(uuid4()), json={"visibility": "PUBLIC"}, headers=_auth(user_talent_a))

    assert foreign.status_code == unknown.status_code == 404
    foreign_body = {k: v for k, v in foreign.json().items() if k != "request_id"}
    unknown_body = {k: v for k, v in unknown.json().items() if k != "request_id"}
    assert foreign_body == unknown_body


def test_talentless_user_gets_404(client, session, exp_a_private):
    org_member = User(email="vis-org-member@example.com", password_hash="hash")
    session.add(org_member)
    session.flush()

    response = client.patch(_url(exp_a_private.id), json={"visibility": "PUBLIC"}, headers=_auth(org_member))

    assert response.status_code == 404
    session.refresh(exp_a_private)
    assert exp_a_private.visibility == "PRIVATE"


def test_unauthenticated_request_is_rejected(client, exp_a_private):
    response = client.patch(_url(exp_a_private.id), json={"visibility": "PUBLIC"})

    assert response.status_code == 401


@pytest.mark.parametrize("value", ["public", "EVERYONE", "", None])
def test_invalid_visibility_is_rejected(client, user_talent_a, talent_a, exp_a_private, value):
    response = client.patch(_url(exp_a_private.id), json={"visibility": value}, headers=_auth(user_talent_a))

    assert response.status_code == 422
