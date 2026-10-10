"""YET-196: seed users never get their verification mail, so the seed marks them verified."""

import uuid

import pytest
from sqlalchemy import select

from app.models import User
from scripts.seed import SEED_EMAIL_DOMAINS, seed_verify_users

pytestmark = pytest.mark.unverified_users


def test_seed_verify_users_verifies_only_seed_domain_accounts(session):
    seed_users = [
        User(email=f"seed-{uuid.uuid4()}@{domain}", password_hash="h")
        for domain in ("posta.test", "cinaralti.edu.test", "yelkovanyazilim.test")
    ]
    # Real or foreign accounts: another .test domain, a lookalike of a seed
    # domain and a real domain must never be touched.
    other_users = [
        User(email=f"real-{uuid.uuid4()}@{domain}", password_hash="h")
        for domain in ("example.com", "baska.test", "notposta.test", "posta.test.example.com")
    ]
    session.add_all(seed_users + other_users)
    session.flush()

    updated = seed_verify_users(session)

    assert updated >= len(seed_users)
    session.expire_all()
    for user in seed_users:
        assert session.execute(select(User.email_verified_at).where(User.id == user.id)).scalar_one() is not None
    for user in other_users:
        assert session.execute(select(User.email_verified_at).where(User.id == user.id)).scalar_one() is None, user.email


def test_seed_email_domains_are_all_reserved_test_domains():
    assert SEED_EMAIL_DOMAINS and all(domain.endswith(".test") for domain in SEED_EMAIL_DOMAINS)


def test_seed_verify_users_is_idempotent(session):
    session.add(User(email=f"seed-{uuid.uuid4()}@posta.test", password_hash="h"))
    session.flush()
    seed_verify_users(session)

    assert seed_verify_users(session) == 0
