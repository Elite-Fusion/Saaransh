"""
Pydantic schemas for Part 4 - Intelligent Map System.
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class PoliceStationResponse(BaseModel):
    id: int = Field(..., description="UnitID of the police station")
    name: str = Field(..., description="Station name")
    station_code: str = Field(..., description="Unique station code")
    officer_in_charge: str = Field("Inspector In-Charge", description="Officer in charge name")
    officer_rank: str = Field("Inspector", description="Officer rank")
    district_id: int | None = Field(None, description="District ID")
    district_name: str = Field("Karnataka Central", description="District Name")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    total_firs: int = Field(0, description="Total FIRs registered")
    active_cases: int = Field(0, description="Active case count")
    pending_cases: int = Field(0, description="Pending case count")
    solved_cases: int = Field(0, description="Solved case count")
    avg_response_time_mins: float = Field(12.5, description="Average response time in minutes")
    nearest_hotspots: list[str] = Field(default_factory=list, description="Nearest crime hotspots")


class FIRMarkerResponse(BaseModel):
    id: int = Field(..., description="CaseMasterID")
    fir_number: str = Field(..., description="Crime number / FIR Number")
    crime_type: str = Field(..., description="Major crime head")
    crime_sub_type: str | None = Field(None, description="Minor crime subhead")
    registered_date: str = Field(..., description="FIR registration date ISO string")
    incident_date: str | None = Field(None, description="Incident date ISO string")
    victim_name: str | None = Field(None, description="Victim name if available")
    complainant_name: str | None = Field(None, description="Complainant name")
    status: str = Field("Under Investigation", description="Case status name")
    assigned_officer: str | None = Field(None, description="Assigned investigating officer")
    linked_cases_count: int = Field(0, description="Number of linked cases")
    nearest_police_station: str | None = Field(None, description="Nearest police station name")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    severity: str = Field("medium", description="Severity level: very_high, high, medium, low")
    district_name: str | None = Field(None, description="District name")
    is_repeat_offender_involved: bool = Field(False, description="Flag if linked to repeat offender")


class HeatmapPointResponse(BaseModel):
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")
    weight: float = Field(1.0, description="Weight / intensity metric (0.1 to 1.0)")
    crime_type: str = Field("General", description="Crime major head")
    date: str = Field(..., description="Registration date")


class HotspotResponse(BaseModel):
    id: int = Field(..., description="Hotspot ID")
    name: str = Field(..., description="Hotspot area name")
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")
    radius_meters: float = Field(1000.0, description="Radius in meters")
    risk_level: str = Field("high", description="Risk level: very_high, high, medium, low")
    total_crimes: int = Field(..., description="Total crime occurrences in zone")
    primary_crime_type: str = Field(..., description="Dominant crime category")
    trend: str = Field("Increasing", description="Trend direction")


class PredictedZoneResponse(BaseModel):
    id: int = Field(..., description="Prediction Zone ID")
    lat: float = Field(..., description="Center latitude")
    lng: float = Field(..., description="Center longitude")
    radius_meters: float = Field(1500.0, description="Radius of prediction zone")
    timeframe: str = Field("24h", description="Time horizon: 24h, 3d, 7d, month")
    confidence_pct: float = Field(..., description="Prediction confidence percentage (0-100)")
    likely_crime: str = Field(..., description="Predicted crime category")
    expected_time_window: str = Field(..., description="Expected time window of crime")
    reasoning_factors: list[str] = Field(default_factory=list, description="Explainable AI factors")
    suggested_patrol_units: list[str] = Field(default_factory=list, description="Recommended patrol units")
    risk_score: int = Field(..., description="Risk score out of 100")


class CrimeClusterResponse(BaseModel):
    cluster_id: int = Field(..., description="Cluster ID")
    center_lat: float = Field(..., description="Center latitude")
    center_lng: float = Field(..., description="Center longitude")
    crime_count: int = Field(..., description="Number of crimes in cluster")
    common_crime_type: str = Field(..., description="Dominant crime type")
    most_active_hours: str = Field("22:00 - 04:00", description="Peak active hours")
    repeat_offenders_count: int = Field(0, description="Repeat offenders detected in cluster")
    cluster_confidence: float = Field(92.5, description="Clustering confidence percentage")
    fir_numbers: list[str] = Field(default_factory=list, description="List of FIR numbers in cluster")


class PatrolRouteResponse(BaseModel):
    unit_id: str = Field(..., description="Patrol unit ID")
    unit_name: str = Field(..., description="Vehicle / Unit call sign")
    vehicle_type: str = Field("PCR Interceptor", description="Vehicle type")
    route_coords: list[list[float]] = Field(..., description="Polyline path coordinates [[lat, lng], ...]")
    current_position: list[float] = Field(..., description="Current live position [lat, lng]")
    coverage_radius_meters: float = Field(2000.0, description="Coverage radius")
    est_response_time_mins: int = Field(5, description="Estimated response time")
    reason: str = Field(..., description="Rationale for patrol route deployment")
    priority: str = Field("important", description="Priority level: routine, important, emergency")
    color: str = Field("#eab308", description="Hex color code")


class LiveAlertResponse(BaseModel):
    alert_id: str = Field(..., description="Alert ID")
    alert_type: str = Field(..., description="Alert category: Emergency, Kidnapping, Murder, Chain Snatching, Cyber Crime, Vehicle Theft")
    title: str = Field(..., description="Short alert title")
    description: str = Field(..., description="Alert details")
    timestamp: str = Field(..., description="Timestamp ISO string")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    fir_number: str | None = Field(None, description="Linked FIR number if exists")
    severity: str = Field("very_high", description="Severity level")
    district_name: str = Field(..., description="District name")
    status: str = Field("Active", description="Alert status")


class InvestigationOverlayResponse(BaseModel):
    case_id: int = Field(..., description="Case Master ID")
    fir_number: str = Field(..., description="FIR Number")
    crime_location: dict[str, Any] = Field(..., description="Crime scene location {lat, lng, label}")

    hotspot_zone: dict[str, Any] | None = Field(None, description="Hotspot overlay details")
    repeat_offender_locations: list[dict[str, Any]] = Field(default_factory=list, description="Known offender locations")
    linked_firs: list[dict[str, Any]] = Field(default_factory=list, description="Linked case locations")
    escape_routes: list[list[list[float]]] = Field(default_factory=list, description="Predicted escape route polylines")
    affected_district_ids: list[int] = Field(default_factory=list, description="District IDs impacted")
    summary_notes: str = Field(..., description="AI investigation overlay summary")


class MapStatsResponse(BaseModel):
    total_crimes: int = Field(..., description="Total FIR records in system")
    hotspots_count: int = Field(..., description="Active hotspot zones")
    predictions_count: int = Field(..., description="High risk predicted zones")
    patrol_units_count: int = Field(..., description="Active patrol units deployed")
    avg_response_time_mins: float = Field(..., description="Statewide avg response time in mins")
    solved_percentage: float = Field(..., description="Solved case clearance rate percentage")
    active_cases_count: int = Field(..., description="Total currently active cases")
