"""
Portfolio items: the talent's own certificates/works on the profile
(docs/arastirma-ogrenci-profili.md §4).

A portfolio item is a self-declared claim. Its public badge is derived here and
never chosen by the student:
  - COORDINATOR_CONFIRMED: the linked evidence (same owner, not deleted) has a
    certificate_checks row with decision=CONFIRMED — a coordinator's decision.
  - COORDINATOR_REJECTED (owner only): the coordinator rejected it; such an item
    is never listed publicly, not even as a self-declared claim.
  - SELF_DECLARED: everything else.
The evidence file always stays PRIVATE; only summary fields reach the public page.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CertificateCheck, Evidence, PortfolioItem
from app.services.audit import log_audit_event
from app.services.authorization import (
    Principal,
    get_scoped_or_404,
    scoped_evidence,
    scoped_own_portfolio_items,
    scoped_public_portfolio_items,
)
from app.services.certificate_check import get_certificate_check_for_evidence

CONFIRMED = "COORDINATOR_CONFIRMED"
REJECTED = "COORDINATOR_REJECTED"
SELF_DECLARED = "SELF_DECLARED"

# Live items per talent; bounds the public payload (atdd AC-S11).
MAX_ITEMS_PER_TALENT = 50

# Official verification pages only; anything else is never rendered as a link
# (open redirect / phishing on a page that carries our "confirmed" badge).
OFFICIAL_VERIFY_HOSTS = frozenset(
    {"coursera.org", "www.coursera.org", "udemy.com", "www.udemy.com", "ude.my"}
)

EDITABLE_FIELDS = ("kind", "title", "issuer", "issued_on", "credential_id", "external_url", "show_on_profile")


class PortfolioEvidenceNotFoundError(Exception):
    """evidence_id is not the caller's own, live evidence (404)."""


class PortfolioEvidenceAlreadyLinkedError(Exception):
    """The evidence already backs another portfolio item (409)."""


class PortfolioLimitReachedError(Exception):
    """The talent already has MAX_ITEMS_PER_TALENT live items (409)."""


def https_host(url: str | None) -> str | None:
    """ASCII (punycode) host of a plain https URL (no credentials, default port), else None.

    Punycode makes IDN homographs visible ("gооgle.com" → "xn--ggle-55da.com").
    """
    if not url:
        return None
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        return None
    if port not in (None, 443):
        return None
    try:
        return parts.hostname.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return None


def official_verify_url(url: str | None) -> str | None:
    """The URL itself when it is https on a provider's own domain, else None."""
    host = https_host(url)
    return url if host in OFFICIAL_VERIFY_HOSTS else None


def _badge(check: CertificateCheck | None) -> str:
    if check is not None and check.decision == "CONFIRMED":
        return CONFIRMED
    if check is not None and check.decision == "REJECTED":
        return REJECTED
    return SELF_DECLARED


def _own_check(session: Session, principal: Principal, item: PortfolioItem) -> CertificateCheck | None:
    """Certificate check of the item's evidence, only while that evidence is the caller's and live."""
    if item.evidence_id is None:
        return None
    evidence = get_scoped_or_404(
        scoped_evidence(session, principal).where(
            Evidence.id == item.evidence_id, Evidence.deleted_at.is_(None)
        ),
        session,
    )
    if evidence is None:
        return None
    return get_certificate_check_for_evidence(session, principal, evidence.id)


def _serialize(session: Session, principal: Principal, item: PortfolioItem) -> dict:
    check = _own_check(session, principal, item)
    return {
        "id": item.id,
        "kind": item.kind,
        "title": item.title,
        "issuer": item.issuer,
        "issued_on": item.issued_on,
        "credential_id": item.credential_id,
        "external_url": item.external_url,
        "evidence_id": item.evidence_id,
        "show_on_profile": item.show_on_profile,
        "badge": _badge(check),
        "provider": check.provider if check is not None else None,
        "created_at": item.created_at,
    }


def _get_own(session: Session, principal: Principal, item_id: uuid.UUID) -> PortfolioItem | None:
    return get_scoped_or_404(
        scoped_own_portfolio_items(session, principal).where(PortfolioItem.id == item_id), session
    )


def list_own_portfolio(session: Session, principal: Principal) -> dict:
    """The caller's items plus engagement certificates that could be added to the showcase."""
    items = (
        session.execute(
            scoped_own_portfolio_items(session, principal).order_by(PortfolioItem.created_at.desc())
        )
        .scalars()
        .all()
    )
    linked = {item.evidence_id: item.id for item in items if item.evidence_id is not None}

    certificates = (
        session.execute(
            scoped_evidence(session, principal)
            .where(
                Evidence.kind == "CERTIFICATE",
                Evidence.deliverable_id.isnot(None),
                Evidence.deleted_at.is_(None),
            )
            .order_by(Evidence.created_at.desc())
        )
        .scalars()
        .all()
    )
    engagement_certificates = []
    for evidence in certificates:
        check = get_certificate_check_for_evidence(session, principal, evidence.id)
        engagement_certificates.append(
            {
                "evidence_id": evidence.id,
                "created_at": evidence.created_at,
                "provider": check.provider if check is not None else None,
                "credential_id": check.credential_id if check is not None else None,
                "decision": check.decision if check is not None else None,
                "portfolio_item_id": linked.get(evidence.id),
            }
        )

    return {
        "items": [_serialize(session, principal, item) for item in items],
        "engagement_certificates": engagement_certificates,
    }


def create_own_portfolio_item(session: Session, principal: Principal, data: dict) -> dict:
    """New item owned by the caller. A linked evidence must be the caller's own, live evidence."""
    if principal.talent_id is None:
        raise PortfolioEvidenceNotFoundError("talent-less principal")
    evidence_id = data.get("evidence_id")
    if evidence_id is not None:
        evidence = get_scoped_or_404(
            scoped_evidence(session, principal).where(
                Evidence.id == evidence_id, Evidence.deleted_at.is_(None)
            ),
            session,
        )
        if evidence is None:
            raise PortfolioEvidenceNotFoundError(str(evidence_id))

    live_count = session.execute(
        select(func.count()).select_from(scoped_own_portfolio_items(session, principal).subquery())
    ).scalar_one()
    if live_count >= MAX_ITEMS_PER_TALENT:
        raise PortfolioLimitReachedError(str(principal.talent_id))

    item = PortfolioItem(talent_id=principal.talent_id, **{k: v for k, v in data.items() if v is not None})
    session.add(item)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        if "uq_portfolio_items_evidence_id" not in str(exc.orig):
            raise
        raise PortfolioEvidenceAlreadyLinkedError(str(evidence_id)) from exc

    log_audit_event(
        session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="PORTFOLIO_ITEM_CREATED",
        subject_type="portfolio_item",
        subject_id=item.id,
        result="SUCCESS",
        metadata={"kind": item.kind, "show_on_profile": item.show_on_profile},
    )
    session.refresh(item)
    return _serialize(session, principal, item)


def update_own_portfolio_item(
    session: Session, principal: Principal, item_id: uuid.UUID, updates: dict
) -> dict | None:
    """Apply the provided fields; None when the item is not the caller's (→ 404)."""
    item = _get_own(session, principal, item_id)
    if item is None:
        return None

    previous_consent = item.show_on_profile
    for field_name, value in updates.items():
        if field_name in EDITABLE_FIELDS:
            setattr(item, field_name, value)
    item.updated_at = datetime.now(timezone.utc)
    session.flush()

    if item.show_on_profile != previous_consent:
        log_audit_event(
            session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="PORTFOLIO_ITEM_VISIBILITY_CHANGED",
            subject_type="portfolio_item",
            subject_id=item.id,
            result="SUCCESS",
            metadata={"from": previous_consent, "to": item.show_on_profile},
        )
    return _serialize(session, principal, item)


def delete_own_portfolio_item(session: Session, principal: Principal, item_id: uuid.UUID) -> bool:
    """Soft delete; the linked evidence file is not touched. False when not the caller's (→ 404).

    evidence_id is released so the same file can be added to the showcase again
    (uq_portfolio_items_evidence_id covers deleted rows too); the audit row keeps the item id.
    """
    item = _get_own(session, principal, item_id)
    if item is None:
        return False
    item.deleted_at = datetime.now(timezone.utc)
    item.show_on_profile = False
    item.evidence_id = None
    session.flush()
    log_audit_event(
        session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="PORTFOLIO_ITEM_DELETED",
        subject_type="portfolio_item",
        subject_id=item.id,
        result="SUCCESS",
        metadata=None,
    )
    return True


@dataclass
class PublicCertificate:
    kind: str
    title: str
    issuer: str | None
    issued_on: date | None
    credential_id: str | None
    badge: str
    provider: str | None
    # COORDINATOR_CONFIRMED only, and only on an allowlisted provider domain.
    verify_url: str | None
    # SELF_DECLARED only: the student's own https link, rendered with its host visible.
    link_url: str | None
    link_host: str | None


def build_public_certificates(session: Session, talent_id: uuid.UUID) -> list[PublicCertificate]:
    """Consented items of an already-resolved PUBLIC talent; confirmed first, then newest.

    On a confirmed card provider and credential number come only from the
    coordinator-reviewed check, never from what the student typed (atdd AC-S6).
    """
    result: list[tuple[PublicCertificate, datetime]] = []
    for item, check in session.execute(scoped_public_portfolio_items(session, talent_id)).all():
        badge = _badge(check)
        if badge == REJECTED:
            continue
        confirmed = badge == CONFIRMED
        link_host = None if confirmed else https_host(item.external_url)
        result.append(
            (
                PublicCertificate(
                    kind=item.kind,
                    title=item.title,
                    issuer=None if confirmed else item.issuer,
                    issued_on=item.issued_on,
                    credential_id=check.credential_id if confirmed else item.credential_id,
                    badge=badge,
                    provider=check.provider if confirmed else None,
                    verify_url=official_verify_url(check.verify_url) if confirmed else None,
                    link_url=item.external_url if link_host else None,
                    link_host=link_host,
                ),
                item.created_at,
            )
        )
    result.sort(
        key=lambda pair: (
            pair[0].badge != CONFIRMED,
            -(pair[0].issued_on or date.min).toordinal(),
            -pair[1].timestamp(),
        )
    )
    return [cert for cert, _ in result[:MAX_ITEMS_PER_TALENT]]
