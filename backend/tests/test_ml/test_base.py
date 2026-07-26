"""Tests for the predictor base protocol and registry."""
from __future__ import annotations

import pytest

from backend.ml.models import (
    BaseSklearnPredictor,
    EvidenceItem,
    FeatureContribution,
    HotspotPredictor,
    PredictionResult,
    Predictor,
    get_predictor,
    known_predictors,
)


EXPECTED = {
    "hotspot",
    "repeat_offender",
    "trend",
    "clustering",
    "similarity",
    "risk_score",
}


def test_known_predictors_is_sorted():
    assert known_predictors() == sorted(known_predictors())


def test_known_predictors_contains_expected_set():
    assert set(known_predictors()) == EXPECTED


def test_get_predictor_returns_fresh_instance():
    a = get_predictor("hotspot")
    b = get_predictor("hotspot")
    assert a is not b
    assert isinstance(a, HotspotPredictor)
    assert isinstance(a, BaseSklearnPredictor)
    assert isinstance(a, Predictor)


def test_get_predictor_unknown_raises():
    with pytest.raises(KeyError):
        get_predictor("does-not-exist")


def test_prediction_result_defaults():
    r = PredictionResult(value=1, confidence=0.5)
    assert r.top_features == []
    assert r.evidence == []


def test_feature_contribution_is_frozen():
    fc = FeatureContribution(feature="x", value=1, importance=0.5)
    with pytest.raises(Exception):
        fc.feature = "y"  # type: ignore[misc]


def test_evidence_item_defaults():
    e = EvidenceItem()
    assert e.case_id is None
    assert e.fir_number is None
    assert e.label == ""


def test_all_predictors_have_name():
    for name in known_predictors():
        p = get_predictor(name)
        assert isinstance(p.name, str)
        assert p.name  # non-empty
