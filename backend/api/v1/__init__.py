"""
Versioned API router. v1 is the only version for now.

Add more routers here as they are introduced (analytics, similarity, etc.).
"""
from fastapi import APIRouter

from backend.api.v1 import (
    ai,
    auth,
    cases,
    command_center,
    dashboard,
    health,
    investigation,
    map,
    monitoring,
    notification,
    predictions,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(monitoring.router, tags=["monitoring"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(
    dashboard.router, prefix="/dashboard", tags=["dashboard"]
)
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(
    predictions.router, prefix="/predictions", tags=["predictions"]
)
api_router.include_router(map.router, prefix="/map", tags=["map"])
api_router.include_router(
    investigation.router, prefix="/investigation", tags=["investigation"]
)
api_router.include_router(
    command_center.router, prefix="/command-center", tags=["command-center"]
)
api_router.include_router(
    notification.router, prefix="/notifications", tags=["notifications"]
)




