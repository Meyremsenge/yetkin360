"""
Skill search authorization and security tests (YET-10 — skill-search).

Implements AC-S1 (information disclosure), AC-S2 (SQL injection) and
AC-8 (authentication) from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Verify response schema does NOT leak internal fields (AC-S1)
- Verify SQL injection attempts are safely handled (AC-S2)
- Verify authentication is required (AC-8)

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests implement security contract (ATDD).
"""

import pytest

from app.models import Skill, User


# ============================================================================
# Fixtures: Users, Skills
# ============================================================================


@pytest.fixture
def user_searcher(session):
    """Authenticated test user (any skill searcher)."""
    user = User(email="searcher@example.com", password_hash="hash_searcher")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def skill_python_active(session):
    """ACTIVE skill: Python language."""
    skill = Skill(
        slug="python",
        name_tr="Python",
        name_en="Python",
        category="LANGUAGE",
        status="ACTIVE",
        parent_id=None,
        merged_into_id=None,
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_merged_example(session, skill_python_active):
    """MERGED skill for AC-S1 testing (internal fields check)."""
    skill = Skill(
        slug="old-python",
        name_tr="Old Python",
        name_en="Old Python",
        category="LANGUAGE",
        status="MERGED",
        parent_id=None,
        merged_into_id=skill_python_active.id,
    )
    session.add(skill)
    session.flush()
    return skill


# ============================================================================
# AC-S1: Response does NOT leak internal fields (status, merged_into_id)
# ============================================================================


class TestSkillSearchResponseSchema:
    """AC-S1: Response schema leaks no internal/management fields."""

    def test_response_does_not_contain_status_field(self, client, user_searcher, skill_python_active):
        """
        AC-S1: Response items do NOT contain 'status' field.

        ORM model has status, but response DTO must not expose it.
        """
        response = client.get("/skills", headers={"X-Debug-User-Id": str(user_searcher.id)})

        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert "status" not in item, f"Response should not contain 'status' field, got: {item}"

    def test_response_does_not_contain_merged_into_id_field(self, client, user_searcher, skill_python_active):
        """
        AC-S1: Response items do NOT contain 'merged_into_id' field.

        This is an internal management field, should never be exposed.
        """
        response = client.get("/skills", headers={"X-Debug-User-Id": str(user_searcher.id)})

        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert "merged_into_id" not in item, f"Response should not contain 'merged_into_id', got: {item}"

    def test_response_only_contains_allowed_fields(self, client, user_searcher, skill_python_active):
        """
        AC-S1: Response items contain ONLY allowed fields:
        id, slug, name_tr, name_en, category, parent_id.
        """
        response = client.get("/skills", headers={"X-Debug-User-Id": str(user_searcher.id)})

        assert response.status_code == 200
        data = response.json()

        allowed_fields = {"id", "slug", "name_tr", "name_en", "category", "parent_id"}

        for item in data["items"]:
            item_fields = set(item.keys())
            # Verify no extra fields
            extra_fields = item_fields - allowed_fields
            assert not extra_fields, f"Response contains unexpected fields: {extra_fields}"

            # Verify all required fields present
            required_fields = {"id", "slug", "name_tr", "name_en", "category"}
            missing_fields = required_fields - item_fields
            assert not missing_fields, f"Response missing required fields: {missing_fields}"

    def test_response_does_not_contain_created_at_updated_at(self, client, user_searcher, skill_python_active):
        """
        AC-S1: Response does not expose timestamp fields (created_at, updated_at).

        These are internal auditing fields.
        """
        response = client.get("/skills", headers={"X-Debug-User-Id": str(user_searcher.id)})

        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert "created_at" not in item, "created_at should not be exposed"
            assert "updated_at" not in item, "updated_at should not be exposed"

    def test_search_response_schema_matches_full_list(self, client, user_searcher, skill_python_active):
        """
        AC-S1: Search response has same schema as full list.

        No extra fields leaked in search results.
        """
        list_response = client.get("/skills", headers={"X-Debug-User-Id": str(user_searcher.id)})
        search_response = client.get("/skills?q=python", headers={"X-Debug-User-Id": str(user_searcher.id)})

        assert list_response.status_code == 200
        assert search_response.status_code == 200

        list_fields = set(list_response.json()["items"][0].keys()) if list_response.json()["items"] else set()
        search_fields = set(search_response.json()["items"][0].keys()) if search_response.json()["items"] else set()

        assert list_fields == search_fields, "Search and list responses should have identical schema"


# ============================================================================
# AC-S2: SQL injection attempts are safely handled
# ============================================================================


class TestSkillSearchSQLInjection:
    """AC-S2: SQL injection attempts in query parameter are safely handled."""

    def test_sql_injection_single_quote_returns_200(self, client, user_searcher, skill_python_active):
        """
        AC-S2: GET /skills?q=' → 200 + normal result (no error, no injection).

        SQLAlchemy ORM parametrized queries prevent injection.
        Database is not affected.
        """
        response = client.get("/skills?q='", headers={"X-Debug-User-Id": str(user_searcher.id)})

        # Should return 200, not error
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "items" in data
        # No error should occur; result is likely empty (no skill matches single quote)

    def test_sql_injection_drop_table_returns_200(self, client, user_searcher, skill_python_active):
        """
        AC-S2: GET /skills?q='; DROP TABLE skills; -- → 200 + normal result.

        Injection attempt should be treated as literal string.
        Database table should remain intact (next query still works).
        """
        response = client.get(
            "/skills?q=%27%3B%20DROP%20TABLE%20skills%3B%20--%20",
            headers={"X-Debug-User-Id": str(user_searcher.id)},
        )

        # Should return 200, not error
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "items" in data

        # Verify DB is still accessible (skill_python_active is still in DB)
        subsequent_response = client.get("/skills", headers={"X-Debug-User-Id": str(user_searcher.id)})
        assert subsequent_response.status_code == 200
        assert any(item["slug"] == "python" for item in subsequent_response.json()["items"])

    def test_sql_injection_or_condition_returns_200(self, client, user_searcher, skill_python_active):
        """
        AC-S2: GET /skills?q=' OR '1'='1 → 200 + normal result.

        Classic OR-based injection attempt should be treated literally.
        """
        response = client.get(
            "/skills?q=%27%20OR%20%271%27%3D%271",
            headers={"X-Debug-User-Id": str(user_searcher.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_sql_injection_union_select_returns_200(self, client, user_searcher, skill_python_active):
        """
        AC-S2: GET /skills?q='; UNION SELECT ... -- → 200 + normal result.

        UNION-based injection should be treated as literal string.
        """
        response = client.get(
            "/skills?q=%27%3B%20UNION%20SELECT%20id%2C%20slug%20FROM%20users%3B%20--%20",
            headers={"X-Debug-User-Id": str(user_searcher.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_sql_injection_no_db_corruption(self, client, user_searcher, skill_python_active):
        """
        AC-S2: Multiple injection attempts don't corrupt DB.

        After several injection attempts, normal queries still work.
        """
        injection_attempts = [
            "/skills?q=' OR '1'='1",
            "/skills?q='; DROP TABLE skills; --",
            "/skills?q=%27%20UNION%20SELECT%201%2C2%2C3",
        ]

        for attempt in injection_attempts:
            response = client.get(attempt, headers={"X-Debug-User-Id": str(user_searcher.id)})
            assert response.status_code == 200

        # Verify normal query still works
        response = client.get("/skills", headers={"X-Debug-User-Id": str(user_searcher.id)})
        assert response.status_code == 200

        data = response.json()
        assert any(item["slug"] == "python" for item in data["items"]), "Database should not be corrupted"

    def test_sql_injection_in_category_parameter(self, client, user_searcher, skill_python_active):
        """
        AC-S2: SQL injection attempt in category parameter.

        Category is an enum, Pydantic validates it. Should return 422, not inject.
        """
        response = client.get(
            "/skills?category=LANGUAGE'; DROP TABLE skills; --",
            headers={"X-Debug-User-Id": str(user_searcher.id)},
        )

        # Pydantic enum validation should catch this and return 422
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    def test_special_characters_treated_literally(self, client, user_searcher, skill_python_active):
        """
        AC-S2: Special characters in query are treated as literal search terms.

        Characters like $, %, @, etc. don't cause SQL errors.
        """
        special_chars_queries = [
            "/skills?q=%24%24",  # $$
            "/skills?q=%25%25%25",  # %%%
            "/skills?q=%40%40",  # @@
            "/skills?q=test%5C%5C",  # test\\
        ]

        for query_url in special_chars_queries:
            response = client.get(query_url, headers={"X-Debug-User-Id": str(user_searcher.id)})
            assert response.status_code == 200, f"Query {query_url} should not cause error"
            assert "items" in response.json()


# ============================================================================
# AC-8: Authentication validation (as part of authorization tests)
# ============================================================================


class TestSkillSearchAuthenticationRequired:
    """AC-8: Requests without authentication return 401."""

    def test_missing_header_returns_401(self, client, skill_python_active):
        """
        AC-8: GET /skills without X-Debug-User-Id → 401.

        This endpoint requires authentication.
        """
        response = client.get("/skills")

        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"

    def test_invalid_user_id_returns_401(self, client, skill_python_active):
        """
        AC-8: GET /skills with invalid user ID → 401.

        User must exist in database.
        """
        response = client.get("/skills", headers={"X-Debug-User-Id": "invalid-user-id"})

        assert response.status_code == 401

    def test_empty_header_returns_401(self, client, skill_python_active):
        """AC-8: GET /skills with empty X-Debug-User-Id → 401."""
        response = client.get("/skills", headers={"X-Debug-User-Id": ""})

        assert response.status_code == 401
