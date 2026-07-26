"""
Unit tests for Map Intelligence endpoints (/api/v1/map/*).
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.database import get_db
from backend.main import create_app

app = create_app()
client = TestClient(app, raise_server_exceptions=False)

_mock_session = MagicMock(name="Session")


def _override_db():
    return _mock_session


app.dependency_overrides[get_db] = _override_db


def test_get_stations():
    response = client.get("/api/v1/map/stations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "station_code" in data[0]
    assert "latitude" in data[0]
    assert "longitude" in data[0]


def test_get_fir_markers():
    response = client.get("/api/v1/map/firs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "fir_number" in data[0]
    assert "severity" in data[0]


def test_get_heatmap():
    response = client.get("/api/v1/map/heatmap?time_range=7d")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "weight" in data[0]


def test_get_hotspots():
    response = client.get("/api/v1/map/hotspots")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "radius_meters" in data[0]


def test_get_predictions():
    response = client.get("/api/v1/map/predictions?timeframe=24h")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "confidence_pct" in data[0]
    assert "likely_crime" in data[0]


def test_get_clusters():
    response = client.get("/api/v1/map/clusters")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "crime_count" in data[0]


def test_get_patrols():
    response = client.get("/api/v1/map/patrols")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "route_coords" in data[0]
    assert "unit_name" in data[0]


def test_get_alerts():
    response = client.get("/api/v1/map/alerts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "alert_type" in data[0]


def test_get_investigation_overlay():
    response = client.get("/api/v1/map/investigation-overlay/1")
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == 1
    assert "crime_location" in data
    assert "escape_routes" in data


def test_get_map_stats():
    response = client.get("/api/v1/map/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_crimes" in data
    assert "solved_percentage" in data
