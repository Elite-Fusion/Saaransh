from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.database import get_db
from backend.main import create_app

app = create_app()
_mock_session = MagicMock(name="Session")


def _override_db():
    return _mock_session


app.dependency_overrides[get_db] = _override_db
client = TestClient(app, raise_server_exceptions=False)



def test_smart_investigation_endpoint():
    response = client.get("/api/v1/investigation/1/smart-analysis")
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == 1
    assert "fir_number" in data
    assert "similar_cases" in data
    assert len(data["similar_cases"]) > 0
    assert "suspect_predictions" in data
    assert "pattern_analysis" in data
    assert "deployment_recommendation" in data
    assert "timeline" in data
    assert "evidence" in data
    assert "scores" in data


def test_investigation_timeline_endpoint():
    response = client.get("/api/v1/investigation/1/timeline")
    assert response.status_code == 200
    steps = response.json()
    assert isinstance(steps, list)
    assert len(steps) >= 5
    assert steps[0]["title"] == "FIR Registered"


def test_investigation_evidence_endpoints():
    response = client.get("/api/v1/investigation/1/evidence")
    assert response.status_code == 200
    evidence = response.json()
    assert isinstance(evidence, list)
    assert len(evidence) >= 3

    # Post new evidence
    add_resp = client.post(
        "/api/v1/investigation/1/evidence",
        json={"category": "Photos", "title": "CCTV Still Image", "collected_by": "Inspector Suresh"},
    )
    assert add_resp.status_code == 200
    added = add_resp.json()
    assert added["category"] == "Photos"
    assert added["title"] == "CCTV Still Image"

    # Patch evidence status
    patch_resp = client.patch(
        "/api/v1/investigation/evidence/99",
        json={"status": "Verified"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["new_status"] == "Verified"


def test_live_command_center_kpis():
    response = client.get("/api/v1/command-center/live-kpis")
    assert response.status_code == 200
    data = response.json()
    assert "active_firs" in data
    assert "todays_firs" in data
    assert "critical_alerts" in data
    assert "officers_on_patrol" in data
    assert "high_risk_districts" in data


def test_notifications_endpoints():
    response = client.get("/api/v1/notifications")
    assert response.status_code == 200
    data = response.json()
    assert "unread_count" in data
    assert "items" in data
    assert len(data["items"]) > 0

    read_all_resp = client.post("/api/v1/notifications/read-all")
    assert read_all_resp.status_code == 200

    single_read = client.patch("/api/v1/notifications/NOTIF-101/read")
    assert single_read.status_code == 200


def test_kannada_and_multilingual_investigation_filter_parsing():
    from backend.ai.services.investigation_service import _build_case_filters
    f1 = _build_case_filters("ಬೆಂಗಳೂರು chain snatching ಎಷ್ಟು?")
    assert f1.district == "Bengaluru"
    assert f1.crime_head == "Chain Snatching"

    f2 = _build_case_filters("ಮೈಸೂರು crime in last 30 days")
    assert f2.district == "Mysuru"
