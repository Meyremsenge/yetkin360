"""
PLAN 3.51: attestation.created ve engagement.pending_approval için outbox
handler'ları — ikisi de servis katmanında PLAN 2.8/T1 geçişinden beri
kuyruğa ekleniyordu ama DEFAULT_HANDLERS'da hiç kayıtlı değildi, bu yüzden
worker sonsuza kadar çalışsa bile seçilmiyordu (process_batch yalnız
handler'ı olan topic'leri çeker).
"""

from pathlib import Path

import pytest

from app.core.config import settings
from app.workers import outbox_worker

FRONTEND_APP = Path(__file__).resolve().parents[2] / "frontend" / "app"

ATTESTATION_PAYLOAD = {
    "attestation_id": "att-1",
    "engagement_id": "eng-1",
    "talent_id": "talent-1",
    "claim_type": "COMPETENCE",
    "downgrade_reasons": [],
}

ENGAGEMENT_PAYLOAD = {
    "engagement_id": "eng-2",
    "talent_id": "talent-2",
    "organization_id": "org-1",
    "institution_id": "inst-1",
}


class TestHandlerRegistration:
    def test_attestation_created_is_registered(self):
        assert (
            outbox_worker.DEFAULT_HANDLERS["attestation.created"]
            is outbox_worker.attestation_created_handler
        )

    def test_engagement_pending_approval_is_registered(self):
        assert (
            outbox_worker.DEFAULT_HANDLERS["engagement.pending_approval"]
            is outbox_worker.engagement_pending_approval_handler
        )


class TestAttestationCreatedHandler:
    @pytest.mark.parametrize(
        "claim_type,label",
        [("COMPETENCE", "Yetkinlik"), ("PARTICIPATION", "Katılım"), ("CONTRIBUTION", "Katkı"), ("CONDUCT", "Davranış")],
    )
    def test_smtp_mail_goes_to_the_talent_with_claim_type_label_and_engagement_link(
        self, monkeypatch, claim_type, label
    ):
        monkeypatch.setattr(settings, "frontend_origin", "https://app.example.test")
        monkeypatch.setattr(settings, "email_backend", "smtp")
        monkeypatch.setattr(outbox_worker, "_resolve_talent_user_email", lambda talent_id: "talent@example.test")
        sent: list[dict] = []
        monkeypatch.setattr(
            outbox_worker,
            "_send_smtp_email",
            lambda to_email, subject, body: sent.append({"to": to_email, "subject": subject, "body": body}),
        )

        outbox_worker.attestation_created_handler({**ATTESTATION_PAYLOAD, "claim_type": claim_type}, 1)

        assert len(sent) == 1
        assert sent[0]["to"] == "talent@example.test"
        assert sent[0]["subject"] == "Yetkin360 - Çalışmanız doğrulandı"
        assert label in sent[0]["body"]
        assert "https://app.example.test/calismalar/eng-1" in sent[0]["body"]
        assert (FRONTEND_APP / "calismalar" / "[id]" / "page.tsx").is_file()

    def test_unknown_talent_is_skipped_without_sending(self, monkeypatch):
        monkeypatch.setattr(settings, "email_backend", "smtp")
        monkeypatch.setattr(outbox_worker, "_resolve_talent_user_email", lambda talent_id: None)
        sent: list = []
        monkeypatch.setattr(outbox_worker, "_send_smtp_email", lambda **kw: sent.append(kw))

        outbox_worker.attestation_created_handler(ATTESTATION_PAYLOAD, 1)

        assert sent == []

    def test_console_backend_prints_no_address_and_does_not_resolve_the_talent(self, monkeypatch, capsys):
        monkeypatch.setattr(settings, "email_backend", "console")

        def must_not_be_called(talent_id):
            raise AssertionError("console backend must not look the talent up")

        monkeypatch.setattr(outbox_worker, "_resolve_talent_user_email", must_not_be_called)

        outbox_worker.attestation_created_handler(ATTESTATION_PAYLOAD, 7)

        out = capsys.readouterr().out
        assert "outbox_id=7" in out
        assert "@" not in out


class TestEngagementPendingApprovalHandler:
    def test_smtp_mail_goes_to_every_coordinator_of_the_institution(self, monkeypatch):
        monkeypatch.setattr(settings, "frontend_origin", "https://app.example.test")
        monkeypatch.setattr(settings, "email_backend", "smtp")
        monkeypatch.setattr(
            outbox_worker,
            "_resolve_institution_coordinator_emails",
            lambda institution_id: ["coord1@example.test", "coord2@example.test"],
        )
        sent: list[dict] = []
        monkeypatch.setattr(
            outbox_worker,
            "_send_smtp_email",
            lambda to_email, subject, body: sent.append({"to": to_email, "subject": subject, "body": body}),
        )

        outbox_worker.engagement_pending_approval_handler(ENGAGEMENT_PAYLOAD, 1)

        assert {s["to"] for s in sent} == {"coord1@example.test", "coord2@example.test"}
        assert all(s["subject"] == "Yetkin360 - Onay bekleyen bir çalışma var" for s in sent)
        assert all("https://app.example.test/calismalar/eng-2" in s["body"] for s in sent)

    def test_chosen_coordinators_alone_receive_the_mail(self, monkeypatch):
        monkeypatch.setattr(settings, "frontend_origin", "https://app.example.test")
        monkeypatch.setattr(settings, "email_backend", "smtp")
        asked: list[tuple] = []

        def selected(institution_id, user_ids):
            asked.append((institution_id, user_ids))
            return ["coord2@example.test"]

        def everyone(institution_id):
            raise AssertionError("every coordinator must not be resolved when a chosen one exists")

        monkeypatch.setattr(outbox_worker, "_resolve_selected_coordinator_emails", selected)
        monkeypatch.setattr(outbox_worker, "_resolve_institution_coordinator_emails", everyone)
        sent: list[str] = []
        monkeypatch.setattr(outbox_worker, "_send_smtp_email", lambda to_email, subject, body: sent.append(to_email))

        outbox_worker.engagement_pending_approval_handler({**ENGAGEMENT_PAYLOAD, "notify_user_ids": ["user-2"]}, 1)

        assert asked == [("inst-1", ["user-2"])]
        assert sent == ["coord2@example.test"]

    def test_chosen_coordinator_no_longer_a_member_falls_back_to_everyone(self, monkeypatch):
        monkeypatch.setattr(settings, "email_backend", "smtp")
        monkeypatch.setattr(outbox_worker, "_resolve_selected_coordinator_emails", lambda institution_id, user_ids: [])
        monkeypatch.setattr(
            outbox_worker, "_resolve_institution_coordinator_emails", lambda institution_id: ["coord1@example.test"]
        )
        sent: list[str] = []
        monkeypatch.setattr(outbox_worker, "_send_smtp_email", lambda to_email, subject, body: sent.append(to_email))

        outbox_worker.engagement_pending_approval_handler({**ENGAGEMENT_PAYLOAD, "notify_user_ids": ["gone"]}, 1)

        assert sent == ["coord1@example.test"]

    def test_no_coordinators_sends_nothing(self, monkeypatch):
        monkeypatch.setattr(settings, "email_backend", "smtp")
        monkeypatch.setattr(outbox_worker, "_resolve_institution_coordinator_emails", lambda institution_id: [])
        sent: list = []
        monkeypatch.setattr(outbox_worker, "_send_smtp_email", lambda **kw: sent.append(kw))

        outbox_worker.engagement_pending_approval_handler(ENGAGEMENT_PAYLOAD, 1)

        assert sent == []

    def test_console_backend_prints_no_address_and_does_not_resolve_coordinators(self, monkeypatch, capsys):
        monkeypatch.setattr(settings, "email_backend", "console")

        def must_not_be_called(institution_id):
            raise AssertionError("console backend must not look coordinators up")

        monkeypatch.setattr(outbox_worker, "_resolve_institution_coordinator_emails", must_not_be_called)

        outbox_worker.engagement_pending_approval_handler(ENGAGEMENT_PAYLOAD, 9)

        out = capsys.readouterr().out
        assert "outbox_id=9" in out
        assert "@" not in out
