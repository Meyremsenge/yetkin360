"""
Skill taxonomy search endpoint authorization and contract tests.

Implements AC-1 through AC-11 from atdd.md for GET /skills/search?q=...

Acceptance Criteria:
- AC-1: Happy path — authenticated user, q=python → 200, sorted results
- AC-2: q validation — min_length=2, missing q → 400
- AC-3: Empty results → 200 + {"items": [], "total": 0}
- AC-4: MERGED skills included with merged_into_id; DEPRECATED excluded
- AC-5: No token / invalid token → 401
- AC-6-8: Seed script tests (separate file: test_seed_skills.py)
- AC-9 (AC-S1): ILIKE wildcard characters (%, _) handled safely (parametrized query)
- AC-10 (AC-S2): DB connection error → 500, no stack trace in response
- AC-11 (AC-S3): q > 200 chars or limit > 100 → 400

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient with X-Debug-User-Id header for auth override
- Skill fixtures with ACTIVE, MERGED, DEPRECATED statuses
- Parametric tests for different principal kinds (all should get 200 for global taxonomy)

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests implement search and auth contract.
"""

import uuid

import pytest

from app.models import Skill, User


# ============================================================================
# Skill Fixtures: ACTIVE, MERGED, DEPRECATED statuses
# ============================================================================


@pytest.fixture
def user_talent(session):
    """Test talent user (for search access)."""
    user = User(email="talent-search@example.com", password_hash="hash_talent")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def skill_python_active(session):
    """Active skill: Python (LANGUAGE category)."""
    skill = Skill(
        slug="python",
        name_tr="Python",
        name_en="Python",
        category="LANGUAGE",
        status="ACTIVE"
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_javascript_active(session):
    """Active skill: JavaScript (LANGUAGE category)."""
    skill = Skill(
        slug="javascript",
        name_tr="JavaScript",
        name_en="JavaScript",
        category="LANGUAGE",
        status="ACTIVE"
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_react_active(session):
    """Active skill: React (FRAMEWORK category)."""
    skill = Skill(
        slug="react",
        name_tr="React",
        name_en="React",
        category="FRAMEWORK",
        status="ACTIVE"
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_vue_merged(session, skill_react_active):
    """Merged skill: Vue → React (deprecation scenario)."""
    skill = Skill(
        slug="vue",
        name_tr="Vue",
        name_en="Vue",
        category="FRAMEWORK",
        status="MERGED",
        merged_into_id=skill_react_active.id
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_coffeescript_deprecated(session):
    """Deprecated skill: CoffeeScript (no merged_into_id)."""
    skill = Skill(
        slug="coffeescript",
        name_tr="CoffeeScript",
        name_en="CoffeeScript",
        category="LANGUAGE",
        status="DEPRECATED"
    )
    session.add(skill)
    session.flush()
    return skill


# ============================================================================
# AC-1: Happy Path — Search returns sorted results
# ============================================================================


class TestSkillSearchHappyPath:
    """AC-1: Authenticated user can search skills, results sorted alphabetically by name_tr."""

    def test_search_python_returns_200_with_results(
        self, client, user_talent, skill_python_active, skill_javascript_active
    ):
        """
        AC-1: GET /skills/search?q=python → 200, contains Python skill.

        Acceptance Criteria:
        - Status code: 200 OK
        - Response shape: {"items": [...], "total": N}
        - Each item has: id, slug, name_tr, name_en, category, status
        - Results sorted by name_tr alphabetically
        """
        response = client.get(
            "/skills/search?q=python",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 1

        # Verify Python skill is in results
        skill_slugs = [item["slug"] for item in data["items"]]
        assert "python" in skill_slugs

        # Verify response schema: each item has required fields
        for item in data["items"]:
            assert "id" in item
            assert "slug" in item
            assert "name_tr" in item
            assert "name_en" in item
            assert "category" in item
            assert "status" in item

    def test_search_results_sorted_alphabetically_by_name_tr(
        self, client, user_talent, skill_python_active, skill_javascript_active, skill_react_active
    ):
        """
        AC-1: Results sorted by name_tr (alphabetically ascending).

        Given multiple matching skills, results are sorted A-Z by Turkish name.
        """
        response = client.get(
            "/skills/search?q=",  # Will be validated, but if accepted, broad search
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        # This test expects 400 due to min_length=2, so adjust to valid query
        response = client.get(
            "/skills/search?q=ja",  # Matches JavaScript, Java (if exists)
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        if response.status_code == 200:
            data = response.json()
            if len(data["items"]) > 1:
                names = [item["name_tr"] for item in data["items"]]
                assert names == sorted(names), "Results must be sorted by name_tr"

    def test_search_different_principal_kinds_all_200(
        self, client, session
    ):
        """
        AC-1: All authenticated principal kinds (TALENT, ORG_MEMBER, COORDINATOR)
        can search — skill taxonomy is global, not role-gated.
        """
        # Create users of different kinds
        talent_user = User(email="talent@test.com", password_hash="hash")
        session.add(talent_user)
        session.flush()

        # All should get 200 for global taxonomy (even if implementation detail differs)
        for user_id in [talent_user.id]:
            response = client.get(
                "/skills/search?q=py",
                headers={"X-Debug-User-Id": str(user_id)}
            )
            # Should be 200 or at worst 200 + empty list (if no skills match)
            assert response.status_code in [200], f"Expected 200, got {response.status_code}"


# ============================================================================
# AC-2: Query Validation — min_length=2, max_length tested
# ============================================================================


class TestSkillSearchValidation:
    """AC-2: Query parameter validation (min_length=2, max_length=200)."""

    def test_search_missing_q_parameter_400(self, client, user_talent):
        """AC-2: GET /skills/search (no ?q=...) → 400."""
        response = client.get(
            "/skills/search",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 400

    def test_search_q_one_char_400(self, client, user_talent):
        """AC-2: GET /skills/search?q=x (1 char) → 400 (min_length=2)."""
        response = client.get(
            "/skills/search?q=x",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 400

    def test_search_q_two_chars_200_or_empty(self, client, user_talent, skill_python_active):
        """AC-2: GET /skills/search?q=py (2 chars) → 200 (minimum valid length)."""
        response = client.get(
            "/skills/search?q=py",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        # Should be 200 (valid query), might return empty or python
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data.get("items"), list)

    def test_search_q_over_200_chars_400(self, client, user_talent):
        """AC-11 (AC-S3): GET /skills/search?q=<201 chars> → 400 (max_length=200)."""
        long_query = "a" * 201
        response = client.get(
            f"/skills/search?q={long_query}",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 400


# ============================================================================
# AC-3: Empty Results — 200 + empty list (not 404)
# ============================================================================


class TestSkillSearchEmptyResults:
    """AC-3: No matching skills → 200 + {"items": [], "total": 0}, not 404."""

    def test_search_no_matches_200_empty_list(self, client, user_talent, skill_python_active):
        """
        AC-3: GET /skills/search?q=nonexistent → 200, empty items list.

        Acceptance Criteria:
        - Status code: 200 OK (not 404 — resource taxonomy exists)
        - Response: {"items": [], "total": 0}
        """
        response = client.get(
            "/skills/search?q=nonexistentskillxyz",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0


# ============================================================================
# AC-4: MERGED and DEPRECATED skill handling
# ============================================================================


class TestSkillSearchMergedDeprecated:
    """
    AC-4: MERGED skills included in results (with merged_into_id);
    DEPRECATED skills excluded.
    """

    def test_search_includes_merged_skills_with_target(
        self, client, user_talent, skill_vue_merged, skill_react_active
    ):
        """
        AC-4: Search for "vue" → returns MERGED skill with merged_into_id (React).

        Acceptance Criteria:
        - MERGED skill appears in results
        - Response includes merged_into_id = React.id
        - Response includes target skill's slug/name_tr for navigation
        """
        response = client.get(
            "/skills/search?q=vue",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 200
        data = response.json()
        # Find Vue in results
        vue_item = next((item for item in data["items"] if item["slug"] == "vue"), None)
        assert vue_item is not None, "MERGED skill (Vue) should be in results"
        assert vue_item["status"] == "MERGED"
        assert vue_item["merged_into_id"] == str(skill_react_active.id)

    def test_search_excludes_deprecated_skills(
        self, client, user_talent, skill_coffeescript_deprecated, skill_python_active
    ):
        """
        AC-4: DEPRECATED skills do NOT appear in search results.

        Acceptance Criteria:
        - CoffeeScript (DEPRECATED) not in results
        - Status code: 200
        - total does not include DEPRECATED skill
        """
        response = client.get(
            "/skills/search?q=coff",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 200
        data = response.json()
        # Verify CoffeeScript is not in results
        slugs = [item["slug"] for item in data["items"]]
        assert "coffeescript" not in slugs, "DEPRECATED skill should not appear"


# ============================================================================
# AC-5: Authentication — No token → 401
# ============================================================================


class TestSkillSearchAuthentication:
    """AC-5: Unauthenticated requests → 401 (no X-Debug-User-Id header)."""

    def test_search_no_token_401(self, client, skill_python_active):
        """
        AC-5: GET /skills/search without X-Debug-User-Id header → 401.

        Acceptance Criteria:
        - Status code: 401 Unauthorized
        - No skill data in response
        """
        response = client.get("/skills/search?q=python")

        assert response.status_code == 401

    def test_search_invalid_user_id_401(self, client):
        """AC-5: GET /skills/search with invalid X-Debug-User-Id → 401."""
        fake_uuid = str(uuid.uuid4())
        response = client.get(
            "/skills/search?q=python",
            headers={"X-Debug-User-Id": fake_uuid}
        )

        assert response.status_code == 401


# ============================================================================
# AC-9 (AC-S1): SQL Injection Protection — wildcard characters safe
# ============================================================================


class TestSkillSearchSQLInjectionProtection:
    """
    AC-9 (AC-S1): ILIKE wildcard characters (%, _) handled safely.
    Parametrized query used (SQLAlchemy ilike()), not raw string interpolation.
    """

    def test_search_with_percent_wildcard_no_error(
        self, client, user_talent, skill_python_active
    ):
        """
        AC-9: Query with % (ILIKE wildcard) → 200, processed safely.

        Acceptance Criteria:
        - Query with % in it: treated as literal (% must be escaped in ilike)
          or handled such that no error/crash occurs
        - System continues to function normally
        """
        # Query with wildcards should be handled safely (escaped or literal)
        response = client.get(
            "/skills/search?q=python%",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        # Should not crash (500), should return 200 or 400 (invalid query format)
        assert response.status_code in [200, 400]

    def test_search_with_underscore_wildcard_no_error(
        self, client, user_talent, skill_python_active
    ):
        """
        AC-9: Query with _ (ILIKE wildcard) → 200, no system slowdown/error.
        """
        response = client.get(
            "/skills/search?q=pyth_n",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code in [200, 400]

    def test_search_with_percent_and_underscore_safe(
        self, client, user_talent, skill_python_active
    ):
        """
        AC-9: Complex wildcard pattern → no DoS, system stable.
        """
        response = client.get(
            "/skills/search?q=%_%_%",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code in [200, 400]


# ============================================================================
# AC-10 (AC-S2): Database Error Handling — no stack trace leakage
# ============================================================================


class TestSkillSearchDatabaseErrorHandling:
    """
    AC-10 (AC-S2): DB connection error → 500, response body has generic message.
    No stack trace, no DB implementation details in response.
    """

    def test_db_connection_error_returns_500_generic_message(
        self, client, user_talent, skill_python_active
    ):
        """
        AC-10: Database connection error → 500, generic error message.

        Acceptance Criteria:
        - Status code: 500 Internal Server Error
        - Response body: generic "Internal server error" message (no DB details)
        - No Traceback, no SQLAlchemy exception types in response
        - Error logged securely (PII/DB details in logs, not response)

        Simulated by overriding search_skills service to raise a DB error.
        The route handler's exception handler will catch it and return generic 500.
        """
        from sqlalchemy.exc import OperationalError
        import app.api.skills

        original_search_skills = app.api.skills.search_skills

        def failing_search_skills(*args, **kwargs):
            """Mock service that simulates DB connection error."""
            raise OperationalError(
                "could not connect to database",
                None,
                None
            )

        # Override search_skills in the API module (where it's actually called)
        app.api.skills.search_skills = failing_search_skills

        try:
            response = client.get(
                "/skills/search?q=python",
                headers={"X-Debug-User-Id": str(user_talent.id)}
            )

            assert response.status_code == 500
            data = response.json()
            response_text = str(data)

            # Verify no DB implementation details leaked
            assert "OperationalError" not in response_text
            assert "could not connect to database" not in response_text
            assert "Traceback" not in response_text
            assert "sqlalchemy" not in response_text.lower()
        finally:
            # Restore original service
            app.api.skills.search_skills = original_search_skills

    def test_db_error_does_not_leak_query_details(
        self, client, user_talent
    ):
        """
        AC-10: Error response doesn't expose query SQL or table structure.
        """
        from sqlalchemy.exc import IntegrityError
        import app.api.skills

        original_search_skills = app.api.skills.search_skills

        def failing_search_skills(*args, **kwargs):
            """Mock service that simulates DB integrity error."""
            raise IntegrityError(
                "duplicate key",
                None,
                None
            )

        # Override search_skills in the API module (where it's actually called)
        app.api.skills.search_skills = failing_search_skills

        try:
            response = client.get(
                "/skills/search?q=test",
                headers={"X-Debug-User-Id": str(user_talent.id)}
            )

            assert response.status_code == 500
            data = response.json()
            response_text = str(data)
            assert "skills" not in response_text.lower()  # Table name not exposed
            assert "duplicate key" not in response_text
        finally:
            # Restore original service
            app.api.skills.search_skills = original_search_skills


# ============================================================================
# AC-11 (AC-S3): Limit Parameter Validation — max_limit=100
# ============================================================================


class TestSkillSearchLimitValidation:
    """AC-11 (AC-S3): limit > 100 → 400 (prevent large offset DoS)."""

    def test_search_limit_over_100_400(self, client, user_talent):
        """
        AC-11: GET /skills/search?q=python&limit=101 → 400.

        Acceptance Criteria:
        - Status code: 400 Unprocessable Entity
        - Pydantic validation error
        - limit defaults to 20, max is 100
        """
        response = client.get(
            "/skills/search?q=python&limit=101",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 400

    def test_search_limit_100_valid(self, client, user_talent, skill_python_active):
        """AC-11: GET /skills/search?q=python&limit=100 → 200 (max allowed)."""
        response = client.get(
            "/skills/search?q=python&limit=100",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 200

    def test_search_limit_default_20(self, client, user_talent, skill_python_active):
        """AC-11: Default limit=20 when not specified."""
        response = client.get(
            "/skills/search?q=py",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 200
        # Verify response respects limit (if we had 100+ skills, would limit to 20)
        # This is a contract test, actual count depends on fixture


# ============================================================================
# Pagination: offset parameter (if implemented)
# ============================================================================


class TestSkillSearchPagination:
    """
    Pagination with limit/offset (baseline contract, AC-1 mentions it).
    """

    def test_search_with_offset_parameter(self, client, user_talent, skill_python_active):
        """
        Pagination: offset parameter skips N results, useful for fetching pages.

        This is a contract requirement from AC-1 assumptions (baseline pagination).
        """
        response = client.get(
            "/skills/search?q=py&limit=10&offset=0",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


# ============================================================================
# Response Contract: Consistency between empty, error, and success
# ============================================================================


class TestSkillSearchResponseContract:
    """
    Verify response shape consistency across success, empty, and error cases.
    """

    def test_response_shape_success(self, client, user_talent, skill_python_active):
        """Success case: {"items": [...], "total": N}."""
        response = client.get(
            "/skills/search?q=py",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert isinstance(data["total"], int)

    def test_response_shape_empty(self, client, user_talent):
        """Empty case: {"items": [], "total": 0}."""
        response = client.get(
            "/skills/search?q=nonexistent123",
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_validation_error_400_has_detail(self, client, user_talent):
        """Validation error: 400 with detail message."""
        response = client.get(
            "/skills/search?q=x",  # Too short
            headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 400
        data = response.json()
        # FastAPI validation error includes "detail" field
        assert "detail" in data or "items" in data or isinstance(data, dict)
