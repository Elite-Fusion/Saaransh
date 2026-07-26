"""
Presence service — FastAPI-independent.

Tracks which officers are online, their last-active time, role, and
police station.  Powered by the ConnectionManager but does not depend
on FastAPI itself.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.services.base import BaseService


class PresenceService(BaseService):
    """Query and manage officer presence.

    Accepts an optional ``connection_manager`` so it can query live
    connection state without importing FastAPI.
    """

    def __init__(self, session, connection_manager=None) -> None:
        super().__init__(session)
        self._cm = connection_manager

    def get_online_users(self) -> list[dict[str, Any]]:
        """Return a list of currently online officers with metadata."""
        if self._cm is None:
            return []
        result = []
        for uid in self._cm.online_user_ids():
            meta = self._cm.user_meta(uid) or {}
            result.append({
                "user_id": uid,
                "email": meta.get("email", ""),
                "role": meta.get("role", ""),
                "police_station": meta.get("police_station", ""),
                "last_active": datetime.now(timezone.utc).isoformat(),
            })
        return result

    def get_online_count(self) -> int:
        """Return the number of distinct online users."""
        if self._cm is None:
            return 0
        return self._cm.online_count

    def is_user_online(self, user_id: int) -> bool:
        """Check if a specific user is online."""
        if self._cm is None:
            return False
        return user_id in self._cm.online_user_ids()

    def get_user_presence(self, user_id: int) -> dict[str, Any] | None:
        """Return presence info for a specific user, or None if offline."""
        if self._cm is None:
            return None
        meta = self._cm.user_meta(user_id)
        if meta is None:
            return None
        return {
            "user_id": user_id,
            "email": meta.get("email", ""),
            "role": meta.get("role", ""),
            "police_station": meta.get("police_station", ""),
            "online": True,
            "last_active": datetime.now(timezone.utc).isoformat(),
        }
