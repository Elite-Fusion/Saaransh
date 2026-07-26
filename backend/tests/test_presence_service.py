"""Tests for PresenceService wrapping ConnectionManager."""
import pytest
from backend.websocket.connection_manager import ConnectionManager
from backend.services.presence_service import PresenceService


class _FakeWebSocket:
    def __init__(self):
        self.sent: list[str] = []

    async def accept(self):
        pass

    async def send_json(self, data):
        import json
        self.sent.append(json.dumps(data))

    async def close(self):
        pass


@pytest.fixture
def cm():
    return ConnectionManager(heartbeat_interval=3600)


@pytest.fixture
def svc(cm):
    return PresenceService(session=None, connection_manager=cm)


class TestPresenceService:
    @pytest.mark.asyncio
    async def test_get_online_users_empty(self, svc):
        result = svc.get_online_users()
        assert result == []
        assert svc.get_online_count() == 0

    @pytest.mark.asyncio
    async def test_get_online_users(self, svc, cm):
        ws1, ws2 = _FakeWebSocket(), _FakeWebSocket()
        await cm.connect(ws1, 1, {"email": "a@b.com", "role": "si"})
        await cm.connect(ws2, 2, {"email": "c@d.com", "role": "psi"})

        result = svc.get_online_users()
        assert len(result) == 2
        emails = [u["email"] for u in result]
        assert "a@b.com" in emails
        assert "c@d.com" in emails

    @pytest.mark.asyncio
    async def test_is_user_online(self, svc, cm):
        ws = _FakeWebSocket()
        await cm.connect(ws, 10, {})

        assert svc.is_user_online(10) is True
        assert svc.is_user_online(99) is False

    @pytest.mark.asyncio
    async def test_get_online_count(self, svc, cm):
        assert svc.get_online_count() == 0
        await cm.connect(_FakeWebSocket(), 1, {})
        await cm.connect(_FakeWebSocket(), 2, {})
        assert svc.get_online_count() == 2

    @pytest.mark.asyncio
    async def test_get_user_presence(self, svc, cm):
        ws = _FakeWebSocket()
        await cm.connect(ws, 7, {"email": "test@ksp.gov.in", "role": "si", "police_station": "MG Road PS"})

        result = svc.get_user_presence(7)
        assert result is not None
        assert result["email"] == "test@ksp.gov.in"
        assert result["role"] == "si"
        assert result["online"] is True

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_presence(self, svc):
        result = svc.get_user_presence(999)
        assert result is None
