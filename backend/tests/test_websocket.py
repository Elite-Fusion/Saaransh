"""Tests for WebSocket ConnectionManager and EventBus."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.websocket.connection_manager import ConnectionManager
from backend.websocket.event_bus import EventBus


# ---------------------------------------------------------------------------
# ConnectionManager
# ---------------------------------------------------------------------------


class _FakeWebSocket:
    """Minimal WebSocket mock for testing."""

    def __init__(self):
        self.sent: list[str] = []
        self.closed = False
        self._accepted = False

    async def accept(self):
        self._accepted = True

    async def send_json(self, data):
        self.sent.append(json.dumps(data))

    async def close(self):
        self.closed = True


class TestConnectionManager:
    @pytest.fixture
    def cm(self):
        return ConnectionManager(heartbeat_interval=3600)

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self, cm):
        ws = _FakeWebSocket()
        user_id = 1
        meta = {"email": "a@b.com", "role": "admin"}

        await cm.connect(ws, user_id, meta)
        assert ws._accepted
        assert user_id in cm.online_user_ids()

        await cm.disconnect(ws, user_id)
        assert user_id not in cm.online_user_ids()

    @pytest.mark.asyncio
    async def test_broadcast_all_reaches_all(self, cm):
        ws1, ws2 = _FakeWebSocket(), _FakeWebSocket()
        await cm.connect(ws1, 10, {})
        await cm.connect(ws2, 11, {})

        await cm.broadcast_all({"type": "alert", "msg": "hi"})
        assert len(ws1.sent) == 1
        assert len(ws2.sent) == 1
        assert json.loads(ws1.sent[0])["msg"] == "hi"

    @pytest.mark.asyncio
    async def test_send_personal(self, cm):
        ws1, ws2 = _FakeWebSocket(), _FakeWebSocket()
        await cm.connect(ws1, 10, {})
        await cm.connect(ws2, 11, {})

        await cm.send_personal(10, {"type": "ack"})
        assert len(ws1.sent) == 1
        assert len(ws2.sent) == 0

    @pytest.mark.asyncio
    async def test_room_join_leave(self, cm):
        ws = _FakeWebSocket()
        await cm.connect(ws, 5, {})

        cm.join_room(5, "dashboard")
        assert 5 in cm.room_members("dashboard")

        cm.leave_room(5, "dashboard")
        assert 5 not in cm.room_members("dashboard")

    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, cm):
        ws1, ws2, ws3 = _FakeWebSocket(), _FakeWebSocket(), _FakeWebSocket()
        await cm.connect(ws1, 1, {})
        await cm.connect(ws2, 2, {})
        await cm.connect(ws3, 3, {})

        cm.join_room(1, "analytics")
        cm.join_room(2, "analytics")
        # ws3 does NOT join

        await cm.broadcast_to_room("analytics", {"type": "trend"})
        assert len(ws1.sent) == 1
        assert len(ws2.sent) == 1
        assert len(ws3.sent) == 0

    @pytest.mark.asyncio
    async def test_user_online(self, cm):
        ws = _FakeWebSocket()
        await cm.connect(ws, 42, {"email": "test@ksp.gov.in"})

        assert 42 in cm.online_user_ids()
        assert 999 not in cm.online_user_ids()

    @pytest.mark.asyncio
    async def test_online_count(self, cm):
        assert cm.online_count == 0
        await cm.connect(_FakeWebSocket(), 1, {})
        await cm.connect(_FakeWebSocket(), 2, {})
        assert cm.online_count == 2

    @pytest.mark.asyncio
    async def test_user_meta(self, cm):
        ws = _FakeWebSocket()
        await cm.connect(ws, 7, {"email": "si@ksp.gov.in", "role": "si"})

        meta = cm.user_meta(7)
        assert meta["email"] == "si@ksp.gov.in"
        assert meta["role"] == "si"
        assert cm.user_meta(999) is None

    @pytest.mark.asyncio
    async def test_rooms_for_user(self, cm):
        ws = _FakeWebSocket()
        await cm.connect(ws, 5, {})
        cm.join_room(5, "dashboard")
        cm.join_room(5, "analytics")

        rooms = cm.rooms_for_user(5)
        assert "dashboard" in rooms
        assert "analytics" in rooms

    @pytest.mark.asyncio
    async def test_leave_all_rooms(self, cm):
        ws = _FakeWebSocket()
        await cm.connect(ws, 5, {})
        cm.join_room(5, "dashboard")
        cm.join_room(5, "analytics")

        cm.leave_all_rooms(5)
        assert cm.rooms_for_user(5) == []

    @pytest.mark.asyncio
    async def test_offline_user_send_personal(self, cm):
        """Sending to an offline user should not raise."""
        await cm.send_personal(9999, {"type": "test"})

    @pytest.mark.asyncio
    async def test_multiple_connections_same_user(self, cm):
        ws1, ws2 = _FakeWebSocket(), _FakeWebSocket()
        await cm.connect(ws1, 10, {})
        await cm.connect(ws2, 10, {})

        assert cm.online_count == 1  # one distinct user
        await cm.send_personal(10, {"type": "ping"})
        assert len(ws1.sent) == 1
        assert len(ws2.sent) == 1

        # Disconnect one, user still online
        await cm.disconnect(ws1, 10)
        assert 10 in cm.online_user_ids()

        # Disconnect second, user gone
        await cm.disconnect(ws2, 10)
        assert 10 not in cm.online_user_ids()


# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------


class TestEventBus:
    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.mark.asyncio
    async def test_subscribe_and_emit(self, bus):
        received = []
        bus.subscribe("test.event", lambda data: received.append(data))

        await bus.emit("test.event", {"key": "value"})
        assert len(received) == 1
        assert received[0]["key"] == "value"

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus):
        received = []
        handler = lambda data: received.append(data)
        bus.subscribe("test", handler)

        await bus.emit("test", {})
        assert len(received) == 1

        bus.unsubscribe("test", handler)
        await bus.emit("test", {})
        assert len(received) == 1  # no new message

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, bus):
        a, b = [], []
        bus.subscribe("ev", lambda d: a.append(d))
        bus.subscribe("ev", lambda d: b.append(d))

        await bus.emit("ev", {"x": 1})
        assert len(a) == 1
        assert len(b) == 1

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_propagate(self, bus):
        def bad_handler(data):
            raise RuntimeError("oops")

        bus.subscribe("ev", bad_handler)

        # Should not raise
        await bus.emit("ev", {"a": 1})

    @pytest.mark.asyncio
    async def test_emit_no_subscribers(self, bus):
        # Should not raise
        await bus.emit("nonexistent.event", {"b": 2})
