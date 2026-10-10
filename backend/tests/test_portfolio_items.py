"""
Domain/validation tests for "Hakkımda" (talent_profiles.about) and portfolio items
(docs/arastirma-ogrenci-profili.md §4). Authorization lives in
tests/authorization/test_portfolio_items_authz.py.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import PortfolioItem, TalentProfile, User
from app.services.portfolio import MAX_ITEMS_PER_TALENT, https_host, official_verify_url

BASE = "/talents/me/portfolio-items"


@pytest.fixture
def owner(session):
    user = User(email="portfolio-owner@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    profile = TalentProfile(user_id=user.id, full_name="Portfolyo Sahibi", visibility="PUBLIC", public_slug="portfolyo-sahibi")
    session.add(profile)
    session.flush()
    return user, profile


def _auth(user) -> dict:
    return {"X-Debug-User-Id": str(user.id)}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url, host",
    [
        ("https://www.coursera.org/verify/X", "www.coursera.org"),
        ("https://Credential.NET/abc", "credential.net"),
        ("https://example.com:443/a", "example.com"),
        ("https://gооgle.com/x", "xn--ggle-55da.com"),  # Cyrillic о: homograph made visible
        ("http://example.com", None),
        ("javascript:alert(1)", None),
        ("https://user:pass@example.com", None),
        ("https://example.com:8443/a", None),
        ("https://", None),
        ("", None),
        (None, None),
    ],
)
def test_https_host(url, host):
    assert https_host(url) == host


@pytest.mark.parametrize(
    "url, allowed",
    [
        ("https://www.coursera.org/verify/ABC", True),
        ("https://coursera.org/share/ABC", True),
        ("https://www.udemy.com/certificate/UC-1/", True),
        ("https://ude.my/UC-1", True),
        ("https://coursera.org.evil.example/verify", False),
        ("https://evilcoursera.org/verify", False),
        ("http://www.coursera.org/verify/ABC", False),
    ],
)
def test_official_verify_url_allowlist(url, allowed):
    assert (official_verify_url(url) == url) is allowed


# ---------------------------------------------------------------------------
# Portfolio item validation (API + DB)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "CERTIFICATE", "title": "   "},
        {"kind": "CERTIFICATE", "title": "x" * 121},
        {"kind": "BADGE", "title": "Rozet"},
        {"kind": "WORK", "title": "Site", "external_url": "http://ornek.dev"},
        {"kind": "WORK", "title": "Site", "external_url": "javascript:alert(1)"},
        {"kind": "CERTIFICATE", "title": "Gelecek", "issued_on": (date.today() + timedelta(days=40)).isoformat()},
    ],
)
def test_create_rejects_invalid_payload(client, owner, payload):
    user, _ = owner
    assert client.post(BASE, json=payload, headers=_auth(user)).status_code == 422


def test_create_trims_and_clears_blank_optionals(client, owner):
    user, _ = owner
    response = client.post(
        BASE,
        json={"kind": "CERTIFICATE", "title": "  SQL Temelleri ", "issuer": "  ", "credential_id": " AB-1 "},
        headers=_auth(user),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "SQL Temelleri"
    assert body["issuer"] is None
    assert body["credential_id"] == "AB-1"


def test_patch_cannot_null_required_fields(client, session, owner):
    user, profile = owner
    item = PortfolioItem(talent_id=profile.id, kind="WORK", title="Proje")
    session.add(item)
    session.flush()
    for field in ("title", "kind", "show_on_profile"):
        response = client.patch(f"{BASE}/{item.id}", json={field: None}, headers=_auth(user))
        assert response.status_code == 422, field


def test_patch_clears_optional_field(client, session, owner):
    user, profile = owner
    item = PortfolioItem(talent_id=profile.id, kind="WORK", title="Proje", issuer="Kulüp")
    session.add(item)
    session.flush()
    response = client.patch(f"{BASE}/{item.id}", json={"issuer": None}, headers=_auth(user))
    assert response.status_code == 200
    assert response.json()["issuer"] is None


@pytest.mark.parametrize(
    "fields",
    [
        {"kind": "WORK", "title": "Site", "external_url": "http://ornek.dev"},
        {"kind": "OTHER", "title": "x"},
        {"kind": "WORK", "title": ""},
    ],
)
def test_db_constraints_back_the_api_rules(session, owner, fields):
    _, profile = owner
    session.add(PortfolioItem(talent_id=profile.id, **fields))
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.flush()


def test_self_declared_link_shows_host_publicly(client, session, owner):
    _, profile = owner
    session.add(
        PortfolioItem(
            talent_id=profile.id,
            kind="WORK",
            title="Açık kaynak katkı",
            external_url="https://github.com/ornek/proje",
            show_on_profile=True,
        )
    )
    session.flush()
    cert = client.get("/public/talents/portfolyo-sahibi").json()["certificates"][0]
    assert cert["badge"] == "SELF_DECLARED"
    assert cert["link_url"] == "https://github.com/ornek/proje"
    assert cert["link_host"] == "github.com"
    assert cert["verify_url"] is None


# ---------------------------------------------------------------------------
# "Hakkımda"
# ---------------------------------------------------------------------------


def test_about_round_trip_and_public(client, session, owner):
    user, profile = owner
    text = "Bilgisayar mühendisliği 3. sınıf öğrencisiyim.\nVeri görselleştirme ile ilgileniyorum."
    response = client.patch("/talents/me", json={"about": text}, headers=_auth(user))
    assert response.status_code == 200, response.text
    assert response.json()["about"] == text
    assert client.get("/me", headers=_auth(user)).json()["talent_profile"]["about"] == text
    assert client.get("/public/talents/portfolyo-sahibi").json()["about"] == text


def test_about_limit_and_blank(client, session, owner):
    user, profile = owner
    assert client.patch("/talents/me", json={"about": "a" * 1001}, headers=_auth(user)).status_code == 422
    assert client.patch("/talents/me", json={"about": "a" * 1000}, headers=_auth(user)).status_code == 200
    response = client.patch("/talents/me", json={"about": "   \n "}, headers=_auth(user))
    assert response.status_code == 200
    assert response.json()["about"] is None


def test_about_db_check(session, owner):
    _, profile = owner
    profile.about = "a" * 1001
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.flush()


def test_item_limit_per_talent(client, session, owner):
    """AC-S11: at most MAX_ITEMS_PER_TALENT live items; deleted ones do not count."""
    user, profile = owner
    session.add_all(
        PortfolioItem(talent_id=profile.id, kind="WORK", title=f"Kayıt {n}") for n in range(MAX_ITEMS_PER_TALENT)
    )
    session.flush()

    blocked = client.post(BASE, json={"kind": "WORK", "title": "Fazladan"}, headers=_auth(user))
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "PORTFOLIO_LIMIT_REACHED"

    first_id = client.get(BASE, headers=_auth(user)).json()["items"][0]["id"]
    assert client.delete(f"{BASE}/{first_id}", headers=_auth(user)).status_code == 204
    assert client.post(BASE, json={"kind": "WORK", "title": "Yer açıldı"}, headers=_auth(user)).status_code == 201
