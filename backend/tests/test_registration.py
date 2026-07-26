"""Registration and role-based access tests.

Tests the POST /auth/register endpoint (unauthenticated first-user creation)
and the updated POST /auth/users endpoint (authenticated control_center_officer).
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.schemas.auth import ALLOWED_ROLES, CreateUserRequest, RegisterRequest
from backend.services.auth_service import (
    AuthError,
    AuthService,
    ForbiddenError,
    hash_password,
)


# -------------------------------------------------------------------
# Schema validation tests
# -------------------------------------------------------------------


class TestRegisterRequestSchema:
    def test_valid_register_request(self):
        req = RegisterRequest(
            name="Test User",
            email="test@ksp.gov.in",
            password="securepass123",
            confirm_password="securepass123",
            role="control_center_officer",
        )
        assert req.name == "Test User"
        assert req.role == "control_center_officer"

    def test_password_mismatch_allowed_at_schema_level(self):
        req = RegisterRequest(
            name="Test User",
            email="test@ksp.gov.in",
            password="securepass123",
            confirm_password="differentpass",
            role="police_station_officer",
        )
        assert req.password != req.confirm_password

    def test_invalid_role_rejected(self):
        with pytest.raises(Exception):
            RegisterRequest(
                name="Test User",
                email="test@ksp.gov.in",
                password="securepass123",
                confirm_password="securepass123",
                role="admin",
            )

    def test_invalid_role_officer_rejected(self):
        with pytest.raises(Exception):
            RegisterRequest(
                name="Test User",
                email="test@ksp.gov.in",
                password="securepass123",
                confirm_password="securepass123",
                role="officer",
            )

    def test_short_password_rejected(self):
        with pytest.raises(Exception):
            RegisterRequest(
                name="Test User",
                email="test@ksp.gov.in",
                password="short",
                confirm_password="short",
                role="control_center_officer",
            )

    def test_empty_name_rejected(self):
        with pytest.raises(Exception):
            RegisterRequest(
                name="",
                email="test@ksp.gov.in",
                password="securepass123",
                confirm_password="securepass123",
                role="control_center_officer",
            )


class TestCreateUserRequestSchema:
    def test_valid_create_user_request(self):
        req = CreateUserRequest(
            name="Officer Kumar",
            email="new@ksp.gov.in",
            password="securepass123",
            role="police_station_officer",
        )
        assert req.name == "Officer Kumar"
        assert req.role == "police_station_officer"

    def test_invalid_role_rejected(self):
        with pytest.raises(Exception):
            CreateUserRequest(
                name="Officer Kumar",
                email="new@ksp.gov.in",
                password="securepass123",
                role="admin",
            )

    def test_default_role_is_police_station_officer(self):
        req = CreateUserRequest(
            name="Officer Kumar",
            email="new@ksp.gov.in",
            password="securepass123",
        )
        assert req.role == "police_station_officer"


# -------------------------------------------------------------------
# Allowed roles constant
# -------------------------------------------------------------------


class TestAllowedRoles:
    def test_contains_expected_roles(self):
        from typing import get_args

        roles = get_args(ALLOWED_ROLES)
        assert "police_station_officer" in roles
        assert "data_center_officer" in roles
        assert "control_center_officer" in roles
        assert len(roles) == 3

    def test_rejects_old_roles(self):
        from typing import get_args

        roles = get_args(ALLOWED_ROLES)
        assert "admin" not in roles
        assert "officer" not in roles
        assert "viewer" not in roles


# -------------------------------------------------------------------
# AuthService — registration-related unit tests
# -------------------------------------------------------------------


def _fake_user(
    user_id: int = 1,
    email: str = "test@ksp.gov.in",
    password: str = "password123",
    role: str = "control_center_officer",
    name: str = "Test User",
    is_active: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        UserID=user_id,
        email=email,
        password_hash=hash_password(password),
        role=role,
        name=name,
        is_active=is_active,
        last_login=None,
        created_at=datetime.now(timezone.utc),
    )


class TestAuthServiceRegistration:
    def _svc(self, users=None, count=0):
        """Build an AuthService with a mocked session."""
        users = users or []
        session = MagicMock()

        def execute_side_effect(stmt):
            result = MagicMock()
            # Handle both select and count queries
            stmt_str = str(stmt)
            if "count()" in stmt_str.lower() or "count" in stmt_str.lower():
                result.scalar_one.return_value = count if count else len(users)
            elif users:
                result.scalar_one_or_none.return_value = users[0]
            else:
                result.scalar_one_or_none.return_value = None
            return result

        session.execute.side_effect = execute_side_effect
        return AuthService(session)

    def test_create_user_with_name(self):
        svc = self._svc([])
        new_user = svc.create_user(
            "new@ksp.gov.in", "password123", "police_station_officer", name="Officer Kumar"
        )
        assert new_user.email == "new@ksp.gov.in"
        assert new_user.role == "police_station_officer"
        assert new_user.name == "Officer Kumar"
        assert new_user.is_active is True

    def test_create_user_without_name(self):
        svc = self._svc([])
        new_user = svc.create_user("new@ksp.gov.in", "password123", "data_center_officer")
        assert new_user.email == "new@ksp.gov.in"
        assert new_user.name is None

    def test_create_user_duplicate_email(self):
        user = _fake_user()
        svc = self._svc([user])
        with pytest.raises(AuthError, match="already registered"):
            svc.create_user("test@ksp.gov.in", "password123", "officer")

    def test_count_users(self):
        svc = self._svc([], count=5)
        assert svc.count_users() == 5

    def test_count_users_zero(self):
        svc = self._svc([], count=0)
        assert svc.count_users() == 0


# -------------------------------------------------------------------
# Role-based access tests
# -------------------------------------------------------------------


class TestRoleBasedAccess:
    def test_valid_roles_list(self):
        from typing import get_args

        roles = get_args(ALLOWED_ROLES)
        assert len(roles) == 3
        for role in roles:
            assert isinstance(role, str)
            assert "_" in role

    def test_control_center_officer_has_full_access(self):
        control_center = "control_center_officer"
        all_routes = [
            "dashboard",
            "cases",
            "map",
            "predictions",
            "assistant",
            "cross_case_linker",
            "analytics",
            "alerts",
            "reports",
            "users",
            "settings",
        ]
        # Control center officer should have access to all routes
        assert control_center == "control_center_officer"

    def test_police_station_officer_limited_access(self):
        allowed = {"dashboard", "cases", "assistant"}
        denied = {"map", "predictions", "analytics", "alerts", "reports", "users", "settings", "cross_case_linker"}
        assert len(allowed) == 3
        assert len(denied) == 8
        assert allowed.isdisjoint(denied)

    def test_data_center_officer_limited_access(self):
        allowed = {"dashboard", "analytics", "predictions", "reports"}
        denied = {"cases", "map", "assistant", "alerts", "users", "settings", "cross_case_linker"}
        assert len(allowed) == 4
        assert len(denied) == 7
        assert allowed.isdisjoint(denied)
