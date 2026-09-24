"""Skill signal service: business logic for fetching and grouping skill signals."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Skill, SkillSignal
from app.services.authorization import Principal, scoped_skill_signals


def list_skill_signals(
    session: Session,
    principal: Principal,
    skill_id: str | None = None,
) -> list[dict]:
    """
    List skill signals for the authenticated talent, grouped by skill.

    AC-2, AC-3: GET /talents/me/signals logic.
    - Returns signals scoped to talent (via scoped_skill_signals)
    - Groups signals by skill_id
    - Optional filter by skill_id
    - Each item includes skill details and signals array
    - Empty list if no signals (AC-4, AC-6)

    Args:
        session: Database session
        principal: Authorization context (must have talent_id)
        skill_id: Optional UUID string to filter by specific skill

    Returns:
        List of dicts: [{"skill": {...}, "signals": [...]}, ...]
    """
    import uuid

    # Get scoped signals for this talent
    scoped_query = scoped_skill_signals(session, principal)

    # Apply skill_id filter if provided
    if skill_id:
        try:
            skill_uuid = uuid.UUID(skill_id)
            scoped_query = scoped_query.where(SkillSignal.skill_id == skill_uuid)
        except ValueError:
            # Invalid UUID format → return empty list (AC-6)
            return []

    signals = session.execute(scoped_query).scalars().all()

    # Group signals by skill_id
    signals_by_skill: dict[uuid.UUID, list] = {}
    for signal in signals:
        if signal.skill_id not in signals_by_skill:
            signals_by_skill[signal.skill_id] = []
        signals_by_skill[signal.skill_id].append(signal)

    # Build response items with skill details and signals
    items = []
    for skill_uuid, skill_signals in signals_by_skill.items():
        # Fetch the skill
        skill = session.execute(
            select(Skill).where(Skill.id == skill_uuid)
        ).scalar_one()

        # Build signal objects
        signal_items = []
        for sig in skill_signals:
            signal_items.append({
                "source_type": sig.source_type,
                "strength": sig.strength,
                "occurred_at": sig.occurred_at.isoformat() if sig.occurred_at else None,
                "attested_by": None,  # SELF_CLAIM always has null attested_by
                "superseded": sig.superseded_by_id is not None,
            })

        items.append({
            "skill": {
                "id": str(skill.id),
                "slug": skill.slug,
                "name_tr": skill.name_tr,
                "name_en": skill.name_en,
                "category": skill.category,
            },
            "signals": signal_items,
        })

    return items
