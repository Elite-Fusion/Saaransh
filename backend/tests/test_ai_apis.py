"""
Tests for the AI investigation API endpoint.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.v1 import ai
from backend.ai.schemas.ai import InvestigationResponse, ExplanationBlock, EvidenceItem


@pytest.fixture
def app():
    """Create a test app with the AI router."""
    app = FastAPI()
    app.include_router(ai.router, prefix="/ai", tags=["ai"])
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_investigation_response():
    """Return a sample InvestigationResponse."""
    return InvestigationResponse(
        request_id="123e4567-e89b-12d3-a456-426614174000",
        intent="case_search",
        operation="service",
        reasoning="Question classified as case_search (keywords: crime, theft, Mumbai). "
                "Operation: CaseService.list_cases.",
        executed_operation="CaseService.list_cases",
        confidence=0.85,
        assumptions=["No date range provided; assumes all time."],
        supporting_evidence=[
            EvidenceItem(
                case_id=101,
                fir_number="104430001202400001",
                label="Case: 202400001; Status: Under Investigation"
            )
        ],
        explanation=ExplanationBlock(
            summary="Found 1 matching case from Jan 2024 to present.",
            evidence=[
                EvidenceItem(
                    case_id=101,
                    fir_number="104430001202400001",
                    label="Case: 202400001; Status: Under Investigation"
                )
            ],
            why="The query asked for recent theft cases in Mumbai. "
                "The system matched the crime head 'Theft' and "
                "returned the most recent case.",
            confidence="high",
            confidence_score=0.85,
            confidence_reason="High confidence due to exact match on crime head and recent date.",
            caveats=["Does not include sealed cases."]
        ),
        raw_sql=None,
        raw_params=None,
        row_count=1,
        columns=["CaseMasterID", "CrimeNo", "CrimeRegisteredDate", "case_status", "crime_major_head"],
        placeholder=None
    )


def test_investigate_success(client, mock_investigation_response):
    """Test a successful investigation request."""
    with patch("backend.api.v1.ai.InvestigationService") as mock_service_class:
        # Configure the mock service instance
        mock_service = MagicMock()
        mock_service.investigate.return_value = mock_investigation_response
        mock_service_class.return_value = mock_service

        response = client.post(
            "/ai/investigate",
            json={
                "question": "Show me theft cases in Mumbai from last month",
                "request_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == "123e4567-e89b-12d3-a456-426614174000"
        assert data["intent"] == "case_search"
        assert data["operation"] == "service"
        assert data["confidence"] == 0.85
        # Check that the service was called with the correct arguments
        mock_service_class.assert_called_once()
        # The investigate method should have been called
        mock_service.investigate.assert_called_once()
        args, kwargs = mock_service.investigate.call_args
        assert kwargs["question"] == "Show me theft cases in Mumbai from last month"
        assert kwargs["request_id"] == "123e4567-e89b-12d3-a456-426614174000"


def test_investigate_missing_question(client):
    """Test that a missing question field results in a 422 error."""
    response = client.post(
        "/ai/investigate",
        json={
            # "question" is missing
            "request_id": "123e4567-e89b-12d3-a456-426614174000"
        }
    )
    assert response.status_code == 422
    # Check that the error is about the missing field
    assert "question" in str(response.json())


def test_investigate_missing_request_id(client):
    """Test that a missing request_id field results in a 422 error."""
    response = client.post(
        "/ai/investigate",
        json={
            "question": "Show me theft cases in Mumbai from last month",
            # "request_id" is missing
        }
    )
    assert response.status_code == 422
    assert "request_id" in str(response.json())


def test_investigate_unknown_intent(client):
    """Test that an unknown intent results in a 400 error."""
    with patch("backend.api.v1.ai.InvestigationService") as mock_service_class:
        # Configure the mock service to raise UnknownIntent
        from backend.ai.services.exceptions import UnknownIntent
        mock_service = MagicMock()
        mock_service.investigate.side_effect = UnknownIntent(
            question="blah blah",
            reason="classifier returned UNKNOWN"
        )
        mock_service_class.return_value = mock_service

        response = client.post(
            "/ai/investigate",
            json={
                "question": "blah blah",
                "request_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "UNKNOWN_INTENT"
        # Message should match OpenAPI documentation format
        assert "Could not determine intent from question: 'blah blah'." in data["detail"]["message"]


def test_investigate_unsafe_sql(client):
    """Test that unsafe SQL results in a 400 error."""
    with patch("backend.api.v1.ai.InvestigationService") as mock_service_class:
        from backend.ai.services.exceptions import UnsafeSQL
        mock_service = MagicMock()
        mock_service.investigate.side_effect = UnsafeSQL(
            reason="DELETE not allowed",
            sql="DELETE FROM case_master WHERE 1=1",
            category="verb"
        )
        mock_service_class.return_value = mock_service

        response = client.post(
            "/ai/investigate",
            json={
                "question": "Delete all cases",
                "request_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "UNSAFE_SQL"
        assert "DELETE not allowed" in data["detail"]["message"]


def test_investigate_case_not_found(client):
    """Test that a non-existent case ID for explain_case intent results in a 404."""
    with patch("backend.api.v1.ai.InvestigationService") as mock_service_class:
        from backend.services import CaseNotFoundError
        mock_service = MagicMock()
        mock_service.investigate.side_effect = CaseNotFoundError(case_id=99999)
        mock_service_class.return_value = mock_service

        response = client.post(
            "/ai/investigate",
            json={
                "question": "Explain case 99999",
                "request_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "CASE_NOT_FOUND"
        assert "Case 99999 not found" in data["detail"]["message"]


def test_investigate_internal_error(client):
    """Test that an unexpected exception results in a 500 error."""
    with patch("backend.api.v1.ai.InvestigationService") as mock_service_class:
        mock_service = MagicMock()
        mock_service.investigate.side_effect = RuntimeError("Unexpected error")
        mock_service_class.return_value = mock_service

        response = client.post(
            "/ai/investigate",
            json={
                "question": "Something that causes an error",
                "request_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        )

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == "INTERNAL_ERROR"
        assert "An unexpected error occurred" in data["detail"]["message"]


def test_investigate_request_id_propagated_to_service(client, mock_investigation_response):
    """The route must propagate the client-supplied request_id
    through to the underlying service so the audit log can correlate
    AI requests with the case work they produced."""
    with patch("backend.api.v1.ai.InvestigationService") as mock_service_class:
        mock_service = MagicMock()
        mock_service.investigate.return_value = mock_investigation_response
        mock_service_class.return_value = mock_service

        response = client.post(
            "/ai/investigate",
            json={
                "question": "Show me theft cases in Mumbai from last month",
                "request_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        )

        assert response.status_code == 200
        args, kwargs = mock_service.investigate.call_args
        assert kwargs["request_id"] == "123e4567-e89b-12d3-a456-426614174000"
        # The service is constructed and the investigate call returns
        # the mock response. The response envelope matches the
        # InvestigationResponse schema.
        data = response.json()
        assert data["request_id"] == "123e4567-e89b-12d3-a456-426614174000"
        # Required top-level fields
        for field in (
            "request_id",
            "intent",
            "operation",
            "reasoning",
            "executed_operation",
            "confidence",
            "assumptions",
            "supporting_evidence",
        ):
            assert field in data, f"Missing field: {field}"


def test_investigate_response_envelope_matches_schema(client, mock_investigation_response):
    """Every field in the documented InvestigationResponse schema
    must be present and well-typed in the JSON response."""
    with patch("backend.api.v1.ai.InvestigationService") as mock_service_class:
        mock_service = MagicMock()
        mock_service.investigate.return_value = mock_investigation_response
        mock_service_class.return_value = mock_service

        response = client.post(
            "/ai/investigate",
            json={
                "question": "Show me theft cases in Mumbai from last month",
                "request_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["intent"], str)
        assert isinstance(data["operation"], str)
        assert isinstance(data["confidence"], (int, float))
        assert isinstance(data["assumptions"], list)
        assert isinstance(data["supporting_evidence"], list)
        # Evidence items have the documented shape
        if data["supporting_evidence"]:
            ev = data["supporting_evidence"][0]
            assert "label" in ev
        # Explanation block, when present, has the documented fields
        if data.get("explanation"):
            exp = data["explanation"]
            for field in ("summary", "evidence", "why", "confidence"):
                assert field in exp, f"Explanation missing: {field}"


def test_investigate_empty_question_rejected(client):
    """An empty question string is rejected as 400 UNKNOWN_INTENT
    because IntentService short-circuits questions below 8 chars
    before the model is even called."""
    response = client.post(
        "/ai/investigate",
        json={
            "question": "",
            "request_id": "123e4567-e89b-12d3-a456-426614174000"
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "UNKNOWN_INTENT"


def test_investigate_openapi_documents_endpoint(client):
    """The /ai/investigate route must show up in the OpenAPI schema
    so Swagger can drive a manual test."""
    schema = client.get("/openapi.json").json()
    assert "/ai/investigate" in schema["paths"]
    op = schema["paths"]["/ai/investigate"]["post"]
    assert "200" in op["responses"]
    assert "400" in op["responses"]
    assert "404" in op["responses"]
    assert "422" in op["responses"]


# ---------------------------------------------------------------------
# Phase 8 — endpoint exposes ``results`` and ``raw_sql`` from the
# SQL path so the frontend can render the actual rows + a "View
# generated SQL" disclosure.
# ---------------------------------------------------------------------


def test_investigate_endpoint_returns_results_in_response(client):
    """When the SQL path fires, the endpoint must surface the
    executor's rows in the new ``results`` field."""
    sql_response = InvestigationResponse(
        request_id="123e4567-e89b-12d3-a456-426614174000",
        intent="case_search",
        operation="sql",
        reasoning="Question classified as case_search. Operation: SQL.",
        executed_operation="SQLAlchemySQLExecutor.execute",
        confidence=0.7,
        assumptions=["SQL fallback used."],
        supporting_evidence=[],
        explanation=None,
        raw_sql="SELECT CaseMasterID FROM CaseMaster LIMIT 2",
        raw_params={},
        row_count=2,
        columns=["CaseMasterID"],
        placeholder=None,
        results=[
            {"CaseMasterID": 11},
            {"CaseMasterID": 12},
        ],
    )
    with patch("backend.api.v1.ai.InvestigationService") as mock_service_class:
        mock_service = MagicMock()
        mock_service.investigate.return_value = sql_response
        mock_service_class.return_value = mock_service
        response = client.post(
            "/ai/investigate",
            json={
                "question": "Show crimes between 2024-01-01 and 2024-06-30",
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["operation"] == "sql"
    assert data["results"] == [
        {"CaseMasterID": 11},
        {"CaseMasterID": 12},
    ]
    assert data["row_count"] == 2
    assert data["columns"] == ["CaseMasterID"]


def test_investigate_endpoint_returns_generated_sql_in_response(client):
    """The endpoint must echo the generated SQL so the frontend
    can show a "View generated SQL" disclosure."""
    sql_response = InvestigationResponse(
        request_id="123e4567-e89b-12d3-a456-426614174000",
        intent="dashboard_analytics",
        operation="sql",
        reasoning="Question classified as dashboard_analytics. Operation: SQL.",
        executed_operation="SQLAlchemySQLExecutor.execute",
        confidence=0.7,
        assumptions=["SQL fallback used."],
        supporting_evidence=[],
        explanation=None,
        raw_sql=(
            "SELECT district, COUNT(*) AS case_count FROM CaseMaster "
            "GROUP BY district ORDER BY case_count DESC LIMIT 1"
        ),
        raw_params={},
        row_count=1,
        columns=["district", "case_count"],
        placeholder=None,
        results=[{"district": "Bengaluru", "case_count": 30}],
    )
    with patch("backend.api.v1.ai.InvestigationService") as mock_service_class:
        mock_service = MagicMock()
        mock_service.investigate.return_value = sql_response
        mock_service_class.return_value = mock_service
        response = client.post(
            "/ai/investigate",
            json={
                "question": "Which district has the highest theft?",
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["raw_sql"] is not None
    assert "ORDER BY" in data["raw_sql"].upper()
    # The results field is populated.
    assert data["results"][0]["district"] == "Bengaluru"