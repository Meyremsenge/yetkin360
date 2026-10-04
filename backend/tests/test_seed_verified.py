"""YET-196: seed users never get their verification mail, so the seed marks them verified."""

import uuid

import pytest
from sqlalchemy import select

from app.models import User
from scripts.seed import seed_verify_users

pytestmark = pytest.mark.unverified_users


def test_seed_verify_users_verifies_only_seed_local_accounts(session):
    seed_user = User(email=f"seed-{uuid.uuid4()}@seed.local", password_hash="h")
    real_user = User(email=f"real-{uuid.uuid4()}@example.com", password_hash="h")
    session.add_all([seed_user, real_user])
    session.flush()
    assert seed_user.email_verified_at is None
    assert real_user.email_verified_at is None

    updated = seed_verify_users(session)

    assert updated >= 1
    session.expire_all()
    assert session.execute(select(User.email_verified_at).where(User.id == seed_user.id)).scalar_one() is not None
    assert session.execute(select(User.email_verified_at).where(User.id == real_user.id)).scalar_one() is None


def test_seed_verify_users_is_idempotent(session):
    session.add(User(email=f"seed-{uuid.uuid4()}@seed.local", password_hash="h"))
    session.flush()
    seed_verify_users(session)

    assert seed_verify_users(session) == 0
