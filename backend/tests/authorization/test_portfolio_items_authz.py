"""
Authorization tests for /talents/me/portfolio-items and the public certificates list.

docs/arastirma-ogrenci-profili.md §4.3-4.4:
- Owner only; ownership from the session. Another talent's item, an unknown id and
  a talent-less caller answer an identical 404 and leave the record untouched.
- evidence_id must be the caller's own live evidence (someone else's → 404).
- Public profile lists only consented (show_on_profile) items of a PUBLIC talent;
  file and OCR fields never leak; the "coordinator confirmed" badge can only come
  from a CONFIRMED check on the owner's own evidence.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models import (
    AuditEvent,
    CertificateCheck,
    Deliverable,
    Engagement,
    Evidence,
    Organization,
    PortfolioItem,
    User,
)

BASE = "/talents/me/portfolio-items"


def _auth(user) -> dict:
    return {"X-Debug-User-Id": str(user.id)}


def _item(session, talent, **kwargs) -> PortfolioItem:
    fields = {"kind": "CERTIFICATE", "title": "Veri Analizi Sertifikası", "show_on_profile": False}
    fields.update(kwargs)
    item = PortfolioItem(talent_id=talent.id, **fields)
    session.add(item)
    session.flush()
    return item


def _evidence(session, talent, deliverable_id=None) -> Evidence:
    ev = Evidence(
        owner_talent_id=talent.id,
        kind="CERTIFICATE",
        storage_key=f"evidence/{talent.id}/{uuid.uuid4()}.png",
        mime_type="image/png",
        size_bytes=100,
        scan_status="CLEAN",
        deliverable_id=deliverable_id,
    )
    session.add(ev)
    session.flush()
    return ev


@pytest.fixture
def item_a(session, talent_a):
    return _item(session, talent_a, title="A sertifikası")


@pytest.fixture
def item_b(session, talent_b):
    return _item(session, talent_b, title="B sertifikası")


@pytest.fixture
def talentless_user(session):
    user = User(email="portfolio-org-member@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


# ---------------------------------------------------------------------------
# Owner — positive
# ---------------------------------------------------------------------------


def test_owner_creates_lists_updates_and_deletes(client, session, user_talent_a, talent_a):
    created = client.post(
        BASE,
        json={"kind": "WORK", "title": "Kişisel web sitesi", "external_url": "https://ornek.dev"},
        headers=_auth(user_talent_a),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["badge"] == "SELF_DECLARED"
    assert body["show_on_profile"] is False  # consent defaults to off
    item_id = body["id"]

    listed = client.get(BASE, headers=_auth(user_talent_a))
    assert listed.status_code == 200
    assert [i["id"] for i in listed.json()["items"]] == [item_id]

    patched = client.patch(f"{BASE}/{item_id}", json={"show_on_profile": True}, headers=_auth(user_talent_a))
    assert patched.status_code == 200
    assert patched.json()["show_on_profile"] is True

    deleted = client.delete(f"{BASE}/{item_id}", headers=_auth(user_talent_a))
    assert deleted.status_code == 204
    assert client.get(BASE, headers=_auth(user_talent_a)).json()["items"] == []
    row = session.get(PortfolioItem, uuid.UUID(item_id))
    assert row.deleted_at is not None and row.show_on_profile is False


def test_owner_can_link_own_evidence(client, session, user_talent_a, talent_a):
    ev = _evidence(session, talent_a)
    response = client.post(
        BASE,
        json={"kind": "CERTIFICATE", "title": "Dosyalı sertifika", "evidence_id": str(ev.id)},
        headers=_auth(user_talent_a),
    )
    assert response.status_code == 201, response.text
    assert response.json()["evidence_id"] == str(ev.id)

    again = client.post(
        BASE,
        json={"kind": "CERTIFICATE", "title": "İkinci kez", "evidence_id": str(ev.id)},
        headers=_auth(user_talent_a),
    )
    assert again.status_code == 409
    assert again.json()["code"] == "EVIDENCE_ALREADY_IN_PORTFOLIO"


def test_deleted_item_releases_its_evidence(client, session, user_talent_a, talent_a):
    """red_team finding: a soft-deleted item must not keep its evidence locked forever."""
    ev = _evidence(session, talent_a)
    body = {"kind": "CERTIFICATE", "title": "Tekrar eklenecek", "evidence_id": str(ev.id)}
    first = client.post(BASE, json=body, headers=_auth(user_talent_a))
    assert client.delete(f"{BASE}/{first.json()['id']}", headers=_auth(user_talent_a)).status_code == 204

    again = client.post(BASE, json=body, headers=_auth(user_talent_a))
    assert again.status_code == 201, again.text
    assert session.get(Evidence, ev.id).deleted_at is None  # the file itself is untouched


def test_consent_change_is_audited(client, session, user_talent_a, talent_a, item_a):
    client.patch(f"{BASE}/{item_a.id}", json={"show_on_profile": True}, headers=_auth(user_talent_a))

    events = session.execute(
        select(AuditEvent).where(
            AuditEvent.action == "PORTFOLIO_ITEM_VISIBILITY_CHANGED",
            AuditEvent.subject_id == item_a.id,
        )
    ).scalars().all()
    assert len(events) == 1
    assert events[0].actor_user_id == user_talent_a.id
    assert events[0].event_metadata == {"from": False, "to": True}


# ---------------------------------------------------------------------------
# Negative — identical 404, record untouched
# ---------------------------------------------------------------------------


def test_other_talent_cannot_update_or_delete(client, session, user_talent_a, talent_a, item_b):
    patched = client.patch(f"{BASE}/{item_b.id}", json={"show_on_profile": True}, headers=_auth(user_talent_a))
    deleted = client.delete(f"{BASE}/{item_b.id}", headers=_auth(user_talent_a))

    assert patched.status_code == deleted.status_code == 404
    assert patched.json()["code"] == "PORTFOLIO_ITEM_NOT_FOUND"
    session.refresh(item_b)
    assert item_b.show_on_profile is False
    assert item_b.deleted_at is None


def test_other_talent_items_not_listed(client, user_talent_a, talent_a, item_a, item_b):
    ids = [i["id"] for i in client.get(BASE, headers=_auth(user_talent_a)).json()["items"]]
    assert ids == [str(item_a.id)]


def test_foreign_and_unknown_ids_are_indistinguishable(client, user_talent_a, talent_a, item_b):
    foreign = client.patch(f"{BASE}/{item_b.id}", json={"title": "x"}, headers=_auth(user_talent_a))
    unknown = client.patch(f"{BASE}/{uuid.uuid4()}", json={"title": "x"}, headers=_auth(user_talent_a))

    assert foreign.status_code == unknown.status_code == 404
    strip = lambda r: {k: v for k, v in r.json().items() if k != "request_id"}  # noqa: E731
    assert strip(foreign) == strip(unknown)


def test_cannot_link_someone_elses_evidence(client, session, user_talent_a, talent_a, talent_b):
    foreign_ev = _evidence(session, talent_b)
    response = client.post(
        BASE,
        json={"kind": "CERTIFICATE", "title": "Çalıntı", "evidence_id": str(foreign_ev.id)},
        headers=_auth(user_talent_a),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "EVIDENCE_NOT_FOUND"
    assert session.execute(select(PortfolioItem).where(PortfolioItem.evidence_id == foreign_ev.id)).first() is None


def test_cannot_link_deleted_evidence(client, session, user_talent_a, talent_a):
    ev = _evidence(session, talent_a)
    ev.deleted_at = datetime.now(timezone.utc)
    session.flush()
    response = client.post(
        BASE, json={"kind": "CERTIFICATE", "title": "Silinmiş", "evidence_id": str(ev.id)}, headers=_auth(user_talent_a)
    )
    assert response.status_code == 404


def test_talent_id_in_body_is_ignored(client, session, user_talent_a, talent_a, talent_b):
    response = client.post(
        BASE,
        json={"kind": "WORK", "title": "Kimin?", "talent_id": str(talent_b.id)},
        headers=_auth(user_talent_a),
    )
    assert response.status_code == 201
    row = session.get(PortfolioItem, uuid.UUID(response.json()["id"]))
    assert row.talent_id == talent_a.id


def test_talentless_user(client, talentless_user, item_a):
    assert client.get(BASE, headers=_auth(talentless_user)).json() == {"items": [], "engagement_certificates": []}
    assert client.patch(f"{BASE}/{item_a.id}", json={"title": "x"}, headers=_auth(talentless_user)).status_code == 404
    assert client.delete(f"{BASE}/{item_a.id}", headers=_auth(talentless_user)).status_code == 404
    assert client.post(BASE, json={"kind": "WORK", "title": "x"}, headers=_auth(talentless_user)).status_code == 404


def test_unauthenticated_is_rejected(client, item_a):
    assert client.get(BASE).status_code == 401
    assert client.post(BASE, json={"kind": "WORK", "title": "x"}).status_code == 401
    assert client.patch(f"{BASE}/{item_a.id}", json={"title": "x"}).status_code == 401
    assert client.delete(f"{BASE}/{item_a.id}").status_code == 401


# ---------------------------------------------------------------------------
# Public profile — consent, privacy, badge integrity
# ---------------------------------------------------------------------------


@pytest.fixture
def public_talent_a(session, talent_a):
    talent_a.visibility = "PUBLIC"
    talent_a.public_slug = "portfolyo-a"
    session.flush()
    return talent_a


@pytest.fixture
def engagement_certificate_a(session, user_talent_a, public_talent_a):
    org = Organization(name="Portfolyo Org", verification_level="T2")
    session.add(org)
    session.flush()
    engagement = Engagement(
        talent_id=public_talent_a.id,
        organization_id=org.id,
        institution_id=None,
        kind="SHORT_PROJECT",
        title="Sertifikalı çalışma",
        status="ACTIVE",
        version=1,
    )
    session.add(engagement)
    session.flush()
    deliverable = Deliverable(
        engagement_id=engagement.id,
        title="Çıktı",
        submitted_by_user_id=user_talent_a.id,
        submitted_at=datetime.now(timezone.utc),
    )
    session.add(deliverable)
    session.flush()
    ev = _evidence(session, public_talent_a, deliverable_id=deliverable.id)
    check = CertificateCheck(
        evidence_id=ev.id,
        status="DONE",
        provider="COURSERA",
        credential_id="ABC123XYZ",
        verify_url="https://www.coursera.org/verify/ABC123XYZ",
        qr_raw_data="https://www.coursera.org/verify/ABC123XYZ",
        extracted_name="Gizli Ad Soyad",
        name_match=True,
        page_name="Gizli Sayfa Adı",
        decision="CONFIRMED",
    )
    session.add(check)
    session.flush()
    return ev


def test_public_lists_only_consented_items(client, session, public_talent_a):
    _item(session, public_talent_a, title="Gizli kalan", show_on_profile=False)
    _item(session, public_talent_a, title="Görünen", show_on_profile=True)
    _item(session, public_talent_a, title="Silinmiş", show_on_profile=True, deleted_at=datetime.now(timezone.utc))

    body = client.get("/public/talents/portfolyo-a").json()
    assert [c["title"] for c in body["certificates"]] == ["Görünen"]
    assert body["certificates"][0]["badge"] == "SELF_DECLARED"


def test_non_public_talent_exposes_nothing(client, session, talent_a):
    talent_a.public_slug = "portfolyo-gizli"
    session.flush()
    _item(session, talent_a, title="Rızalı ama profil kapalı", show_on_profile=True)

    response = client.get("/public/talents/portfolyo-gizli")
    assert response.status_code == 404
    assert "Rızalı" not in response.text


def test_confirmed_certificate_exposes_summary_only(client, session, public_talent_a, engagement_certificate_a):
    _item(session, public_talent_a, title="Coursera — Veri Bilimi", evidence_id=engagement_certificate_a.id, show_on_profile=True)

    response = client.get("/public/talents/portfolyo-a")
    cert = response.json()["certificates"][0]
    assert cert["badge"] == "COORDINATOR_CONFIRMED"
    assert cert["provider"] == "COURSERA"
    assert cert["credential_id"] == "ABC123XYZ"
    assert cert["verify_url"] == "https://www.coursera.org/verify/ABC123XYZ"
    assert cert["link_url"] is None
    for leaked in ("Gizli Ad Soyad", "Gizli Sayfa Adı", "storage_key", "evidence/", str(engagement_certificate_a.id)):
        assert leaked not in response.text


def test_badge_cannot_be_borrowed_from_foreign_evidence(client, session, public_talent_a, talent_b, engagement_certificate_a):
    """A CONFIRMED check on talent A's evidence must not make talent B's row confirmed,
    even if a row were (bypassing the API) pointed at that evidence."""
    talent_b.visibility = "PUBLIC"
    talent_b.public_slug = "portfolyo-b"
    session.flush()
    _item(session, talent_b, title="Ödünç rozet", evidence_id=engagement_certificate_a.id, show_on_profile=True)

    cert = client.get("/public/talents/portfolyo-b").json()["certificates"][0]
    assert cert["badge"] == "SELF_DECLARED"
    assert cert["verify_url"] is None and cert["provider"] is None


def _set_decision(session, evidence, decision):
    check = session.execute(select(CertificateCheck).where(CertificateCheck.evidence_id == evidence.id)).scalar_one()
    check.decision = decision
    session.flush()


def test_pending_check_is_self_declared(client, session, public_talent_a, engagement_certificate_a):
    _set_decision(session, engagement_certificate_a, "PENDING")
    _item(session, public_talent_a, title="Bekleyen", evidence_id=engagement_certificate_a.id, show_on_profile=True)

    cert = client.get("/public/talents/portfolyo-a").json()["certificates"][0]
    assert cert["badge"] == "SELF_DECLARED"
    assert cert["verify_url"] is None and cert["provider"] is None


def test_rejected_certificate_is_hidden_publicly(client, session, user_talent_a, public_talent_a, engagement_certificate_a):
    """AC-S7: a coordinator-rejected certificate never reaches the public page, not even as a claim."""
    _set_decision(session, engagement_certificate_a, "REJECTED")
    item = _item(session, public_talent_a, title="Reddedilmiş", evidence_id=engagement_certificate_a.id, show_on_profile=True)

    assert client.get("/public/talents/portfolyo-a").json()["certificates"] == []
    own = client.get(BASE, headers=_auth(user_talent_a)).json()["items"]
    assert [(i["id"], i["badge"]) for i in own] == [(str(item.id), "COORDINATOR_REJECTED")]


def test_confirmed_card_ignores_student_typed_credential(client, session, public_talent_a, engagement_certificate_a):
    """AC-S6: on a confirmed card credential number/provider come only from the reviewed check."""
    _item(
        session,
        public_talent_a,
        title="Onaylı",
        issuer="Google",
        credential_id="SAHTE-999",
        evidence_id=engagement_certificate_a.id,
        show_on_profile=True,
    )
    cert = client.get("/public/talents/portfolyo-a").json()["certificates"][0]
    assert cert["badge"] == "COORDINATOR_CONFIRMED"
    assert cert["credential_id"] == "ABC123XYZ"
    assert cert["issuer"] is None
    assert cert["provider"] == "COURSERA"


def test_client_cannot_forge_badge_or_relink_evidence(client, session, user_talent_a, talent_a, engagement_certificate_a):
    """AC-S4: badge/provider/decision in the body are ignored; PATCH cannot move evidence_id."""
    created = client.post(
        BASE,
        json={
            "kind": "CERTIFICATE",
            "title": "Sahte onay",
            "badge": "COORDINATOR_CONFIRMED",
            "provider": "COURSERA",
            "decision": "CONFIRMED",
        },
        headers=_auth(user_talent_a),
    )
    assert created.status_code == 201
    assert created.json()["badge"] == "SELF_DECLARED"
    item_id = created.json()["id"]

    patched = client.patch(
        f"{BASE}/{item_id}",
        json={"evidence_id": str(engagement_certificate_a.id), "badge": "COORDINATOR_CONFIRMED"},
        headers=_auth(user_talent_a),
    )
    assert patched.status_code == 200
    assert patched.json()["evidence_id"] is None
    assert patched.json()["badge"] == "SELF_DECLARED"


def test_non_provider_verify_url_is_dropped(client, session, public_talent_a, engagement_certificate_a):
    check = session.execute(
        select(CertificateCheck).where(CertificateCheck.evidence_id == engagement_certificate_a.id)
    ).scalar_one()
    check.verify_url = "https://coursera.org.evil.example/verify/ABC"
    session.flush()
    _item(session, public_talent_a, title="Şüpheli link", evidence_id=engagement_certificate_a.id, show_on_profile=True)

    cert = client.get("/public/talents/portfolyo-a").json()["certificates"][0]
    assert cert["badge"] == "COORDINATOR_CONFIRMED"
    assert cert["verify_url"] is None


def test_public_certificate_keys_are_an_exact_allowlist(client, session, public_talent_a, engagement_certificate_a):
    """Any new key on a public certificate must be a deliberate decision (leak guard)."""
    _item(session, public_talent_a, title="Onaylı", evidence_id=engagement_certificate_a.id, show_on_profile=True)
    _item(session, public_talent_a, title="Beyan", show_on_profile=True)

    for cert in client.get("/public/talents/portfolyo-a").json()["certificates"]:
        assert set(cert) == {
            "kind", "title", "issuer", "issued_on", "credential_id",
            "badge", "provider", "verify_url", "link_url", "link_host",
        }
