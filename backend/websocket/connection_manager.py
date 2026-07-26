"""
WebSocket connection manager — handles connections, rooms, and broadcast.

This module is the core of the real-time infrastructure.  It manages:

* Per-user WebSocket connections (one user may have multiple tabs)
* Role-aware room subscriptions (``dashboard``, ``analytics``, etc.)
* Broadcast to all, to a room, or to a specific user
* Heartbeat (ping/pong) with configurable interval
* Graceful disconnect handling

The manager is instantiated once at app startup and shared across all
WebSocket endpoints.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Default heartbeat interval in seconds
DEFAULT_HEARTBEAT_INTERVAL = 30


class ConnectionManager:
    """Manages active WebSocket connections with room-based routing."""

    def __init__(self, heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL) -> None:
        # user_id -> set of WebSocket connections (multiple tabs)
        self._connections: dict[int, set[WebSocket]] = {}
        # room_name -> set of user_ids in that room
        self._rooms: dict[str, set[int]] = {}
        # user_id -> user metadata (email, role, station)
        self._user_meta: dict[int, dict[str, Any]] = {}
        # ws -> last pong time
        self._last_pong: dict[WebSocket, float] = {}
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        user_meta: dict[str, Any] | None = None,
    ) -> None:
        """Accept a new WebSocket and register it."""
        await websocket.accept()
        self._connections.setdefault(user_id, set()).add(websocket)
        if user_meta:
            self._user_meta[user_id] = user_meta
        self._last_pong[websocket] = time.monotonic()
        logger.info("WS connected: user=%s", user_id)

    async def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """Remove a single connection.  If the user has no more connections
        they are removed from all rooms.
        """
        conns = self._connections.get(user_id)
        if conns:
            conns.discard(websocket)
            if not conns:
                self._connections.pop(user_id, None)
                self._user_meta.pop(user_id, None)
                # Remove from all rooms
                for room_users in self._rooms.values():
                    room_users.discard(user_id)
        self._last_pong.pop(websocket, None)
        logger.info("WS disconnected: user=%s (remaining=%s)", user_id, len(self._connections.get(user_id, set())))

    # ------------------------------------------------------------------
    # Room management
    # ------------------------------------------------------------------

    def join_room(self, user_id: int, room: str) -> None:
        """Subscribe *user_id* to *room*."""
        self._rooms.setdefault(room, set()).add(user_id)

    def leave_room(self, user_id: int, room: str) -> None:
        """Unsubscribe *user_id* from *room*."""
        if room in self._rooms:
            self._rooms[room].discard(user_id)

    def leave_all_rooms(self, user_id: int) -> None:
        """Remove *user_id* from every room."""
        for room_users in self._rooms.values():
            room_users.discard(user_id)

    # ------------------------------------------------------------------
    # Sending / broadcasting
    # ------------------------------------------------------------------

    async def send_personal(self, user_id: int, message: dict[str, Any]) -> None:
        """Send a message to all connections of a specific user."""
        conns = self._connections.get(user_id, set())
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            conns.discard(ws)

    async def broadcast_to_room(self, room: str, message: dict[str, Any]) -> None:
        """Send a message to every user in *room*."""
        user_ids = self._rooms.get(room, set())
        for uid in list(user_ids):
            await self.send_personal(uid, message)

    async def broadcast_all(self, message: dict[str, Any]) -> None:
        """Send a message to every connected user."""
        for uid in list(self._connections):
            await self.send_personal(uid, message)

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    async def start_heartbeat(self) -> None:
        """Start the background heartbeat loop."""
        if self._heartbeat_task is not None:
            return
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop_heartbeat(self) -> None:
        """Stop the heartbeat loop."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            now = time.monotonic()
            stale: list[tuple[WebSocket, int]] = []
            for user_id, conns in list(self._connections.items()):
                for ws in list(conns):
                    last = self._last_pong.get(ws, 0)
                    if now - last > self._heartbeat_interval * 3:
                        stale.append((ws, user_id))
                    else:
                        try:
                            ws._loop.create_task(  # type: ignore[attr-defined]
                                ws.send_json({"type": "ping", "ts": now})
                            )
                        except Exception:  # noqa: BLE001
                            stale.append((ws, user_id))
            for ws, uid in stale:
                await self.disconnect(ws, uid)

    def record_pong(self, websocket: WebSocket) -> None:
        """Record that a pong was received from *websocket*."""
        self._last_pong[websocket] = time.monotonic()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def online_count(self) -> int:
        """Number of distinct users with at least one active connection."""
        return len(self._connections)

    def online_user_ids(self) -> list[int]:
        """List of user IDs that are currently connected."""
        return list(self._connections.keys())

    def user_meta(self, user_id: int) -> dict[str, Any] | None:
        """Return metadata for *user_id*, or ``None`` if not connected."""
        return self._user_meta.get(user_id)

    def room_members(self, room: str) -> list[int]:
        """Return user IDs currently in *room*."""
        return list(self._rooms.get(room, set()))

    def rooms_for_user(self, user_id: int) -> list[str]:
        """Return rooms that *user_id* belongs to."""
        return [room for room, members in self._rooms.items() if user_id in members]
