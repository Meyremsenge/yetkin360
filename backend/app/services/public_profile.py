"""
Public profile assembly (GET /public/talents/{slug}).

Builds the showcase payload for a PUBLIC talent: identity line, PUBLIC verified
experiences with their skills, and a skill map aggregated from those experiences
only. Nothing from PRIVATE/INSTITUTION/ORGANIZATIONS experiences, no internal
talent/user ids, no e-mail.

Two evidence tiers, never mixed visually on the page:
  - attested: an organization/institution vouched for the skill (ATTESTATION signal)
  - evidenced: the skill was exercised in a task/deliverable of a verified
    engagement (TASK/DELIVERABLE signal) but not separately attested
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models import Engagement, Institution, Organization, Skill, TalentProfile
from app.services.authorization import (
    scoped_attestations_for_engagement,
    scoped_public_skill_signals,
    scoped_public_verified_experiences,
)
from app.services.visibility_service import filter_public_experiences

# Higher index = stronger evidence. Mirrors skill_signals.strength CHECK.
STRENGTH_ORDER = ("NONE", "WEAK", "MODERATE", "STRONG")


@dataclass
class PublicAttestedSkill:
    name_tr: str
    category: str
    claim_type: str
    attestor_organization: str | None


@dataclass
class PublicEvidencedSkill:
    name_tr: str
    category: str


@dataclass
class PublicExperience:
    id: uuid.UUID
    organization_name_snapshot: str
    organization_trust_level: str
    role_snapshot: str
    institution_name_snapshot: str | None
    started_on_snapshot: date | None
    ended_on_snapshot: date | None
    claim_type: str
    created_at: datetime
    public_token: str | None
    skills: list[PublicAttestedSkill] = field(default_factory=list)
    evidenced_skills: list[PublicEvidencedSkill] = field(default_factory=list)


@dataclass
class PublicSkill:
    name_tr: str
    category: str
    strength: str
    attested: bool
    experience_count: int


@dataclass
class PublicProfile:
    display_name: str
    headline: str | None
    department: str | None
    study_year: int | None
    city: str | None
    institution_name: str | None
    institution_trust_level: str | None
    verified_experiences: list[PublicExperience]
    skills: list[PublicSkill]
    attesting_organization_count: int


@dataclass
class _SkillAggregate:
    strength: str = "NONE"
    attested: bool = False
    engagements: set[uuid.UUID] = field(default_factory=set)


def build_public_profile(session: Session, talent: TalentProfile) -> PublicProfile:
    """Assemble the public payload for a talent already resolved via scoped_public_talent_profile()."""
    experiences = filter_public_experiences(
        list(session.execute(scoped_public_verified_experiences(session, talent.id)).scalars().all())
    )
    experiences.sort(key=lambda ve: (ve.started_on_snapshot or date.min, ve.created_at), reverse=True)

    institution = session.get(Institution, talent.institution_id) if talent.institution_id else None

    skill_cache: dict[uuid.UUID, Skill | None] = {}
    org_cache: dict[uuid.UUID, Organization | None] = {}

    def skill_of(skill_id: uuid.UUID) -> Skill | None:
        if skill_id not in skill_cache:
            skill_cache[skill_id] = session.get(Skill, skill_id)
        return skill_cache[skill_id]

    def org_of(org_id: uuid.UUID) -> Organization | None:
        if org_id not in org_cache:
            org_cache[org_id] = session.get(Organization, org_id)
        return org_cache[org_id]

    # Skill signals of PUBLIC experiences only, grouped per skill and per engagement.
    engagement_ids = [ve.engagement_id for ve in experiences]
    aggregates: dict[uuid.UUID, _SkillAggregate] = {}
    evidenced_by_engagement: dict[uuid.UUID, list[uuid.UUID]] = {}
    for signal, engagement_id in session.execute(
        scoped_public_skill_signals(session, talent.id, engagement_ids)
    ).all():
        agg = aggregates.setdefault(signal.skill_id, _SkillAggregate())
        if STRENGTH_ORDER.index(signal.strength) > STRENGTH_ORDER.index(agg.strength):
            agg.strength = signal.strength
        agg.engagements.add(engagement_id)
        if signal.source_type == "ATTESTATION":
            agg.attested = True
        else:
            bucket = evidenced_by_engagement.setdefault(engagement_id, [])
            if signal.skill_id not in bucket:
                bucket.append(signal.skill_id)

    attestor_orgs: set[uuid.UUID] = set()
    public_experiences: list[PublicExperience] = []
    for ve in experiences:
        engagement = session.get(Engagement, ve.engagement_id)
        organization = org_of(engagement.organization_id) if engagement else None
        item = PublicExperience(
            id=ve.id,
            organization_name_snapshot=ve.organization_name_snapshot,
            organization_trust_level=organization.verification_level if organization else "T1",
            role_snapshot=ve.role_snapshot,
            institution_name_snapshot=ve.institution_name_snapshot,
            started_on_snapshot=ve.started_on_snapshot,
            ended_on_snapshot=ve.ended_on_snapshot,
            claim_type=ve.claim_type,
            created_at=ve.created_at,
            public_token=ve.public_token,
        )
        attested_here: set[uuid.UUID] = set()
        for att in session.execute(scoped_attestations_for_engagement(session, ve.engagement_id)).scalars().all():
            skill = skill_of(att.skill_id)
            if skill is None or att.skill_id in attested_here:
                continue
            attested_here.add(att.skill_id)
            attestor = org_of(att.attestor_org_id) if att.attestor_org_id else None
            if att.attestor_org_id is not None:
                attestor_orgs.add(att.attestor_org_id)
            item.skills.append(
                PublicAttestedSkill(
                    name_tr=skill.name_tr,
                    category=skill.category,
                    claim_type=att.claim_type,
                    attestor_organization=attestor.name if attestor else None,
                )
            )
        for skill_id in evidenced_by_engagement.get(ve.engagement_id, []):
            skill = skill_of(skill_id)
            if skill is None or skill_id in attested_here:
                continue
            item.evidenced_skills.append(PublicEvidencedSkill(name_tr=skill.name_tr, category=skill.category))
        public_experiences.append(item)

    skills: list[PublicSkill] = []
    for skill_id, agg in aggregates.items():
        skill = skill_of(skill_id)
        if skill is None:
            continue
        skills.append(
            PublicSkill(
                name_tr=skill.name_tr,
                category=skill.category,
                strength=agg.strength,
                attested=agg.attested,
                experience_count=len(agg.engagements),
            )
        )
    skills.sort(
        key=lambda s: (not s.attested, -STRENGTH_ORDER.index(s.strength), -s.experience_count, s.name_tr)
    )

    return PublicProfile(
        display_name=talent.full_name,
        headline=talent.headline,
        department=talent.department,
        study_year=talent.study_year,
        city=talent.city,
        institution_name=institution.name if institution else None,
        institution_trust_level=institution.verification_level if institution else None,
        verified_experiences=public_experiences,
        skills=skills,
        attesting_organization_count=len(attestor_orgs),
    )
