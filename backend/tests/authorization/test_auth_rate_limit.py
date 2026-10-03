"""
YET-186 (GUV-11): DB-backed rate limits on the identity endpoints.

docs/SECURITY.md §3 + YET-186 additions: login 5/min/IP + 10/hour/account,
register 3/hour/IP + 3/hour/account, forgot-password 10/hour/IP + 3/hour/account,
reset-password 20/hour/IP, verify-email 20/hour/IP, refresh 60/min/IP.
Over the limit: 429 RATE_LIMITED + Retry-After, identical whether or not the
account exists (enumeration guard, YET-180/183), no raw e-mail/IP stored.

The limiter is off by default in the suite (conftest `_rate_limiter_switch`);
every test here opts in through the module-level `rate_limited` marker.
"""

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models import AuthRateLimit, Outbox, User
from app.services import rate_limit

pytestmark = pytest.mark.rate_limited

_PASSWORD = "Str0ngPassw0rd!"


class _ClientIp:
    """ASGI wrapper: TestClient always reports 'testclient'; let a header set the peer address."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            for key, value in scope["headers"]:
                if key == b"x-test-client-ip":
                    scope["client"] = (value.decode(), 50000)
        await self.inner(scope, receive, send)


def _from(ip: str) -> TestClient:
    return TestClient(_ClientIp(app), headers={"X-Test-Client-IP": ip})


def _ip(n: int) -> str:
    return f"203.0.113.{n}"


def _email(tag: str = "rl") -> str:
    return f"{tag}-{uuid.uuid4().hex[:12]}@example.com"


def _login(c: TestClient, email: str, password: str = "Wrong-pass-1!"):
    return c.post("/auth/login", json={"email": email, "password": password})


def _forgot(c: TestClient, email: str):
    return c.post("/auth/forgot-password", json={"email": email})


def _register(c: TestClient, email: str):
    return c.post("/auth/register", json={"email": email, "password": _PASSWORD, "full_name": "RL Test"})


def _assert_limited(response) -> None:
    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMITED"
    retry_after = int(response.headers["Retry-After"])
    assert 1 <= retry_after <= 3600


@pytest.fixture
def real_user(session) -> User:
    user = User(email=_email("real"), password_hash=hash_password(_PASSWORD))
    session.add(user)
    session.flush()
    return user


# ---------------------------------------------------------------------------
# Per-IP limits, one table row per endpoint
# ---------------------------------------------------------------------------


def test_login_ip_limit_5_per_minute(client):
    c = _from(_ip(10))
    codes = [_login(c, _email()).status_code for _ in range(5)]
    assert codes == [401] * 5
    _assert_limited(_login(c, _email()))


def test_login_ip_limit_is_per_ip(client):
    for _ in range(6):
        _login(_from(_ip(11)), _email())
    assert _login(_from(_ip(12)), _email()).status_code == 401


def test_register_ip_limit_3_per_hour(client):
    c = _from(_ip(13))
    assert [_register(c, _email()).status_code for _ in range(3)] == [201] * 3
    _assert_limited(_register(c, _email()))


def test_forgot_password_ip_limit_10_per_hour(client):
    c = _from(_ip(14))
    assert [_forgot(c, _email()).status_code for _ in range(10)] == [204] * 10
    _assert_limited(_forgot(c, _email()))


def test_reset_password_ip_limit_20_per_hour(client):
    c = _from(_ip(15))
    body = {"token": "x" * 43, "new_password": _PASSWORD}
    assert [c.post("/auth/reset-password", json=body).status_code for _ in range(20)] == [400] * 20
    _assert_limited(c.post("/auth/reset-password", json=body))


def test_verify_email_ip_limit_20_per_hour(client):
    c = _from(_ip(16))
    body = {"token": "x" * 43}
    assert [c.post("/auth/verify-email", json=body).status_code for _ in range(20)] == [400] * 20
    _assert_limited(c.post("/auth/verify-email", json=body))


def test_refresh_ip_limit_60_per_minute(client):
    c = _from(_ip(17))
    assert [c.post("/auth/refresh").status_code for _ in range(60)] == [401] * 60
    _assert_limited(c.post("/auth/refresh"))


# ---------------------------------------------------------------------------
# Per-account limits: keyed on the submitted e-mail, from many IPs
# ---------------------------------------------------------------------------


def test_login_account_limit_10_per_hour_across_ips(client):
    email = _email()
    for n in range(10):
        assert _login(_from(_ip(20 + n)), email).status_code == 401
    _assert_limited(_login(_from(_ip(40)), email))


def test_login_account_limit_ignores_email_case(client):
    email = _email("MiXeD")
    for n in range(10):
        _login(_from(_ip(41 + n)), email if n % 2 else email.upper())
    _assert_limited(_login(_from(_ip(60)), email.lower()))


def test_register_account_limit_3_per_hour_across_ips(client):
    email = _email()
    for n in range(3):
        assert _register(_from(_ip(61 + n)), email).status_code == 201
    _assert_limited(_register(_from(_ip(70)), email))


def test_forgot_password_account_limit_3_per_hour_across_ips(client):
    email = _email()
    for n in range(3):
        assert _forgot(_from(_ip(71 + n)), email).status_code == 204
    _assert_limited(_forgot(_from(_ip(80)), email))


def test_forgot_password_for_real_account_cannot_flood_outbox(client, session, real_user):
    """The e-mail-bombing case from the Jira description: at most 3 reset mails per hour."""
    for n in range(8):
        _forgot(_from(_ip(81 + n)), real_user.email)
    queued = session.execute(
        select(func.count()).select_from(Outbox).where(Outbox.topic == "email.password_reset")
    ).scalar_one()
    assert queued == 3


def test_register_duplicate_email_cannot_flood_victim_with_notices(client, session, real_user):
    for n in range(8):
        _register(_from(_ip(90 + n)), real_user.email)
    queued = session.execute(
        select(func.count())
        .select_from(Outbox)
        .where(Outbox.topic == "email.duplicate_registration_attempt")
    ).scalar_one()
    assert queued == 3


# ---------------------------------------------------------------------------
# No enumeration: the limit answer does not depend on the account existing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("endpoint", ["login", "forgot", "register"])
def test_limit_response_identical_for_existing_and_unknown_email(client, real_user, endpoint):
    call = {"login": _login, "forgot": _forgot, "register": _register}[endpoint]
    shapes = []
    for i, email in enumerate((real_user.email, _email("ghost"))):
        # fresh IPs per email so only the account bucket is exhausted
        for n in range(10):
            call(_from(_ip(100 + i * 50 + n)), email)
        r = call(_from(_ip(100 + i * 50 + 20)), email)
        shapes.append((r.status_code, r.json()["code"], r.json()["message"], "Retry-After" in r.headers))
    assert shapes[0] == shapes[1]
    assert shapes[0][0] == 429


# ---------------------------------------------------------------------------
# YET-175 interplay
# ---------------------------------------------------------------------------


def test_locked_account_still_answers_423_within_limits(client, session, real_user):
    real_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
    session.flush()
    r = _login(_from(_ip(200)), real_user.email, _PASSWORD)
    assert r.status_code == 423
    assert r.json()["code"] == "ACCOUNT_LOCKED"


def test_rate_limit_is_answered_before_the_lock(client, session, real_user):
    real_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
    session.flush()
    c = _from(_ip(201))
    for _ in range(5):
        assert _login(c, real_user.email).status_code == 423
    _assert_limited(_login(c, real_user.email))


# ---------------------------------------------------------------------------
# Window and cleanup behaviour
# ---------------------------------------------------------------------------


def test_counter_resets_in_the_next_window(client, session):
    c = _from(_ip(210))
    for _ in range(6):
        _login(c, _email())
    _assert_limited(_login(c, _email()))

    session.execute(update(AuthRateLimit).values(window_start=AuthRateLimit.window_start - timedelta(hours=1)))
    session.flush()
    assert _login(c, _email()).status_code == 401


def test_expired_windows_are_purged_and_current_ones_kept(client, session, monkeypatch):
    stale = AuthRateLimit(
        bucket="login_ip",
        key_hash="0" * 64,
        window_start=datetime.now(timezone.utc) - timedelta(hours=3),
        count=4,
    )
    session.add(stale)
    session.flush()
    monkeypatch.setattr(rate_limit.secrets, "randbelow", lambda _n: 0)

    _login(_from(_ip(211)), _email())

    remaining = session.execute(select(AuthRateLimit.key_hash)).scalars().all()
    assert "0" * 64 not in remaining
    assert len(remaining) == 2  # the login_ip and login_account windows just written


def test_counter_is_atomic_count_not_overwrite(client, session):
    for _ in range(3):
        _login(_from(_ip(212)), _email())
    ip_row = session.execute(
        select(AuthRateLimit).where(AuthRateLimit.bucket == "login_ip")
    ).scalars().one()
    assert ip_row.count == 3


# ---------------------------------------------------------------------------
# Keys: no PII, IPv6 /64 grouping
# ---------------------------------------------------------------------------


def test_table_and_logs_hold_no_raw_email_or_ip(client, session, caplog):
    email = _email("pii")
    ip = _ip(220)
    with caplog.at_level(logging.DEBUG):
        for _ in range(6):
            _login(_from(ip), email)

    rows = session.execute(select(AuthRateLimit)).scalars().all()
    assert rows
    for row in rows:
        assert re.fullmatch(r"[0-9a-f]{64}", row.key_hash)
        assert email not in row.key_hash and ip not in row.key_hash
        assert email not in row.bucket and ip not in row.bucket
    assert email not in caplog.text
    assert ip not in caplog.text


def test_key_hash_depends_on_server_secret(monkeypatch):
    before = rate_limit._key_hash("login_ip", "198.51.100.1")
    monkeypatch.setattr(settings, "secret_key", settings.secret_key + "-rotated")
    assert rate_limit._key_hash("login_ip", "198.51.100.1") != before


def test_ipv6_clients_share_a_bucket_per_64(client):
    for n in range(5):
        _login(_from(f"2001:db8:1:2::{n + 1}"), _email())
    _assert_limited(_login(_from("2001:db8:1:2:ffff::9"), _email()))
    assert _login(_from("2001:db8:1:3::1"), _email()).status_code == 401


def test_normalize_ip_unit():
    assert rate_limit.normalize_ip("203.0.113.7") == "203.0.113.7"
    assert rate_limit.normalize_ip("2001:db8:1:2:3:4:5:6") == "2001:db8:1:2::/64"
    assert rate_limit.normalize_ip(None) == "unknown"
    assert rate_limit.normalize_ip("testclient") == "unknown"


def test_limiter_can_be_switched_off(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    c = _from(_ip(230))
    assert [_login(c, _email()).status_code for _ in range(8)] == [401] * 8


# ---------------------------------------------------------------------------
# Real get_session (no override): the hit must survive the request rollback
# ---------------------------------------------------------------------------


def test_hits_survive_the_request_rollback_with_real_get_session():
    """
    The 401 raised after the hit makes the real get_session roll back. If the
    limiter did not commit its counter first, every attempt would start from 0
    and the 6th would never be 429.
    """
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    ip = _ip(240)
    try:
        c = _from(ip)
        codes = [_login(c, _email()).status_code for _ in range(6)]
        assert codes == [401] * 5 + [429]
    finally:
        cleanup = Session()
        cleanup.execute(AuthRateLimit.__table__.delete())
        cleanup.commit()
        cleanup.close()
        engine.dispose()
