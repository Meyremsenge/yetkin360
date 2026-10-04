"""L-02 / YET-237: organization ADMIN can change the domain; the change never leaks a trust level.

Contract pinned here:
- PATCH /organizations/{id} {domain}: org ADMIN only; everyone else (outsider, MEMBER, platform admin
  who is not a member, unknown id) gets 404 and nothing changes.
- T1: changes. T2: changes and drops to T1 (verified_at/verified_by/token cleared, DNS needed again).
  T3/T4 (admin approved): 409 ALAN_ADI_KILITLI.
- Format -> 422, free e-mail provider -> 400 FREE_EMAIL_DOMAIN, domain verified by another org -> 409.
- Same value -> 200 no-op. last_verify_attempt_at is never reset (60 s verify-domain cooldown holds).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import dns.resolver
import pytest
from sqlalchemy import select

from app.models import AuditEvent, Organization, OrganizationMember, User

NEW = "new.l02.example"


def _user(session, email, admin=False):
    user = User(email=email, password_hash="x", is_platform_admin=admin)
    session.add(user)
    session.flush()
    return user


def _h(user):
    return {"X-Debug-User-Id": str(user.id)}


def _org(session, name, domain, level, admin, role="ADMIN", token=None, deleted=False, verified=False):
    org = Organization(
        name=name,
        domain=domain,
        verification_level=level,
        status="ACTIVE",
        domain_verification_token=token,
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )
    if verified:
        org.verified_at = datetime.now(timezone.utc)
        org.verified_by_user_id = admin.id
    session.add(org)
    session.flush()
    session.add(OrganizationMember(organization_id=org.id, user_id=admin.id, role=role, status="ACTIVE"))
    session.flush()
    return org


def _patch(client, org, user, domain=NEW):
    return client.patch(f"/organizations/{org.id}", json={"domain": domain}, headers=_h(user))


def _fresh(session, org):
    session.expire_all()
    return session.get(Organization, org.id)


# ----------------------------------------------------------------------------
# Authorization: unauthorised = 404, nothing changes
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("who", ["outsider", "member", "platform_admin", "other_org_admin"])
def test_non_admin_gets_404_and_nothing_changes(client, session, who):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T2", owner, token="tok", verified=True)
    actor = _user(session, "actor@l02.test", admin=(who == "platform_admin"))
    if who == "member":
        session.add(OrganizationMember(organization_id=org.id, user_id=actor.id, role="MEMBER", status="ACTIVE"))
        session.flush()
    if who == "other_org_admin":
        _org(session, "Other", "other.l02.example", "T1", actor)

    r = _patch(client, org, actor)

    assert r.status_code == 404, r.text
    after = _fresh(session, org)
    assert after.domain == "old.l02.example"
    assert after.verification_level == "T2"
    assert after.domain_verification_token == "tok"


def test_unknown_org_is_404(client, session):
    actor = _user(session, "actor@l02.test")
    ghost = Organization(id="00000000-0000-7000-8000-000000000000", name="x")

    r = _patch(client, ghost, actor)

    assert r.status_code == 404


def test_unauthenticated_is_rejected(client, session):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T1", owner)

    r = client.patch(f"/organizations/{org.id}", json={"domain": NEW})

    assert r.status_code == 401


def test_denied_response_is_identical_for_missing_and_foreign_org(client, session):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T1", owner)
    actor = _user(session, "actor@l02.test")
    ghost = Organization(id="00000000-0000-7000-8000-000000000001", name="x")

    foreign = _patch(client, org, actor).json()
    missing = _patch(client, ghost, actor).json()

    foreign.pop("request_id", None)
    missing.pop("request_id", None)
    assert foreign == missing


# ----------------------------------------------------------------------------
# Level behaviour
# ----------------------------------------------------------------------------


def test_t1_admin_changes_domain(client, session):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T1", owner, token="old-token")

    r = _patch(client, org, owner)

    assert r.status_code == 200, r.text
    assert r.json()["domain"] == NEW
    assert r.json()["verification_level"] == "T1"
    after = _fresh(session, org)
    assert after.domain == NEW
    assert after.domain_verification_token is None  # a token issued for the old domain must not carry over


def test_padded_domain_is_stored_trimmed(client, session):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T1", owner)

    r = _patch(client, org, owner, domain=f"  {NEW}\t")

    assert r.status_code == 200, r.text
    assert _fresh(session, org).domain == NEW


def test_t2_change_drops_to_t1_and_clears_verification(client, session):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T2", owner, token="old-token", verified=True)
    cooldown = datetime.now(timezone.utc) - timedelta(seconds=5)
    org.last_verify_attempt_at = cooldown
    session.flush()

    r = _patch(client, org, owner)

    assert r.status_code == 200, r.text
    assert r.json()["verification_level"] == "T1"
    after = _fresh(session, org)
    assert after.domain == NEW
    assert after.verification_level == "T1"
    assert after.verified_at is None
    assert after.verified_by_user_id is None
    assert after.domain_verification_token is None
    assert after.last_verify_attempt_at is not None  # cooldown is NOT reset


@pytest.mark.parametrize("level", ["T3", "T4"])
def test_admin_approved_levels_are_locked(client, session, level):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", level, owner, token="tok", verified=True)

    r = _patch(client, org, owner)

    assert r.status_code == 409, r.text
    assert r.json()["code"] == "ALAN_ADI_KILITLI"
    after = _fresh(session, org)
    assert after.domain == "old.l02.example"
    assert after.verification_level == level
    assert after.verified_at is not None
    assert after.domain_verification_token == "tok"


@pytest.mark.parametrize("level", ["T1", "T2", "T3", "T4"])
def test_same_value_is_a_noop_that_keeps_the_level(client, session, level):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", level, owner, token="tok", verified=level != "T1")

    r = _patch(client, org, owner, domain="OLD.l02.example")

    assert r.status_code == 200, r.text
    after = _fresh(session, org)
    assert after.verification_level == level
    assert after.domain_verification_token == "tok"
    assert r.json()["verification_level"] == level


# ----------------------------------------------------------------------------
# Input validation and conflicts
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad", ["10.0.0.1", "localhost", "a.example:8080", "a.example/path", "", "   ", "-bad.example", "a b.example"]
)
def test_invalid_domain_is_422_and_nothing_changes(client, session, bad):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T2", owner, verified=True)

    r = _patch(client, org, owner, domain=bad)

    assert r.status_code == 422, r.text
    after = _fresh(session, org)
    assert after.domain == "old.l02.example"
    assert after.verification_level == "T2"


@pytest.mark.parametrize("body", [{}, {"domain": None}, {"domain": 5}])
def test_missing_or_null_domain_is_422(client, session, body):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T1", owner)

    r = client.patch(f"/organizations/{org.id}", json=body, headers=_h(owner))

    assert r.status_code == 422, r.text
    assert _fresh(session, org).domain == "old.l02.example"  # clearing the domain is not supported


@pytest.mark.parametrize("free", ["gmail.com", "mail.gmail.com", "GMAIL.COM"])
def test_free_email_domain_is_400_and_nothing_changes(client, session, free):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T2", owner, verified=True)

    r = _patch(client, org, owner, domain=free)

    assert r.status_code == 400, r.text
    assert r.json()["code"] == "FREE_EMAIL_DOMAIN"
    after = _fresh(session, org)
    assert after.domain == "old.l02.example"
    assert after.verification_level == "T2"


@pytest.mark.parametrize("holder_level", ["T2", "T3", "T4"])
def test_domain_verified_by_another_org_is_409(client, session, holder_level):
    owner = _user(session, "owner@l02.test")
    other = _user(session, "other@l02.test")
    _org(session, "Holder", NEW, holder_level, other, verified=True)
    org = _org(session, "Acme", "old.l02.example", "T2", owner, token="tok", verified=True)

    r = _patch(client, org, owner)

    assert r.status_code == 409, r.text
    assert r.json()["code"] == "DOMAIN_ALREADY_VERIFIED"
    after = _fresh(session, org)
    assert after.domain == "old.l02.example"
    assert after.verification_level == "T2"  # a rejected change must not demote
    assert after.domain_verification_token == "tok"


def test_unverified_or_deleted_holders_do_not_block(client, session):
    owner = _user(session, "owner@l02.test")
    other = _user(session, "other@l02.test")
    _org(session, "T1 holder", NEW, "T1", other)
    _org(session, "Deleted T4", NEW, "T4", other, deleted=True)
    org = _org(session, "Acme", "old.l02.example", "T1", owner)

    r = _patch(client, org, owner)

    assert r.status_code == 200, r.text


# ----------------------------------------------------------------------------
# Follow-up behaviour: verification restarts, cooldown holds, audit, response shape
# ----------------------------------------------------------------------------


def _resolver_with_txt(token):
    resolver = MagicMock()
    record = MagicMock()
    record.strings = [f"yetkin360_verify_{token}".encode()]
    answers = MagicMock()
    answers.__iter__ = lambda self: iter([record])
    resolver.resolve.return_value = answers
    return resolver


def test_new_domain_can_be_verified_again(client, session):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T2", owner, token="old-token", verified=True)
    assert _patch(client, org, owner).status_code == 200
    token = _fresh(session, org).domain_verification_token
    assert token is None

    with patch("dns.resolver.Resolver") as resolver_cls:
        # first call issues a new token (pending), the DNS record for it is read on the second call
        resolver_cls.return_value = MagicMock(resolve=MagicMock(side_effect=dns.resolver.NXDOMAIN()))
        first = client.post(f"/organizations/{org.id}/verify-domain", headers=_h(owner))
    assert first.status_code == 200, first.text
    new_token = first.json()["dns_txt_record"].removeprefix("yetkin360_verify_")
    assert new_token != "old-token"

    org_row = _fresh(session, org)
    org_row.last_verify_attempt_at = None
    session.flush()
    with patch("dns.resolver.Resolver") as resolver_cls:
        resolver_cls.return_value = _resolver_with_txt(new_token)
        second = client.post(f"/organizations/{org.id}/verify-domain", headers=_h(owner))
    assert second.json()["status"] == "verified"
    assert _fresh(session, org).verification_level == "T2"


def test_change_does_not_reset_verify_domain_cooldown(client, session):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T1", owner)
    org.last_verify_attempt_at = datetime.now(timezone.utc)
    session.flush()

    assert _patch(client, org, owner).status_code == 200
    r = client.post(f"/organizations/{org.id}/verify-domain", headers=_h(owner))

    assert r.status_code == 429, r.text


def test_change_is_audited_without_the_domain_value(client, session):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T2", owner, verified=True)

    assert _patch(client, org, owner).status_code == 200

    rows = session.execute(
        select(AuditEvent).where(
            AuditEvent.action == "ORGANIZATION_DOMAIN_CHANGED", AuditEvent.subject_id == org.id
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].actor_user_id == owner.id
    assert rows[0].result == "SUCCESS"
    assert rows[0].event_metadata == {"from_level": "T2", "to_level": "T1"}


def test_noop_writes_no_audit(client, session):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T2", owner, verified=True)

    assert _patch(client, org, owner, domain="old.l02.example").status_code == 200

    rows = session.execute(
        select(AuditEvent).where(
            AuditEvent.action == "ORGANIZATION_DOMAIN_CHANGED", AuditEvent.subject_id == org.id
        )
    ).scalars().all()
    assert rows == []


def test_response_is_the_organization_response_shape(client, session):
    owner = _user(session, "owner@l02.test")
    org = _org(session, "Acme", "old.l02.example", "T1", owner, token="tok")

    body = _patch(client, org, owner).json()

    assert set(body) == {"id", "name", "domain", "legal_id", "verification_level", "status"}
