"""Pydantic models for authentication and user management."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Allowed roles ----------

ALLOWED_ROLES = Literal[
    "police_station_officer",
    "data_center_officer",
    "control_center_officer",
]


# ---------- Request models ----------


class LoginRequest(BaseModel):
    """Body for POST /auth/login."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """Body for POST /auth/refresh."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(..., min_length=1)


class CreateUserRequest(BaseModel):
    """Body for POST /auth/users (control_center_officer only)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: ALLOWED_ROLES = "police_station_officer"


class RegisterRequest(BaseModel):
    """Body for POST /auth/register (unauthenticated, first user only)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    role: ALLOWED_ROLES


# ---------- Response models ----------


class TokenResponse(BaseModel):
    """Access + refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    """Public user profile returned by GET /auth/me."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: int = Field(..., alias="UserID")
    name: str | None = None
    email: str
    role: str
    is_active: bool
    last_login: datetime | None = None


class RegisterResponse(BaseModel):
    """Response after successful registration."""

    message: str
    user_id: int


class UserApprovalRequest(BaseModel):
    """Request to approve or reject a user."""

    user_id: int = Field(..., gt=0)
    action: Literal["approve", "reject"] = Field(
        ..., description="Action to perform: 'approve' or 'reject'"
    )
    notes: str | None = Field(
        None, max_length=500, description="Optional notes for the action"
    )


class UserListResponse(BaseModel):
    """Response for listing users."""

    users: list[UserOut]
    total: int
