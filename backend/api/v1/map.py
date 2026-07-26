"""
Map Intelligence API Router — Part 4 Intelligent Map System.

Endpoints:
  - GET /api/v1/map/stations
  - GET /api/v1/map/firs
  - GET /api/v1/map/heatmap
  - GET /api/v1/map/hotspots
  - GET /api/v1/map/predictions
  - GET /api/v1/map/clusters
  - GET /api/v1/map/patrols
  - GET /api/v1/map/alerts
  - GET /api/v1/map/investigation-overlay/{case_id}
  - GET /api/v1/map/stats
"""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.map import (
    PoliceStationResponse,
    FIRMarkerResponse,
    HeatmapPointResponse,
    HotspotResponse,
    PredictedZoneResponse,
    CrimeClusterResponse,
    PatrolRouteResponse,
    LiveAlertResponse,
    InvestigationOverlayResponse,
    MapStatsResponse,
)
from backend.services.map_service import MapService

router = APIRouter()


def _svc(db: Session) -> MapService:
    return MapService(db)


@router.get("/stations", response_model=list[PoliceStationResponse], summary="List police stations with status")
def get_police_stations(db: Annotated[Session, Depends(get_db)]):
    """Returns every police station with station details and FIR statistics."""
    return _svc(db).get_police_stations()


@router.get("/firs", response_model=list[FIRMarkerResponse], summary="List FIR markers for map")
def get_fir_markers(
    db: Annotated[Session, Depends(get_db)],
    district: Annotated[str | None, Query(description="District name filter")] = None,
    police_station: Annotated[str | None, Query(description="Police station filter")] = None,
    crime_type: Annotated[str | None, Query(description="Crime major head filter")] = None,
    severity: Annotated[str | None, Query(description="Severity: very_high, high, medium, low")] = None,
    status: Annotated[str | None, Query(description="Case status filter")] = None,
    date_from: Annotated[date | None, Query(description="Start date")] = None,
    date_to: Annotated[date | None, Query(description="End date")] = None,
    bbox_min_lat: Annotated[float | None, Query(description="Bounding box min latitude")] = None,
    bbox_max_lat: Annotated[float | None, Query(description="Bounding box max latitude")] = None,
    bbox_min_lng: Annotated[float | None, Query(description="Bounding box min longitude")] = None,
    bbox_max_lng: Annotated[float | None, Query(description="Bounding box max longitude")] = None,
    repeat_offender_only: Annotated[bool, Query(description="Filter cases with repeat offenders")] = False,
):
    """Returns FIR markers with location coordinates, severity, and popup metadata."""
    return _svc(db).get_fir_markers(
        district=district,
        police_station=police_station,
        crime_type=crime_type,
        severity=severity,
        status=status,
        date_from=date_from,
        date_to=date_to,
        bbox_min_lat=bbox_min_lat,
        bbox_max_lat=bbox_max_lat,
        bbox_min_lng=bbox_min_lng,
        bbox_max_lng=bbox_max_lng,
        repeat_offender_only=repeat_offender_only,
    )


@router.get("/heatmap", response_model=list[HeatmapPointResponse], summary="Get crime heatmap density points")
def get_heatmap_points(
    db: Annotated[Session, Depends(get_db)],
    time_range: Annotated[str, Query(description="Timeframe: 24h, 7d, month, year, custom")] = "7d",
    crime_type: Annotated[str | None, Query(description="Crime type filter")] = None,
    district: Annotated[str | None, Query(description="District name filter")] = None,
):
    """Returns weighted FIR coordinates for Leaflet heatmap density visualization."""
    return _svc(db).get_heatmap_points(time_range=time_range, crime_type=crime_type, district=district)


@router.get("/hotspots", response_model=list[HotspotResponse], summary="Get crime hotspots")
def get_hotspots(db: Annotated[Session, Depends(get_db)]):
    """Returns high-risk crime hotspots with risk levels and total crimes."""
    return _svc(db).get_hotspots()


@router.get("/predictions", response_model=list[PredictedZoneResponse], summary="Get AI predicted crime zones")
def get_predicted_zones(
    db: Annotated[Session, Depends(get_db)],
    timeframe: Annotated[str, Query(description="Time horizon: 24h, 3d, 7d, month")] = "24h",
):
    """Returns AI predicted high-risk zones with confidence %, expected time, and patrol suggestions."""
    return _svc(db).get_predicted_zones(timeframe=timeframe)


@router.get("/clusters", response_model=list[CrimeClusterResponse], summary="Get spatial crime clusters")
def get_clusters(db: Annotated[Session, Depends(get_db)]):
    """Returns spatial crime clusters grouping nearby FIRs with common crime characteristics."""
    return _svc(db).get_clusters()


@router.get("/patrols", response_model=list[PatrolRouteResponse], summary="Get AI suggested patrol routes")
def get_patrols(db: Annotated[Session, Depends(get_db)]):
    """Returns AI recommended patrol vehicle deployment routes and coverage radii."""
    return _svc(db).get_patrol_recommendations()


@router.get("/alerts", response_model=list[LiveAlertResponse], summary="Get real-time crime alerts")
def get_alerts(db: Annotated[Session, Depends(get_db)]):
    """Returns active emergency alerts for blinking markers and top alert ticker."""
    return _svc(db).get_live_alerts()


@router.get("/investigation-overlay/{case_id}", response_model=InvestigationOverlayResponse, summary="Get investigation map overlay")
def get_investigation_overlay(
    case_id: Annotated[int, Path(ge=1, description="CaseMasterID")],
    db: Annotated[Session, Depends(get_db)],
):
    """Returns investigation overlay graph data (crime scene, escape routes, suspect hideouts, linked FIRs)."""
    return _svc(db).get_investigation_overlay(case_id=case_id)


@router.get("/stats", response_model=MapStatsResponse, summary="Get control room summary statistics")
def get_map_stats(db: Annotated[Session, Depends(get_db)]):
    """Returns top control panel operational statistics."""
    return _svc(db).get_map_stats()
