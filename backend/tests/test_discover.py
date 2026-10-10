"""Keşfet directory behaviour: search, filters, ordering, pagination, limits (PLAN R.1)."""

import uuid

import pytest

from app.models import Institution
from app.services import rate_limit
from tests._discover_data import auth, make_org, make_skill, make_talent, make_user, seal_skill, slugs


@pytest.fixture
def viewer(session):
    return make_user(session, "viewer@example.com")


def talents(client, viewer, **params):
    return client.get("/discover/talents", params=params, headers=auth(viewer))


class TestTalentCard:
    def test_card_carries_profile_institution_skills_and_count(self, client, session, viewer):
        institution = Institution(name="Bilgi Üniversitesi", verification_level="T2")
        session.add(institution)
        session.flush()
        talent = make_talent(
            session,
            "alice",
            full_name="Alice Yılmaz",
            headline="Backend geliştirici",
            department="Bilgisayar Mühendisliği",
            city="İstanbul",
            institution_id=institution.id,
        )
        org = make_org(session, "Acme")
        python = make_skill(session, "t-python", "Python")
        sql = make_skill(session, "t-sql", "SQL")
        seal_skill(session, talent, org, python)
        seal_skill(session, talent, org, sql)
        seal_skill(session, talent, org, python)  # same skill twice → one chip

        (card,) = talents(client, viewer).json()["items"]
        assert card == {
            "public_slug": "alice-slug",
            "full_name": "Alice Yılmaz",
            "headline": "Backend geliştirici",
            "department": "Bilgisayar Mühendisliği",
            "city": "İstanbul",
            "institution_name": "Bilgi Üniversitesi",
            "sealed_skills": ["Python", "SQL"],
            "verified_experience_count": 3,
        }

    def test_profile_without_experience_has_empty_skills_and_zero_count(self, client, session, viewer):
        make_talent(session, "bare")
        (card,) = talents(client, viewer).json()["items"]
        assert card["sealed_skills"] == []
        assert card["verified_experience_count"] == 0
        assert card["institution_name"] is None


class TestSearchAndFilters:
    def test_q_matches_name_or_headline_case_insensitively(self, client, session, viewer):
        make_talent(session, "a", full_name="Alice Yılmaz")
        make_talent(session, "b", full_name="Bora Kaya", headline="Veri analisti")
        make_talent(session, "c", full_name="Cem Demir")
        assert slugs(talents(client, viewer, q="alice")) == ["a-slug"]
        assert slugs(talents(client, viewer, q="ANALIST")) == ["b-slug"]

    @pytest.mark.parametrize("wildcard", ["%%", "__", "a%e"])
    def test_like_wildcards_in_q_are_literal(self, client, session, viewer, wildcard):
        make_talent(session, "a", full_name="Alice")
        assert slugs(talents(client, viewer, q=wildcard)) == []

    def test_department_city_and_institution_filters(self, client, session, viewer):
        institution = Institution(name="Uni", verification_level="T2")
        session.add(institution)
        session.flush()
        make_talent(session, "a", department="Hukuk", city="Ankara", institution_id=institution.id)
        make_talent(session, "b", department="Hukuk", city="İzmir")
        make_talent(session, "c", department="Tıp", city="Ankara")
        assert set(slugs(talents(client, viewer, department="hukuk"))) == {"a-slug", "b-slug"}
        assert set(slugs(talents(client, viewer, city="ankara"))) == {"a-slug", "c-slug"}
        assert slugs(talents(client, viewer, department="Hukuk", city="Ankara")) == ["a-slug"]
        assert slugs(talents(client, viewer, institution_id=str(institution.id))) == ["a-slug"]

    def test_multiple_skills_must_all_be_sealed(self, client, session, viewer):
        org = make_org(session, "Acme")
        python = make_skill(session, "t-python", "Python")
        sql = make_skill(session, "t-sql", "SQL")
        both = make_talent(session, "both")
        only_python = make_talent(session, "py")
        seal_skill(session, both, org, python)
        seal_skill(session, both, org, sql)
        seal_skill(session, only_python, org, python)

        assert set(slugs(talents(client, viewer, skill_id=[str(python.id)]))) == {"both-slug", "py-slug"}
        assert slugs(talents(client, viewer, skill_id=[str(python.id), str(sql.id)])) == ["both-slug"]

    def test_unknown_filter_ids_give_empty_200_not_404(self, client, session, viewer):
        make_talent(session, "a")
        for params in ({"skill_id": str(uuid.uuid4())}, {"institution_id": str(uuid.uuid4())}):
            response = talents(client, viewer, **params)
            assert response.status_code == 200
            assert response.json() == {"items": [], "next_cursor": None, "has_more": False}

    @pytest.mark.parametrize(
        "params",
        [
            {"skill_id": "not-a-uuid"},
            {"skill_id": "' OR 1=1--"},
            {"institution_id": "../.."},
            {"limit": 51},
            {"limit": 0},
            {"q": "a"},
            {"q": "x" * 65},
            {"cursor": "not-a-cursor"},
            {"cursor": "e30="},  # valid base64 of {} — wrong shape
        ],
    )
    def test_invalid_input_is_422(self, client, session, viewer, params):
        make_talent(session, "a")
        response = talents(client, viewer, **params)
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"
        assert "a-slug" not in response.text

    def test_more_than_five_skill_filters_is_422(self, client, session, viewer):
        response = talents(client, viewer, skill_id=[str(uuid.uuid4()) for _ in range(6)])
        assert response.status_code == 422


class TestPagination:
    def test_newest_first_and_cursor_walks_every_profile_once(self, client, session, viewer):
        created = [make_talent(session, f"t{i}") for i in range(5)]
        expected = [profile.public_slug for profile in reversed(created)]

        seen: list[str] = []
        cursor = None
        for _ in range(3):
            params = {"limit": 2, **({"cursor": cursor} if cursor else {})}
            body = talents(client, viewer, **params).json()
            seen += [item["public_slug"] for item in body["items"]]
            cursor = body["next_cursor"]
            assert body["has_more"] is (cursor is not None)
        assert seen == expected
        assert cursor is None

    def test_same_request_gives_same_order(self, client, session, viewer):
        for i in range(4):
            make_talent(session, f"t{i}")
        assert slugs(talents(client, viewer)) == slugs(talents(client, viewer))

    def test_response_has_no_score_field(self, client, session, viewer):
        make_talent(session, "a")
        body = talents(client, viewer).json()
        assert "score" not in str(body) and "total" not in body

    def test_query_count_does_not_grow_with_page_size(self, client, session, viewer, query_counter):
        org = make_org(session, "Acme")
        skill = make_skill(session, "t-python", "Python")
        seal_skill(session, make_talent(session, "t0"), org, skill)
        # Built once: reading viewer.id after a commit reloads the user, which
        # would be counted as a query of the endpoint.
        headers = auth(viewer)

        query_counter.start()
        client.get("/discover/talents", headers=headers)
        one = query_counter.stop()

        for i in range(1, 8):
            seal_skill(session, make_talent(session, f"t{i}"), org, skill)
        query_counter.start()
        response = client.get("/discover/talents", headers=headers)
        many = query_counter.stop()

        assert len(response.json()["items"]) == 8
        assert many == one


class TestRateLimit:
    @pytest.mark.rate_limited
    def test_over_the_limit_is_429_with_retry_after(self, client, session, viewer, monkeypatch):
        monkeypatch.setattr(rate_limit, "DISCOVER_USER", rate_limit.Rule("discover_user", 2, 60))
        make_talent(session, "a")
        assert talents(client, viewer).status_code == 200
        # the budget is shared between the two directory endpoints
        assert client.get("/discover/organizations", headers=auth(viewer)).status_code == 200
        response = talents(client, viewer)
        assert response.status_code == 429
        assert response.json()["code"] == "RATE_LIMITED"
        assert int(response.headers["Retry-After"]) >= 1
        assert "a-slug" not in response.text

    @pytest.mark.rate_limited
    def test_limit_is_per_user(self, client, session, viewer, monkeypatch):
        monkeypatch.setattr(rate_limit, "DISCOVER_USER", rate_limit.Rule("discover_user", 1, 60))
        other = make_user(session, "other@example.com")
        assert talents(client, viewer).status_code == 200
        assert talents(client, viewer).status_code == 429
        assert talents(client, other).status_code == 200


class TestOrganizations:
    def test_search_order_and_pagination(self, client, session, viewer):
        for name in ["Zeta", "Acme", "Beta", "Acme Labs"]:
            make_org(session, name)

        def names(**params):
            body = client.get("/discover/organizations", params=params, headers=auth(viewer)).json()
            return [item["name"] for item in body["items"]], body["next_cursor"]

        assert names()[0] == ["Acme", "Acme Labs", "Beta", "Zeta"]
        assert names(q="acme")[0] == ["Acme", "Acme Labs"]

        first, cursor = names(limit=3)
        second, end = names(limit=3, cursor=cursor)
        assert first + second == ["Acme", "Acme Labs", "Beta", "Zeta"]
        assert end is None

    def test_like_wildcards_in_q_are_literal(self, client, session, viewer):
        make_org(session, "Acme")
        body = client.get("/discover/organizations", params={"q": "%%"}, headers=auth(viewer)).json()
        assert body["items"] == []

    @pytest.mark.parametrize("params", [{"limit": 51}, {"q": "a"}, {"cursor": "bad"}])
    def test_invalid_input_is_422(self, client, session, viewer, params):
        response = client.get("/discover/organizations", params=params, headers=auth(viewer))
        assert response.status_code == 422
