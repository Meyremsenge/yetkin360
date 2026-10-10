"""
YET-177 (GUV-03): one person with several self-service accounts vs. verified experience.

Decision K2 (b): no new organization-consent transition. Mitigation is visibility:
- the public verification page shows institution_trust_level and (only if verified) organization_domain.

The chain tests below pin what is open and what is closed TODAY, through the real API:
- OPEN (accepted, K2 b): one person with 2 accounts can run the whole chain against an org they created.
- CLOSED: the result is PARTICIPATION while the org is T1 (even with a 28+ day engagement).
- CLOSED: no org consent is needed to be *named*, but a foreign org's engagement cannot be evaluated
  or attested without that org's own member (coordinator alone gets 403 / 409).
"""

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models import (
    Attestation,
    Engagement,
    Evaluation,
    Institution,
    Organization,
    TalentProfile,
    User,
    VerifiedExperience,
)


def _h(user):
    return {"X-Debug-User-Id": str(user.id)}


def _make_user(session, email, talent=False):
    user = User(email=email, password_hash="h")
    session.add(user)
    session.flush()
    profile = None
    if talent:
        profile = TalentProfile(user_id=user.id, full_name=email, visibility="PRIVATE")
        session.add(profile)
        session.flush()
    return user, profile


def _public_ve(session, *, org_level, org_domain, inst_level):
    """Public VerifiedExperience whose engagement points to an org / institution of given levels."""
    user, talent = _make_user(session, f"pub-{uuid4()}@example.com", talent=True)
    org = Organization(
        name="Pub Org", domain=org_domain, verification_level=org_level, status="ACTIVE"
    )
    inst = (
        Institution(name="Pub Inst", verification_level=inst_level, status="ACTIVE")
        if inst_level
        else None
    )
    session.add(org)
    if inst:
        session.add(inst)
    session.flush()
    eng = Engagement(
        talent_id=talent.id,
        organization_id=org.id,
        institution_id=inst.id if inst else None,
        kind="INTERNSHIP",
        title="Pub Engagement",
        status="EVALUATED",
        version=1,
    )
    session.add(eng)
    session.flush()
    token = f"tok-{uuid4()}"
    session.add(
        VerifiedExperience(
            id=uuid4(),
            talent_id=talent.id,
            engagement_id=eng.id,
            organization_name_snapshot="Pub Org",
            role_snapshot="Pub Engagement",
            started_on_snapshot=date(2026, 1, 1),
            ended_on_snapshot=date(2026, 3, 1),
            institution_name_snapshot="Pub Inst" if inst else None,
            claim_type="PARTICIPATION",
            visibility="PUBLIC",
            public_token=token,
        )
    )
    session.commit()
    return token


class TestPublicShowsWhoVouches:
    """K2 (b) display: a self-created org/institution is visibly unverified."""

    def test_unverified_org_and_institution_levels_shown_domain_hidden(self, client, session):
        token = _public_ve(
            session, org_level="T1", org_domain="attacker-owned.example", inst_level="T1"
        )
        assert session.query(VerifiedExperience).filter_by(public_token=token).count() == 1

        r = client.get(f"/public/v/{token}")

        assert r.status_code == 200
        data = r.json()
        assert data["organization_trust_level"] == "T1"
        assert data["institution_trust_level"] == "T1"
        # Unverified domain is attacker-chosen text: must not be shown as if it were a credential.
        assert data["organization_domain"] is None
        assert "attacker-owned.example" not in r.text

    def test_verified_org_domain_shown(self, client, session):
        token = _public_ve(session, org_level="T2", org_domain="acme.example", inst_level="T1")

        r = client.get(f"/public/v/{token}")

        assert r.status_code == 200
        data = r.json()
        assert data["organization_trust_level"] == "T2"
        assert data["organization_domain"] == "acme.example"

    def test_no_institution_gives_null_institution_level(self, client, session):
        token = _public_ve(session, org_level="T1", org_domain=None, inst_level=None)

        r = client.get(f"/public/v/{token}")

        assert r.status_code == 200
        assert r.json()["institution_trust_level"] is None
        assert r.json()["institution_name"] is None


@pytest.fixture
def sybil_chain(client, session):
    """
    One person, three accounts, real API: account `owner` creates an org + institution and adds
    account `coord` as COORDINATOR (an existing member's role is never overwritten, so the owner
    cannot promote itself); account `talent` links to that institution and opens an engagement
    on the owner's org. Returns everything up to PENDING_EVALUATION (before evaluation).
    """
    owner, _ = _make_user(session, f"sy-owner-{uuid4()}@example.com")
    coord, _ = _make_user(session, f"sy-coord-{uuid4()}@example.com")
    talent_user, talent = _make_user(session, f"sy-talent-{uuid4()}@example.com", talent=True)
    session.commit()

    r = client.post("/organizations/", json={"name": "Sybil Org"}, headers=_h(owner))
    assert r.status_code == 201
    org_id = r.json()["id"]
    assert r.json()["verification_level"] == "T1"
    r = client.post("/institutions/", json={"name": "Sybil Inst"}, headers=_h(owner))
    assert r.status_code == 201
    inst_id = r.json()["id"]
    r = client.post(
        f"/institutions/{inst_id}/members",
        json={"email": coord.email, "role": "COORDINATOR"},
        headers=_h(owner),
    )
    assert r.status_code == 202

    r = client.post(f"/institutions/{inst_id}/link-requests", headers=_h(talent_user))
    assert r.status_code == 201
    r = client.post(
        f"/institutions/{inst_id}/link-requests/{r.json()['id']}/approve", headers=_h(coord)
    )
    assert r.status_code == 200

    r = client.post(
        "/engagements",
        json={
            "talent_id": str(talent.id),
            "organization_id": org_id,
            "kind": "INTERNSHIP",
            "title": "Sahte staj",
            "institution_id": inst_id,
        },
        headers=_h(talent_user),
    )
    assert r.status_code == 201
    eng_id, version = r.json()["id"], r.json()["version"]

    def step(to_status, actor):
        nonlocal version
        resp = client.post(
            f"/engagements/{eng_id}/transitions",
            json={"to_status": to_status, "version": version, "notify_emails": ["approver@example.com"]},
            headers=_h(actor),
        )
        assert resp.status_code == 200, resp.text
        version = resp.json()["version"]

    step("PENDING_APPROVAL", talent_user)
    step("ACTIVE", coord)
    r = client.post(
        f"/engagements/{eng_id}/deliverables", json={"title": "x"}, headers=_h(talent_user)
    )
    assert r.status_code == 201
    step("PENDING_EVALUATION", coord)
    return owner, talent_user, eng_id, coord


EVAL_BODY = {
    "direction": "ORG_TO_TALENT",
    "items": [{"criterion": "COMMUNICATION", "rating": "MEETS", "comment": "ok"}],
}


class TestSybilChainTodayOwnOrg:
    def test_one_person_two_accounts_get_verified_experience_but_only_participation(
        self, client, session, sybil_chain
    ):
        """OPEN by K2 (b): chain completes. CLOSED: result is PARTICIPATION + ATTESTOR_NOT_VERIFIED."""
        owner, _, eng_id, coord = sybil_chain

        r = client.post(f"/engagements/{eng_id}/evaluation", json=EVAL_BODY, headers=_h(owner))
        assert r.status_code == 201
        session.expire_all()
        eng = session.get(Engagement, eng_id)
        assert eng.status == "EVALUATED"

        r = client.post(
            f"/engagements/{eng_id}/attestations",
            json={"claim_type": "COMPETENCE", "version": eng.version},
            headers=_h(coord),
        )

        assert r.status_code == 201
        assert r.json()["claim_type"] == "PARTICIPATION"
        assert "ATTESTOR_NOT_VERIFIED_SUPERVISOR" in r.json()["downgrade_reasons"]
        session.expire_all()
        ves = session.query(VerifiedExperience).filter_by(engagement_id=eng_id).all()
        assert [(v.claim_type, v.visibility) for v in ves] == [("PARTICIPATION", "PRIVATE")]

    def test_t1_org_blocks_competence_even_with_28_plus_days(self, client, session, sybil_chain):
        """The real Sybil guard: duration is satisfied, T1 org alone still downgrades."""
        owner, _, eng_id, coord = sybil_chain
        r = client.post(f"/engagements/{eng_id}/evaluation", json=EVAL_BODY, headers=_h(owner))
        assert r.status_code == 201
        session.expire_all()
        eng = session.get(Engagement, eng_id)
        now = datetime.now(timezone.utc)
        eng.started_on = (now - timedelta(days=60)).date()
        eng.ended_on = (now - timedelta(days=1)).date()
        session.commit()

        r = client.post(
            f"/engagements/{eng_id}/attestations",
            json={"claim_type": "COMPETENCE", "version": eng.version},
            headers=_h(coord),
        )

        assert r.status_code == 201
        assert r.json()["claim_type"] == "PARTICIPATION"
        assert r.json()["downgrade_reasons"] == ["ATTESTOR_NOT_VERIFIED_SUPERVISOR"]


class TestForeignOrgNeedsItsOwnMember:
    """Talent may name any org, but without a member of that org the chain cannot finish."""

    def test_coordinator_alone_cannot_evaluate_or_attest_for_foreign_org(self, client, session):
        victim_org = Organization(
            name="Gercek Sirket A.S.", verification_level="T2", status="ACTIVE"
        )
        session.add(victim_org)
        coord, _ = _make_user(session, f"fo-coord-{uuid4()}@example.com")
        inst_admin, _ = _make_user(session, f"fo-admin-{uuid4()}@example.com")
        talent_user, talent = _make_user(session, f"fo-talent-{uuid4()}@example.com", talent=True)
        session.commit()

        r = client.post("/institutions/", json={"name": "Fo Inst"}, headers=_h(inst_admin))
        inst_id = r.json()["id"]
        r = client.post(
            f"/institutions/{inst_id}/members",
            json={"email": coord.email, "role": "COORDINATOR"},
            headers=_h(inst_admin),
        )
        assert r.status_code == 202
        r = client.post(f"/institutions/{inst_id}/link-requests", headers=_h(talent_user))
        client.post(
            f"/institutions/{inst_id}/link-requests/{r.json()['id']}/approve", headers=_h(coord)
        )
        r = client.post(
            "/engagements",
            json={
                "talent_id": str(talent.id),
                "organization_id": str(victim_org.id),
                "kind": "INTERNSHIP",
                "title": "Sahte",
                "institution_id": inst_id,
            },
            headers=_h(talent_user),
        )
        assert r.status_code == 201
        eng_id, version = r.json()["id"], r.json()["version"]
        for to_status, actor in (
            ("PENDING_APPROVAL", talent_user),
            ("ACTIVE", coord),
        ):
            r = client.post(
                f"/engagements/{eng_id}/transitions",
                json={"to_status": to_status, "version": version, "notify_emails": ["approver@example.com"]},
                headers=_h(actor),
            )
            assert r.status_code == 200
            version = r.json()["version"]
        client.post(
            f"/engagements/{eng_id}/deliverables", json={"title": "x"}, headers=_h(talent_user)
        )
        r = client.post(
            f"/engagements/{eng_id}/transitions",
            json={"to_status": "PENDING_EVALUATION", "version": version},
            headers=_h(coord),
        )
        assert r.status_code == 200
        version = r.json()["version"]

        r = client.post(f"/engagements/{eng_id}/evaluation", json=EVAL_BODY, headers=_h(coord))
        assert r.status_code == 403
        r = client.post(
            f"/engagements/{eng_id}/attestations",
            json={"claim_type": "PARTICIPATION", "version": version},
            headers=_h(coord),
        )
        assert r.status_code == 409

        session.expire_all()
        assert session.get(Engagement, eng_id).status == "PENDING_EVALUATION"
        assert session.query(Evaluation).filter_by(engagement_id=eng_id).count() == 0
        assert session.query(Attestation).filter_by(engagement_id=eng_id).count() == 0
        assert session.query(VerifiedExperience).filter_by(engagement_id=eng_id).count() == 0
