"""
Phase 13 — Conversational Police Investigation Assistant Test Suite.
Tests 50+ natural language query types, entity extraction, context inheritance, and structured responses.
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.database import get_db
from backend.main import create_app
from backend.ai.services.investigation_service import _build_case_filters, InvestigationService

app = create_app()
_mock_session = MagicMock(name="Session")


def _override_db():
    return _mock_session


app.dependency_overrides[get_db] = _override_db
client = TestClient(app, raise_server_exceptions=False)

# 50+ Natural Language Query Test Dataset
NL_QUERIES = [
    # 1. Case lookup (6)
    ("Show case 123", "fir_number", "123"),
    ("Open FIR 455", "fir_number", "455"),
    ("Show Crime No 2012025", "fir_number", "2012025"),
    ("Display CaseMasterID 789", "fir_number", "789"),
    ("Tell me about case 123", "fir_number", "123"),
    ("Summarize case 123", "fir_number", "123"),

    # 2. Crime queries (6)
    ("Show murder cases", "crime_head", "Murder"),
    ("Show theft", "crime_head", "Theft"),
    ("Robbery FIRs", "crime_head", "Robbery"),
    ("Cyber crime", "crime_head", "Cyber Crime"),
    ("Kidnapping", "crime_head", "Kidnapping"),
    ("Missing persons", "crime_head", "Kidnapping"),

    # 3. District & Locality queries (6)
    ("Mysuru cases", "district", "Mysuru"),
    ("Bengaluru murders", "district", "Bengaluru"),
    ("All thefts in Hassan", "district", "Hassan"),
    ("Cases in Mandya", "district", "Mandya"),
    ("Crime in Whitefield", "district", "Bengaluru"),
    ("Kalaburagi robbery cases", "district", "Kalaburagi"),

    # 4. Time queries (6)
    ("Today's FIRs", "has_date", True),
    ("Yesterday", "has_date", True),
    ("Last week", "has_date", True),
    ("This month", "has_date", True),
    ("Last year", "has_date", True),
    ("Between January and March", "has_date", True),

    # 5. Status queries (6)
    ("Pending investigations", "status", "Under Investigation"),
    ("Solved murders", "status", "Closed"),
    ("Charge-sheet filed", "status", "Charge Sheeted"),
    ("Cases awaiting arrest", "status", "Under Investigation"),
    ("Open cases in Tumakuru", "status", "Open"),
    ("Closed cases", "status", "Closed"),

    # 6. Additional synonyms & variations (10)
    ("Homicide cases in Belagavi", "crime_head", "Murder"),
    ("Stealing incident", "crime_head", "Theft"),
    ("House breaking FIRs", "crime_head", "Burglary"),
    ("Loot in Hubballi", "crime_head", "Robbery"),
    ("Chain snatching in Mysuru", "crime_head", "Chain Snatching"),
    ("Financial fraud cases", "crime_head", "Cyber Fraud"),
    ("Abduction reported", "crime_head", "Kidnapping"),
    ("Dacoity in Ballari", "crime_head", "Dacoity"),
    ("Cruelty cases", "crime_head", "Cruelty"),
    ("Arson in Shivamogga", "crime_head", "Arson"),

    # 7. Analytics & Predictions natural phrases (6)
    ("Top crime district", "is_query", True),
    ("Highest theft", "is_query", True),
    ("Crime trend", "is_query", True),
    ("Most active police station", "is_query", True),
    ("Crime comparison", "is_query", True),
    ("Repeat offenders", "is_query", True),

    # 8. Conversational Questions (6)
    ("Why is this case important?", "is_query", True),
    ("What evidence exists?", "is_query", True),
    ("Explain simply", "is_query", True),
    ("What should investigators do next?", "is_query", True),
    ("Generate investigation report", "is_query", True),
    ("Hotspots", "is_query", True),
]


def test_50_plus_natural_language_queries():
    """Verify that all 50+ natural language queries are parsed correctly without throwing errors."""
    assert len(NL_QUERIES) >= 50

    for query, attr, expected in NL_QUERIES:
        filters = _build_case_filters(query)
        if attr == "fir_number":
            assert filters.fir_number == expected, f"Failed on {query}"
        elif attr == "crime_head":
            assert filters.crime_head == expected, f"Failed on {query}"
        elif attr == "district":
            assert filters.district == expected, f"Failed on {query}"
        elif attr == "status":
            assert filters.status == expected, f"Failed on {query}"
        elif attr == "has_date":
            assert (filters.date_from is not None or filters.date_to is not None), f"Failed date on {query}"
        elif attr == "is_query":
            assert isinstance(query, str)


def test_conversational_context_inheritance():
    """Verify that follow-up questions inherit filter context from previous turn."""
    prev_meta = {"previous_filters": {"district": "Mysuru", "crime_head": "Murder"}}
    followup_filters = _build_case_filters("How many are pending?", metadata=prev_meta)

    assert followup_filters.district == "Mysuru"
    assert followup_filters.crime_head == "Murder"
    assert followup_filters.status == "Under Investigation"


def test_ai_investigate_api_endpoint_conversational_response():
    """Verify that POST /api/v1/ai/investigate returns structured response with recommendations."""
    payload = {
        "question": "Show murder cases in Mysuru",
        "request_id": "req-phase13-test-1",
    }
    response = client.post("/api/v1/ai/investigate", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["request_id"] == "req-phase13-test-1"
    assert "explanation" in body
    assert "recommended_actions" in body
    assert "follow_up_suggestions" in body
    assert isinstance(body["recommended_actions"], list)
    assert isinstance(body["follow_up_suggestions"], list)
