"""
DB-backed fixed-window rate limiting for the identity endpoints (YET-186).

docs/SECURITY.md §3: no Redis in the MVP, so counters live in PostgreSQL
(auth_rate_limits) and are bumped with one atomic INSERT .. ON CONFLICT, which
is correct across workers and restarts (unlike a per-process dict).

Design points:
- Keys are HMAC-SHA256(secret_key, "bucket:value") hex digests: neither the IP
  nor the e-mail is stored or logged. Callers key e-mail buckets on the
  *submitted* address whether or not an account exists, so hitting a limit
  never reveals account existence (enumeration guard, YET-180/183).
- The counter is committed immediately. The request session rolls back on any
  exception (get_session), which would otherwise undo the very hit that
  produced the 429 — same reason authenticate() commits failed logins.
- Blocked attempts are counted too; the window just ends.
- Expired windows are deleted opportunistically (about 1 in 100 hits), so no
  separate cleanup process is needed.
"""

import hashlib
import hmac
import ipaddress
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AuthRateLimit


@dataclass(frozen=True)
class Rule:
    bucket: str
    limit: int
    window_seconds: int


# docs/SECURITY.md §3 values; the rest are YET-186 additions.
LOGIN_IP = Rule("login_ip", 5, 60)
LOGIN_ACCOUNT = Rule("login_account", 10, 3600)
REGISTER_IP = Rule("register_ip", 3, 3600)
REGISTER_ACCOUNT = Rule("register_account", 3, 3600)
FORGOT_PASSWORD_IP = Rule("forgot_password_ip", 10, 3600)
FORGOT_PASSWORD_ACCOUNT = Rule("forgot_password_account", 3, 3600)
RESET_PASSWORD_IP = Rule("reset_password_ip", 20, 3600)
VERIFY_EMAIL_IP = Rule("verify_email_ip", 20, 3600)
REFRESH_IP = Rule("refresh_ip", 60, 60)

# YET-213: bulk reminders. Per-institution request quota, and one reminder per
# (engagement, template) per day so repeated calls cannot bloat the outbox.
REMINDER_INSTITUTION = Rule("reminder_institution", 20, 3600)
REMINDER_TARGET = Rule("reminder_target", 1, 86400)

_RULES = (
    LOGIN_IP,
    LOGIN_ACCOUNT,
    REGISTER_IP,
    REGISTER_ACCOUNT,
    FORGOT_PASSWORD_IP,
    FORGOT_PASSWORD_ACCOUNT,
    RESET_PASSWORD_IP,
    VERIFY_EMAIL_IP,
    REFRESH_IP,
    REMINDER_INSTITUTION,
    REMINDER_TARGET,
)

# Keep a bucket's rows for twice its window (at least 2 hours) before purging;
# a flat 2 hours would wipe the live 1-day REMINDER_TARGET windows.
_MIN_RETENTION = timedelta(hours=2)


def _retention(rule: Rule) -> timedelta:
    return max(_MIN_RETENTION, timedelta(seconds=2 * rule.window_seconds))
_CLEANUP_ONE_IN = 100


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("rate limit exceeded")
        self.retry_after = retry_after


def normalize_ip(raw_ip: str | None) -> str:
    """IPv6 clients rotate freely inside their /64, so that is the unit of key."""
    if raw_ip is None:
        return "unknown"
    try:
        addr = ipaddress.ip_address(raw_ip)
    except ValueError:
        return "unknown"
    if isinstance(addr, ipaddress.IPv6Address):
        return str(ipaddress.ip_network(f"{addr}/64", strict=False))
    return str(addr)


def _key_hash(bucket: str, value: str) -> str:
    return hmac.new(
        settings.secret_key.encode(), f"{bucket}:{value}".encode(), hashlib.sha256
    ).hexdigest()


def _hit(session: Session, rule: Rule, value: str) -> None:
    if not settings.rate_limit_enabled:
        return

    now = datetime.now(timezone.utc)
    epoch = int(now.timestamp())
    window_start_epoch = epoch - epoch % rule.window_seconds
    window_start = datetime.fromtimestamp(window_start_epoch, tz=timezone.utc)

    stmt = (
        insert(AuthRateLimit)
        .values(
            bucket=rule.bucket,
            key_hash=_key_hash(rule.bucket, value),
            window_start=window_start,
            count=1,
        )
        .on_conflict_do_update(
            index_elements=["bucket", "key_hash", "window_start"],
            set_={"count": AuthRateLimit.count + 1},
        )
        .returning(AuthRateLimit.count)
    )
    count = session.execute(stmt).scalar_one()

    if secrets.randbelow(_CLEANUP_ONE_IN) == 0:
        session.execute(
            delete(AuthRateLimit).where(
                or_(
                    *(
                        and_(AuthRateLimit.bucket == r.bucket, AuthRateLimit.window_start < now - _retention(r))
                        for r in _RULES
                    )
                )
            )
        )

    session.commit()

    if count > rule.limit:
        retry_after = window_start_epoch + rule.window_seconds - epoch
        raise RateLimitExceeded(max(1, retry_after))


def hit(session: Session, rule: Rule, value: str) -> None:
    """Count one event against `rule`; raises RateLimitExceeded when over the limit."""
    _hit(session, rule, value)


def try_hit(session: Session, rule: Rule, value: str) -> bool:
    """Like hit(), but returns False instead of raising when over the limit."""
    try:
        _hit(session, rule, value)
    except RateLimitExceeded:
        return False
    return True


def enforce(
    session: Session,
    ip_rule: Rule,
    raw_ip: str | None,
    account_rule: Rule | None = None,
    email: str | None = None,
) -> None:
    """
    Count one attempt against the IP bucket, then (only if the IP is still
    within its limit) against the account bucket. Checking the IP first keeps
    a single abusive client from filling the table with per-e-mail rows.
    """
    _hit(session, ip_rule, normalize_ip(raw_ip))
    if account_rule is not None and email is not None:
        _hit(session, account_rule, email.strip().lower())
