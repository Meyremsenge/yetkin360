"""Organization-invite e-mail handler (topic email.organization_member_invited)."""

from pathlib import Path

import pytest

from app.core.config import settings
from app.workers import outbox_worker

FRONTEND_APP = Path(__file__).resolve().parents[2] / "frontend" / "app"
PAYLOAD = {
    "user_id": "u-1",
    "organization_id": "o-1",
    "organization_name": "Acme Teknoloji",
    "role": "ADMIN",
}


def test_handler_is_registered_for_the_topic():
    assert (
        outbox_worker.DEFAULT_HANDLERS["email.organization_member_invited"]
        is outbox_worker.email_organization_member_invited_handler
    )


@pytest.mark.parametrize("role,label", [("ADMIN", "yönetici"), ("MEMBER", "üye")])
def test_smtp_mail_goes_to_the_invited_user_with_org_name_role_label_and_real_login_link(
    monkeypatch, role, label
):
    monkeypatch.setattr(settings, "frontend_origin", "https://app.example.test")
    monkeypatch.setattr(settings, "email_backend", "smtp")
    monkeypatch.setattr(outbox_worker, "_resolve_user_email", lambda user_id: "invited@example.test")
    sent: list[dict] = []
    monkeypatch.setattr(
        outbox_worker,
        "_send_smtp_email",
        lambda to_email, subject, body: sent.append({"to": to_email, "subject": subject, "body": body}),
    )

    outbox_worker.email_organization_member_invited_handler({**PAYLOAD, "role": role}, 1)

    assert len(sent) == 1
    assert sent[0]["to"] == "invited@example.test"
    assert sent[0]["subject"] == "Yetkin360 - Bir kuruluşa eklendiniz"
    assert f"Acme Teknoloji kuruluşuna {label} olarak eklendiniz." in sent[0]["body"]
    assert "https://app.example.test/giris" in sent[0]["body"]
    assert (FRONTEND_APP / "giris" / "page.tsx").is_file()


def test_unknown_user_is_skipped_without_sending(monkeypatch):
    monkeypatch.setattr(settings, "email_backend", "smtp")
    monkeypatch.setattr(outbox_worker, "_resolve_user_email", lambda user_id: None)
    sent: list = []
    monkeypatch.setattr(outbox_worker, "_send_smtp_email", lambda **kw: sent.append(kw))

    outbox_worker.email_organization_member_invited_handler(PAYLOAD, 1)

    assert sent == []


def test_console_backend_prints_no_address_and_does_not_resolve_the_user(monkeypatch, capsys):
    monkeypatch.setattr(settings, "email_backend", "console")

    def must_not_be_called(user_id):
        raise AssertionError("console backend must not look the user up")

    monkeypatch.setattr(outbox_worker, "_resolve_user_email", must_not_be_called)

    outbox_worker.email_organization_member_invited_handler(PAYLOAD, 7)

    out = capsys.readouterr().out
    assert "outbox_id=7" in out
    assert "@" not in out
