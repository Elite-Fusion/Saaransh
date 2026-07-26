"""
Saaransh AI — FastAPI application entry point.

Run locally with:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Or via the convenience script:
    python -m backend.main
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend.api.v1 import api_router
from backend.api.v1 import ws as ws_module
from backend.config import settings
from backend.config.logging import configure_logging, get_logger
from backend.middleware.audit import AuditLogMiddleware
from backend.middleware.rate_limit import RateLimitMiddleware
from backend.middleware.security import SecurityHeadersMiddleware
from backend.services.notification_service import NotificationService
from backend.services.presence_service import PresenceService
from backend.websocket.connection_manager import ConnectionManager
from backend.websocket.event_bus import event_bus

logger = get_logger(__name__)

# Module-level ConnectionManager shared across the app
connection_manager = ConnectionManager()


async def _on_event(event_type: str, payload: dict) -> None:
    """Generic event handler — routes events to the ConnectionManager."""
    if event_type.startswith("dashboard.") or event_type.startswith("case."):
        await connection_manager.broadcast_to_room("dashboard", {
            "type": event_type,
            "data": payload,
        })
    elif event_type.startswith("notification."):
        # Send to specific user if user_id is in payload, else broadcast
        uid = payload.get("user_id")
        if uid:
            await connection_manager.send_personal(uid, {
                "type": event_type,
                "data": payload,
            })
    elif event_type.startswith("presence."):
        await connection_manager.broadcast_to_room("presence", {
            "type": event_type,
            "data": payload,
        })
    elif event_type.startswith("analytics."):
        await connection_manager.broadcast_to_room("analytics", {
            "type": event_type,
            "data": payload,
        })
    elif event_type.startswith("prediction."):
        await connection_manager.broadcast_to_room("predictions", {
            "type": event_type,
            "data": payload,
        })


async def _on_high_risk_event(payload: dict) -> None:
    """Create a notification when a high-risk event occurs."""
    # Emit notification events to relevant users
    await event_bus.emit("notification.created", {
        "user_id": payload.get("user_id", 0),
        "notification": payload,
    })


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application startup / shutdown hooks."""
    configure_logging()
    logger.info(
        "Starting %s v%s in %s mode",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )

    # Wire the ConnectionManager into the ws module
    ws_module.register_ws_dependencies(
        cm=connection_manager,
        notification_svc_factory=NotificationService,
        presence_svc_factory=PresenceService,
    )

    # Subscribe the broadcast handler to all events
    event_bus.subscribe("dashboard.", _on_event)
    event_bus.subscribe("case.", _on_event)
    event_bus.subscribe("analytics.", _on_event)
    event_bus.subscribe("prediction.", _on_event)
    event_bus.subscribe("presence.", _on_event)
    event_bus.subscribe("notification.", _on_event)
    event_bus.subscribe("notification.created", _on_high_risk_event)

    # Start heartbeat
    await connection_manager.start_heartbeat()

    yield

    # Shutdown
    await connection_manager.stop_heartbeat()
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Application factory — used by uvicorn and by tests."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # ---- GZip compression ----
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # ---- Security headers ----
    app.add_middleware(SecurityHeadersMiddleware)

    # ---- Rate limiting ----
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60, burst=10)

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Audit logging ----
    app.add_middleware(AuditLogMiddleware)

    # ---- Routers ----
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    # WebSocket + notification/presence REST endpoints
    app.include_router(ws_module.router, prefix=settings.api_v1_prefix, tags=["websocket"])

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
        }

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
