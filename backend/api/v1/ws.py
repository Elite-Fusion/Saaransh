"""
WebSocket API — real-time endpoints.

Provides:
  - ``/ws`` — main WebSocket endpoint with JWT auth via query param
  - ``/notifications/*`` — REST endpoints for notification CRUD
  - ``/presence/*`` — REST endpoints for presence queries

The WebSocket connection subscribes the user to default rooms
(``dashboard``, ``notifications``) and handles incoming messages for
room management, heartbeat, and acknowledgements.
"""
from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.api.v1.openapi import code_samples, standard_error_responses
from backend.database.session import get_db
from backend.middleware.auth import get_current_user
from backend.models.ai import Users
from backend.schemas.auth import UserOut
from backend.services.auth_service import AuthService, decode_token, AuthError
from backend.services.notification_service import NotificationService
from backend.services.presence_service import PresenceService
from backend.websocket.connection_manager import ConnectionManager
from backend.websocket.event_bus import event_bus

logger = logging.getLogger(__name__)

router = APIRouter()

# These are set at app startup via ``register_ws_dependencies``
_cm: ConnectionManager | None = None
_notification_svc_factory: Any = None
_presence_svc_factory: Any = None


def register_ws_dependencies(
    cm: ConnectionManager,
    notification_svc_factory=None,
    presence_svc_factory=None,
) -> None:
    """Wire the ConnectionManager and service factories into this module.

    Called once from ``main.py`` during app startup.
    """
    global _cm, _notification_svc_factory, _presence_svc_factory
    _cm = cm
    _notification_svc_factory = notification_svc_factory
    _presence_svc_factory = presence_svc_factory


# ------------------------------------------------------------------
# WebSocket endpoint
# ------------------------------------------------------------------


async def _authenticate_ws(token: str, db: Session) -> Users | None:
    """Validate a JWT token and return the Users row, or None."""
    try:
        payload = decode_token(token)
    except AuthError:
        return None
    if payload.get("type") != "access":
        return None
    svc = AuthService(db)
    user = svc.get_user_by_id(int(payload["sub"]))
    if user is None or not user.is_active:
        return None
    return user


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
) -> None:
    """Main WebSocket endpoint.

    Client connects with ``ws://host/ws?token=<JWT>``.

    Protocol (JSON messages):
      - Server -> Client: ``{"type": "<event>", "data": {...}}``
      - Client -> Server: ``{"type": "subscribe", "room": "<name>"}``
      - Client -> Server: ``{"type": "unsubscribe", "room": "<name>"}``
      - Client -> Server: ``{"type": "pong"}``
    """
    user = await _authenticate_ws(token, db)
    if user is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    if _cm is None:
        await websocket.close(code=1011, reason="Server not ready")
        return

    user_meta = {
        "email": user.email,
        "role": user.role,
        "police_station": "",
    }

    await _cm.connect(websocket, user.UserID, user_meta)

    # Auto-subscribe to default rooms
    _cm.join_room(user.UserID, "dashboard")
    _cm.join_room(user.UserID, "notifications")
    _cm.join_room(user.UserID, "presence")

    # Notify presence subscribers
    await event_bus.emit("presence.user_joined", {
        "user_id": user.UserID,
        "email": user.email,
        "role": user.role,
    })

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            if msg_type == "pong":
                _cm.record_pong(websocket)

            elif msg_type == "subscribe":
                room = msg.get("room")
                if room:
                    _cm.join_room(user.UserID, room)

            elif msg_type == "unsubscribe":
                room = msg.get("room")
                if room:
                    _cm.leave_room(user.UserID, room)

            elif msg_type == "ack":
                # Client acknowledges a notification
                nid = msg.get("notification_id")
                if nid and _notification_svc_factory:
                    svc = _notification_svc_factory(db)
                    svc.mark_read(user.UserID, nid)
                    await _cm.send_personal(user.UserID, {
                        "type": "notification.ack",
                        "notification_id": nid,
                    })

    except WebSocketDisconnect:
        pass
    finally:
        await _cm.disconnect(websocket, user.UserID)
        await event_bus.emit("presence.user_left", {
            "user_id": user.UserID,
        })


# ------------------------------------------------------------------
# REST — Notifications
# ------------------------------------------------------------------


@router.get(
    "/notifications",
    summary="List notifications",
    description="Returns notifications for the authenticated user, newest first.",
    responses=standard_error_responses(
        success_description="Notifications and unread count.",
        include_not_found=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl -H 'Authorization: Bearer <token>' "
                "'http://localhost:8000/api/v1/notifications?limit=20'"
            ),
        }
    ),
)
def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List notifications for the current user."""
    svc = NotificationService(db)
    notifications = svc.list_for_user(current_user.UserID, unread_only=unread_only, limit=limit)
    return {
        "notifications": notifications,
        "unread_count": svc.unread_count(current_user.UserID),
    }


@router.get(
    "/notifications/unread-count",
    summary="Unread notification count",
    description="Returns the number of unread notifications for the authenticated user.",
    responses=standard_error_responses(
        success_description="Unread count.",
        include_not_found=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl -H 'Authorization: Bearer <token>' "
                "'http://localhost:8000/api/v1/notifications/unread-count'"
            ),
        }
    ),
)
def notification_unread_count(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return the unread notification count."""
    svc = NotificationService(db)
    return {"unread_count": svc.unread_count(current_user.UserID)}


@router.post(
    "/notifications/{notification_id}/read",
    summary="Mark notification read",
    description="Mark a single notification as read.",
    responses=standard_error_responses(
        success_description="Whether the notification was found and marked read.",
        include_not_found=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl -X POST -H 'Authorization: Bearer <token>' "
                "'http://localhost:8000/api/v1/notifications/<id>/read'"
            ),
        }
    ),
)
def mark_notification_read(
    notification_id: str,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Mark a single notification as read."""
    svc = NotificationService(db)
    found = svc.mark_read(current_user.UserID, notification_id)
    return {"success": found}


@router.post(
    "/notifications/read-all",
    summary="Mark all notifications read",
    description="Mark all notifications as read for the authenticated user.",
    responses=standard_error_responses(
        success_description="Count of notifications marked read.",
        include_not_found=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl -X POST -H 'Authorization: Bearer <token>' "
                "'http://localhost:8000/api/v1/notifications/read-all'"
            ),
        }
    ),
)
def mark_all_notifications_read(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Mark all notifications as read."""
    svc = NotificationService(db)
    count = svc.mark_all_read(current_user.UserID)
    return {"marked_read": count}


# ------------------------------------------------------------------
# REST — Presence
# ------------------------------------------------------------------


@router.get(
    "/presence/online",
    summary="Online officers",
    description="List currently online officers.",
    responses=standard_error_responses(
        success_description="List of online users.",
        include_not_found=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl -H 'Authorization: Bearer <token>' "
                "'http://localhost:8000/api/v1/presence/online'"
            ),
        }
    ),
)
def online_users(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List currently online officers."""
    cm = _cm
    svc = PresenceService(db, connection_manager=cm)
    users = svc.get_online_users()
    return {"users": users, "count": len(users)}


@router.get(
    "/presence/me",
    summary="My presence",
    description="Return the current user's presence status.",
    responses=standard_error_responses(
        success_description="Current user presence info.",
        include_not_found=False,
    ),
    openapi_extra=code_samples(
        {
            "lang": "curl",
            "source": (
                "curl -H 'Authorization: Bearer <token>' "
                "'http://localhost:8000/api/v1/presence/me'"
            ),
        }
    ),
)
def my_presence(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return the current user's presence status."""
    cm = _cm
    svc = PresenceService(db, connection_manager=cm)
    info = svc.get_user_presence(current_user.UserID)
    return {"presence": info or {"online": False, "user_id": current_user.UserID}}
