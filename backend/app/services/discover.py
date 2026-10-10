"""
Keşfet directory (PLAN R.1, docs/kesfet-tasarim.md).

A directory with filters, not a matching engine: no score, no ranking by fit.
Ordering is fixed (talents: created_at DESC, id DESC; organizations: name, id),
so two callers with the same filters see the same list.
"""

import base64
import binascii
import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, func, or_, select, tuple_
from sqlalchemy.orm import Session

from app.models import Attestation, Institution, Organization, Skill, TalentProfile
from app.services import rate_limit
from app.services.authorization import (
    Principal,
    scoped_discoverable_attestations,
    scoped_discoverable_talent_profiles,
    scoped_discoverable_verified_experiences,
    scoped_organization_directory,
)

DEFAULT_LIMIT = 20
MAX_LIMIT = 50
MAX_SKILL_FILTERS = 5
VERIFIED_DOMAIN_LEVELS = ("T2", "T3", "T4")


class InvalidCursorError(Exception):
    """Cursor is not one this service issued (→ 422)."""


@dataclass(frozen=True)
class TalentCard:
    public_slug: str
    full_name: str
    headline: str | None
    department: str | None
    city: str | None
    institution_name: str | None
    sealed_skills: list[str]
    verified_experience_count: int


@dataclass(frozen=True)
class OrganizationCard:
    id: uuid.UUID
    name: str
    verification_level: str
    domain: str | None


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    next_cursor: str | None


def _encode_cursor(payload: dict[str, str]) -> str:
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str, keys: tuple[str, ...]) -> dict[str, str]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except (binascii.Error, ValueError):
        raise InvalidCursorError
    if not isinstance(payload, dict) or set(payload) != set(keys):
        raise InvalidCursorError
    if not all(isinstance(payload[key], str) for key in keys):
        raise InvalidCursorError
    return payload


def _contains(column, term: str) -> ColumnElement[bool]:
    """Case-insensitive substring match; LIKE wildcards in the term are literal."""
    return column.ilike(f"%{_escape_like(term)}%", escape="\\")


def _equals_ci(column, term: str) -> ColumnElement[bool]:
    return column.ilike(_escape_like(term), escape="\\")


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_talents(
    session: Session,
    principal: Principal,
    *,
    q: str | None = None,
    skill_ids: list[uuid.UUID] | None = None,
    institution_id: uuid.UUID | None = None,
    department: str | None = None,
    city: str | None = None,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> Page[TalentCard]:
    """
    List PUBLIC talent profiles for the Keşfet directory.

    Raises:
        rate_limit.RateLimitExceeded: caller exceeded 60 directory requests/minute (→ 429)
        InvalidCursorError: cursor was not issued by this service (→ 422)
    """
    rate_limit.hit(session, rate_limit.DISCOVER_USER, str(principal.user_id))

    query = scoped_discoverable_talent_profiles(session, principal)
    if q:
        query = query.where(or_(_contains(TalentProfile.full_name, q), _contains(TalentProfile.headline, q)))
    if institution_id is not None:
        query = query.where(TalentProfile.institution_id == institution_id)
    if department:
        query = query.where(_equals_ci(TalentProfile.department, department))
    if city:
        query = query.where(_equals_ci(TalentProfile.city, city))
    # Every requested skill must be sealed on a PUBLIC experience (AND, not OR).
    for skill_id in skill_ids or []:
        query = query.where(
            scoped_discoverable_attestations(session)
            .where(Attestation.talent_id == TalentProfile.id, Attestation.skill_id == skill_id)
            .exists()
        )
    if cursor is not None:
        position = _decode_cursor(cursor, ("c", "i"))
        try:
            after = (datetime.fromisoformat(position["c"]), uuid.UUID(position["i"]))
        except ValueError:
            raise InvalidCursorError
        query = query.where(tuple_(TalentProfile.created_at, TalentProfile.id) < after)

    rows = session.execute(
        query.add_columns(Institution.name)
        .outerjoin(Institution, Institution.id == TalentProfile.institution_id)
        .order_by(TalentProfile.created_at.desc(), TalentProfile.id.desc())
        .limit(limit + 1)
    ).all()
    page_rows = rows[:limit]
    talent_ids = [profile.id for profile, _ in page_rows]

    skills_by_talent: dict[uuid.UUID, list[str]] = {}
    counts_by_talent: dict[uuid.UUID, int] = {}
    if talent_ids:
        skill_rows = session.execute(
            scoped_discoverable_attestations(session)
            .where(Attestation.talent_id.in_(talent_ids))
            .join(Skill, Skill.id == Attestation.skill_id)
            .with_only_columns(Attestation.talent_id, Skill.name_tr)
            .distinct()
            .order_by(Skill.name_tr)
        ).all()
        for talent_id, name_tr in skill_rows:
            skills_by_talent.setdefault(talent_id, []).append(name_tr)

        experiences = scoped_discoverable_verified_experiences(session, talent_ids).subquery()
        count_rows = session.execute(
            select(experiences.c.talent_id, func.count()).group_by(experiences.c.talent_id)
        ).all()
        counts_by_talent = {talent_id: count for talent_id, count in count_rows}

    next_cursor = None
    if len(rows) > limit:
        last = page_rows[-1][0]
        next_cursor = _encode_cursor({"c": last.created_at.isoformat(), "i": str(last.id)})

    return Page(
        items=[
            TalentCard(
                public_slug=profile.public_slug,
                full_name=profile.full_name,
                headline=profile.headline,
                department=profile.department,
                city=profile.city,
                institution_name=institution_name,
                sealed_skills=skills_by_talent.get(profile.id, []),
                verified_experience_count=counts_by_talent.get(profile.id, 0),
            )
            for profile, institution_name in page_rows
        ],
        next_cursor=next_cursor,
    )


def list_organizations(
    session: Session,
    principal: Principal,
    *,
    q: str | None = None,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> Page[OrganizationCard]:
    """
    List ACTIVE organizations for the Keşfet directory.

    Raises:
        rate_limit.RateLimitExceeded: caller exceeded 60 directory requests/minute (→ 429)
        InvalidCursorError: cursor was not issued by this service (→ 422)
    """
    rate_limit.hit(session, rate_limit.DISCOVER_USER, str(principal.user_id))

    query = scoped_organization_directory(session, principal)
    if q:
        query = query.where(_contains(Organization.name, q))
    if cursor is not None:
        position = _decode_cursor(cursor, ("n", "i"))
        try:
            after = (position["n"], uuid.UUID(position["i"]))
        except ValueError:
            raise InvalidCursorError
        query = query.where(tuple_(Organization.name, Organization.id) > after)

    orgs = session.execute(query.order_by(Organization.name, Organization.id).limit(limit + 1)).scalars().all()
    page_orgs = orgs[:limit]

    next_cursor = None
    if len(orgs) > limit:
        last = page_orgs[-1]
        next_cursor = _encode_cursor({"n": last.name, "i": str(last.id)})

    return Page(
        items=[
            OrganizationCard(
                id=org.id,
                name=org.name,
                verification_level=org.verification_level,
                # An unverified domain is free text chosen by whoever created the
                # organization (GUV-03): only show it once verified.
                domain=org.domain if org.verification_level in VERIFIED_DOMAIN_LEVELS else None,
            )
            for org in page_orgs
        ],
        next_cursor=next_cursor,
    )
