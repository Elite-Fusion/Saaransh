"""
Unit tests for the prediction API endpoints.

The tests mock the SQLAlchemy ``Session`` and the underlying
:class:`PredictionService` so we can exercise the route layer
end-to-end without a live database or trained models.
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.database import get_db
from backend.main import create_app
from backend.schemas.prediction import (
    CrimeCluster,
    FIRRiskScore,
    FeatureContributionOut,
    HotspotPrediction,
    OfficerRecommendation,
    RepeatOffenderPrediction,
    SimilarCase,
    TrendForecast,
)
from backend.services.prediction_service import (
    CaseNotTrainedError,
    PredictionService,
)

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

app = create_app()
client = TestClient(app, raise_server_exceptions=False)

_mock_session = MagicMock(name="Session")


def _override_db():
    return _mock_session


app.dependency_overrides[get_db] = _override_db


def _make_hotspot(district="Mysuru", head="Crimes Against Property", month=1):
    return HotspotPrediction(
        district_name=district,
        crime_head=head,
        month=month,
        predicted_count=5,
        risk_band="medium",
        confidence=0.75,
        top_features=[
            FeatureContributionOut(feature="district", value=1, importance=0.5)
        ],
    )


def _make_repeat_offender():
    return RepeatOffenderPrediction(
        accused_id=1,
        accused_name="Test Accused",
        age=30,
        prior_count=2,
        will_reoffend=True,
        probability=0.85,
        confidence=0.85,
        top_features=[
            FeatureContributionOut(feature="prior_count", value=2, importance=0.8)
        ],
    )


def _make_trend():
    return TrendForecast(
        crime_head="Crimes Against Property",
        year=2024,
        month=3,
        month_label="Mar",
        predicted_count=42,
        current_count=35,
        confidence=0.70,
    )


def _make_cluster():
    return CrimeCluster(
        cluster_id=0,
        label="Theft",
        size=25,
        top_sub_heads=["Theft", "Burglary"],
        confidence=0.65,
    )


def _make_risk_score(case_id=1):
    return FIRRiskScore(
        case_id=case_id,
        fir_number="104430001202400001",
        risk_label="high",
        risk_numeric=85,
        district="Mysuru",
        crime_sub_head="Chain Snatching",
        confidence=0.85,
        top_features=[
            FeatureContributionOut(feature="crime_sub_head_id", value=1, importance=0.7)
        ],
    )


def _make_similar(case_id=2):
    return SimilarCase(
        case_id=case_id,
        fir_number="104430001202400019",
        crime_sub_head="Theft",
        district="Mysuru",
        similarity=0.92,
        confidence=0.92,
        brief_facts="Gold chain stolen near bus stand",
    )


def _make_recommendation():
    return OfficerRecommendation(
        officer_id=1,
        officer_name="Rajesh Kumar",
        rank="Inspector",
        reason="Handled 5 similar cases recently",
        confidence=0.90,
    )


# ---------------------------------------------------------------------
# GET /predictions/hotspots
# ---------------------------------------------------------------------


def test_hotspots_returns_200():
    with patch.object(
        PredictionService, "predict_hotspots", return_value=[_make_hotspot()]
    ):
        resp = client.get("/api/v1/predictions/hotspots")
    assert resp.status_code == 200
    body = resp.json()
    assert body["predictor"] == "hotspot"
    assert len(body["hotspots"]) == 1
    assert body["hotspots"][0]["district_name"] == "Mysuru"


def test_hotspots_passes_top_n():
    with patch.object(
        PredictionService, "predict_hotspots", return_value=[_make_hotspot()]
    ) as mock:
        client.get("/api/v1/predictions/hotspots?top_n=5")
    mock.assert_called_once_with(top_n=5)


def test_hotspots_empty_list():
    with patch.object(PredictionService, "predict_hotspots", return_value=[]):
        resp = client.get("/api/v1/predictions/hotspots")
    assert resp.status_code == 200
    assert resp.json()["hotspots"] == []


# ---------------------------------------------------------------------
# GET /predictions/trends
# ---------------------------------------------------------------------


def test_trends_returns_200():
    with patch.object(
        PredictionService, "predict_trends", return_value=[_make_trend()]
    ):
        resp = client.get("/api/v1/predictions/trends")
    assert resp.status_code == 200
    body = resp.json()
    assert body["predictor"] == "trend"
    assert len(body["trends"]) == 1


def test_trends_passes_horizon():
    with patch.object(
        PredictionService, "predict_trends", return_value=[_make_trend()]
    ) as mock:
        client.get("/api/v1/predictions/trends?horizon_months=3")
    mock.assert_called_once_with(horizon_months=3)


# ---------------------------------------------------------------------
# GET /predictions/repeat-offenders
# ---------------------------------------------------------------------


def test_repeat_offenders_returns_200():
    with patch.object(
        PredictionService, "predict_repeat_offenders",
        return_value=[_make_repeat_offender()],
    ):
        resp = client.get("/api/v1/predictions/repeat-offenders")
    assert resp.status_code == 200
    body = resp.json()
    assert body["predictor"] == "repeat_offender"
    assert len(body["repeat_offenders"]) == 1
    assert body["repeat_offenders"][0]["will_reoffend"] is True


def test_repeat_offenders_passes_top_n():
    with patch.object(
        PredictionService, "predict_repeat_offenders",
        return_value=[],
    ) as mock:
        client.get("/api/v1/predictions/repeat-offenders?top_n=15")
    mock.assert_called_once_with(top_n=15)


# ---------------------------------------------------------------------
# GET /predictions/clusters
# ---------------------------------------------------------------------


def test_clusters_returns_200():
    with patch.object(
        PredictionService, "cluster_patterns", return_value=[_make_cluster()]
    ):
        resp = client.get("/api/v1/predictions/clusters")
    assert resp.status_code == 200
    body = resp.json()
    assert body["predictor"] == "clustering"
    assert len(body["clusters"]) == 1
    assert body["clusters"][0]["label"] == "Theft"


def test_clusters_passes_top_n():
    with patch.object(
        PredictionService, "cluster_patterns", return_value=[]
    ) as mock:
        client.get("/api/v1/predictions/clusters?top_n=3")
    mock.assert_called_once_with(top_n=3)


# ---------------------------------------------------------------------
# GET /predictions/risk-score/{case_id}
# ---------------------------------------------------------------------


def test_risk_score_returns_200():
    with patch.object(
        PredictionService, "score_fir_risk", return_value=_make_risk_score(12)
    ):
        resp = client.get("/api/v1/predictions/risk-score/12")
    assert resp.status_code == 200
    body = resp.json()
    assert body["predictor"] == "risk_score"
    assert body["risk_score"]["risk_label"] == "high"
    assert body["risk_score"]["risk_numeric"] == 85


def test_risk_score_404_when_case_not_found():
    with patch.object(
        PredictionService, "score_fir_risk",
        side_effect=CaseNotTrainedError(999),
    ):
        resp = client.get("/api/v1/predictions/risk-score/999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "CASE_NOT_FOUND"


def test_risk_score_422_when_invalid_id():
    resp = client.get("/api/v1/predictions/risk-score/0")
    assert resp.status_code == 422


# ---------------------------------------------------------------------
# POST /predictions/similar-cases
# ---------------------------------------------------------------------


def test_similar_cases_returns_200():
    with patch.object(
        PredictionService, "find_similar_cases",
        return_value=[_make_similar(2)],
    ):
        resp = client.post(
            "/api/v1/predictions/similar-cases",
            json={"case_id": 1, "top_k": 5},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["predictor"] == "similarity"
    assert len(body["similar_cases"]) == 1
    assert body["similar_cases"][0]["similarity"] == 0.92


def test_similar_cases_404_when_case_not_found():
    with patch.object(
        PredictionService, "find_similar_cases",
        side_effect=CaseNotTrainedError(999),
    ):
        resp = client.post(
            "/api/v1/predictions/similar-cases",
            json={"case_id": 999, "top_k": 5},
        )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "CASE_NOT_FOUND"


def test_similar_cases_422_when_missing_body():
    resp = client.post("/api/v1/predictions/similar-cases", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------
# GET /predictions/recommendations/{case_id}
# ---------------------------------------------------------------------


def test_recommendations_returns_200():
    with patch.object(
        PredictionService, "recommend_officers",
        return_value=[_make_recommendation()],
    ):
        resp = client.get("/api/v1/predictions/recommendations/12")
    assert resp.status_code == 200
    body = resp.json()
    assert body["predictor"] == "recommendation"
    assert len(body["recommendations"]) == 1
    assert body["recommendations"][0]["officer_name"] == "Rajesh Kumar"


def test_recommendations_404_when_case_not_found():
    with patch.object(
        PredictionService, "recommend_officers",
        side_effect=CaseNotTrainedError(999),
    ):
        resp = client.get("/api/v1/predictions/recommendations/999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "CASE_NOT_FOUND"


def test_recommendations_passes_top_n():
    with patch.object(
        PredictionService, "recommend_officers", return_value=[]
    ) as mock:
        client.get("/api/v1/predictions/recommendations/1?top_n=5")
    mock.assert_called_once_with(case_id=1, top_n=5)
