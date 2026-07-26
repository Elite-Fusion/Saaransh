"""Tests for NotificationService (in-memory CRUD)."""
import pytest
from backend.services.notification_service import NotificationService


@pytest.fixture(autouse=True)
def svc():
    s = NotificationService()
    s.clear_store()
    return s


class TestNotificationService:
    def test_create_returns_notification(self, svc):
        n = svc.create(
            user_id=1,
            notification_type="case",
            title="Test",
            message="Body",
        )
        assert n["user_id"] == 1
        assert n["title"] == "Test"
        assert n["read"] is False
        assert "id" in n

    def test_list_for_user(self, svc):
        svc.create(user_id=1, notification_type="case", title="A", message="a")
        svc.create(user_id=2, notification_type="alert", title="B", message="b")
        svc.create(user_id=1, notification_type="case", title="C", message="c")

        result = svc.list_for_user(user_id=1)
        assert len(result) == 2
        # Newest first
        assert result[0]["title"] == "C"
        assert result[1]["title"] == "A"

    def test_list_for_user_unread_only(self, svc):
        svc.create(user_id=1, notification_type="case", title="A", message="a")
        svc.create(user_id=1, notification_type="case", title="B", message="b")

        # Mark first as read
        notifs = svc.list_for_user(user_id=1)
        svc.mark_read(user_id=1, notification_id=notifs[1]["id"])

        unread = svc.list_for_user(user_id=1, unread_only=True)
        assert len(unread) == 1
        assert unread[0]["title"] == "B"

    def test_unread_count(self, svc):
        svc.create(user_id=1, notification_type="case", title="A", message="a")
        svc.create(user_id=1, notification_type="alert", title="B", message="b")
        assert svc.unread_count(user_id=1) == 2

        notifs = svc.list_for_user(user_id=1)
        svc.mark_read(user_id=1, notification_id=notifs[0]["id"])
        assert svc.unread_count(user_id=1) == 1

    def test_mark_read(self, svc):
        svc.create(user_id=1, notification_type="case", title="X", message="x")
        notifs = svc.list_for_user(user_id=1)
        n_id = notifs[0]["id"]

        success = svc.mark_read(user_id=1, notification_id=n_id)
        assert success is True

        notifs2 = svc.list_for_user(user_id=1)
        updated = next(n for n in notifs2 if n["id"] == n_id)
        assert updated["read"] is True

    def test_mark_read_wrong_user(self, svc):
        svc.create(user_id=1, notification_type="case", title="X", message="x")
        notifs = svc.list_for_user(user_id=1)
        n_id = notifs[0]["id"]

        success = svc.mark_read(user_id=2, notification_id=n_id)
        assert success is False

    def test_mark_all_read(self, svc):
        svc.create(user_id=1, notification_type="case", title="A", message="a")
        svc.create(user_id=1, notification_type="case", title="B", message="b")
        assert svc.unread_count(user_id=1) == 2

        count = svc.mark_all_read(user_id=1)
        assert count == 2
        assert svc.unread_count(user_id=1) == 0

    def test_mark_all_read_only_own(self, svc):
        svc.create(user_id=1, notification_type="case", title="A", message="a")
        svc.create(user_id=2, notification_type="case", title="B", message="b")

        svc.mark_all_read(user_id=1)
        assert svc.unread_count(user_id=1) == 0
        assert svc.unread_count(user_id=2) == 1

    def test_list_limit(self, svc):
        for i in range(15):
            svc.create(user_id=1, notification_type="case", title=f"N{i}", message="m")

        result = svc.list_for_user(user_id=1, limit=5)
        assert len(result) == 5

    def test_empty_user(self, svc):
        result = svc.list_for_user(user_id=999)
        assert result == []
        assert svc.unread_count(user_id=999) == 0
