"""
Fraud risk signals (PLAN 3.56): suspicious organizations, colluding/fake
attestations and suspicious institution approvals.

Every signal here is DETERMINISTIC — computed from platform records with fixed
thresholds, never by a model. A signal is not a verdict: it only inserts a
PENDING row into fraud_flags, and an admin confirms or dismisses it
(final-analiz §11.4.6 — AI/automation may flag, a human always decides).

This module runs in the outbox worker's system context (no request principal),
like the other worker-side reads; nothing it computes is returned to a user
except through the admin-only fraud queue.

Reasons are short Turkish sentences built from counts only — never a name,
e-mail address or statement text (the admin opens the subject to see those).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Attestation,
    AuditEvent,
    Engagement,
    FraudFlag,
    Institution,
    Organization,
    OrganizationMember,
    TalentProfile,
    User,
)
from app.services.organization import is_free_email_domain

# Marks flags produced by this module (fraud_flags.model is the "who said so" column).
RULES_MODEL = "rules-v1"

# Levels at which nobody has vouched for the organization's identity yet.
UNVERIFIED_ORG_LEVELS = ("T1",)

RAPID_VERIFICATION_WINDOW = timedelta(hours=1)
DUPLICATE_STATEMENT_MIN_LENGTH = 40
ORG_VOLUME_WINDOW = timedelta(days=7)
ORG_VOLUME_THRESHOLD = 5
NEW_ORG_AGE = timedelta(days=7)
NEW_ORG_BURST_THRESHOLD = 3
SINGLE_TALENT_THRESHOLD = 3
BULK_APPROVAL_WINDOW = timedelta(minutes=10)
BULK_APPROVAL_THRESHOLD = 5

# A dismissed signal is not raised again for the same subject within this period.
REFLAG_COOLDOWN = timedelta(days=30)


@dataclass(frozen=True)
class RiskSignal:
    subject_type: str  # ATTESTATION | ORGANIZATION | INSTITUTION
    subject_id: uuid.UUID
    signal: str
    confidence: str  # LOW | MEDIUM | HIGH
    reason: str


def _email_domain(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return email.rsplit("@", 1)[1].strip().lower() or None


def attestation_signals(session: Session, attestation_id: uuid.UUID) -> list[RiskSignal]:
    """Collusion patterns around one attestation (witness vs. the attested talent)."""
    row = session.execute(
        select(Attestation, Engagement.created_at, TalentProfile.user_id)
        .join(Engagement, Engagement.id == Attestation.engagement_id)
        .join(TalentProfile, TalentProfile.id == Attestation.talent_id)
        .where(Attestation.id == attestation_id)
    ).first()
    if row is None:
        return []
    attestation, engagement_created_at, talent_user_id = row
    signals: list[RiskSignal] = []

    def add(signal: str, confidence: str, reason: str) -> None:
        signals.append(RiskSignal("ATTESTATION", attestation.id, signal, confidence, reason))

    if attestation.attestor_user_id == talent_user_id:
        add("SELF_ATTESTATION", "HIGH", "Tanıklığı veren hesap ile tanıklık edilen kişi aynı kullanıcı.")
    else:
        emails: dict[uuid.UUID, str] = {
            user_id: email
            for user_id, email in session.execute(
                select(User.id, User.email).where(User.id.in_([attestation.attestor_user_id, talent_user_id]))
            )
        }
        attestor_domain = _email_domain(emails.get(attestation.attestor_user_id))
        talent_domain = _email_domain(emails.get(talent_user_id))
        if attestor_domain and attestor_domain == talent_domain and not is_free_email_domain(attestor_domain):
            add(
                "SHARED_EMAIL_DOMAIN",
                "MEDIUM",
                "Tanık ile kişinin e-posta adresleri aynı alan adından; tanık kuruluştan bağımsız olmayabilir.",
            )

    statement = (attestation.statement or "").strip()
    if len(statement) >= DUPLICATE_STATEMENT_MIN_LENGTH:
        same_source = Attestation.attestor_user_id == attestation.attestor_user_id
        if attestation.attestor_org_id is not None:
            same_source = same_source | (Attestation.attestor_org_id == attestation.attestor_org_id)
        duplicates = session.execute(
            select(func.count(func.distinct(Attestation.talent_id))).where(
                Attestation.id != attestation.id,
                Attestation.talent_id != attestation.talent_id,
                same_source,
                # Exact text after trimming: copy-paste is exact, and case folding
                # differs between Python and PostgreSQL for Turkish I/ı/İ/i.
                func.btrim(Attestation.statement) == statement,
            )
        ).scalar_one()
        if duplicates:
            add(
                "DUPLICATE_STATEMENT",
                "MEDIUM",
                f"Aynı tanıklık metni bu tanık/kuruluş tarafından {duplicates} farklı kişi için daha kullanılmış.",
            )

    elapsed = attestation.created_at - engagement_created_at
    if timedelta(0) <= elapsed < RAPID_VERIFICATION_WINDOW:
        minutes = int(elapsed.total_seconds() // 60)
        add(
            "RAPID_VERIFICATION",
            "MEDIUM",
            f"Çalışma oluşturulduktan {minutes} dakika sonra tanıklık verilmiş; gerçek bir çalışma süresi görünmüyor.",
        )

    return signals


def organization_signals(session: Session, organization_id: uuid.UUID) -> list[RiskSignal]:
    """
    Volume/shape patterns of the attested engagements carried out AT an
    organization. Counted through engagements.organization_id, not
    attestations.attestor_org_id: the witness is often the institution's
    coordinator, and the organization is still the party being vouched for.
    """
    org = session.execute(
        select(Organization.id, Organization.verification_level, Organization.created_at).where(
            Organization.id == organization_id
        )
    ).first()
    if org is None:
        return []
    now = datetime.now(timezone.utc)
    signals: list[RiskSignal] = []

    def add(signal: str, confidence: str, reason: str) -> None:
        signals.append(RiskSignal("ORGANIZATION", org.id, signal, confidence, reason))

    attested = (
        select(Attestation.engagement_id, Attestation.talent_id, Attestation.created_at)
        .join(Engagement, Engagement.id == Attestation.engagement_id)
        .where(Engagement.organization_id == organization_id)
        .subquery()
    )
    total_engagements, distinct_talents = session.execute(
        select(func.count(func.distinct(attested.c.engagement_id)), func.count(func.distinct(attested.c.talent_id)))
    ).one()
    recent_engagements = session.execute(
        select(func.count(func.distinct(attested.c.engagement_id))).where(
            attested.c.created_at >= now - ORG_VOLUME_WINDOW
        )
    ).scalar_one()

    if org.verification_level in UNVERIFIED_ORG_LEVELS and recent_engagements >= ORG_VOLUME_THRESHOLD:
        add(
            "UNVERIFIED_HIGH_VOLUME",
            "MEDIUM",
            f"Kimliği doğrulanmamış kuruluşun son {ORG_VOLUME_WINDOW.days} günde {recent_engagements} çalışmasına tanıklık verilmiş.",
        )
    if now - org.created_at <= NEW_ORG_AGE and total_engagements >= NEW_ORG_BURST_THRESHOLD:
        add(
            "NEW_ORG_BURST",
            "HIGH",
            f"Kuruluş {NEW_ORG_AGE.days} günden yeni ve şimdiden {total_engagements} çalışmasına tanıklık verilmiş.",
        )
    if total_engagements >= SINGLE_TALENT_THRESHOLD and distinct_talents == 1:
        add(
            "SINGLE_TALENT_ONLY",
            "LOW",
            f"Kuruluşun tanıklık verilen {total_engagements} çalışmasının tamamı tek bir kişiye ait.",
        )

    return signals


def institution_approval_signals(
    session: Session, engagement_id: uuid.UUID, approver_user_id: uuid.UUID
) -> list[RiskSignal]:
    """Patterns in how an institution's coordinator approved an engagement (T2)."""
    engagement = session.execute(
        select(Engagement.id, Engagement.institution_id, Engagement.organization_id).where(
            Engagement.id == engagement_id
        )
    ).first()
    if engagement is None or engagement.institution_id is None:
        return []
    signals: list[RiskSignal] = []

    def add(signal: str, confidence: str, reason: str) -> None:
        signals.append(RiskSignal("INSTITUTION", engagement.institution_id, signal, confidence, reason))

    approver_is_org_member = session.execute(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == engagement.organization_id,
            OrganizationMember.user_id == approver_user_id,
            OrganizationMember.status == "ACTIVE",
        )
    ).first()
    if approver_is_org_member is not None:
        add(
            "APPROVER_IS_ORG_MEMBER",
            "HIGH",
            "Çalışmayı onaylayan koordinatör, aynı zamanda çalışmanın yapıldığı kuruluşun üyesi (çıkar çatışması).",
        )

    now = datetime.now(timezone.utc)
    bulk_approvals = session.execute(
        select(func.count(func.distinct(AuditEvent.subject_id)))
        .join(Engagement, Engagement.id == AuditEvent.subject_id)
        .where(
            AuditEvent.action == "ENGAGEMENT_TRANSITIONED",
            AuditEvent.subject_type == "engagement",
            AuditEvent.result == "SUCCESS",
            AuditEvent.actor_user_id == approver_user_id,
            AuditEvent.event_metadata["from_status"].astext == "PENDING_APPROVAL",
            AuditEvent.event_metadata["to_status"].astext == "ACTIVE",
            AuditEvent.created_at >= now - BULK_APPROVAL_WINDOW,
            Engagement.institution_id == engagement.institution_id,
            Engagement.organization_id == engagement.organization_id,
        )
    ).scalar_one()
    if bulk_approvals >= BULK_APPROVAL_THRESHOLD:
        minutes = int(BULK_APPROVAL_WINDOW.total_seconds() // 60)
        add(
            "RAPID_BULK_APPROVAL",
            "MEDIUM",
            f"Aynı koordinatör aynı kuruluşun {bulk_approvals} çalışmasını {minutes} dakika içinde onaylamış.",
        )

    return signals


def record_signals(session: Session, signals: list[RiskSignal], model: str = RULES_MODEL) -> int:
    """
    Inserts a PENDING fraud_flags row per signal; returns how many were new.

    Skipped when the same (subject, signal) is already waiting in the queue or
    was raised within REFLAG_COOLDOWN — one pattern is one row for the admin,
    not one row per event that re-triggers it.
    """
    created = 0
    cutoff = datetime.now(timezone.utc) - REFLAG_COOLDOWN
    for signal in signals:
        already = session.execute(
            select(FraudFlag.id).where(
                FraudFlag.subject_type == signal.subject_type,
                FraudFlag.subject_id == signal.subject_id,
                FraudFlag.signal == signal.signal,
                (FraudFlag.status == "PENDING") | (FraudFlag.created_at >= cutoff),
            )
        ).first()
        if already is not None:
            continue
        session.add(
            FraudFlag(
                subject_type=signal.subject_type,
                subject_id=signal.subject_id,
                signal=signal.signal,
                reason=signal.reason[:2000],
                confidence=signal.confidence,
                model=model,
            )
        )
        created += 1
    session.flush()
    return created


def organization_identity_context(session: Session, organization_id: uuid.UUID) -> dict | None:
    """
    The ONLY data sent to the AI identity check: organization-level, no person's
    name or e-mail. `legal_id` itself never leaves — only whether one was given.
    """
    org = session.execute(
        select(
            Organization.name,
            Organization.domain,
            Organization.verification_level,
            Organization.legal_id,
        ).where(Organization.id == organization_id, Organization.deleted_at.is_(None))
    ).first()
    if org is None:
        return None
    return {
        "name": org.name,
        "domain": org.domain,
        "domain_is_free_email_provider": bool(org.domain) and is_free_email_domain(org.domain),
        "verification_level": org.verification_level,
        "has_legal_id": bool(org.legal_id),
    }


def subject_labels(session: Session, flags: list[FraudFlag]) -> dict[uuid.UUID, str]:
    """Display names for the admin queue: organization/institution name per flag id."""
    labels: dict[uuid.UUID, str] = {}
    for subject_type, model in (("ORGANIZATION", Organization), ("INSTITUTION", Institution)):
        ids = {flag.subject_id for flag in flags if flag.subject_type == subject_type}
        if not ids:
            continue
        names: dict[uuid.UUID, str] = {
            subject_id: name
            for subject_id, name in session.execute(select(model.id, model.name).where(model.id.in_(ids)))
        }
        for flag in flags:
            if flag.subject_type == subject_type and flag.subject_id in names:
                labels[flag.id] = names[flag.subject_id]
    return labels
