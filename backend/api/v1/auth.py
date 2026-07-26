"""Auth API — login, logout, refresh, current user, registration."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.v1 import examples
from backend.api.v1.openapi import code_samples, standard_error_responses
from backend.database.session import get_db
from backend.middleware.auth import get_current_user, require_role
from backend.models.ai import Users
from backend.schemas.auth import (
    CreateUserRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserOut,
)
from backend.services.auth_service import (
    AuthError,
    AuthService,
    ForbiddenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user",
    description="Authenticate with email + password. Returns access + refresh tokens.",
    responses=standard_error_responses(
        success_model=TokenResponse,
        success_examples={"success": examples.EXAMPLE_AUTH_LOGIN_SUCCESS},
        success_description="Login successful. Use the access_token for subsequent requests.",
        include_not_found=False,
        bad_request_examples={
            "invalid": examples.EXAMPLE_AUTH_LOGIN_INVALID,
            "deactivated": examples.EXAMPLE_AUTH_LOGIN_DEACTIVATED,
        },
        bad_request_description="Invalid credentials or deactivated account.",
        include_validation=True,
    ),
    openapi_extra=code_samples(
        {"lang": "curl", "source": "curl -X POST http://localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' -d '{\"email\": \"officer@ksp.gov.in\", \"password\": \"secret\"}'"}
    ),
)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email + password.  Returns access + refresh tokens."""
    svc = AuthService(db)
    try:
        user = svc.authenticate_user(body.email, body.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    access_token = create_access_token(user.UserID, user.role)
    refresh_token = create_refresh_token(user.UserID)

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new token pair.",
    responses=standard_error_responses(
        success_model=TokenResponse,
        success_examples={"success": examples.EXAMPLE_AUTH_REFRESH_SUCCESS},
        success_description="New token pair issued.",
        include_not_found=False,
        bad_request_examples={
            "invalid": examples.EXAMPLE_AUTH_REFRESH_INVALID,
        },
        bad_request_description="Invalid or expired refresh token.",
        include_validation=True,
    ),
    openapi_extra=code_samples(
        {"lang": "curl", "source": "curl -X POST http://localhost:8000/api/v1/auth/refresh -H 'Content-Type: application/json' -d '{\"refresh_token\": \"eyJ...\"}'"}
    ),
)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new token pair."""
    try:
        payload = decode_token(body.refresh_token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a refresh token",
        )

    user_id = int(payload["sub"])
    svc = AuthService(db)
    user = svc.get_user_by_id(user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token = create_access_token(user.UserID, user.role)
    new_refresh_token = create_refresh_token(user.UserID)
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user profile",
    description="Return the profile of the currently authenticated user.",
    responses=standard_error_responses(
        success_model=UserOut,
        success_examples={"success": examples.EXAMPLE_AUTH_ME_SUCCESS},
        success_description="Current user profile.",
        include_not_found=False,
        bad_request_examples={
            "unauthorized": examples.EXAMPLE_AUTH_ME_UNAUTHORIZED,
        },
        bad_request_description="Missing or invalid Bearer token.",
        include_validation=False,
    ),
    openapi_extra=code_samples(
        {"lang": "curl", "source": "curl http://localhost:8000/api/v1/auth/me -H 'Authorization: Bearer eyJ...'"}
    ),
)
def me(current_user: Users = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return current_user


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register first user (unauthenticated)",
    description=(
        "Register the first Control Center Officer when no users exist. "
        "After the first user is created, only authenticated Control Center "
        "Officers can create new users via POST /auth/users."
    ),
    responses=standard_error_responses(
        success_model=RegisterResponse,
        success_examples={"success": {"summary": "201 — registration submitted", "value": {"message": "Registration submitted successfully. Please sign in.", "user_id": 1}}},
        success_description="Registration successful. Please sign in.",
        include_not_found=False,
        bad_request_examples={
            "users_exist": {"summary": "403 — users already exist", "value": {"detail": "Registration is closed. Only Control Center Officers can create new users."}},
            "wrong_role": {"summary": "403 — first user must be control_center_officer", "value": {"detail": "The first user must be a Control Center Officer."}},
            "duplicate": examples.EXAMPLE_AUTH_CREATE_USER_DUPLICATE,
        },
        bad_request_description="Users already exist, invalid role for first user, or email already registered.",
        include_validation=True,
    ),
)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Register the first user when no users exist."""
    if body.password != body.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    if body.role != "control_center_officer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The first user must be a Control Center Officer.",
        )

    svc = AuthService(db)

    if svc.count_users() > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is closed. Only Control Center Officers can create new users.",
        )

    try:
        user = svc.create_user(body.email, body.password, body.role, name=body.name)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return RegisterResponse(
        message="Registration submitted successfully. Pending approval by a Control Center Officer.",
        user_id=user.UserID,
    )


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user account. Data Center Officer only.",
    responses=standard_error_responses(
        success_model=UserOut,
        success_examples={"success": examples.EXAMPLE_AUTH_CREATE_USER_SUCCESS},
        success_description="User created successfully.",
        include_not_found=False,
        bad_request_examples={
            "duplicate": examples.EXAMPLE_AUTH_CREATE_USER_DUPLICATE,
            "forbidden": examples.EXAMPLE_AUTH_CREATE_USER_FORBIDDEN,
        },
        bad_request_description="Email already exists or insufficient permissions.",
        include_validation=True,
    ),
    openapi_extra=code_samples(
        {"lang": "curl", "source": "curl -X POST http://localhost:8000/api/v1/auth/users -H 'Content-Type: application/json' -H 'Authorization: Bearer eyJ...' -d '{\"name\": \"Officer Kumar\", \"email\": \"new@ksp.gov.in\", \"password\": \"securepass123\", \"role\": \"police_station_officer\"}'"}
    ),
)
def create_user(
    body: CreateUserRequest,
    db: Session = Depends(get_db),
    _admin: Users = Depends(require_role("data_center_officer")),
):
    """Create a new user.

    Restricted to authenticated ``data_center_officer`` callers. Public
    registration is **not** available through this endpoint — the only
    unauthenticated registration path is ``POST /auth/register``, which
    only succeeds while ``users`` is empty and always creates a
    ``control_center_officer``. After the first user is created, new
    users must be provisioned by an existing ``data_center_officer``
    via this route.
    """
    svc = AuthService(db)
    try:
        user = svc.create_user(body.email, body.password, body.role, name=body.name)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return user



@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout",
    description="Logout the current user (client should discard tokens).",
)
def logout(_current_user: Users = Depends(get_current_user)):
    """Stateless logout — client discards tokens."""
    return {"message": "Logged out successfully"}
