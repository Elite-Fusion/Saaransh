"""
Versioned API router. v1 is the only version for now.

Add more routers here as they are introduced (analytics, similarity, etc.).
"""
from fastapi import APIRouter

from backend.api.v1 import cases, dashboard, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(
    dashboard.router, prefix="/dashboard", tags=["dashboard"]
)
