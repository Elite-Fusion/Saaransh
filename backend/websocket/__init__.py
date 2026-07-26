"""
WebSocket infrastructure for real-time intelligence.

Provides the connection manager, event bus, and room-based broadcast
used by the live dashboard, notifications, and presence system.
"""
from backend.websocket.connection_manager import ConnectionManager
from backend.websocket.event_bus import EventBus

__all__ = ["ConnectionManager", "EventBus"]
