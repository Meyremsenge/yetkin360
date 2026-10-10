"""
Database URL utilities for test isolation.

Exports:
- resolve_test_database_url(database_url, test_database_url=None)
- apply_test_db_suffix(url, suffix)
- assert_safe_test_url(url)
- maintenance_url(url)
- session_override(session) — factory for generator-based session override

Used by conftest.py to derive test database URL from dev URL and verify safety.
"""

import re
from collections.abc import Generator

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


def resolve_test_database_url(
    database_url: str, test_database_url: str | None = None
) -> str:
    """Derive test database URL: explicit > already-test > append _test."""
    # Explicit override takes precedence
    if test_database_url:
        assert_safe_test_url(test_database_url)
        return test_database_url

    # Parse the dev URL
    url = make_url(database_url)
    db_name = url.database

    if not db_name:
        raise ValueError("Database URL has no database name")

    # Already ends with "test" or "_test" → use as-is (CI case: "test", or "yetkin360_test")
    if db_name.endswith("test"):
        return database_url

    # Append "_test" suffix and reconstruct URL with password preserved
    new_db_name = f"{db_name}_test"
    new_url = url.set(database=new_db_name)
    # Render URL with password preserved (default SQLAlchemy masking hides it)
    return new_url.render_as_string(hide_password=False)


_SUFFIX_RE = re.compile(r"^[a-z0-9]{1,16}$")


def apply_test_db_suffix(url: str, suffix: str | None) -> str:
    """Insert a per-session suffix before '_test' so parallel sessions get separate DBs.

    "yetkin360_test" + "s0" → "yetkin360_s0_test". No suffix → URL unchanged.
    The suffix ends up inside a quoted SQL identifier (CREATE/DROP DATABASE),
    so it is restricted to a strict allowlist.
    """
    if not suffix:
        return url
    if not _SUFFIX_RE.fullmatch(suffix):
        # Do not echo the raw value: it is untrusted input.
        raise ValueError("TEST_DB_SUFFIX must match ^[a-z0-9]{1,16}$")

    parsed_url = make_url(url)
    db_name = parsed_url.database
    if not db_name:
        raise ValueError("Database URL has no database name")

    base = db_name[: -len("_test")] if db_name.endswith("_test") else db_name
    new_url = parsed_url.set(database=f"{base}_{suffix}_test")
    result = new_url.render_as_string(hide_password=False)
    assert_safe_test_url(result)
    return result


def assert_safe_test_url(url: str) -> None:
    """Verify DB name ends with 'test'; raise RuntimeError if not."""
    parsed_url = make_url(url)
    db_name = parsed_url.database

    if not db_name or not db_name.endswith("test"):
        # Never include password in error message (sûr/secret guard).
        raise RuntimeError(
            f"Database name '{db_name}' does not end with 'test'. "
            f"Tests must use an isolated test database (e.g., 'yetkin360_test', 'test'). "
            f"Configure TEST_DATABASE_URL or check CONTRIBUTING.md."
        )


def maintenance_url(url: str) -> str:
    """Switch DB to 'postgres' for CREATE/DROP DATABASE operations."""
    parsed_url = make_url(url)
    maint_url = parsed_url.set(database="postgres")
    return maint_url.render_as_string(hide_password=False)


def session_override(session: Session):
    """
    Factory: return a generator that mimics production get_session semantics.
    Commits fixture setup via savepoint (remains until test ends), then yields.
    On success: commits request changes; on exception: rolls back and re-raises.
    Does not close session (test fixture manages lifecycle).
    """
    def override() -> Generator[Session, None, None]:
        session.commit()  # Pin test setup as committed
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    return override
