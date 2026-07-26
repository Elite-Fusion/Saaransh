"""Unit tests for the prediction service.

The tests mock the SQLAlchemy session and the lazy-loaded
predictors. The real predictor classes are tiny and
deterministic, but going through them end-to-end would
require a running model store, so the unit tests stub the
``_load`` helper to return a pre-populated predictor.
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.ml.models import (
    ClusteringPredictor,
    EvidenceItem,
    FeatureContribution,
    HotspotPredictor,
    PredictionResult,
    RepeatOffenderPredictor,
    RiskScorePredictor,
    SimilarityPredictor,
    TrendPredictor,
)
from backend.services.prediction_service import (
    CaseNotTrainedError,
    PredictionService,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _make_case_row(case_id=1, head="Crimes Against Property",
                   sub="Theft", district="Mysuru",
                   registered=None, brief="gold chain stolen"):
    """Build a CaseMaster-shaped SimpleNamespace."""
    station = SimpleNamespace(
        UnitID=1,
        district=SimpleNamespace(DistrictID=1, DistrictName=district),
    )
    return SimpleNamespace(
        CaseMasterID=case_id,
        CrimeNo=f"1044{case_id:012d}",
        CaseRegisteredDate=registered or date(2024, 1, 15),
        latitude=12.5,
        longitude=76.0,
        BriefFacts=brief,
        is_series_crime=False,
        series_id=None,
        mo_embedding=None,
        police_station=station,
        crime_major_head=SimpleNamespace(
            CrimeHeadID=1, CrimeGroupName=head
        ),
        crime_minor_head=SimpleNamespace(
            CrimeSubHeadID=1, CrimeHeadName=sub
        ),
        gravity=SimpleNamespace(GravityOffenceID=1, LookupValue="Heinous"),
        PolicePersonID=1,
    )


def _mock_session(cases=None, employees=None):
    """Build a mock SQLAlchemy session.

    The service uses two statement shapes:

      * by-id: ``.execute(stmt).scalar_one_or_none()``
      * list: ``.execute(stmt).scalars().all()``

    We pick the right result by inspecting the statement
    via a marker. Tests that need a finer split (e.g. one
    by-id then one list) pre-populate both lists; the
    call order is then deterministic.
    """
    cases = cases or []
    employees = employees or []
    session = SimpleNamespace()
    call_count = {"n": 0}

    def _execute(stmt):
        call_count["n"] += 1
        # ``_get_case`` uses ``scalar_one_or_none`` (no limit).
        # ``_load_cases`` / ``_load_accused`` / ``_load_employees``
        # use ``scalars().all()`` (with a limit). Detect via
        # the SQLAlchemy ``_limit_clause`` attribute, which is
        # set when ``.limit(N)`` is applied.
        has_limit = (
            getattr(stmt, "_limit_clause", None) is not None
            or getattr(stmt, "_limit", None) is not None
        )
        if not has_limit:
            result = SimpleNamespace()
            result.scalar_one_or_none = lambda: cases[0] if cases else None
            return result
        # List query — pick cases or employees based on which
        # table-like object the statement selects. We can't
        # reliably detect that, so we return whichever list
        # the test set up; if both, prefer cases first then
        # employees on subsequent calls.
        result = SimpleNamespace()
        # Naive heuristic: return cases unless they're empty.
        if cases and (call_count["n"] == 1 or not employees):
            payload = list(cases)
        elif employees:
            payload = list(employees)
        else:
            payload = []
        result.scalars = lambda p=payload: SimpleNamespace(
            all=lambda pl=p: pl
        )
        return result

    session.execute = _execute
    return session


# ---------------------------------------------------------------------
# 1. Hotspots
# ---------------------------------------------------------------------


def test_predict_hotspots_returns_top_n():
    cases = [
        _make_case_row(case_id=i, head="Crimes Against Property")
        for i in range(1, 6)
    ]
    session = _mock_session(cases=cases)
    svc = PredictionService(session)

    fake_predictor = HotspotPredictor()
    fake_predictor._model = object()  # non-None → not the empty branch

    # Patch the lazy loader.
    with patch(
        "backend.services.prediction_service._load",
        return_value=fake_predictor,
    ):
        # Patch the predict method on the instance.
        with patch.object(
            HotspotPredictor, "predict",
            return_value=[
                PredictionResult(
                    value=3,
                    confidence=0.8,
                    top_features=[
                        FeatureContribution(
                            feature="district_id", value=1, importance=0.5
                        )
                    ],
                )
                for _ in cases
            ],
        ):
            results = svc.predict_hotspots(top_n=3)
    assert results
    for r in results:
        assert r.predicted_count >= 0
        assert r.risk_band in {"low", "medium", "high", "very_high"}


def test_predict_hotspots_empty_when_no_cases():
    session = _mock_session(cases=[])
    svc = PredictionService(session)
    assert svc.predict_hotspots() == []


def test_predict_hotspots_empty_when_model_not_trained():
    cases = [_make_case_row()]
    session = _mock_session(cases=cases)
    svc = PredictionService(session)
    fake = HotspotPredictor()  # _model is None
    with patch(
        "backend.services.prediction_service._load", return_value=fake
    ):
        assert svc.predict_hotspots() == []


# ---------------------------------------------------------------------
# 2. Repeat offenders
# ---------------------------------------------------------------------


def test_predict_repeat_offenders_top_n():
    accused = [
        SimpleNamespace(
            AccusedMasterID=i,
            AccusedName=f"Accused {i}",
            AgeYear=30,
            GenderID=1,
            is_known_criminal=bool(i % 2),
            criminal_history="",
        )
        for i in range(1, 6)
    ]
    session = _mock_session(accused=accused)
    svc = PredictionService(session)
    fake = RepeatOffenderPredictor()
    fake._model = object()
    with patch(
        "backend.services.prediction_service._load", return_value=fake
    ):
        with patch.object(
            RepeatOffenderPredictor, "predict",
            return_value=[
                PredictionResult(
                    value=1, confidence=0.9,
                    top_features=[
                        FeatureContribution(
                            feature="prior_count", value=2, importance=0.8
                        )
                    ],
                )
                for _ in accused
            ],
        ):
            results = svc.predict_repeat_offenders(top_n=3)
    assert len(results) == 3
    for r in results:
        assert r.will_reoffend is True
        assert 0.0 <= r.probability <= 1.0


# ---------------------------------------------------------------------
# 3. Trends
# ---------------------------------------------------------------------


def test_predict_trends_aggregates_by_month():
    cases = [
        _make_case_row(case_id=i, registered=date(2024, m, 15))
        for i, m in enumerate([1, 2, 3, 1, 2], start=1)
    ]
    session = _mock_session(cases=cases)
    svc = PredictionService(session)
    fake = TrendPredictor()
    fake._model = object()
    with patch(
        "backend.services.prediction_service._load", return_value=fake
    ):
        with patch.object(
            TrendPredictor, "predict",
            return_value=[
                PredictionResult(value=1, confidence=0.5)
                for _ in cases
            ],
        ):
            results = svc.predict_trends()
    assert results
    # The 12-month window is filled; the aggregation yields
    # one row per (head, year, month).
    for r in results:
        assert 1 <= r.month <= 12
        assert r.month_label in {
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        }


# ---------------------------------------------------------------------
# 4. Clustering
# ---------------------------------------------------------------------


def test_cluster_patterns_groups_by_cluster():
    cases = [
        _make_case_row(case_id=i, sub="Theft") for i in range(1, 6)
    ]
    session = _mock_session(cases=cases)
    svc = PredictionService(session)
    fake = ClusteringPredictor()
    fake._model = object()
    # 5 rows, all going to cluster 1 — produces one cluster.
    cluster_results = [
        PredictionResult(
            value=1, confidence=0.6,
            evidence=[EvidenceItem(case_id=c.CaseMasterID, label="1")],
        )
        for c in cases
    ]
    with patch(
        "backend.services.prediction_service._load", return_value=fake
    ):
        with patch.object(
            ClusteringPredictor, "predict", return_value=cluster_results
        ):
            results = svc.cluster_patterns()
    assert results
    assert results[0].size == 5


# ---------------------------------------------------------------------
# 5. Similarity
# ---------------------------------------------------------------------


def test_find_similar_cases_returns_top_k():
    cases = [_make_case_row(case_id=i) for i in range(1, 11)]
    session = _mock_session(cases=cases)
    svc = PredictionService(session)
    fake = SimilarityPredictor()
    fake._model = object()
    fake._corpus = cases  # required by predict()
    with patch(
        "backend.services.prediction_service._load", return_value=fake
    ):
        with patch.object(
            SimilarityPredictor, "predict",
            return_value=[
                PredictionResult(
                    value=cases[1].CaseMasterID, confidence=0.95,
                    evidence=[EvidenceItem(case_id=cases[1].CaseMasterID)],
                    top_features=[
                        FeatureContribution(
                            feature="brief_facts", value="theft", importance=0.9
                        )
                    ],
                )
            ],
        ):
            results = svc.find_similar_cases(case_id=1, top_k=3)
    assert results
    assert results[0].case_id == cases[1].CaseMasterID


def test_find_similar_cases_unknown_id_raises():
    session = _mock_session(cases=[])
    svc = PredictionService(session)
    with pytest.raises(CaseNotTrainedError):
        svc.find_similar_cases(case_id=999)


# ---------------------------------------------------------------------
# 6. Risk score
# ---------------------------------------------------------------------


def test_score_fir_risk_returns_label():
    case = _make_case_row(case_id=1)
    session = _mock_session(cases=[case])
    svc = PredictionService(session)
    fake = RiskScorePredictor()
    fake._model = object()
    with patch(
        "backend.services.prediction_service._load", return_value=fake
    ):
        with patch.object(
            RiskScorePredictor, "predict",
            return_value=[
                PredictionResult(
                    value="high", confidence=0.85,
                    top_features=[
                        FeatureContribution(
                            feature="crime_sub_head_id", value=1, importance=0.7
                        )
                    ],
                )
            ],
        ):
            result = svc.score_fir_risk(case_id=1)
    assert result.risk_label == "high"
    assert result.risk_numeric == 85
    assert 0.0 <= result.confidence <= 1.0


def test_score_fir_risk_falls_back_when_untrained():
    case = _make_case_row(case_id=1)
    session = _mock_session(cases=[case])
    svc = PredictionService(session)
    fake = RiskScorePredictor()  # untrained
    with patch(
        "backend.services.prediction_service._load", return_value=fake
    ):
        result = svc.score_fir_risk(case_id=1)
    # Untrained fallback returns medium / 50.
    assert result.risk_label == "medium"
    assert result.risk_numeric == 50


# ---------------------------------------------------------------------
# 7. Officer recommendations
# ---------------------------------------------------------------------


def test_recommend_officers_returns_top_n():
    case = _make_case_row(case_id=1, head="Crimes Against Property")
    employees = [
        SimpleNamespace(
            EmployeeID=1, FirstName="Rajesh",
            rank=SimpleNamespace(RankName="Inspector"),
        ),
        SimpleNamespace(
            EmployeeID=2, FirstName="Priya",
            rank=SimpleNamespace(RankName="Sub-Inspector"),
        ),
    ]
    session = _mock_session(cases=[case], employees=employees)
    svc = PredictionService(session)
    results = svc.recommend_officers(case_id=1, top_n=2)
    assert len(results) == 2
    for r in results:
        assert r.officer_id in {1, 2}
        assert r.reason


def test_recommend_officers_unknown_case_raises():
    session = _mock_session(cases=[])
    svc = PredictionService(session)
    with pytest.raises(CaseNotTrainedError):
        svc.recommend_officers(case_id=999)


# ---------------------------------------------------------------------
# Domain model + service-independence
# ---------------------------------------------------------------------


def test_service_inherits_base_service():
    session = _mock_session()
    svc = PredictionService(session)
    assert hasattr(svc, "session")
    assert svc.session is session


def test_module_does_not_import_fastapi():
    """Sanity check: the service must not import fastapi."""
    import re
    import backend.services.prediction_service as mod
    src = open(mod.__file__, encoding="utf-8").read()
    # Strip the docstring so a passing mention of "fastapi"
    # in prose doesn't trip the assertion.
    code = re.sub(r'""".*?"""', "", src, flags=re.DOTALL)
    assert "import fastapi" not in code
    assert "from fastapi" not in code
    assert "starlette" not in code
