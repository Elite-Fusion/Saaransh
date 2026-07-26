"""Auth service unit tests — password hashing, JWT, user lookup."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.services.auth_service import (
    AuthError,
    AuthService,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


# -------------------------------------------------------------------
# Password hashing
# -------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_and_verify(self):
        plain = "supersecret"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False


# -------------------------------------------------------------------
# JWT helpers
# -------------------------------------------------------------------


class TestJWT:
    def test_access_token_roundtrip(self):
        token = create_access_token(subject=42, role="officer")
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["role"] == "officer"
        assert payload["type"] == "access"

    def test_refresh_token_roundtrip(self):
        token = create_refresh_token(subject=7)
        payload = decode_token(token)
        assert payload["sub"] == "7"
        assert payload["type"] == "refresh"

    def test_invalid_token_raises(self):
        with pytest.raises(AuthError, match="Invalid token"):
            decode_token("garbage.token.value")


# -------------------------------------------------------------------
# AuthService — unit tests with mocked session
# -------------------------------------------------------------------


def _fake_user(
    user_id: int = 1,
    email: str = "test@ksp.gov.in",
    password: str = "password123",
    role: str = "officer",
    is_active: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        UserID=user_id,
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
        last_login=None,
        created_at=datetime.now(timezone.utc),
    )


class TestAuthService:
    def _svc(self, users=None):
        """Build an AuthService with a mocked session."""
        users = users or []
        session = MagicMock()
        result = MagicMock()
        # simulate session.execute(...).scalar_one_or_none()
        if users:
            result.scalar_one_or_none.return_value = users[0]
        else:
            result.scalar_one_or_none.return_value = None
        session.execute.return_value = result
        return AuthService(session)

    def test_authenticate_user_success(self):
        user = _fake_user()
        svc = self._svc([user])
        result = svc.authenticate_user("test@ksp.gov.in", "password123")
        assert result.UserID == 1

    def test_authenticate_user_wrong_password(self):
        user = _fake_user(password="correct")
        svc = self._svc([user])
        with pytest.raises(AuthError, match="Invalid email or password"):
            svc.authenticate_user("test@ksp.gov.in", "wrong")

    def test_authenticate_user_not_found(self):
        svc = self._svc([])
        with pytest.raises(AuthError, match="Invalid email or password"):
            svc.authenticate_user("nobody@ksp.gov.in", "pass")

    def test_authenticate_inactive_user(self):
        user = _fake_user(is_active=False)
        svc = self._svc([user])
        with pytest.raises(AuthError, match="deactivated"):
            svc.authenticate_user("test@ksp.gov.in", "password123")

    def test_get_user_by_id_found(self):
        user = _fake_user()
        svc = self._svc([user])
        assert svc.get_user_by_id(1) is user

    def test_get_user_by_id_not_found(self):
        svc = self._svc([])
        assert svc.get_user_by_id(999) is None

    def test_create_user_duplicate_email(self):
        user = _fake_user()
        svc = self._svc([user])
        with pytest.raises(AuthError, match="already registered"):
            svc.create_user("test@ksp.gov.in", "password123", "officer")

    def test_create_user_success(self):
        svc = self._svc([])
        new_user = svc.create_user("new@ksp.gov.in", "password123", "admin")
        assert new_user.email == "new@ksp.gov.in"
        assert new_user.role == "admin"
        assert new_user.is_active is True
