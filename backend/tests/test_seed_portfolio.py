"""
Showcase "Hakkımda" + certificate showcase seed (/p/ayse-yilmaz).

The demo profile must show one coordinator-confirmed certificate (from a verified
engagement), self-declared items in their own tier, hide the consent-off item,
and never seed a link that would 404 in a live demo.
"""

from sqlalchemy import func, select

from app.models import PortfolioItem
from scripts.seed import (
    SHOWCASE_ABOUT,
    seed_engagements,
    seed_institutions_and_organizations,
    seed_public_experiences,
    seed_showcase_portfolio,
    seed_showcase_profile,
    seed_skills,
    seed_talents,
    seed_verified_organizations,
)


def _run_full_seed(session) -> None:
    seed_skills(session)
    seed_talents(session)
    seed_institutions_and_organizations(session)
    seed_verified_organizations(session)
    seed_engagements(session)
    seed_showcase_profile(session)
    seed_showcase_portfolio(session)
    seed_public_experiences(session)
    session.commit()


def test_showcase_portfolio_on_public_profile(client, session):
    _run_full_seed(session)

    body = client.get("/public/talents/ayse-yilmaz").json()
    assert body["about"] == SHOWCASE_ABOUT

    certificates = body["certificates"]
    assert [c["badge"] for c in certificates] == ["COORDINATOR_CONFIRMED", "SELF_DECLARED", "SELF_DECLARED"]
    confirmed = certificates[0]
    assert confirmed["provider"] == "COURSERA"
    assert confirmed["credential_id"] == "SEED-PGPERF-2026"
    assert "İngilizce B2" not in [c["title"] for c in certificates]  # consent off
    assert all(c["verify_url"] is None and c["link_url"] is None for c in certificates)


def test_showcase_portfolio_is_idempotent(session):
    _run_full_seed(session)
    seed_showcase_portfolio(session)
    session.commit()

    assert session.execute(select(func.count()).select_from(PortfolioItem)).scalar_one() == 4
