"""
The /admin router gate (require_platform_admin) is structural, not per-handler.

These tests are generated from the live route table, so an admin endpoint added
later is covered without anyone remembering to add a row — and a route mounted
under /admin without the gate fails the build.
"""

import uuid

import pytest
from fastapi.routing import APIRoute

from app.api.admin import require_platform_admin
from app.main import app
from app.models import User

ADMIN_ROUTES = [
    route for route in app.routes if isinstance(route, APIRoute) and route.path.startswith("/admin")
]
ROUTE_CASES = [
    pytest.param(method, route.path, id=f"{method} {route.path}")
    for route in ADMIN_ROUTES
    for method in sorted(route.methods)
]


def _concrete(path: str) -> str:
    """Fill path parameters with a random id — the gate must answer before any lookup."""
    return "/".join(str(uuid.uuid4()) if part.startswith("{") else part for part in path.split("/"))


def _user(session, email: str, **fields) -> User:
    user = User(email=email, password_hash="hash", **fields)
    session.add(user)
    session.flush()
    return user


def test_admin_routes_exist():
    assert len(ADMIN_ROUTES) >= 10


@pytest.mark.parametrize("route", ADMIN_ROUTES, ids=lambda route: route.path)
def test_every_admin_route_carries_the_gate(route):
    assert any(dep.call is require_platform_admin for dep in route.dependant.dependencies), (
        f"{route.path} is under /admin but not behind require_platform_admin"
    )


@pytest.mark.parametrize("method,path", ROUTE_CASES)
def test_anonymous_gets_401(client, method, path):
    assert client.request(method, _concrete(path), json={}).status_code == 401


@pytest.mark.parametrize("method,path", ROUTE_CASES)
def test_non_admin_gets_404_not_403(client, session, method, path):
    user = _user(session, "plain@example.com")
    response = client.request(method, _concrete(path), json={}, headers={"X-Debug-User-Id": str(user.id)})
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.unverified_users
@pytest.mark.parametrize("method,path", ROUTE_CASES)
def test_unverified_email_order_is_unchanged(client, session, method, path):
    """G6: a write answers the unverified e-mail first (401); a read goes straight to the admin check (404)."""
    user = _user(session, "unverified@example.com")
    response = client.request(method, _concrete(path), json={}, headers={"X-Debug-User-Id": str(user.id)})
    if method == "GET":
        assert response.status_code == 404
    else:
        assert response.status_code == 401
        assert response.json()["code"] == "EMAIL_NOT_VERIFIED"


@pytest.mark.parametrize("method,path", ROUTE_CASES)
def test_admin_passes_the_gate(client, session, method, path):
    """An admin gets past the gate: the answer comes from the handler (never the gate's 404 body on a list route)."""
    admin = _user(session, "gate-admin@example.com", is_platform_admin=True)
    response = client.request(method, _concrete(path), json={}, headers={"X-Debug-User-Id": str(admin.id)})
    assert response.status_code != 401
    if "{" not in path and method == "GET":
        assert response.status_code == 200
