"""
FastAPI Router for Part 8 - Notification Center.
"""
from __future__ import annotations

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db

router = APIRouter()


class NotificationItem(BaseModel):
    id: str = Field(..., description="Notification ID")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification body text")
    category: str = Field(..., description="new_fir, hotspot, prediction, officer_assigned, evidence, case_linked, alert")
    timestamp: str = Field(..., description="Timestamp ISO string")
    is_read: bool = Field(False, description="Read flag")
    link: str | None = Field(None, description="Optional relative link path")


class NotificationListResponse(BaseModel):
    unread_count: int = Field(..., description="Total unread notifications count")
    items: list[NotificationItem] = Field(default_factory=list, description="Notification list")


# In-memory notification store for demonstration & testing
_NOTIFICATIONS_DB = [
    NotificationItem(
        id="NOTIF-101",
        title="🚨 Critical Alert: Kidnapping Attempt",
        message="Vehicle KA-01-MJ-9921 fleeing towards Mysore Road toll.",
        category="alert",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        is_read=False,
        link="/map-intelligence",
    ),
    NotificationItem(
        id="NOTIF-102",
        title="🎯 AI Prediction Generated",
        message="High-risk forecast circle active for Koramangala 5th Block.",
        category="prediction",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        is_read=False,
        link="/map-intelligence",
    ),
    NotificationItem(
        id="NOTIF-103",
        title="📁 New FIR Registered",
        message="FIR/2026/0898 registered at Kalaburagi Station Bazaar PS.",
        category="new_fir",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        is_read=False,
        link="/cases",
    ),
    NotificationItem(
        id="NOTIF-104",
        title="🔗 Series Case Link Detected",
        message="AI linked FIR/2026/0891 with FIR/2026/0712 (94% similarity).",
        category="case_linked",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        is_read=True,
        link="/smart-investigation/1",
    ),
]


@router.get("", response_model=NotificationListResponse, summary="Get notification list & unread count")
def get_notifications(db: Annotated[Session, Depends(get_db)]):
    """Returns all notifications with unread count."""
    unread = sum(1 for n in _NOTIFICATIONS_DB if not n.is_read)
    return NotificationListResponse(unread_count=unread, items=_NOTIFICATIONS_DB)


@router.post("/read-all", response_model=dict[str, str], summary="Mark all notifications as read")
def mark_all_read(db: Annotated[Session, Depends(get_db)]):
    """Marks all notifications in notification center as read."""
    for n in _NOTIFICATIONS_DB:
        n.is_read = True
    return {"message": "All notifications marked as read"}


@router.patch("/{notification_id}/read", response_model=dict[str, str], summary="Mark single notification as read")
def mark_notification_read(
    notification_id: Annotated[str, Path(description="Notification ID")],
    db: Annotated[Session, Depends(get_db)],
):
    """Marks specified notification as read."""
    for n in _NOTIFICATIONS_DB:
        if n.id == notification_id:
            n.is_read = True
            break
    return {"message": f"Notification {notification_id} marked as read"}
