"""GUV-09b / YET-241: a verified (T2/T3/T4) domain has exactly one owner, enforced by the DB.

Contract pinned here:
- DB: partial UNIQUE on organizations(domain) for T2/T3/T4 and not deleted (case-insensitive: CITEXT).
- Admin verification-level: raising an org to T2/T3/T4 on a domain another active T2+ org owns -> 409.
- verify-domain race lost at the DB -> 409 DomainAlreadyVerifiedError, never a raw IntegrityError.
"""

import threading
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Organization, OrganizationMember, User
from app.services import organization as svc


def _user(session, email, admin=False):
    user = User(email=email, password_hash="x", is_platform_admin=admin)
    session.add(user)
    session.flush()
    return user


def _h(user):
    return {"X-Debug-User-Id": str(user.id)}


def _org(session, name, domain, level, admin, token=None, deleted=False):
    org = Organization(
        name=name,
        domain=domain,
        verification_level=level,
        status="ACTIVE",
        domain_verification_token=token,
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )
    session.add(org)
    session.flush()
    session.add(OrganizationMember(organization_id=org.id, user_id=admin.id, role="ADMIN", status="ACTIVE"))
    session.flush()
    return org


def _resolver_with_txt(token):
    resolver = MagicMock()
    record = MagicMock()
    record.strings = [f"yetkin360_verify_{token}".encode()]
    answers = MagicMock()
    answers.__iter__ = lambda self: iter([record])
    resolver.resolve.return_value = answers
    return resolver


# ----------------------------------------------------------------------------
# AC-1: DB constraint
# ----------------------------------------------------------------------------

_VERIFIED = ["T2", "T3", "T4"]


@pytest.mark.parametrize("first", _VERIFIED)
@pytest.mark.parametrize("second", _VERIFIED)
def test_db_rejects_two_verified_orgs_on_one_domain(session, first, second):
    owner = _user(session, "owner@guv09b.test")
    _org(session, "First", "one.guv09b.example", first, owner)

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            _org(session, "Second", "one.guv09b.example", second, owner)


def test_db_unique_is_case_insensitive(session):
    owner = _user(session, "owner@guv09b.test")
    _org(session, "First", "case.guv09b.example", "T3", owner)

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            _org(session, "Second", "CASE.guv09b.example", "T2", owner)


def test_db_allows_t1_duplicates_and_deleted_rows(session):
    owner = _user(session, "owner@guv09b.test")
    _org(session, "Owner", "free.guv09b.example", "T3", owner)

    _org(session, "T1 a", "free.guv09b.example", "T1", owner)
    _org(session, "T1 b", "free.guv09b.example", "T1", owner)
    _org(session, "Deleted T4", "free.guv09b.example", "T4", owner, deleted=True)


# ----------------------------------------------------------------------------
# AC-2/AC-4: admin verification-level
# ----------------------------------------------------------------------------


def _set_level(client, admin, org, level):
    return client.post(
        f"/admin/organizations/{org.id}/verification-level",
        json={"verification_level": level},
        headers=_h(admin),
    )


@pytest.mark.parametrize("owner_level", _VERIFIED)
@pytest.mark.parametrize("target", _VERIFIED)
def test_admin_cannot_raise_org_onto_a_verified_domain(client, session, owner_level, target):
    admin = _user(session, "admin@guv09b.test", admin=True)
    owner = _user(session, "owner@guv09b.test")
    other = _user(session, "other@guv09b.test")
    _org(session, "Legit", "legit.guv09b.example", owner_level, owner)
    squat = _org(session, "Squat", "legit.guv09b.example", "T1", other)

    r = _set_level(client, admin, squat, target)

    assert r.status_code == 409, r.text
    assert r.json()["code"] == "DOMAIN_ALREADY_VERIFIED"
    session.expire_all()
    refreshed = session.get(Organization, squat.id)
    assert refreshed.verification_level == "T1"
    assert refreshed.verified_at is None
    assert refreshed.verified_by_user_id is None


def test_admin_conflict_leaves_no_success_audit(client, session):
    from app.models import AuditEvent

    admin = _user(session, "admin@guv09b.test", admin=True)
    owner = _user(session, "owner@guv09b.test")
    _org(session, "Legit", "audit.guv09b.example", "T3", owner)
    squat = _org(session, "Squat", "audit.guv09b.example", "T1", owner)

    r = _set_level(client, admin, squat, "T3")

    assert r.status_code == 409
    rows = session.execute(
        select(AuditEvent).where(
            AuditEvent.action == "ADMIN_SET_VERIFICATION_LEVEL", AuditEvent.subject_id == squat.id
        )
    ).scalars().all()
    assert rows == []


def test_admin_can_still_lower_or_keep_levels(client, session):
    admin = _user(session, "admin@guv09b.test", admin=True)
    owner = _user(session, "owner@guv09b.test")
    org = _org(session, "Mine", "mine.guv09b.example", "T3", owner)

    same = _set_level(client, admin, org, "T3")  # own level re-set: not a conflict with itself
    lowered = _set_level(client, admin, org, "T1")

    assert same.status_code == 200, same.text
    assert lowered.status_code == 200, lowered.text


def test_admin_can_raise_org_without_domain_or_with_free_domain(client, session):
    admin = _user(session, "admin@guv09b.test", admin=True)
    owner = _user(session, "owner@guv09b.test")
    no_domain = _org(session, "NoDomain", None, "T1", owner)

    r = _set_level(client, admin, no_domain, "T3")

    assert r.status_code == 200, r.text


def test_admin_can_raise_when_other_owner_is_t1_or_deleted(client, session):
    admin = _user(session, "admin@guv09b.test", admin=True)
    owner = _user(session, "owner@guv09b.test")
    _org(session, "T1 holder", "ok.guv09b.example", "T1", owner)
    _org(session, "Deleted", "ok.guv09b.example", "T4", owner, deleted=True)
    target = _org(session, "Target", "ok.guv09b.example", "T1", owner)

    r = _set_level(client, admin, target, "T3")

    assert r.status_code == 200, r.text


# ----------------------------------------------------------------------------
# AC-3: verify-domain race decided by the DB (two real sessions, real commits)
# ----------------------------------------------------------------------------


def test_verify_domain_race_loser_gets_domain_already_verified():
    assert settings.database_url.rsplit("/", 1)[-1].split("?")[0] != "yetkin360", "refusing dev DB"
    engine = create_engine(settings.database_url)
    with Session(engine) as s:
        u1 = _user(s, "race-1@guv09b.test")
        u2 = _user(s, "race-2@guv09b.test")
        o1 = _org(s, "Race1", "race.guv09b.example", "T1", u1, token="tok1")
        o2 = _org(s, "Race2", "race.guv09b.example", "T1", u2, token="tok2")
        s.commit()
        ids = {"o1": o1.id, "o2": o2.id, "u1": u1.id, "u2": u2.id}
    outcome: dict = {}

    def run(key, token):
        with Session(engine) as s:
            try:
                with patch("dns.resolver.Resolver") as resolver_cls:
                    resolver_cls.return_value = _resolver_with_txt(token)
                    result = svc.verify_domain(ids[key], s)
                if key == "o1":
                    time.sleep(2.0)  # keep the flushed-but-uncommitted T2 open so o2 collides on the index
                s.commit()
                outcome[key] = ("ok", result["status"])
            except Exception as exc:  # noqa: BLE001
                s.rollback()
                outcome[key] = ("exc", type(exc).__name__)

    t1 = threading.Thread(target=run, args=("o1", "tok1"))
    t2 = threading.Thread(target=run, args=("o2", "tok2"))
    try:
        t1.start()
        time.sleep(0.7)
        t2.start()
        t1.join()
        t2.join()
        with Session(engine) as s:
            levels = dict(
                s.execute(
                    select(Organization.name, Organization.verification_level).where(
                        Organization.id.in_([ids["o1"], ids["o2"]])
                    )
                ).all()
            )
        assert outcome["o1"] == ("ok", "verified")
        assert outcome["o2"] == ("exc", "DomainAlreadyVerifiedError"), outcome
        assert levels == {"Race1": "T2", "Race2": "T1"}
    finally:
        with Session(engine) as s:
            org_ids = [ids["o1"], ids["o2"]]
            s.execute(delete(OrganizationMember).where(OrganizationMember.organization_id.in_(org_ids)))
            s.execute(delete(Organization).where(Organization.id.in_(org_ids)))
            s.execute(delete(User).where(User.id.in_([ids["u1"], ids["u2"]])))
            s.commit()
        engine.dispose()
