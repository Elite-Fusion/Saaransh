"""Auth middleware — FastAPI dependencies for JWT extraction and RBAC.

The ``get_current_user`` dependency extracts the Bearer token from the
Authorization header, decodes it, and returns the ``Users`` ORM row.
The ``require_role`` factory builds a dependency that additionally
checks the user's role against a whitelist.
"""
from __future__ import annotations

from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.database.session import get_db
from backend.services.auth_service import (
    AuthError,
    AuthService,
    ForbiddenError,
    decode_token,
)

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------- get_current_user ----------


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
    db=Depends(get_db),
):
    """Extract and validate the current user from the Bearer token.

    Returns the ``Users`` ORM instance.  Raises 401 on missing / invalid
    token and 403 if the user is inactive.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not an access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = int(payload["sub"])
    svc = AuthService(db)
    user = svc.get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


# ---------- RBAC helper ----------


def require_role(*allowed_roles: str) -> Callable:
    """Return a FastAPI dependency that enforces role-based access.

    Usage::

        @router.get("/admin-only")
        def admin_page(user=Depends(require_role("admin"))):
            ...
    """

    def _role_checker(
        current_user: Annotated[object, Depends(get_current_user)],
    ):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not allowed. Required: {', '.join(allowed_roles)}",
            )
        return current_user

    return _role_checker
