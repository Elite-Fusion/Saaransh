"""Authentication service — JWT, password hashing, user lookup.

This module is intentionally **FastAPI-independent** so it can be used
from CLI scripts, tests, and AI call-sites.  The API layer wraps
these helpers into FastAPI dependencies and routes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from backend.config.settings import settings
from backend.models.ai import Users
from backend.services.base import BaseService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------- Exceptions ----------


class AuthError(Exception):
    """Raised for authentication failures (bad credentials, expired token, etc.)."""

    def __init__(self, message: str = "Authentication failed") -> None:
        self.message = message
        super().__init__(self.message)


class ForbiddenError(Exception):
    """Raised when a valid user lacks the required role."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        self.message = message
        super().__init__(self.message)


# ---------- Password hashing ----------


def hash_password(plain: str) -> str:
    """Return the bcrypt hash of *plain*."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return pwd_context.verify(plain, hashed)


# ---------- JWT helpers (module-level, no DB needed) ----------


def create_access_token(subject: int, role: str) -> str:
    """Create a short-lived access token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: int) -> str:
    """Create a long-lived refresh token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": str(subject),
        "type": "refresh",
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT.  Raises AuthError on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise AuthError(f"Invalid token: {exc}") from exc
    if payload.get("sub") is None:
        raise AuthError("Token missing 'sub' claim")
    return payload


# ---------- Service class ----------


class AuthService(BaseService):
    """User lookup and authentication against the database."""

    def authenticate_user(self, email: str, password: str) -> Users:
        """Verify credentials and return the Users row.

        Raises AuthError on invalid credentials or inactive account.
        """
        stmt = select(Users).where(Users.email == email)
        user = self.session.execute(stmt).scalar_one_or_none()

        if user is None:
            raise AuthError("Invalid email or password")

        if not verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")

        if not user.is_active:
            raise AuthError("Account is deactivated")

        return user

    def get_user_by_id(self, user_id: int) -> Users | None:
        """Fetch a user by primary key."""
        stmt = select(Users).where(Users.UserID == user_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_user_by_email(self, email: str) -> Users | None:
        """Fetch a user by email."""
        stmt = select(Users).where(Users.email == email)
        return self.session.execute(stmt).scalar_one_or_none()

    def create_user(self, email: str, password: str, role: str, name: str | None = None) -> Users:
        """Create a new user.  Raises AuthError if email already exists."""
        if self.get_user_by_email(email):
            raise AuthError("Email already registered")

        user = Users(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def count_users(self) -> int:
        """Return the total number of users."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(Users)
        return self.session.execute(stmt).scalar_one()
