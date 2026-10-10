"""
Keşfet directory seed (PLAN R.1): 32 extra public students (DIRECTORY_EMAILS)
next to the original 20, so the directory shows a realistic size and paging.
"""

from sqlalchemy import func, select

from app.models import Engagement, Organization, TalentProfile, User, VerifiedExperience
from scripts.seed import (
    DIRECTORY_EMAILS,
    DIRECTORY_STUDENTS,
    STUDENT_EMAILS,
    seed_directory_students,
    seed_engagements,
    seed_institutions_and_organizations,
    seed_public_experiences,
    seed_skills,
    seed_talents,
    seed_verified_organizations,
)


def _seed_base(session) -> None:
    seed_skills(session)
    seed_talents(session)
    seed_institutions_and_organizations(session)
    seed_verified_organizations(session)
    seed_engagements(session)
    session.commit()


def _directory_profiles(session) -> list[TalentProfile]:
    return list(
        session.execute(
            select(TalentProfile)
            .join(User, TalentProfile.user_id == User.id)
            .where(User.email.in_(DIRECTORY_EMAILS))
        ).scalars()
    )


def test_directory_seed_adds_public_students_with_verified_engagements(session):
    _seed_base(session)
    engagements_before = session.scalar(select(func.count(Engagement.id)))

    inserted = seed_directory_students(session)
    seed_public_experiences(session)
    session.commit()

    profiles = _directory_profiles(session)
    assert inserted == len(DIRECTORY_STUDENTS) == len(profiles) == 32
    assert all(p.visibility == "PUBLIC" and p.public_slug for p in profiles)
    assert all(p.institution_id is not None for p in profiles)

    expected_engagements = sum(len(row[7]) for row in DIRECTORY_STUDENTS)
    new_engagements = session.scalar(select(func.count(Engagement.id))) - engagements_before
    assert new_engagements == expected_engagements

    ids = [p.id for p in profiles]
    experiences = list(
        session.execute(select(VerifiedExperience).where(VerifiedExperience.talent_id.in_(ids))).scalars()
    )
    assert len(experiences) == expected_engagements
    assert all(e.visibility == "PUBLIC" for e in experiences)

    # The original demo is unchanged: still exactly 20 STUDENT_EMAILS accounts.
    students = session.scalar(
        select(func.count(TalentProfile.id))
        .join(User, TalentProfile.user_id == User.id)
        .where(User.email.in_(STUDENT_EMAILS))
    )
    assert students == 20


def test_directory_seed_is_idempotent(session):
    _seed_base(session)
    seed_directory_students(session)
    session.commit()
    engagements = session.scalar(select(func.count(Engagement.id)))

    assert seed_directory_students(session) == 0
    session.commit()
    assert len(_directory_profiles(session)) == 32
    assert session.scalar(select(func.count(Engagement.id))) == engagements


def test_directory_seed_engagements_avoid_unverified_volume(session):
    """Directory engagements go to verified (T3) organizations, except a single
    one at Kalemtıraş Tasarım, so seed data alone never trips the unverified-volume rule."""
    unverified = {
        org.legal_id
        for org in session.execute(select(Organization)).scalars()
        if org.verification_level == "T1"
    } or {"ORG2", "ORG5"}
    per_org: dict[str, int] = {}
    for row in DIRECTORY_STUDENTS:
        for legal_id, _spec, _period in row[7]:
            per_org[legal_id] = per_org.get(legal_id, 0) + 1
    assert sum(n for org, n in per_org.items() if org in unverified) <= 1
