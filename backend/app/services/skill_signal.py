"""Skill signal service: business logic for fetching and grouping skill signals."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import SkillSignal, SkillClaim
from app.models.identity import Organization
from app.services.authorization import Principal, scoped_skill_signals


def list_skill_signals(
    session: Session,
    principal: Principal,
    skill_id: str | None = None,
) -> list[dict]:
    """
    List skill signals for the authenticated talent, grouped by skill.

    AC-2, AC-3: GET /talents/me/signals logic.
    AC-9 (IS-06): Filter out SELF_CLAIM signals whose source claim was deleted (append-only).
    AC-12 (L-09): No N+1 queries — use selectinload for Skill JOIN.
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
    scoped_query = scoped_skill_signals(session, principal).options(selectinload(SkillSignal.skill))

    # Apply skill_id filter if provided
    if skill_id:
        try:
            skill_uuid = uuid.UUID(skill_id)
            scoped_query = scoped_query.where(SkillSignal.skill_id == skill_uuid)
        except ValueError:
            # Invalid UUID format → return empty list (AC-6)
            return []

    signals = session.execute(scoped_query).scalars().all()

    # AC-9: Filter out invalid SELF_CLAIM signals (source claim deleted)
    # AC-12: Batch query (not N+1) to check claim validity
    # Append-only rule: signal never deleted, but claim can be hard-deleted
    self_claim_signals = [s for s in signals if s.source_type == "SELF_CLAIM"]
    valid_signals = signals  # Start with all signals

    if self_claim_signals:
        # Batch query: get all claim IDs that still exist (AC-12: single batch query, not N+1)
        source_ids = [s.source_id for s in self_claim_signals if s.source_id is not None]
        existing_claim_set: set = set()
        if source_ids:
            existing_claim_set = set(
                session.execute(
                    select(SkillClaim.id).where(SkillClaim.id.in_(source_ids))
                ).scalars().all()
            )

        # Filter: a SELF_CLAIM signal with no source_id isn't tied to a claim's
        # lifecycle (not an orphan); only drop one whose linked claim was deleted.
        valid_signals = [
            s for s in signals
            if s.source_type != "SELF_CLAIM"
            or s.source_id is None
            or s.source_id in existing_claim_set
        ]

    # AC-12: Batch-resolve organization names for EVALUATION signals (not N+1) —
    # attested_by must be a human-readable name, never the raw org UUID.
    org_ids = {s.attested_by_org_id for s in valid_signals if s.source_type == "EVALUATION" and s.attested_by_org_id}
    org_names: dict = {}
    if org_ids:
        org_names = dict(
            session.execute(
                select(Organization.id, Organization.name).where(Organization.id.in_(org_ids))
            ).all()
        )

    # Group signals by skill_id
    signals_by_skill: dict[uuid.UUID, list] = {}
    for signal in valid_signals:
        if signal.skill_id not in signals_by_skill:
            signals_by_skill[signal.skill_id] = []
        signals_by_skill[signal.skill_id].append(signal)

    # Build response items with skill details and signals
    items = []
    for skill_uuid, skill_signals in signals_by_skill.items():
        # Skill already loaded via selectinload — no additional query
        skill = skill_signals[0].skill

        # Build signal objects
        signal_items = []
        for sig in skill_signals:
            # AC-9: Calculate attested_by based on signal source_type
            attested_by = None
            if sig.source_type == "EVALUATION":
                # For EVALUATION signals, attested_by is the organization's name
                # (never the raw UUID — that would leak an internal id to the UI).
                attested_by = org_names.get(sig.attested_by_org_id) if sig.attested_by_org_id else None
            elif sig.source_type == "SELF_CLAIM":
                # For SELF_CLAIM, attested_by is the claim itself
                attested_by = str(sig.source_id) if sig.source_id else None

            signal_items.append({
                "source_type": sig.source_type,
                "skill_id": str(sig.skill_id),
                "strength": sig.strength,
                "occurred_at": sig.occurred_at.isoformat() if sig.occurred_at else None,
                "attested_by": attested_by,
                "kind": sig.source_type,  # Alias for test compatibility
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
