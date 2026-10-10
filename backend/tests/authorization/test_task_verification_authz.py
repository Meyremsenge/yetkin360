"""
Authorization tests for task verification.

A talent may add tasks to their own engagement, but such a task is unverified
and produces no SkillSignal until the organization side verifies it:
POST /engagements/{id}/tasks/{task_id}/verify — organization member of the
engagement or the institution's coordinator only. The talent can never verify
their own task, not even when they are also a member of the organization.
"""

import uuid

import pytest
from sqlalchemy import select

from app.models import (
    AuditEvent,
    Engagement,
    EngagementTask,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    Skill,
    SkillSignal,
    TalentProfile,
    User,
)


def _user(session, email: str) -> User:
    user = User(email=email, password_hash="hash")
    session.add(user)
    session.flush()
    return user


def _auth(user: User) -> dict[str, str]:
    return {"X-Debug-User-Id": str(user.id)}


@pytest.fixture
def world(session):
    """One engagement (org A, institution A) plus every kind of actor around it."""
    org_a = Organization(name="Org A", verification_level="T2", status="ACTIVE")
    org_b = Organization(name="Org B", verification_level="T2", status="ACTIVE")
    inst_a = Institution(name="Inst A", verification_level="T2")
    inst_b = Institution(name="Inst B", verification_level="T2")
    session.add_all([org_a, org_b, inst_a, inst_b])
    session.flush()

    talent_user = _user(session, "talent@example.com")
    other_talent_user = _user(session, "other-talent@example.com")
    org_member = _user(session, "org-member@example.com")
    org_admin = _user(session, "org-admin@example.com")
    coordinator = _user(session, "coordinator@example.com")
    other_org_member = _user(session, "other-org@example.com")
    other_coordinator = _user(session, "other-coord@example.com")

    talent = TalentProfile(user_id=talent_user.id, full_name="Talent", institution_id=inst_a.id, visibility="PRIVATE")
    other_talent = TalentProfile(user_id=other_talent_user.id, full_name="Other", visibility="PRIVATE")
    session.add_all([talent, other_talent])
    session.add_all(
        [
            OrganizationMember(organization_id=org_a.id, user_id=org_member.id, role="MEMBER", status="ACTIVE"),
            OrganizationMember(organization_id=org_a.id, user_id=org_admin.id, role="ADMIN", status="ACTIVE"),
            OrganizationMember(organization_id=org_b.id, user_id=other_org_member.id, role="MEMBER", status="ACTIVE"),
            # The talent is ALSO a member of the organization: must still not verify their own task.
            OrganizationMember(organization_id=org_a.id, user_id=talent_user.id, role="MEMBER", status="ACTIVE"),
            InstitutionMember(institution_id=inst_a.id, user_id=coordinator.id, role="COORDINATOR"),
            InstitutionMember(
                institution_id=inst_b.id, user_id=other_coordinator.id, role="COORDINATOR"
            ),
        ]
    )
    session.flush()

    engagement = Engagement(
        talent_id=talent.id,
        organization_id=org_a.id,
        institution_id=inst_a.id,
        kind="INTERNSHIP",
        title="Staj",
        status="ACTIVE",
        confidential=False,
    )
    skill = Skill(slug="t-verify-python", name_en="Python", name_tr="Python", category="LANGUAGE", status="ACTIVE")
    session.add_all([engagement, skill])
    session.flush()

    return {
        "engagement": engagement,
        "talent": talent,
        "skill": skill,
        "talent_user": talent_user,
        "other_talent_user": other_talent_user,
        "org_member": org_member,
        "org_admin": org_admin,
        "coordinator": coordinator,
        "other_org_member": other_org_member,
        "other_coordinator": other_coordinator,
    }


@pytest.fixture
def unverified_task(client, session, world):
    """A task the talent added, tagged with a skill."""
    response = client.post(
        f"/engagements/{world['engagement'].id}/tasks",
        json={"title": "Öğrencinin eklediği görev", "skill_id": str(world["skill"].id)},
        headers=_auth(world["talent_user"]),
    )
    assert response.status_code == 201, response.text
    assert response.json()["verified"] is False
    return session.get(EngagementTask, uuid.UUID(response.json()["id"]))


def _verify(client, world, task, actor: str):
    return client.post(
        f"/engagements/{world['engagement'].id}/tasks/{task.id}/verify",
        headers=_auth(world[actor]) if actor else {},
    )


def _signals(session, world):
    return session.execute(
        select(SkillSignal).where(SkillSignal.talent_id == world["talent"].id, SkillSignal.source_type == "TASK")
    ).scalars().all()


@pytest.mark.parametrize("actor", ["org_member", "org_admin", "coordinator"])
def test_organization_side_can_verify(client, session, world, unverified_task, actor):
    assert _signals(session, world) == []

    response = _verify(client, world, unverified_task, actor)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verified"] is True and body["verified_at"] is not None

    session.refresh(unverified_task)
    assert unverified_task.verified_by_user_id == world[actor].id

    (signal,) = _signals(session, world)
    assert signal.skill_id == world["skill"].id and signal.source_id == unverified_task.id

    audit = session.execute(
        select(AuditEvent).where(AuditEvent.action == "TASK_VERIFIED", AuditEvent.subject_id == unverified_task.id)
    ).scalars().all()
    assert len(audit) == 1 and audit[0].actor_user_id == world[actor].id


@pytest.mark.parametrize(
    "actor,expected",
    [
        ("talent_user", 403),  # own engagement is visible → 403; also an org member, still refused
        ("other_talent_user", 404),
        ("other_org_member", 404),
        ("other_coordinator", 404),
    ],
)
def test_everyone_else_is_refused_and_nothing_changes(client, session, world, unverified_task, actor, expected):
    response = _verify(client, world, unverified_task, actor)
    assert response.status_code == expected, response.text

    session.refresh(unverified_task)
    assert unverified_task.verified_at is None
    assert _signals(session, world) == []


def test_anonymous_is_401(client, world, unverified_task):
    assert _verify(client, world, unverified_task, "").status_code == 401


@pytest.mark.unverified_users
def test_unverified_email_is_401(client, session, world):
    """With this marker every user is unverified, so the task is inserted directly."""
    task = EngagementTask(engagement_id=world["engagement"].id, title="Doğrulanmamış görev", status="PLANNED")
    session.add(task)
    session.flush()

    response = _verify(client, world, task, "org_member")
    assert response.status_code == 401
    assert response.json()["code"] == "EMAIL_NOT_VERIFIED"
    session.refresh(task)
    assert task.verified_at is None


def test_verifying_twice_is_409_and_writes_one_signal(client, session, world, unverified_task):
    assert _verify(client, world, unverified_task, "org_member").status_code == 200
    again = _verify(client, world, unverified_task, "coordinator")
    assert again.status_code == 409
    assert again.json()["code"] == "TASK_ALREADY_VERIFIED"
    assert len(_signals(session, world)) == 1


def test_task_of_another_engagement_is_404(client, session, world, unverified_task):
    """A task id cannot be verified through an engagement it does not belong to."""
    other = Engagement(
        talent_id=world["talent"].id,
        organization_id=world["engagement"].organization_id,
        institution_id=world["engagement"].institution_id,
        kind="INTERNSHIP",
        title="Başka çalışma",
        status="ACTIVE",
        confidential=False,
    )
    session.add(other)
    session.flush()
    response = client.post(
        f"/engagements/{other.id}/tasks/{unverified_task.id}/verify", headers=_auth(world["org_member"])
    )
    assert response.status_code == 404
    session.refresh(unverified_task)
    assert unverified_task.verified_at is None


@pytest.mark.parametrize("bad_id", ["not-a-uuid", "00000000-0000-0000-0000-000000000000"])
def test_unknown_task_is_404(client, world, bad_id):
    response = client.post(
        f"/engagements/{world['engagement'].id}/tasks/{bad_id}/verify", headers=_auth(world["org_member"])
    )
    assert response.status_code == 404


@pytest.mark.parametrize("status", ["DRAFT", "PENDING_APPROVAL", "REJECTED", "CANCELLED"])
def test_cannot_verify_before_the_engagement_is_accepted(client, session, world, unverified_task, status):
    world["engagement"].status = status
    session.flush()
    response = _verify(client, world, unverified_task, "org_member")
    assert response.status_code == 422
    assert response.json()["code"] == "PRECONDITION_FAILED"
    assert _signals(session, world) == []


def test_task_without_skill_is_verified_without_a_signal(client, session, world):
    created = client.post(
        f"/engagements/{world['engagement'].id}/tasks",
        json={"title": "Yetkinliksiz görev"},
        headers=_auth(world["talent_user"]),
    )
    task = session.get(EngagementTask, uuid.UUID(created.json()["id"]))
    assert _verify(client, world, task, "org_member").status_code == 200
    assert _signals(session, world) == []
