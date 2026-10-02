"""
YET-176 regression: non-consensual membership must not cost the victim any talent function.

The attacker uses the REAL API (POST /organizations/, POST /institutions/, POST .../members)
to make the victim ADMIN of an attacker-owned org and institution. Afterwards:
- the victim keeps every talent capability (AC-1..6, AC-9),
- the attacker gains no access to the victim's engagement/evidence/verified experience (AC-7).

Out of scope here (open, tracked elsewhere): unknown-email 500 / enumeration (YET-180),
last-admin + role overwrite (YET-236), invite/accept flow (Faz 5).
"""

from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models import (
    Deliverable,
    Engagement,
    Evidence,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    TalentProfile,
    User,
    VerifiedExperience,
)

VICTIM_EMAIL = "victim-nc@example.com"


def _h(user):
    return {"X-Debug-User-Id": str(user.id)}


@pytest.fixture
def victim(session):
    user = User(email=VICTIM_EMAIL, password_hash="h")
    session.add(user)
    session.flush()
    talent = TalentProfile(user_id=user.id, full_name="Victim", visibility="PRIVATE")
    session.add(talent)
    session.flush()
    return user, talent


@pytest.fixture
def attacker(session):
    """Attacker has a talent profile too, so evidence endpoints exercise scoping (404), not 403."""
    user = User(email="attacker-nc@example.com", password_hash="h")
    session.add(user)
    session.flush()
    session.add(TalentProfile(user_id=user.id, full_name="Attacker", visibility="PRIVATE"))
    session.flush()
    return user


@pytest.fixture
def victim_records(session, victim):
    """Victim's own org/institution, ACTIVE engagement, CLEAN evidence, verified experience."""
    _, talent = victim
    org = Organization(name="Real Org NC", verification_level="T1", status="ACTIVE")
    inst = Institution(name="Real Inst NC", verification_level="T1", status="ACTIVE")
    session.add_all([org, inst])
    session.flush()
    eng = Engagement(
        talent_id=talent.id,
        organization_id=org.id,
        institution_id=inst.id,
        kind="INTERNSHIP",
        title="Victim Engagement",
        status="ACTIVE",
        version=1,
    )
    session.add(eng)
    session.flush()
    evidence = Evidence(
        owner_talent_id=talent.id,
        kind="DOCUMENT",
        provenance="SELF_UPLOADED",
        visibility="PRIVATE",
        scan_status="CLEAN",
        storage_etag="etag-1",
        storage_key=f"{uuid4()}.pdf",
        mime_type="application/pdf",
        size_bytes=10,
    )
    exp = VerifiedExperience(
        id=uuid4(),
        talent_id=talent.id,
        engagement_id=eng.id,
        organization_name_snapshot="Real Org NC",
        role_snapshot="Victim Engagement",
        started_on_snapshot=date(2026, 1, 1),
        ended_on_snapshot=date(2026, 2, 1),
        institution_name_snapshot=None,
        claim_type="COMPETENCE",
        visibility="PRIVATE",
        public_token=f"tok-{uuid4()}",
    )
    session.add_all([evidence, exp])
    session.flush()
    session.commit()
    return org, inst, eng, evidence, exp


@pytest.fixture
def forced_membership(client, attacker, victim, victim_records):
    """Attacker opens an org + institution via the API and force-adds the victim as ADMIN."""
    r = client.post("/organizations/", json={"name": "Attacker Org"}, headers=_h(attacker))
    assert r.status_code == 201
    evil_org_id = r.json()["id"]
    r = client.post(
        f"/organizations/{evil_org_id}/members",
        json={"email": VICTIM_EMAIL, "role": "ADMIN"},
        headers=_h(attacker),
    )
    assert r.status_code == 201
    assert r.json()["role"] == "ADMIN"

    r = client.post("/institutions/", json={"name": "Attacker Inst"}, headers=_h(attacker))
    assert r.status_code == 201
    evil_inst_id = r.json()["id"]
    r = client.post(
        f"/institutions/{evil_inst_id}/members",
        json={"email": VICTIM_EMAIL, "role": "ADMIN"},
        headers=_h(attacker),
    )
    assert r.status_code == 201
    assert r.json()["role"] == "ADMIN"
    return evil_org_id, evil_inst_id


class TestVictimKeepsTalentFunctions:
    """AC-1..6, AC-9: victim is now ADMIN of foreign org + institution, talent functions intact."""

    def test_membership_really_exists(self, session, victim, forced_membership):
        """Guard: the attack precondition holds (otherwise the other tests prove nothing)."""
        v_user, _ = victim
        session.expire_all()
        assert (
            session.query(OrganizationMember).filter_by(user_id=v_user.id, role="ADMIN").count()
            == 1
        )
        assert (
            session.query(InstitutionMember).filter_by(user_id=v_user.id, role="ADMIN").count()
            == 1
        )

    def test_ac1_ac2_engagement_list_and_detail(
        self, client, victim, victim_records, forced_membership
    ):
        v_user, _ = victim
        _, _, eng, _, _ = victim_records
        r = client.get("/engagements", headers=_h(v_user))
        assert r.status_code == 200
        assert [i["id"] for i in r.json()["items"]] == [str(eng.id)]
        r = client.get(f"/engagements/{eng.id}", headers=_h(v_user))
        assert r.status_code == 200

    def test_ac3_deliverable_created(
        self, client, session, victim, victim_records, forced_membership
    ):
        v_user, _ = victim
        _, _, eng, _, _ = victim_records
        r = client.post(
            f"/engagements/{eng.id}/deliverables", json={"title": "Rapor"}, headers=_h(v_user)
        )
        assert r.status_code == 201
        session.expire_all()
        rows = session.query(Deliverable).filter_by(engagement_id=eng.id).all()
        assert len(rows) == 1
        assert rows[0].submitted_by_user_id == v_user.id

    def test_ac4_own_evidence_download(self, client, victim, victim_records, forced_membership):
        v_user, _ = victim
        _, _, _, evidence, _ = victim_records
        with patch("app.services.storage.boto3.client") as mock_boto:
            mock_boto.return_value = MagicMock()
            mock_boto.return_value.generate_presigned_url.return_value = "https://m.example/x"
            mock_boto.return_value.head_object.return_value = {"ETag": '"etag-1"'}
            r = client.get(f"/evidence/{evidence.id}/download-url", headers=_h(v_user))
        assert r.status_code == 200
        assert r.json()["download_url"] == "https://m.example/x"

    def test_ac5_profile_and_verified_experiences(
        self, client, victim, victim_records, forced_membership
    ):
        v_user, talent = victim
        _, _, _, _, exp = victim_records
        r = client.get("/talents/me/verified-experiences/", headers=_h(v_user))
        assert r.status_code == 200
        assert [i["id"] for i in r.json()["items"]] == [str(exp.id)]
        r = client.get("/me", headers=_h(v_user))
        assert r.status_code == 200
        body = r.json()
        assert body["talent_profile"]["id"] == str(talent.id)
        assert {o["name"] for o in body["organizations"]} == {"Attacker Org"}
        assert {i["name"] for i in body["institutions"]} == {"Attacker Inst"}

    def test_ac6_profile_update(self, client, session, victim, forced_membership):
        v_user, talent = victim
        r = client.patch("/talents/me", json={"headline": "hala ben"}, headers=_h(v_user))
        assert r.status_code == 200
        session.expire_all()
        assert session.query(TalentProfile).filter_by(id=talent.id).one().headline == "hala ben"

    def test_ac9_existing_membership_scope_is_unioned(
        self, client, session, victim, victim_records
    ):
        """Pre-existing MEMBER access to the real org survives a later forced membership."""
        v_user, _ = victim
        org, _, eng, _, _ = victim_records
        session.add(OrganizationMember(organization_id=org.id, user_id=v_user.id, role="MEMBER", status="ACTIVE"))
        session.commit()
        # attacker forces the victim into an attacker org
        attacker2 = User(email="attacker2-nc@example.com", password_hash="h")
        session.add(attacker2)
        session.commit()
        r = client.post("/organizations/", json={"name": "Attacker Org 2"}, headers=_h(attacker2))
        assert r.status_code == 201
        r = client.post(
            f"/organizations/{r.json()['id']}/members",
            json={"email": VICTIM_EMAIL, "role": "ADMIN"},
            headers=_h(attacker2),
        )
        assert r.status_code == 201
        assert client.get(f"/engagements/{eng.id}", headers=_h(v_user)).status_code == 200
        # MEMBER of the real org is still not an ADMIN there: unchanged 404
        r = client.post(
            f"/organizations/{org.id}/members",
            json={"email": "x@example.com", "role": "MEMBER"},
            headers=_h(v_user),
        )
        assert r.status_code == 404


class TestAttackerGainsNothing:
    """AC-7 / AC-S1 / AC-S3: forced membership gives the attacker no access to victim data."""

    def test_attacker_cannot_reach_victim_records(
        self, client, session, attacker, victim, victim_records, forced_membership
    ):
        _, _, eng, evidence, exp = victim_records
        h = _h(attacker)

        # records exist (so 404 means "not visible", not "missing")
        session.expire_all()
        assert session.query(Engagement).filter_by(id=eng.id).count() == 1
        assert session.query(Evidence).filter_by(id=evidence.id).count() == 1
        assert session.query(VerifiedExperience).filter_by(id=exp.id).count() == 1

        r = client.get("/engagements", headers=h)
        assert r.status_code == 200
        assert r.json()["items"] == []
        assert client.get(f"/engagements/{eng.id}", headers=h).status_code == 404
        r = client.post(f"/engagements/{eng.id}/deliverables", json={"title": "x"}, headers=h)
        assert r.status_code == 404
        r = client.post(
            f"/engagements/{eng.id}/transitions",
            json={"to_status": "CANCELLED", "version": 1},
            headers=h,
        )
        assert r.status_code == 404
        r = client.get(f"/evidence/{evidence.id}/download-url", headers=h)
        assert r.status_code == 404
        r = client.get("/talents/me/verified-experiences/", headers=h)
        assert r.status_code == 200
        assert r.json()["items"] == []

        # rejected writes changed nothing
        session.expire_all()
        assert session.query(Deliverable).filter_by(engagement_id=eng.id).count() == 0
        assert session.query(Engagement).filter_by(id=eng.id).one().status == "ACTIVE"
