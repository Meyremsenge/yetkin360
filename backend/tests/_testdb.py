"""
Database URL utilities for test isolation.

Exports:
- resolve_test_database_url(database_url, test_database_url=None)
- assert_safe_test_url(url)
- maintenance_url(url)

Used by conftest.py to derive test database URL from dev URL and verify safety.
"""

from sqlalchemy.engine import make_url


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
