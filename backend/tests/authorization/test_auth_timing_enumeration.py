"""
YET-183 (GUV-10): e-mail enumeration through response timing.

The expensive step on the identity endpoints is Argon2. If it runs on only one
branch (new vs. existing e-mail on register; known vs. unknown account on login)
the response time tells an attacker whether an address is registered.

These tests are deterministic on purpose: instead of asserting a wall-clock gap
they count how many times the Argon2 primitives run on each branch. Status code
and body must also stay identical (YET-180/186 contract).
"""

import uuid

import pytest
from argon2 import PasswordHasher

from app.core import security
from app.models import User
from app.services import auth as auth_service

_PASSWORD = "Str0ngPassw0rd!"
_WRONG = "Wrong-pass-1!"


class _Counter:
    """Wraps a function and records how many times it was called."""

    def __init__(self, fn):
        self.fn = fn
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.fn(*args, **kwargs)


@pytest.fixture
def hash_calls(monkeypatch):
    counter = _Counter(auth_service.hash_password)
    monkeypatch.setattr(auth_service, "hash_password", counter)
    return counter


@pytest.fixture
def verify_calls(monkeypatch):
    counter = _Counter(auth_service.verify_password)
    monkeypatch.setattr(auth_service, "verify_password", counter)
    return counter


def _email(tag: str) -> str:
    return f"{tag}-{uuid.uuid4().hex[:12]}@example.com"


def _register(client, email: str):
    return client.post(
        "/auth/register", json={"email": email, "password": _PASSWORD, "full_name": "Timing Test"}
    )


def _login(client, email: str, password: str = _WRONG):
    return client.post("/auth/login", json={"email": email, "password": password})


def _body(response) -> dict:
    """Error body without the per-request id."""
    return {k: v for k, v in response.json().items() if k != "request_id"}


def _add_user(session, status: str = "ACTIVE") -> User:
    user = User(
        email=_email("known"), password_hash=security.hash_password(_PASSWORD), status=status
    )
    session.add(user)
    session.flush()
    return user


# ---------------------------------------------------------------- register


def test_register_hashes_once_for_new_and_existing_email(client, hash_calls):
    email = _email("reg")

    first = _register(client, email)
    assert first.status_code == 201
    assert hash_calls.calls == 1

    hash_calls.calls = 0
    second = _register(client, email)
    assert second.status_code == 201
    assert hash_calls.calls == 1


def test_register_responses_have_same_shape_for_new_and_existing_email(client):
    email = _email("reg-shape")
    first = _register(client, email)
    second = _register(client, email)

    assert first.status_code == second.status_code == 201
    assert set(first.json()) == set(second.json()) == {"user_id"}
    # The existing path must not leak the real id.
    assert first.json()["user_id"] != second.json()["user_id"]


def test_register_existing_email_leaves_account_untouched(client, session, hash_calls):
    user = _add_user(session)
    original_hash = user.password_hash

    response = client.post(
        "/auth/register",
        json={"email": user.email, "password": "An0ther-Passw0rd!", "full_name": "Attacker"},
    )

    assert response.status_code == 201
    session.refresh(user)
    assert user.password_hash == original_hash
    assert hash_calls.calls == 1


# ------------------------------------------------------------------- login


def test_login_verifies_once_for_unknown_and_known_account(client, session, verify_calls):
    known = _add_user(session)

    unknown_resp = _login(client, _email("nouser"))
    unknown_calls = verify_calls.calls
    verify_calls.calls = 0
    known_resp = _login(client, known.email)
    known_calls = verify_calls.calls

    assert unknown_calls == known_calls == 1
    assert unknown_resp.status_code == known_resp.status_code == 401
    assert _body(unknown_resp) == _body(known_resp)


@pytest.mark.parametrize("status", ["SUSPENDED", "DELETED"])
def test_login_verifies_once_for_inactive_account(client, session, verify_calls, status):
    user = _add_user(session, status=status)

    response = _login(client, user.email, _PASSWORD)

    assert response.status_code == 401
    assert _body(response) == _body(_login(client, _email("nouser")))
    # Correct password on an inactive account is still rejected, with one verify each call.
    assert verify_calls.calls == 2


def test_login_unknown_account_cannot_succeed_with_dummy_password(client, verify_calls):
    # The dummy comparison must never turn into a successful login.
    response = _login(client, _email("nouser"), password=_PASSWORD)

    assert response.status_code == 401
    assert verify_calls.calls == 1


# ------------------------------------------------------------- dummy hash


def test_dummy_hash_matches_real_hasher_parameters():
    # A weaker dummy hash would itself open a timing gap.
    assert PasswordHasher().check_needs_rehash(auth_service._DUMMY_PASSWORD_HASH) is False
    assert security.verify_password(_WRONG, auth_service._DUMMY_PASSWORD_HASH) is False
