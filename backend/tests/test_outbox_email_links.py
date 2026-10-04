"""
YET-210 (OPS-02): the verify/reset e-mail links pointed at /verify-email and
/reset-password, but the frontend pages live at /e-posta-dogrula and
/sifre-sifirla (no redirect), so every link landed on the not-found page.

The tests resolve the link a user would actually click against the frontend
route tree on disk, so a renamed page or a changed link breaks here instead
of in a user's inbox.
"""

import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from app.core.config import settings
from app.workers import outbox_worker

FRONTEND_APP = Path(__file__).resolve().parents[2] / "frontend" / "app"
ORIGIN = "https://app.example.test"
RAW_TOKEN = "raw-token-value-123"

CASES = [
    ("email.verify_email", outbox_worker.email_verify_email_handler, "/e-posta-dogrula"),
    ("email.password_reset", outbox_worker.email_password_reset_handler, "/sifre-sifirla"),
]


def _extract_link(text: str) -> str:
    match = re.search(r"https?://\S+", text)
    assert match is not None, f"no link found in: {text!r}"
    return match.group(0)


def _assert_link_is_a_real_frontend_route(link: str, expected_path: str) -> None:
    parsed = urlparse(link)
    assert f"{parsed.scheme}://{parsed.netloc}" == ORIGIN
    assert parsed.path == expected_path
    assert parse_qs(parsed.query) == {"token": [RAW_TOKEN]}
    assert (FRONTEND_APP / parsed.path.strip("/") / "page.tsx").is_file()


@pytest.mark.parametrize("topic,handler,expected_path", CASES)
def test_console_backend_link_points_at_existing_frontend_page(
    monkeypatch, capsys, topic, handler, expected_path
):
    monkeypatch.setattr(settings, "frontend_origin", ORIGIN)
    monkeypatch.setattr(settings, "email_backend", "console")

    handler({"user_id": "u-1", "raw_token": RAW_TOKEN}, 1)

    _assert_link_is_a_real_frontend_route(_extract_link(capsys.readouterr().out), expected_path)


@pytest.mark.parametrize("topic,handler,expected_path", CASES)
def test_smtp_body_link_points_at_existing_frontend_page(
    monkeypatch, topic, handler, expected_path
):
    monkeypatch.setattr(settings, "frontend_origin", ORIGIN)
    monkeypatch.setattr(settings, "email_backend", "smtp")
    monkeypatch.setattr(outbox_worker, "_resolve_user_email", lambda user_id: "user@example.test")
    sent: list[dict] = []
    monkeypatch.setattr(
        outbox_worker,
        "_send_smtp_email",
        lambda to_email, subject, body: sent.append({"to": to_email, "body": body}),
    )

    handler({"user_id": "u-1", "raw_token": RAW_TOKEN}, 1)

    assert len(sent) == 1
    assert sent[0]["to"] == "user@example.test"
    _assert_link_is_a_real_frontend_route(_extract_link(sent[0]["body"]), expected_path)
