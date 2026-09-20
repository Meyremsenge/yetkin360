"""
Default-deny behavior tests for can() function (AC-S1, AC-6).

Tests that can() returns False for undefined (kind, action) combinations,
for all Principal.kind values. This implements the "default-deny" security model.

Migrated from backend/tests/test_authorization.py::test_can_default_deny_undefined_action (YET-2).
"""

import pytest

from app.models import User
from app.services.authorization import Principal, can


class TestCanDefaultDenyUndefinedAction:
    """AC-S1 / AC-6: can() default-deny for undefined actions."""

    @pytest.mark.parametrize("kind_value", [
        "ANONYMOUS",
        "TALENT",
        "ORG_MEMBER",
        "ORG_ADMIN",
        "ORG_SUPERVISOR",
        "COORDINATOR",
        "INST_ADMIN",
        "PLATFORM_ADMIN",
        "SUSPENDED"
    ])
    def test_can_default_deny_undefined_action(self, session, kind_value):
        """
        AC-S1 / AC-6: can() returns False for undefined action, for all Principal.kind values.

        Implements "default-deny" — if an action is not explicitly defined in can(),
        it must return False. Tests all 9 Principal.kind enum values.
        """
        user = User(email=f"user-{kind_value}@example.com", password_hash="hash")
        session.add(user)
        session.flush()

        principal = Principal(
            user_id=user.id,
            kind=kind_value,
            talent_id=None if kind_value != "TALENT" else "550e8400-e29b-41d4-a716-446655440001",
            org_ids=["550e8400-e29b-41d4-a716-446655440001"] if kind_value in ["ORG_MEMBER", "ORG_ADMIN", "ORG_SUPERVISOR"] else [],
            org_admin_ids=["550e8400-e29b-41d4-a716-446655440001"] if kind_value in ["ORG_ADMIN"] else [],
            institution_ids=["550e8400-e29b-41d4-a716-446655440002"] if kind_value in ["TALENT", "COORDINATOR", "INST_ADMIN"] else [],
            is_platform_admin=(kind_value == "PLATFORM_ADMIN"),
            is_suspended=(kind_value == "SUSPENDED"),
        )

        # Undefined action (should not exist in authorization matrix)
        result = can(principal, "undefined_action_xyz", user)
        assert result is False, f"can() must return False for undefined action, but got {result} for kind={kind_value}"


class TestCanDefaultDenyUnknownResource:
    """can() default-deny for unknown resource types."""

    def test_can_default_deny_unknown_resource_type(self, session):
        """
        AC-S1: can() returns False for resource types not explicitly handled.

        If a resource type (e.g., a hypothetical "Document" class) is not handled
        in can(), it must return False by default.
        """
        user = User(email="user-unknown-resource@example.com", password_hash="hash")
        session.add(user)
        session.flush()

        principal = Principal(
            user_id=user.id,
            kind="TALENT",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[],
            is_platform_admin=False,
            is_suspended=False,
        )

        # Use a dict as a "fake" resource (not a known model)
        fake_resource = {"id": "some-id", "type": "UnknownType"}
        result = can(principal, "read", fake_resource)
        assert result is False, "can() must return False for unknown resource types"
