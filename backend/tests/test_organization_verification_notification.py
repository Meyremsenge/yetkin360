"""O2: verification decision -> outbox event (same transaction) -> notification to org ADMINs."""

import pytest

from app.core.config import settings
from app.models import Organization, Outbox
from app.services import organization as org_service
from app.workers import outbox_worker

TOPIC = "organization.verification_decided"


def _org(session, level="T2"):
    org = Organization(name="Bildirim Kurulusu", verification_level=level, legal_id="LID-O2")
    session.add(org)
    session.flush()
    return org


def _events(session, org):
    rows = session.query(Outbox).filter(Outbox.topic == TOPIC).all()
    return [r for r in rows if r.payload.get("organization_id") == str(org.id)]


def test_raise_enqueues_approved_event_with_ids_only(session):
    org = _org(session)
    org_service.set_verification_level(session, org.id, "T3", admin_user_id=None)
    events = _events(session, org)
    assert len(events) == 1
    assert events[0].payload == {
        "organization_id": str(org.id),
        "decision": "APPROVED",
        "verification_level": "T3",
    }


@pytest.mark.parametrize("new_level", ["T2", "T1"])
def test_same_level_or_downgrade_enqueues_nothing(session, new_level):
    org = _org(session)
    org_service.set_verification_level(session, org.id, new_level, admin_user_id=None)
    assert _events(session, org) == []


def test_reject_enqueues_rejected_event_without_note_or_address(session):
    org = _org(session)
    org_service.reject_verification(session, org.id)
    events = _events(session, org)
    assert len(events) == 1
    assert events[0].payload == {"organization_id": str(org.id), "decision": "REJECTED"}


def test_reject_not_pending_enqueues_nothing(session):
    org = _org(session, level="T1")
    with pytest.raises(org_service.NotPendingError):
        org_service.reject_verification(session, org.id)
    assert _events(session, org) == []


def test_handler_registered():
    assert outbox_worker.DEFAULT_HANDLERS[TOPIC] is outbox_worker.organization_verification_decided_handler


@pytest.mark.parametrize("decision,fragment", [("APPROVED", "onaylandı"), ("REJECTED", "reddedildi")])
def test_handler_mails_every_org_admin(monkeypatch, decision, fragment):
    monkeypatch.setattr(settings, "email_backend", "smtp")
    monkeypatch.setattr(
        outbox_worker, "_resolve_organization_admin_recipients", lambda oid: ("Acme", ["a@x.test", "b@x.test"])
    )
    sent = []
    monkeypatch.setattr(
        outbox_worker, "_send_smtp_email", lambda to_email, subject, body: sent.append((to_email, subject, body))
    )
    outbox_worker.organization_verification_decided_handler({"organization_id": "o-1", "decision": decision}, 1)
    assert [s[0] for s in sent] == ["a@x.test", "b@x.test"]
    assert fragment in sent[0][1] and "Acme" in sent[0][2]


def test_handler_skips_when_no_admin_or_unknown_org(monkeypatch):
    monkeypatch.setattr(settings, "email_backend", "smtp")
    sent = []
    monkeypatch.setattr(outbox_worker, "_send_smtp_email", lambda **kw: sent.append(kw))
    monkeypatch.setattr(outbox_worker, "_resolve_organization_admin_recipients", lambda oid: ("Acme", []))
    outbox_worker.organization_verification_decided_handler({"organization_id": "o", "decision": "APPROVED"}, 1)
    monkeypatch.setattr(outbox_worker, "_resolve_organization_admin_recipients", lambda oid: (None, ["a@x.test"]))
    outbox_worker.organization_verification_decided_handler({"organization_id": "o", "decision": "APPROVED"}, 1)
    assert sent == []


def test_console_backend_does_not_resolve_recipients(monkeypatch, capsys):
    monkeypatch.setattr(settings, "email_backend", "console")

    def boom(oid):
        raise AssertionError("console must not resolve recipients")

    monkeypatch.setattr(outbox_worker, "_resolve_organization_admin_recipients", boom)
    outbox_worker.organization_verification_decided_handler({"organization_id": "o", "decision": "REJECTED"}, 9)
    out = capsys.readouterr().out
    assert "outbox_id=9" in out and "@" not in out
