"""
Complaint authorization matrix (sikayet-backend, AC-S9 / AC-S10 / AC-S11 / AC-S13).

Actors: owner (talent A), other talent (B), respondent (derived coordinator),
other coordinator of the same institution, coordinator of an unrelated
institution, platform admin, anonymous. Unauthorized → 404 (never 403);
anonymous → 401.
"""

import uuid

import pytest

from app.models import Evidence
from tests._complaint_data import (
    add_attachment,
    add_engagement,
    fake_storage,
    h,
    make_world,
    open_complaint,
    to_escalated,
    to_explanation_requested,
)

ACTORS = ["owner", "other_talent", "respondent", "other_coord", "unrelated_coord", "admin", "anonymous"]


def _user(w, actor):
    return {
        "owner": w.user_a,
        "other_talent": w.user_b,
        "respondent": w.coord,
        "other_coord": w.coord2,
        "unrelated_coord": w.unrelated_coord,
        "admin": w.admin,
        "anonymous": None,
    }[actor]


def _headers(w, actor):
    user = _user(w, actor)
    return {} if user is None else h(user)


@pytest.fixture
def world(session, client, monkeypatch):
    """A complaint at EXPLANATION_REQUESTED with one attachment."""
    w = make_world(session)
    fake_storage(monkeypatch)
    w.complaint = open_complaint(client, w)
    w.attachment = add_attachment(client, w, w.complaint["id"]).json()
    to_explanation_requested(client, w, w.complaint["id"])
    # A second, still OPEN complaint: target of the admin transition probe (DISMISS is valid there).
    w.open_complaint = open_complaint(client, w, engagement=add_engagement(session, w, w.talent_a))
    return w


# --- student/respondent routes ----------------------------------------------

DETAIL_EXPECTED = {
    "owner": 200,
    "other_talent": 404,
    "respondent": 200,
    "other_coord": 404,  # only after escalation
    "unrelated_coord": 404,
    "admin": 404,  # the admin reads through /admin/complaints
    "anonymous": 401,
}


@pytest.mark.parametrize("actor", ACTORS)
def test_get_complaint_detail(client, world, actor):
    r = client.get(f"/complaints/{world.complaint['id']}", headers=_headers(world, actor))
    assert r.status_code == DETAIL_EXPECTED[actor], r.text
    if r.status_code == 404:
        assert "description" not in r.text and "items" not in r.json()


ATTACHMENT_EXPECTED = {
    "owner": 200,
    "other_talent": 404,
    "respondent": 404,  # AC-S9: the respondent never downloads the attachment
    "other_coord": 404,
    "unrelated_coord": 404,
    "admin": 404,  # student route; admin uses /admin/...
    "anonymous": 401,
}


@pytest.mark.parametrize("actor", ACTORS)
def test_download_attachment_student_route(client, world, actor):
    r = client.get(
        f"/complaints/{world.complaint['id']}/attachments/{world.attachment['id']}", headers=_headers(world, actor)
    )
    assert r.status_code == ATTACHMENT_EXPECTED[actor], r.text
    if r.status_code != 200:
        assert "download_url" not in r.text


@pytest.mark.parametrize("actor", ACTORS)
def test_list_own_complaints_only(client, world, actor):
    r = client.get("/complaints", headers=_headers(world, actor))
    if actor == "anonymous":
        assert r.status_code == 401
        return
    assert r.status_code == 200
    ids = {i["id"] for i in r.json()["items"]}
    assert ids == ({world.complaint["id"], world.open_complaint["id"]} if actor == "owner" else set())


@pytest.mark.parametrize("actor", ACTORS)
def test_assigned_list(client, world, actor):
    r = client.get("/complaints/assigned", headers=_headers(world, actor))
    if actor == "anonymous":
        assert r.status_code == 401
        return
    assert r.status_code == 200
    ids = [i["id"] for i in r.json()["items"]]
    assert ids == ([world.complaint["id"]] if actor == "respondent" else [])


EXPLAIN_EXPECTED = {
    "owner": 404,
    "other_talent": 404,
    "respondent": 200,
    "other_coord": 404,
    "unrelated_coord": 404,
    "admin": 404,
    "anonymous": 401,
}


@pytest.mark.parametrize("actor", ACTORS)
def test_submit_explanation(client, world, actor):
    r = client.post(
        f"/complaints/{world.complaint['id']}/explanation", headers=_headers(world, actor), json={"text": "Açıklama."}
    )
    assert r.status_code == EXPLAIN_EXPECTED[actor], r.text


UPLOAD_EXPECTED = {
    "owner": 200,
    "other_talent": 404,
    "respondent": 404,
    "other_coord": 404,
    "unrelated_coord": 404,
    "admin": 404,
    "anonymous": 401,
}


@pytest.mark.parametrize("actor", ACTORS)
def test_attachment_upload_url(client, world, actor):
    r = client.post(
        f"/complaints/{world.complaint['id']}/attachments/upload-url",
        headers=_headers(world, actor),
        json={"filename": "a.pdf", "content_type": "application/pdf", "size_bytes": 209},
    )
    assert r.status_code == UPLOAD_EXPECTED[actor], r.text


@pytest.mark.parametrize("actor", ACTORS)
def test_attachment_register(client, world, actor):
    key = f"complaints/{world.complaint['id']}/{uuid.uuid4()}.pdf"
    r = client.post(
        f"/complaints/{world.complaint['id']}/attachments",
        headers=_headers(world, actor),
        json={"storage_key": key, "mime_type": "application/pdf", "size_bytes": 209},
    )
    assert r.status_code == (201 if actor == "owner" else UPLOAD_EXPECTED[actor]), r.text


@pytest.mark.parametrize("actor", ["respondent", "other_coord", "unrelated_coord", "admin"])
def test_non_talent_cannot_open_complaint_about_someone_elses_subject(client, world, actor):
    r = client.post(
        "/complaints",
        headers=_headers(world, actor),
        json={"subject_type": "ENGAGEMENT", "subject_id": str(world.engagement.id), "description": "Yetkisiz şikayet denemesi."},
    )
    assert r.status_code == 404


def test_anonymous_cannot_open_complaint(client, world):
    r = client.post(
        "/complaints",
        json={"subject_type": "ENGAGEMENT", "subject_id": str(world.engagement.id), "description": "Anonim şikayet denemesi."},
    )
    assert r.status_code == 401


def test_other_coordinator_reads_after_escalation_but_still_no_attachment(client, session, monkeypatch):
    w = make_world(session)
    fake_storage(monkeypatch)
    created = open_complaint(client, w)
    attachment = add_attachment(client, w, created["id"]).json()
    to_escalated(client, w, created["id"])

    r = client.get(f"/complaints/{created['id']}", headers=h(w.coord2))
    assert r.status_code == 200
    assert "description" not in r.json()
    for user in (w.coord2, w.inst_admin, w.coord):
        assert client.get(f"/complaints/{created['id']}/attachments/{attachment['id']}", headers=h(user)).status_code == 404
    assert client.get(f"/complaints/{created['id']}", headers=h(w.unrelated_coord)).status_code == 404
    # Escalated members cannot write an explanation either (single explanation by the respondent).
    r = client.post(f"/complaints/{created['id']}/explanation", headers=h(w.coord2), json={"text": "x"})
    assert r.status_code == 409


# --- admin routes -------------------------------------------------------------

NON_ADMINS = ["owner", "other_talent", "respondent", "other_coord", "unrelated_coord"]


def _admin_requests(world):
    cid = world.complaint["id"]
    return [
        ("GET", "/admin/complaints", None),
        ("GET", f"/admin/complaints/{cid}", None),
        ("GET", f"/admin/complaints/{cid}/attachments/{world.attachment['id']}", None),
        ("POST", f"/admin/complaints/{world.open_complaint['id']}/transitions", {"action": "DISMISS", "reason": "Kapatıldı."}),
    ]


@pytest.mark.parametrize("actor", NON_ADMINS)
@pytest.mark.parametrize("index", range(4))
def test_admin_routes_hidden_from_non_admins(client, world, actor, index):
    method, path, body = _admin_requests(world)[index]
    r = client.request(method, path, headers=_headers(world, actor), json=body)
    assert r.status_code == 404, r.text
    for key in ("items", "has_more", "limit", "offset", "description", "download_url"):
        assert key not in r.json()


@pytest.mark.parametrize("index", range(4))
def test_admin_routes_anonymous_401(client, world, index):
    method, path, body = _admin_requests(world)[index]
    assert client.request(method, path, json=body).status_code == 401


@pytest.mark.parametrize("index", range(4))
def test_admin_routes_allowed_for_platform_admin(client, world, index):
    method, path, body = _admin_requests(world)[index]
    r = client.request(method, path, headers=h(world.admin), json=body)
    assert r.status_code == 200, r.text


# --- AC-S10: admin's PRIVATE evidence access is unchanged ----------------------


def test_admin_still_cannot_download_students_private_evidence(client, session, world):
    evidence = Evidence(
        owner_talent_id=world.talent_a.id,
        kind="DOCUMENT",
        provenance="SELF_UPLOADED",
        visibility="PRIVATE",
        scan_status="CLEAN",
        storage_key=f"evidence/{world.talent_a.id}/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        storage_etag="etag-1",
    )
    session.add(evidence)
    session.flush()
    r = client.get(f"/evidence/{evidence.id}/download-url", headers=h(world.admin))
    assert r.status_code == 403  # unchanged pre-existing behaviour (AUTHORIZATION §4.1)
    assert "download_url" not in r.text


# --- AC-S13: public counter carries only a number ------------------------------


def test_discover_card_leaks_no_complaint_details(client, world):
    r = client.get("/discover/organizations", headers=h(world.user_b))
    assert r.status_code == 200
    assert "Stajım" not in r.text and "Ayşe" not in r.text and "complaint_id" not in r.text
