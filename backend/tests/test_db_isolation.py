"""
Test suite for database isolation utility (_testdb.py).

Tests resolve_test_database_url(), assert_safe_test_url(), and maintenance_url()
to ensure tests use isolated test databases and never target dev/production.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.engine import create_engine

from tests._testdb import (
    apply_test_db_suffix,
    resolve_test_database_url,
    assert_safe_test_url,
    maintenance_url,
)


# AC-1: resolve_test_database_url derivation and precedence
@pytest.mark.parametrize(
    "dev_url,explicit_test_url,expected",
    [
        # Local dev URL → add "_test" suffix
        (
            "postgresql+psycopg://testuser:testpass@localhost:5432/yetkin360",  # pragma: allowlist secret
            None,
            "postgresql+psycopg://testuser:testpass@localhost:5432/yetkin360_test",  # pragma: allowlist secret
        ),
        # CI: already "test" → return as-is
        (
            "postgresql+psycopg://ci_user:ci_pass@postgres_host:5432/test",  # pragma: allowlist secret
            None,
            "postgresql+psycopg://ci_user:ci_pass@postgres_host:5432/test",  # pragma: allowlist secret
        ),
        # Already "_test" → no double suffix
        (
            "postgresql+psycopg://user:pass@localhost:5432/yetkin360_test",  # pragma: allowlist secret
            None,
            "postgresql+psycopg://user:pass@localhost:5432/yetkin360_test",  # pragma: allowlist secret
        ),
        # Explicit test_database_url takes precedence
        (
            "postgresql+psycopg://user:pass@localhost:5432/yetkin360",  # pragma: allowlist secret
            "postgresql+psycopg://user:pass@localhost:5432/test",  # pragma: allowlist secret
            "postgresql+psycopg://user:pass@localhost:5432/test",  # pragma: allowlist secret
        ),
        # Special characters in DB name
        (
            "postgresql+psycopg://user:pass@localhost:5432/yetkin_360_v2",  # pragma: allowlist secret
            None,
            "postgresql+psycopg://user:pass@localhost:5432/yetkin_360_v2_test",  # pragma: allowlist secret
        ),
        # Preserve query parameters
        (
            "postgresql+psycopg://user:pass@localhost:5432/yetkin360?sslmode=require&application_name=test_app",  # pragma: allowlist secret
            None,
            None,  # Just check it contains the key parts
        ),
    ],
    ids=[
        "local_dev_add_test_suffix",
        "ci_already_test",
        "already_test_suffix",
        "explicit_test_url_valid",
        "special_chars_in_db_name",
        "preserve_query_params",
    ],
)
def test_resolve_test_database_url(dev_url, explicit_test_url, expected):
    """AC-1: URL derivation with various inputs."""
    result = resolve_test_database_url(dev_url, test_database_url=explicit_test_url)

    if expected is not None:
        assert result == expected
    else:
        # Query params test: just verify key parts
        assert "yetkin360_test" in result
        assert "sslmode=require" in result
        assert "application_name=test_app" in result


def test_resolve_test_database_url_explicit_unsafe_raises():
    """AC-1: Explicit TEST_DATABASE_URL matching dev DB raises RuntimeError."""
    dev_url = "postgresql+psycopg://user:pass@localhost:5432/yetkin360"  # pragma: allowlist secret
    unsafe_test_url = "postgresql+psycopg://user:pass@localhost:5432/yetkin360"  # pragma: allowlist secret

    with pytest.raises(RuntimeError):
        resolve_test_database_url(dev_url, test_database_url=unsafe_test_url)


# AC-3: assert_safe_test_url validation
@pytest.mark.parametrize(
    "url,should_pass",
    [
        # Valid: ends with "_test"
        ("postgresql+psycopg://user:pass@localhost:5432/yetkin360_test", True),  # pragma: allowlist secret
        # Valid: exactly "test"
        ("postgresql+psycopg://user:pass@localhost:5432/test", True),  # pragma: allowlist secret
        # Invalid: dev database
        ("postgresql+psycopg://user:pass@localhost:5432/yetkin360", False),  # pragma: allowlist secret
        # Invalid: "test" at start, not end
        ("postgresql+psycopg://user:pass@localhost:5432/test_yetkin360", False),  # pragma: allowlist secret
    ],
    ids=[
        "ends_with_test_suffix",
        "exact_test_name",
        "dev_database",
        "partial_match_fails",
    ],
)
def test_assert_safe_test_url(url, should_pass):
    """AC-3: Verify DB name ends with 'test'."""
    if should_pass:
        assert_safe_test_url(url)
    else:
        with pytest.raises(RuntimeError) as exc_info:
            assert_safe_test_url(url)
        error_msg = str(exc_info.value)
        assert "test" in error_msg.lower()
        # Password safety check (for dev DB case)
        if "password" in url:
            assert "password" not in error_msg


def test_assert_safe_test_url_no_password_in_error():
    """AC-3: Error message must not expose password."""
    unsafe_url = "postgresql+psycopg://user:password123@localhost:5432/yetkin360"  # pragma: allowlist secret

    with pytest.raises(RuntimeError) as exc_info:
        assert_safe_test_url(unsafe_url)

    error_msg = str(exc_info.value)
    assert "yetkin360" in error_msg
    assert "password123" not in error_msg


# AC-8: maintenance_url for database operations
@pytest.mark.parametrize(
    "test_url,expected_db",
    [
        ("postgresql+psycopg://user:pass@localhost:5432/yetkin360_test", "postgres"),  # pragma: allowlist secret
        ("postgresql+psycopg://ci_user:ci_pass@postgres_host:5432/test", "postgres"),  # pragma: allowlist secret
    ],
    ids=["local_test_db", "ci_test_db"],
)
def test_maintenance_url(test_url, expected_db):
    """AC-8: maintenance_url switches DB to 'postgres' (password preserved)."""
    result = maintenance_url(test_url)

    assert f"/{expected_db}" in result
    # Verify credentials preserved
    if "user:pass" in test_url:
        assert "user" in result
    if "ci_user" in test_url:
        assert "ci_user" in result


# AC-2: Live database connection must use test DB
def test_live_database_connection_safety():
    """AC-2: Verify settings.database_url targets a test database."""
    from app.core.config import settings
    from sqlalchemy.engine import make_url

    parsed_url = make_url(settings.database_url)
    db_name = parsed_url.database

    assert db_name is not None, "Database name is None"
    assert db_name.endswith("test"), (
        f"Database name '{db_name}' does not end with 'test'. "
        f"Tests must use isolated DB."
    )

    # Live connection: verify SELECT current_database() matches
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()")).scalar()
            assert result == db_name
    finally:
        engine.dispose()


# S0: TEST_DB_SUFFIX gives each parallel session its own test database
@pytest.mark.parametrize("suffix", [None, ""], ids=["none", "empty"])
def test_apply_test_db_suffix_absent_returns_url_unchanged(suffix):
    url = "postgresql+psycopg://user:pass@localhost:5432/yetkin360_test"  # pragma: allowlist secret
    assert apply_test_db_suffix(url, suffix) == url


def test_apply_test_db_suffix_inserts_before_test():
    url = "postgresql+psycopg://user:pass@localhost:5432/yetkin360_test"  # pragma: allowlist secret
    result = apply_test_db_suffix(url, "s0")
    assert result == "postgresql+psycopg://user:pass@localhost:5432/yetkin360_s0_test"  # pragma: allowlist secret
    assert_safe_test_url(result)


def test_apply_test_db_suffix_bare_test_name():
    url = "postgresql+psycopg://user:pass@localhost:5432/test"  # pragma: allowlist secret
    assert apply_test_db_suffix(url, "d1").endswith("/test_d1_test")


def test_apply_test_db_suffix_preserves_password_and_query():
    url = "postgresql+psycopg://user:s3cret@localhost:5432/yetkin360_test?sslmode=require"  # pragma: allowlist secret
    result = apply_test_db_suffix(url, "h0")
    assert "user:s3cret@" in result
    assert "/yetkin360_h0_test?" in result
    assert "sslmode=require" in result


@pytest.mark.parametrize(
    "suffix",
    ["a;drop", "A", "a" * 17, 'x"y', "s-0", "s 0", "ş0"],
    ids=["semicolon", "uppercase", "too_long", "quote", "dash", "space", "non_ascii"],
)
def test_apply_test_db_suffix_rejects_invalid(suffix):
    url = "postgresql+psycopg://user:s3cret@localhost:5432/yetkin360_test"  # pragma: allowlist secret
    with pytest.raises(ValueError) as exc_info:
        apply_test_db_suffix(url, suffix)
    message = str(exc_info.value)
    # Neither the raw input nor the credentials leak into the error.
    assert suffix not in message
    assert "s3cret" not in message


def test_apply_test_db_suffix_accepts_max_length():
    url = "postgresql+psycopg://user:pass@localhost:5432/yetkin360_test"  # pragma: allowlist secret
    assert apply_test_db_suffix(url, "a" * 16).endswith("/yetkin360_" + "a" * 16 + "_test")
