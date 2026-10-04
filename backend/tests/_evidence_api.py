"""Shared helpers for the evidence API tests (YET-195 list, YET-184 registration)."""

import uuid

from fastapi.testclient import TestClient

from app.core.security import encode_access_token
from app.models import Evidence, User

CSRF = {"X-CSRF-Token": "test-csrf-token"}


def login(client: TestClient, user: User) -> None:
    client.cookies.set("access_token", encode_access_token(user.id))
    client.cookies.set("csrf_token", "test-csrf-token")


def add_evidence(session, talent, **overrides) -> Evidence:
    values = dict(
        owner_talent_id=talent.id,
        kind="DOCUMENT",
        provenance="SELF_UPLOADED",
        visibility="PRIVATE",
        scan_status="PENDING",
        storage_key=f"evidence/{talent.id}/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        size_bytes=100,
    )
    values.update(overrides)
    ev = Evidence(**values)
    session.add(ev)
    session.flush()
    return ev


def body(talent, **overrides) -> dict:
    body = {
        "storage_key": f"evidence/{talent.id}/{uuid.uuid4()}.pdf",
        "kind": "DOCUMENT",
        "mime_type": "application/pdf",
        "size_bytes": 1024,
    }
    body.update(overrides)
    return body
