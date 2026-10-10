"""
Organization showcase assembly (GET /public/organizations/{id}).

An organization's public page lists the verified work done there, but only
with double consent: the organization opened its showcase (showcase_public)
AND each talent made both the record and their profile PUBLIC. Nothing else
about the people leaks — no e-mail, no talent/engagement ids; a record links
out only by the talent's public slug and the record's public token.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.models import Attestation, Engagement, Organization, Skill, VerifiedExperience
from app.services.authorization import (
    scoped_attestations_for_engagements,
    scoped_public_org_showcase_experiences,
)

SHOWCASE_LIMIT = 50
# An unverified domain is free text chosen by the organization's creator (GUV-03).
VERIFIED_DOMAIN_LEVELS = ("T2", "T3", "T4")


@dataclass
class ShowcaseStats:
    verified_public_count: int = 0
    institution_count: int = 0


@dataclass
class ShowcaseExperience:
    role_snapshot: str
    started_on: date | None
    ended_on: date | None
    talent_display_name: str
    talent_public_slug: str
    institution_name: str | None
    public_token: str | None
    skills: list[str] = field(default_factory=list)


@dataclass
class OrganizationShowcase:
    id: uuid.UUID
    name: str
    verification_level: str
    domain: str | None
    showcase_enabled: bool
    stats: ShowcaseStats
    experiences: list[ShowcaseExperience]


def build_org_showcase(session: Session, organization: Organization) -> OrganizationShowcase:
    """Assemble the showcase for an organization already resolved via scoped_public_organization()."""
    showcase = OrganizationShowcase(
        id=organization.id,
        name=organization.name,
        verification_level=organization.verification_level,
        domain=organization.domain if organization.verification_level in VERIFIED_DOMAIN_LEVELS else None,
        showcase_enabled=organization.showcase_public,
        stats=ShowcaseStats(),
        experiences=[],
    )
    if not organization.showcase_public:
        return showcase

    scoped = scoped_public_org_showcase_experiences(session, organization.id)

    # Counted over the same consented set as the list, so hidden records never show up as a number.
    total, institutions = session.execute(
        scoped.with_only_columns(
            func.count(VerifiedExperience.id), func.count(distinct(Engagement.institution_id))
        )
    ).one()
    showcase.stats = ShowcaseStats(verified_public_count=total, institution_count=institutions)

    rows = session.execute(
        scoped.order_by(
            VerifiedExperience.started_on_snapshot.desc().nulls_last(),
            VerifiedExperience.created_at.desc(),
            VerifiedExperience.id,
        ).limit(SHOWCASE_LIMIT)
    ).all()

    engagement_ids = [ve.engagement_id for ve, _ in rows]
    skills_by_engagement: dict[uuid.UUID, list[str]] = {}
    if engagement_ids:
        attestation_rows = session.execute(
            scoped_attestations_for_engagements(session, engagement_ids)
            .add_columns(Skill.name_tr)
            .join(Skill, Skill.id == Attestation.skill_id)
            .order_by(Attestation.created_at, Attestation.id)
        ).all()
        for attestation, skill_name in attestation_rows:
            names = skills_by_engagement.setdefault(attestation.engagement_id, [])
            if skill_name not in names:
                names.append(skill_name)

    for ve, talent in rows:
        showcase.experiences.append(
            ShowcaseExperience(
                role_snapshot=ve.role_snapshot,
                started_on=ve.started_on_snapshot,
                ended_on=ve.ended_on_snapshot,
                talent_display_name=talent.full_name,
                talent_public_slug=talent.public_slug,
                institution_name=ve.institution_name_snapshot,
                public_token=ve.public_token,
                skills=skills_by_engagement.get(ve.engagement_id, []),
            )
        )
    return showcase
