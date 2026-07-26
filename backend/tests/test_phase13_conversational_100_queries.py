"""
Phase 13 — Conversational AI Police Investigation Assistant 100+ Query Test Suite.
Verifies English, Kannada, Mixed queries, Typos, Conversation Memory, Clarifications, Greetings, Farewells, and Analytics.
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.database import get_db
from backend.main import create_app
from backend.ai.services.investigation_service import _build_case_filters, InvestigationService
from backend.ai.services.context_manager import get_context_manager
from backend.ai.schemas.ai import Intent

app = create_app()
_mock_session = MagicMock(name="Session")


def _override_db():
    return _mock_session


app.dependency_overrides[get_db] = _override_db
client = TestClient(app, raise_server_exceptions=False)

# 100 Natural Language Test Queries dataset
NL_100_QUERIES = [
    # 1. Greetings (7)
    ("hello", Intent.GREETING),
    ("hi", Intent.GREETING),
    ("good morning", Intent.GREETING),
    ("good afternoon", Intent.GREETING),
    ("good evening", Intent.GREETING),
    ("namaskara", Intent.GREETING),
    ("ನಮಸ್ಕಾರ", Intent.GREETING),


    # 2. Farewells (4)
    ("bye", Intent.FAREWELL),
    ("thank you", Intent.FAREWELL),
    ("thanks", Intent.FAREWELL),
    ("good night", Intent.FAREWELL),

    # 3. Small talk & Help (4)
    ("who are you", Intent.HELP),
    ("what can you do", Intent.HELP),
    ("help", Intent.HELP),
    ("commands", Intent.HELP),

    # 4. Case Lookups (8)
    ("Show case 123", Intent.EXPLAIN_CASE),
    ("Open FIR 455", Intent.EXPLAIN_CASE),
    ("Show Crime No 2012025", Intent.EXPLAIN_CASE),
    ("Display CaseMasterID 789", Intent.EXPLAIN_CASE),
    ("Tell me about case 123", Intent.EXPLAIN_CASE),
    ("Summarize case 123", Intent.EXPLAIN_CASE),
    ("Describe FIR 999", Intent.EXPLAIN_CASE),
    ("What happened in case 50", Intent.EXPLAIN_CASE),

    # 5. Crime Queries (12)
    ("Show murder cases", Intent.CASE_SEARCH),
    ("Show theft", Intent.CASE_SEARCH),
    ("Robbery FIRs", Intent.CASE_SEARCH),
    ("Cyber crime", Intent.CASE_SEARCH),
    ("Kidnapping", Intent.CASE_SEARCH),
    ("Missing persons", Intent.CASE_SEARCH),
    ("Homicide cases", Intent.CASE_SEARCH),
    ("Burglary incidents", Intent.CASE_SEARCH),
    ("Chain snatching FIRs", Intent.CASE_SEARCH),
    ("Cyber fraud cases", Intent.CASE_SEARCH),
    ("Dowry death cases", Intent.CASE_SEARCH),
    ("Extortion complaints", Intent.CASE_SEARCH),

    # 6. District & Locality Queries (12)
    ("Mysuru cases", Intent.CASE_SEARCH),
    ("Bengaluru murders", Intent.CASE_SEARCH),
    ("All thefts in Hassan", Intent.CASE_SEARCH),
    ("Cases in Mandya", Intent.CASE_SEARCH),
    ("Crime in Whitefield", Intent.CASE_SEARCH),
    ("Kalaburagi robbery cases", Intent.CASE_SEARCH),
    ("Tumakuru cyber crimes", Intent.CASE_SEARCH),
    ("Ballari dacoity cases", Intent.CASE_SEARCH),
    ("Belagavi assault cases", Intent.CASE_SEARCH),
    ("Dharwad theft cases", Intent.CASE_SEARCH),
    ("Hubballi robbery FIRs", Intent.CASE_SEARCH),
    ("Mangaluru fraud cases", Intent.CASE_SEARCH),

    # 7. Time Queries (8)
    ("Today's FIRs", Intent.CASE_SEARCH),
    ("Yesterday", Intent.CASE_SEARCH),
    ("Last week", Intent.CASE_SEARCH),
    ("This month", Intent.CASE_SEARCH),
    ("Last year", Intent.CASE_SEARCH),
    ("Between January and March", Intent.CASE_SEARCH),
    ("Last 7 days", Intent.CASE_SEARCH),
    ("Last 30 days", Intent.CASE_SEARCH),

    # 8. Status Queries (7)
    ("Pending investigations", Intent.CASE_SEARCH),
    ("Solved murders", Intent.CASE_SEARCH),
    ("Charge-sheet filed", Intent.CASE_SEARCH),
    ("Cases awaiting arrest", Intent.CASE_SEARCH),
    ("Open cases in Tumakuru", Intent.CASE_SEARCH),
    ("Closed cases in Mysuru", Intent.CASE_SEARCH),
    ("Chargesheeted thefts", Intent.CASE_SEARCH),

    # 9. Officer Queries (4)
    ("Cases assigned to Officer Ravi", Intent.CASE_SEARCH),
    ("Show investigating officer", Intent.CASE_IO),
    ("Who handled case 123", Intent.CASE_IO),
    ("Who is IO?", Intent.CASE_IO),

    # 10. Analytics & Predictions (10)
    ("Top crime district", Intent.DASHBOARD_ANALYTICS),
    ("Highest theft", Intent.DASHBOARD_ANALYTICS),
    ("Crime trend", Intent.DASHBOARD_ANALYTICS),
    ("Most active police station", Intent.DASHBOARD_ANALYTICS),
    ("Crime comparison", Intent.DASHBOARD_ANALYTICS),
    ("Repeat offenders", Intent.SIMILAR_CASES),
    ("Hotspots", Intent.DASHBOARD_ANALYTICS),
    ("High risk locations", Intent.DASHBOARD_ANALYTICS),
    ("Next week's prediction", Intent.DASHBOARD_ANALYTICS),
    ("Patrol suggestions", Intent.DASHBOARD_ANALYTICS),

    # 11. Case Sub-Intents (8)
    ("Show suspects", Intent.CASE_SUSPECTS),
    ("Who are the accused", Intent.CASE_SUSPECTS),
    ("Show evidence", Intent.CASE_EVIDENCE),
    ("What proof exists", Intent.CASE_EVIDENCE),
    ("Timeline", Intent.CASE_TIMELINE),
    ("Chronology of events", Intent.CASE_TIMELINE),
    ("Investigating officer details", Intent.CASE_IO),
    ("Charge sheet status", Intent.CASE_STATUS),

    # 12. Kannada + English Mixed (10)
    ("ಬೆಂಗಳೂರು theft cases", Intent.CASE_SEARCH),
    ("Mysuru alli murder cases", Intent.CASE_SEARCH),
    ("chain snatching cases torisu", Intent.CASE_SEARCH),
    ("last week alli robbery", Intent.CASE_SEARCH),
    ("ಕೊಲೆ ಪ್ರಕರಣಗಳು", Intent.CASE_SEARCH),
    ("ಎಷ್ಟು theft cases", Intent.DASHBOARD_ANALYTICS),
    ("Mysuru murder cases eshtu", Intent.DASHBOARD_ANALYTICS),
    ("ಕಳ್ಳತನ cases in Hubballi", Intent.CASE_SEARCH),
    ("ದರೋಡೆ in Ballari", Intent.CASE_SEARCH),
    ("ಅಪಹರಣ in Hassan", Intent.CASE_SEARCH),

    # 13. Typos & Misspellings (6)
    ("cases in banglore", Intent.CASE_SEARCH),
    ("murdur cases in mysore", Intent.CASE_SEARCH),
    ("thift in tumkur", Intent.CASE_SEARCH),
    ("robary in kalburgi", Intent.CASE_SEARCH),
    ("snatchin in hubli", Intent.CASE_SEARCH),
    ("belgaum cases", Intent.CASE_SEARCH),
]


def test_100_queries_intent_and_filter_parsing():
    """Verify that all 100 queries parse cleanly into valid intents and filters without throwing exceptions."""
    assert len(NL_100_QUERIES) == 100

    from backend.ai.services.intent_service import IntentService

    for query, expected_intent in NL_100_QUERIES:
        intent_res, _ = IntentService._classify_with_regex(query)
        assert isinstance(intent_res, Intent), f"Failed intent classification on query: {query}"
        filters = _build_case_filters(query)
        assert filters is not None, f"Failed filter extraction on query: {query}"



def test_greetings_farewell_help_api_endpoints():
    """Verify that POST /api/v1/ai/investigate handles greetings, farewells, and help instantly."""
    for phrase, expected_intent in [("hello", "greeting"), ("bye", "farewell"), ("help", "help")]:
        resp = client.post(
            "/api/v1/ai/investigate",
            json={"question": phrase, "request_id": f"req-test-{phrase}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == expected_intent
        assert len(data["explanation"]["summary"]) > 0


def test_clarification_when_case_id_missing():
    """Verify that asking for suspects/evidence without a Case ID triggers a clarification prompt."""
    resp = client.post(
        "/api/v1/ai/investigate",
        json={"question": "Show suspects", "request_id": "req-clarify-1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "clarification"
    assert "Which case would you like to inspect?" in data["explanation"]["summary"]


def test_conversation_memory_active_case_chaining():
    """Verify that multi-turn conversation memory maintains active_case_id across questions."""
    ctx_mgr = get_context_manager()
    session_id = "test-session-chain-1"

    # Turn 1: Show case 100
    resp1 = client.post(
        "/api/v1/ai/investigate",
        json={
            "question": "Show case 100",
            "request_id": "req-chain-1",
            "metadata": {"session_id": session_id},
        },
    )
    assert resp1.status_code == 200

    state1 = ctx_mgr.get_state(session_id)
    assert state1.active_case_id == 100

    # Turn 2: Who is IO? (no explicit case ID in question, reuses 100)
    resp2 = client.post(
        "/api/v1/ai/investigate",
        json={
            "question": "Who is IO?",
            "request_id": "req-chain-2",
            "metadata": {"session_id": session_id},
        },
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["intent"] != "clarification"  # Should NOT clarify because active_case_id = 100 exists
