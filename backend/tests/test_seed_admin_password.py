"""
YET-229 (L-14): seed_admin must not create the platform admin with a guessable
password. Empty, placeholder and short values are rejected; a strong value works.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models import User
from scripts.seed import seed_admin


@pytest.fixture
def admin_email(monkeypatch):
    email = f"seed-admin-{uuid.uuid4().hex[:8]}@yetkin360.local"
    monkeypatch.setattr(settings, "seed_admin_email", email)
    return email


def _admin_exists(session, email: str) -> bool:
    return session.execute(select(User).where(User.email == email)).scalars().first() is not None


def test_settings_have_no_guessable_default_password():
    assert type(settings).model_fields["seed_admin_password"].default == ""


@pytest.mark.parametrize(
    "bad_password",
    ["", "DEGISTIR_admin_parola", "DEGISTIR_baska_bir_deger_uzun", "kisa123"],
)
def test_seed_admin_rejects_weak_password(session, monkeypatch, admin_email, bad_password):
    monkeypatch.setattr(settings, "seed_admin_password", bad_password)

    with pytest.raises(RuntimeError, match="SEED_ADMIN_PASSWORD") as exc:
        seed_admin(session)

    if bad_password:
        assert bad_password not in str(exc.value)  # the secret value is never echoed
    assert not _admin_exists(session, admin_email)


def test_seed_admin_creates_admin_with_strong_password(session, monkeypatch, admin_email):
    monkeypatch.setattr(settings, "seed_admin_password", "Gercek-Guclu-Parola-42!")
    # seed_admin commits; flush instead so the test DB keeps no leftover row.
    monkeypatch.setattr(session, "commit", session.flush)

    seed_admin(session)

    admin = session.execute(select(User).where(User.email == admin_email)).scalars().one()
    assert admin.is_platform_admin is True
