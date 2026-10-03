"""GUV-09 / YET-182: domain squatting and fake trust display.

Contract pinned here:
- POST /institutions/ never reserves a (unverified, attacker-chosen) domain: it is ignored.
- Org domain verification conflicts with ANY already-verified org (T2/T3/T4), never 500s.
- Re-verifying the domain never lowers an org's trust level.
- More free-mail providers are refused for domain verification.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models import Institution, Organization, OrganizationMember, User


def _user(session, email):
    user = User(email=email, password_hash="x")
    session.add(user)
    session.flush()
    return user


def _h(user):
    return {"X-Debug-User-Id": str(user.id)}


def _org(session, name, domain, level, admin, token=None):
    org = Organization(
        name=name, domain=domain, verification_level=level, status="ACTIVE", domain_verification_token=token
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


def _verify(client, org, user, token):
    with patch("dns.resolver.Resolver") as resolver_cls:
        resolver_cls.return_value = _resolver_with_txt(token)
        return client.post(f"/organizations/{org.id}/verify-domain", headers=_h(user))


# ----------------------------------------------------------------------------
# Institution domain is never reserved by an unverified creator
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("domain", ["bilgi.edu.tr", "not a domain!!", "localhost", "http://x/y"])
def test_institution_create_ignores_domain(client, session, domain):
    creator = _user(session, "creator@guv09.test")

    r = client.post("/institutions/", json={"name": "Bilgi", "domain": domain}, headers=_h(creator))

    assert r.status_code == 201, r.text
    assert r.json()["domain"] is None
    assert r.json()["verification_level"] == "T1"
    stored = session.get(Institution, r.json()["id"])
    assert stored.domain is None


def test_institution_domain_not_squattable(client, session):
    attacker = _user(session, "attacker@guv09.test")
    real = _user(session, "real@guv09.test")

    first = client.post("/institutions/", json={"name": "Fake", "domain": "bilgi.edu.tr"}, headers=_h(attacker))
    second = client.post("/institutions/", json={"name": "Real", "domain": "bilgi.edu.tr"}, headers=_h(real))

    assert first.status_code == 201
    assert second.status_code == 201, second.text


# ----------------------------------------------------------------------------
# Org domain verification: conflict with any verified level
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("owner_level", ["T2", "T3", "T4"])
def test_second_org_cannot_verify_domain_owned_by_verified_org(client, session, owner_level):
    owner = _user(session, "owner@guv09.test")
    attacker = _user(session, "attacker@guv09.test")
    _org(session, "Legit", "legit.example", owner_level, owner)
    squat = _org(session, "Squatter", "legit.example", "T1", attacker, token="tok-squat")

    r = _verify(client, squat, attacker, "tok-squat")

    assert r.status_code == 409, r.text
    session.expire_all()
    assert session.get(Organization, squat.id).verification_level == "T1"


def test_conflict_with_several_verified_orgs_is_409_not_500(client, session):
    owner = _user(session, "owner@guv09.test")
    attacker = _user(session, "attacker@guv09.test")
    _org(session, "Legit T2", "dup.example", "T2", owner)
    _org(session, "Legit T3", "dup.example", "T3", owner)
    squat = _org(session, "Squatter", "dup.example", "T1", attacker, token="tok-dup")

    r = _verify(client, squat, attacker, "tok-dup")

    assert r.status_code == 409, r.text


# ----------------------------------------------------------------------------
# Re-verification never downgrades
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("level", ["T3", "T4"])
def test_reverify_does_not_downgrade(client, session, level):
    owner = _user(session, "owner@guv09.test")
    org = _org(session, "Legit", "keep.example", level, owner, token="tok-keep")

    r = _verify(client, org, owner, "tok-keep")

    assert r.status_code == 200, r.text
    assert r.json()["status"] == "verified"
    session.expire_all()
    refreshed = session.get(Organization, org.id)
    assert refreshed.verification_level == level
    assert refreshed.verified_by_user_id is None  # prior approval record is not overwritten


def test_first_verification_still_promotes_t1_to_t2(client, session):
    owner = _user(session, "owner@guv09.test")
    org = _org(session, "New", "fresh.example", "T1", owner, token="tok-fresh")

    r = _verify(client, org, owner, "tok-fresh")

    assert r.status_code == 200, r.text
    session.expire_all()
    refreshed = session.get(Organization, org.id)
    assert refreshed.verification_level == "T2"
    assert refreshed.verified_by_user_id == owner.id


# ----------------------------------------------------------------------------
# Free-mail provider list
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "domain",
    [
        "gmail.com",
        "yandex.com",
        "icloud.com",
        "hotmail.com.tr",
        "outlook.com.tr",
        "protonmail.com",
        "mail.ru",
        "yahoo.com.tr",
        "GMAIL.COM",
    ],
)
def test_free_mail_domains_rejected(client, session, domain):
    owner = _user(session, "owner@guv09.test")
    org = _org(session, "Free", domain, "T1", owner, token="tok-free")

    r = _verify(client, org, owner, "tok-free")

    assert r.status_code == 400, r.text
    assert "FREE_EMAIL_DOMAIN" in r.text
