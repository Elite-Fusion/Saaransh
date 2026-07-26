"""
Notification service — FastAPI-independent.

Handles notification CRUD: creation, listing, read status, and unread
counts.  Notifications are persisted in-memory (list) for the MVP;
swap to a database table for production persistence.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from backend.services.base import BaseService


class NotificationService(BaseService):
    """Create, list, and manage notifications.

    In-memory store — suitable for single-process deployments.
    For multi-process production, replace with a database table.
    """

    # Class-level store shared across instances (single-process only)
    _store: dict[int, list[dict[str, Any]]] = defaultdict(list)

    def __init__(self, session=None) -> None:
        super().__init__(session)

    def create(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create and persist a notification for *user_id*."""
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._store[user_id].append(notification)
        return notification

    def list_for_user(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return notifications for *user_id*, newest first."""
        notifications = self._store.get(user_id, [])
        if unread_only:
            notifications = [n for n in notifications if not n["read"]]
        return list(reversed(notifications[-limit:]))

    def unread_count(self, user_id: int) -> int:
        """Return the count of unread notifications for *user_id*."""
        return sum(1 for n in self._store.get(user_id, []) if not n["read"])

    def mark_read(self, user_id: int, notification_id: str) -> bool:
        """Mark a single notification as read.  Returns True if found."""
        for n in self._store.get(user_id, []):
            if n["id"] == notification_id:
                n["read"] = True
                return True
        return False

    def mark_all_read(self, user_id: int) -> int:
        """Mark all notifications as read for *user_id*.  Returns count."""
        count = 0
        for n in self._store.get(user_id, []):
            if not n["read"]:
                n["read"] = True
                count += 1
        return count

    def clear_store(self) -> None:
        """Reset the in-memory store.  Used by tests."""
        self._store.clear()
