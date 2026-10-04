"""
YET-213 (GUV-13): bulk reminders must not be able to bloat the outbox.

POST /institutions/{id}/reminders used to accept any template (-> any
reminder.<x> topic), an unbounded engagement_ids list, and unlimited repeats
for the same engagement. Now: closed template set, <=100 ids (422), one
reminder per (engagement, template) per day (silent skip, still 202), and
20 requests/hour per institution (429 RATE_LIMITED + Retry-After).
Unauthorized callers get 404 first and never consume quota.

The limiter is off by default in the suite (conftest `_rate_limiter_switch`);
this module opts in through the `rate_limited` marker.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.models import (
    AuditEvent,
    AuthRateLimit,
    Engagement,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    Outbox,
    TalentProfile,
    User,
)
from app.services import rate_limit

pytestmark = pytest.mark.rate_limited


def _user(session, tag: str) -> User:
    user = User(email=f"{tag}.{uuid.uuid4().hex[:8]}@example.com", password_hash="x")
    session.add(user)
    session.flush()
    return user


def _institution(session, name: str) -> Institution:
    inst = Institution(name=name, verification_level="T1")
    session.add(inst)
    session.flush()
    return inst


def _member(session, inst: Institution, role: str) -> User:
    user = _user(session, role.lower())
    session.add(InstitutionMember(institution_id=inst.id, user_id=user.id, role=role))
    session.flush()
    return user


def _engagements(session, inst: Institution, org: Organization, count: int) -> list[Engagement]:
    talent_user = _user(session, "talent")
    talent = TalentProfile(
        user_id=talent_user.id, institution_id=inst.id, full_name="Talent", visibility="PRIVATE"
    )
    session.add(talent)
    session.flush()
    rows = [
        Engagement(
            talent_id=talent.id,
            organization_id=org.id,
            institution_id=inst.id,
            status="PENDING_EVALUATION",
            kind="INTERNSHIP",
            title=f"Eng {i}",
        )
        for i in range(count)
    ]
    session.add_all(rows)
    session.flush()
    return rows


@pytest.fixture
def world(session):
    org = Organization(name="Org", verification_level="T1")
    session.add(org)
    session.flush()
    inst = _institution(session, "Inst A")
    other = _institution(session, "Inst B")
    org_member = _user(session, "orgmember")
    session.add(OrganizationMember(organization_id=org.id, user_id=org_member.id, role="MEMBER"))
    session.flush()
    return {
        "inst": inst,
        "other": other,
        "coord": _member(session, inst, "COORDINATOR"),
        "coord2": _member(session, inst, "COORDINATOR"),
        "admin": _member(session, inst, "ADMIN"),
        "other_coord": _member(session, other, "COORDINATOR"),
        "talent_user": _user(session, "outsider"),
        "org_member": org_member,
        "engs": _engagements(session, inst, org, 3),
        "other_engs": _engagements(session, other, org, 1),
    }


def _post(client, user, inst, ids, template="evaluation_pending"):
    return client.post(
        f"/institutions/{inst.id}/reminders",
        headers={"X-Debug-User-Id": str(user.id)},
        json={"engagement_ids": [str(i) for i in ids], "template": template},
    )


def _outbox(session) -> int:
    return session.execute(
        select(func.count()).select_from(Outbox).where(Outbox.topic.like("reminder.%"))
    ).scalar_one()


def _audits(session) -> int:
    return session.execute(
        select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "REMINDERS_TRIGGERED")
    ).scalar_one()


def _assert_limited(response) -> None:
    assert response.status_code == 429
    body = response.json()
    assert body["code"] == "RATE_LIMITED"
    assert 1 <= int(response.headers["Retry-After"]) <= 3600


# ---------------------------------------------------------------------------
# Input bounds
# ---------------------------------------------------------------------------


def test_too_many_engagement_ids_422_and_no_outbox(client, session, world):
    before = _outbox(session)
    ids = [e.id for e in world["engs"]] + [uuid.uuid4() for _ in range(98)]
    assert len(ids) == 101
    response = _post(client, world["coord"], world["inst"], ids)
    assert response.status_code == 422
    assert _outbox(session) == before


def test_exactly_100_engagement_ids_is_accepted(client, session, world):
    ids = [e.id for e in world["engs"]] + [uuid.uuid4() for _ in range(97)]
    assert len(ids) == 100
    response = _post(client, world["coord"], world["inst"], ids)
    assert response.status_code == 202
    assert response.json()["queued_count"] == 3


@pytest.mark.parametrize("template", ["x1", "Evaluation_Pending", "evaluation_pending ", "A" * 5000, "../x", ""])
def test_template_outside_closed_set_422_and_no_outbox(client, session, world, template):
    before = _outbox(session)
    response = _post(client, world["coord"], world["inst"], [world["engs"][0].id], template)
    assert response.status_code == 422
    assert _outbox(session) == before
    topics = session.execute(select(Outbox.topic).where(Outbox.topic.like("reminder.%"))).scalars().all()
    assert set(topics) <= {"reminder.evaluation_pending"}


def test_duplicate_ids_inside_one_request_queue_once(client, session, world):
    before = _outbox(session)
    eng = world["engs"][0].id
    response = _post(client, world["coord"], world["inst"], [eng, eng, eng])
    assert response.status_code == 202
    assert response.json()["queued_count"] == 1
    assert _outbox(session) - before == 1


# ---------------------------------------------------------------------------
# Repeat protection (engagement, template) / 24 h
# ---------------------------------------------------------------------------


def test_repeating_same_targets_does_not_grow_outbox(client, session, world):
    ids = [e.id for e in world["engs"]]
    before = _outbox(session)
    first = _post(client, world["coord"], world["inst"], ids)
    assert first.json()["queued_count"] == 3
    for _ in range(5):
        again = _post(client, world["coord"], world["inst"], ids)
        assert again.status_code == 202
        assert again.json() == {"queued_count": 0}
    assert _outbox(session) - before == 3
    assert _audits(session) == 1  # skipped repeats write no audit row


def test_repeat_protection_is_per_target_not_per_request(client, session, world):
    a, b, c = (e.id for e in world["engs"])
    assert _post(client, world["coord"], world["inst"], [a]).json()["queued_count"] == 1
    response = _post(client, world["coord"], world["inst"], [a, b, c])
    assert response.json()["queued_count"] == 2


def test_repeat_protection_spans_users_of_the_same_institution(client, session, world):
    ids = [e.id for e in world["engs"]]
    before = _outbox(session)
    assert _post(client, world["coord"], world["inst"], ids).json()["queued_count"] == 3
    assert _post(client, world["coord2"], world["inst"], ids).json()["queued_count"] == 0
    assert _post(client, world["admin"], world["inst"], ids).json()["queued_count"] == 0
    assert _outbox(session) - before == 3


# ---------------------------------------------------------------------------
# Per-institution quota: 20 requests / hour -> 429 + Retry-After
# ---------------------------------------------------------------------------


def test_21st_request_in_the_hour_is_429_and_adds_nothing(client, session, world):
    ids = [world["engs"][0].id]
    for _ in range(20):
        assert _post(client, world["coord"], world["inst"], ids).status_code == 202
    before = _outbox(session)
    audits = _audits(session)
    _assert_limited(_post(client, world["coord"], world["inst"], ids))
    _assert_limited(_post(client, world["coord2"], world["inst"], ids))  # quota is per institution
    assert _outbox(session) == before
    assert _audits(session) == audits


def test_quota_is_per_institution(client, session, world):
    for _ in range(21):
        _post(client, world["coord"], world["inst"], [world["engs"][0].id])
    response = _post(client, world["other_coord"], world["other"], [world["other_engs"][0].id])
    assert response.status_code == 202
    assert response.json()["queued_count"] == 1


# ---------------------------------------------------------------------------
# Authorization stays first: 404, and no quota is consumed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("who", ["talent_user", "org_member", "other_coord"])
def test_unauthorized_callers_get_404_and_leave_outbox_untouched(client, session, world, who):
    before = _outbox(session)
    response = _post(client, world[who], world["inst"], [e.id for e in world["engs"]])
    assert response.status_code == 404
    assert _outbox(session) == before


def test_unauthorized_calls_never_consume_the_quota(client, session, world):
    ids = [world["engs"][0].id]
    for _ in range(25):
        assert _post(client, world["other_coord"], world["inst"], ids).status_code == 404
        assert _post(client, world["talent_user"], world["inst"], ids).status_code == 404
    assert _post(client, world["coord"], world["inst"], ids).status_code == 202


def test_exhausted_quota_does_not_turn_404_into_429(client, session, world):
    ids = [world["engs"][0].id]
    for _ in range(21):
        _post(client, world["coord"], world["inst"], ids)
    assert _post(client, world["talent_user"], world["inst"], ids).status_code == 404
    assert _post(client, world["other_coord"], world["inst"], ids).status_code == 404


def test_foreign_engagement_ids_do_not_consume_target_or_quota(client, session, world):
    foreign = [e.id for e in world["other_engs"]]
    for _ in range(25):
        response = _post(client, world["coord"], world["inst"], foreign)
        assert response.status_code == 202
        assert response.json() == {"queued_count": 0}
    assert _post(client, world["coord"], world["inst"], [world["engs"][0].id]).json()["queued_count"] == 1


# ---------------------------------------------------------------------------
# Opportunistic purge must not wipe live 1-day dedupe windows
# ---------------------------------------------------------------------------


def test_purge_keeps_live_day_windows_and_drops_old_ones(client, session, world, monkeypatch):
    now = datetime.now(timezone.utc)
    live = AuthRateLimit(bucket="reminder_target", key_hash="1" * 64, window_start=now - timedelta(hours=5), count=1)
    old = AuthRateLimit(bucket="reminder_target", key_hash="2" * 64, window_start=now - timedelta(days=3), count=1)
    session.add_all([live, old])
    session.flush()
    monkeypatch.setattr(rate_limit.secrets, "randbelow", lambda _n: 0)

    _post(client, world["coord"], world["inst"], [world["engs"][0].id])

    keys = set(session.execute(select(AuthRateLimit.key_hash)).scalars().all())
    assert "1" * 64 in keys
    assert "2" * 64 not in keys
