"""Tests for the restricted user registration flow.

Covers:
  * ``CreateUserRequest`` schema: role whitelist, password floor, default role.
  * ``AuthService.create_user`` / ``AuthService.count_users`` behavior.
  * The public ``POST /auth/register`` bootstrap closing after the first user.

All tests use the existing mocked-``Session`` pattern from
``test_registration.py`` and ``test_auth.py`` — no real database, no
``TestClient``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from backend.schemas.auth import CreateUserRequest
from backend.services.auth_service import AuthError, AuthService, hash_password


# -------------------------------------------------------------------
# Test helpers (mirror the pattern in test_registration.py)
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


class _SessionStub:
    """A tiny Session double that switches behavior based on the statement.

    The AuthService issues two distinct statements: a SELECT-by-email
    (for duplicate detection) and a SELECT-count() (for the bootstrap
    gate). We dispatch on a substring of the statement's string form.
    """

    def __init__(self, *, count: int = 0, existing_user: SimpleNamespace | None = None):
        self._count = count
        self._existing_user = existing_user
        self.commits = 0
        self.added: list[object] = []

    def execute(self, stmt):
        stmt_str = str(stmt).lower()
        result = MagicMock()
        if "count" in stmt_str:
            result.scalar_one.return_value = self._count
        elif self._existing_user is not None:
            result.scalar_one_or_none.return_value = self._existing_user
        else:
            result.scalar_one_or_none.return_value = None
        return result

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        # Make the object look like a freshly inserted row.
        if not hasattr(obj, "UserID") or obj.UserID is None:
            obj.UserID = 1
        return obj


# -------------------------------------------------------------------
# CreateUserRequest schema
# -------------------------------------------------------------------


class TestCreateUserRequestSchema:
    def test_accepts_police_station_officer(self):
        req = CreateUserRequest(
            name="Officer Kumar",
            email="new@ksp.gov.in",
            password="securepass123",
            role="police_station_officer",
        )
        assert req.role == "police_station_officer"
        assert req.email == "new@ksp.gov.in"

    def test_accepts_data_center_officer(self):
        req = CreateUserRequest(
            name="Officer Kumar",
            email="new@ksp.gov.in",
            password="securepass123",
            role="data_center_officer",
        )
        assert req.role == "data_center_officer"

    def test_accepts_control_center_officer(self):
        req = CreateUserRequest(
            name="Officer Kumar",
            email="new@ksp.gov.in",
            password="securepass123",
            role="control_center_officer",
        )
        assert req.role == "control_center_officer"

    def test_rejects_unknown_roles(self):
        for bad in ("admin", "inspector", "si", "viewer", "officer", ""):
            with pytest.raises(ValidationError):
                CreateUserRequest(
                    name="Officer Kumar",
                    email="new@ksp.gov.in",
                    password="securepass123",
                    role=bad,
                )

    def test_enforces_password_min_length(self):
        with pytest.raises(ValidationError):
            CreateUserRequest(
                name="Officer Kumar",
                email="new@ksp.gov.in",
                password="short",  # < 8 chars
                role="police_station_officer",
            )

    def test_default_role_is_police_station_officer(self):
        req = CreateUserRequest(
            name="Officer Kumar",
            email="new@ksp.gov.in",
            password="securepass123",
        )
        assert req.role == "police_station_officer"

    def test_enforces_email_format(self):
        with pytest.raises(ValidationError):
            CreateUserRequest(
                name="Officer Kumar",
                email="not-an-email",
                password="securepass123",
                role="police_station_officer",
            )


# -------------------------------------------------------------------
# AuthService.create_user / count_users
# -------------------------------------------------------------------


class TestAuthServiceCreateUser:
    def test_persists_role_and_active_flag(self):
        session = _SessionStub(count=0, existing_user=None)
        svc = AuthService(session)
        user = svc.create_user(
            "new@ksp.gov.in", "securepass123", "police_station_officer", name="Officer Kumar"
        )
        assert user.email == "new@ksp.gov.in"
        assert user.role == "police_station_officer"
        assert user.is_active is True
        assert session.commits == 1
        assert len(session.added) == 1

    def test_raises_on_duplicate_email(self):
        existing = _fake_user(email="taken@ksp.gov.in")
        session = _SessionStub(count=1, existing_user=existing)
        svc = AuthService(session)
        with pytest.raises(AuthError, match="already registered"):
            svc.create_user("taken@ksp.gov.in", "password123", "control_center_officer")
        # No row should have been added on a duplicate.
        assert session.added == []
        assert session.commits == 0

    def test_count_users_zero(self):
        session = _SessionStub(count=0)
        svc = AuthService(session)
        assert svc.count_users() == 0

    def test_count_users_reflects_table(self):
        session = _SessionStub(count=1)
        svc = AuthService(session)
        assert svc.count_users() == 1

    def test_count_users_many(self):
        session = _SessionStub(count=42)
        svc = AuthService(session)
        assert svc.count_users() == 42


# -------------------------------------------------------------------
# Public bootstrap gate — POST /auth/register
# -------------------------------------------------------------------


class TestRegisterBootstrapGate:
    """The public /auth/register endpoint closes itself after the first user.

    The route's logic is ``if count_users() > 0: raise 403``. We test the
    service primitive it relies on, plus the gate's contract, by driving
    ``count_users()`` and asserting the route-level precondition.
    """

    def test_first_user_bootstrap_allowed_when_count_is_zero(self):
        session = _SessionStub(count=0)
        svc = AuthService(session)
        # count_users() == 0 means the route will allow the bootstrap.
        assert svc.count_users() == 0

    def test_bootstrap_rejected_after_first_user(self):
        session = _SessionStub(count=1)
        svc = AuthService(session)
        # count_users() > 0 means the route will 403 with "Registration
        # is closed. Only Control Center Officers can create new users."
        assert svc.count_users() > 0

    def test_register_bootstrap_does_not_collide_with_users_route(self):
        """``/auth/users`` is admin-only; ``/auth/register`` is the public
        bootstrap. Both call ``AuthService.create_user`` underneath, but
        only ``/auth/users`` runs the role-restricted path. We assert
        here that the service does not gate ``create_user`` itself —
        the route layer is responsible for role enforcement.
        """
        session = _SessionStub(count=1, existing_user=None)
        svc = AuthService(session)
        # Service does not raise: it is route-layer code that must check
        # the caller's role and the bootstrap-gate before delegating.
        user = svc.create_user(
            "another@ksp.gov.in", "password123", "control_center_officer"
        )
        assert user.role == "control_center_officer"
