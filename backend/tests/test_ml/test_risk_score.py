"""Tests for the RiskScorePredictor."""
from __future__ import annotations

import pytest

from backend.ml.models import RiskScorePredictor, get_predictor


def test_constructable_from_registry():
    p = get_predictor("risk_score")
    assert isinstance(p, RiskScorePredictor)
    assert p.name == "risk_score"


def test_predict_before_train_raises(small_cases):
    p = RiskScorePredictor()
    with pytest.raises(RuntimeError):
        p.predict(small_cases[:1])


def test_train_empty_raises():
    with pytest.raises(ValueError):
        RiskScorePredictor().train([])


def test_train_and_predict_returns_label(small_cases):
    p = RiskScorePredictor().train(small_cases)
    results = p.predict(small_cases)
    assert len(results) == len(small_cases)
    for r in results:
        assert r.value in {"high", "medium", "low"}
        assert 0.0 <= r.confidence <= 1.0


def test_evaluate_returns_metrics(small_cases):
    p = RiskScorePredictor().train(small_cases)
    metrics = p.evaluate(small_cases)
    assert "accuracy" in metrics
    assert "macro_f1" in metrics


def test_top_features_non_empty(small_cases):
    p = RiskScorePredictor().train(small_cases)
    results = p.predict(small_cases[:3])
    for r in results:
        assert len(r.top_features) > 0


def test_save_and_load(small_cases, tmp_path):
    p = RiskScorePredictor().train(small_cases)
    p.save_to_store(tmp_path)
    p2 = RiskScorePredictor().load(str(tmp_path / "risk_score.joblib"))
    results = p2.predict(small_cases[:1])
    assert len(results) == 1
    assert results[0].value in {"high", "medium", "low"}
