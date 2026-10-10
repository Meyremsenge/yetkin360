"""
In-progress demo engagements for institutions and organizations.

Every seed institution and organization must have student engagements waiting
on it, produced through the real state machine (no direct status writes).
"""

from collections import Counter

from sqlalchemy import func, select

from app.models import Engagement, EngagementTask, Institution, Organization, User, VerifiedExperience
from scripts.seed import (
    PIPELINE_ENGAGEMENTS,
    PIPELINE_STUDENT_TASK,
    seed_engagements,
    seed_institutions_and_organizations,
    seed_pipeline_engagements,
    seed_skills,
    seed_talents,
    seed_verified_organizations,
)

PIPELINE_TITLES = {row[2] for row in PIPELINE_ENGAGEMENTS}


def _run_seed(session) -> None:
    seed_skills(session)
    seed_talents(session)
    seed_institutions_and_organizations(session)
    seed_verified_organizations(session)
    seed_engagements(session)
    seed_pipeline_engagements(session)
    session.commit()


def _pipeline(session) -> list[Engagement]:
    return list(session.execute(select(Engagement).where(Engagement.title.in_(PIPELINE_TITLES))).scalars())


def test_pipeline_engagements_stop_at_their_stage(session):
    _run_seed(session)

    by_title = {eng.title: eng for eng in _pipeline(session)}
    assert set(by_title) == PIPELINE_TITLES
    for row in PIPELINE_ENGAGEMENTS:
        assert by_title[row[2]].status == row[7], row[2]


def test_every_institution_and_organization_has_something_waiting(session):
    _run_seed(session)
    engagements = _pipeline(session)

    institutions = session.execute(
        select(Institution).where(Institution.domain.like("inst%.seed.local"))
    ).scalars().all()
    organizations = session.execute(
        select(Organization).where(Organization.legal_id.like("ORG%"))
    ).scalars().all()
    assert len(institutions) == 5 and len(organizations) == 5

    awaiting_approval = Counter(e.institution_id for e in engagements if e.status == "PENDING_APPROVAL")
    awaiting_evaluation = Counter(e.organization_id for e in engagements if e.status == "PENDING_EVALUATION")
    in_progress = Counter(e.organization_id for e in engagements if e.status == "ACTIVE")
    for institution in institutions:
        assert awaiting_approval[institution.id] >= 1, institution.name
    for organization in organizations:
        assert awaiting_evaluation[organization.id] >= 1, organization.name
        assert in_progress[organization.id] >= 1, organization.name


def test_active_engagements_carry_an_unverified_student_task(session):
    _run_seed(session)

    for engagement in _pipeline(session):
        tasks = session.execute(
            select(EngagementTask).where(EngagementTask.engagement_id == engagement.id)
        ).scalars().all()
        unverified = [task for task in tasks if task.verified_at is None]
        if engagement.status == "ACTIVE":
            assert [task.title for task in unverified] == [PIPELINE_STUDENT_TASK], engagement.title
            assert any(task.verified_at is not None for task in tasks), engagement.title
        else:
            assert unverified == [], engagement.title


def test_pipeline_seed_creates_no_verified_experience(session):
    _run_seed(session)

    pipeline_ids = [eng.id for eng in _pipeline(session)]
    count = session.execute(
        select(func.count()).select_from(VerifiedExperience).where(VerifiedExperience.engagement_id.in_(pipeline_ids))
    ).scalar_one()
    assert count == 0


def test_pipeline_seed_is_idempotent(session):
    _run_seed(session)
    before = session.execute(select(func.count()).select_from(Engagement)).scalar_one()

    assert seed_pipeline_engagements(session) == 0
    session.commit()

    assert session.execute(select(func.count()).select_from(Engagement)).scalar_one() == before


def test_coordinator_list_shows_the_waiting_student(client, session):
    _run_seed(session)
    coordinator = session.execute(
        select(User).where(User.email == "kurum1-koordinator@seed.local")
    ).scalar_one()

    response = client.get("/engagements?limit=200", headers={"X-Debug-User-Id": str(coordinator.id)})

    assert response.status_code == 200
    waiting = [item for item in response.json()["items"] if item["status"] == "PENDING_APPROVAL"]
    assert [item["title"] for item in waiting] == ["Ödeme Servisi Entegrasyon Stajı"]
    assert waiting[0]["talent_name"]
