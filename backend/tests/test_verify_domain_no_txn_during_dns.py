"""YET-189 (AUTHZ-04): verify_domain must not hold a DB transaction during the DNS call.

Uses a real committing session (the shared `session` fixture never commits and
would hide the bug). The fake resolver records the session/pool state at the
moment the network call happens.
"""

import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import Organization
from app.services.organization import verify_domain


class _TxtRdata:
    def __init__(self, text: str):
        self.strings = [text.encode()]


class _SpyResolver:
    """Fake resolver: records DB state at call time instead of hitting the network."""

    def __init__(self, session, engine, txt_from_token: bool = False):
        self.session = session
        self.engine = engine
        self.txt_from_token = txt_from_token
        self.calls = 0
        self.in_transaction: bool | None = None
        self.checked_out: int | None = None
        self.token_seen: str | None = None

    def resolve(self, domain, rdtype, lifetime=None):
        self.calls += 1
        self.in_transaction = self.session.in_transaction()
        self.checked_out = self.engine.pool.checkedout()
        if self.txt_from_token:
            org_token = self._token
            return [_TxtRdata(f"yetkin360_verify_{org_token}")]
        return []

    _token: str | None = None


@pytest.fixture
def real_org():
    engine = create_engine(settings.database_url)
    factory = sessionmaker(bind=engine)
    seed = factory()
    org = Organization(name="yet189-test", domain=f"yet189-{uuid.uuid4().hex[:8]}.example.com")
    seed.add(org)
    seed.commit()
    org_id = org.id
    seed.close()

    yield engine, factory, org_id

    cleanup = factory()
    cleanup.execute(Organization.__table__.delete().where(Organization.id == org_id))
    cleanup.commit()
    cleanup.close()
    engine.dispose()


def test_no_transaction_or_connection_held_during_dns_lookup(real_org):
    engine, factory, org_id = real_org
    session = factory()
    try:
        resolver = _SpyResolver(session, engine)
        result = verify_domain(org_id, session, resolver=resolver)

        assert resolver.calls == 1
        assert resolver.in_transaction is False
        assert resolver.checked_out == 0
        assert result["status"] == "pending"
    finally:
        session.close()


def test_rate_limit_timestamp_and_token_committed_before_dns(real_org):
    engine, factory, org_id = real_org
    session = factory()
    try:
        verify_domain(org_id, session, resolver=_SpyResolver(session, engine))
    finally:
        session.close()

    check = factory()
    try:
        org = check.execute(select(Organization).where(Organization.id == org_id)).scalar_one()
        assert org.last_verify_attempt_at is not None
        assert org.domain_verification_token
    finally:
        check.close()


def test_verified_path_still_persists_t2_and_no_txn_during_dns(real_org):
    engine, factory, org_id = real_org
    session = factory()
    try:
        # first call creates the token (and commits)
        verify_domain(org_id, session, resolver=_SpyResolver(session, engine))
        org = session.execute(select(Organization).where(Organization.id == org_id)).scalar_one()
        token = org.domain_verification_token
        org.last_verify_attempt_at = None  # bypass 60s rate limit for the second call
        session.commit()

        resolver = _SpyResolver(session, engine, txt_from_token=True)
        resolver._token = token
        result = verify_domain(org_id, session, resolver=resolver)
        session.commit()

        assert resolver.in_transaction is False
        assert resolver.checked_out == 0
        assert result["status"] == "verified"
    finally:
        session.close()

    check = factory()
    try:
        org = check.execute(select(Organization).where(Organization.id == org_id)).scalar_one()
        assert org.verification_level == "T2"
        assert org.verified_at is not None
    finally:
        check.close()
