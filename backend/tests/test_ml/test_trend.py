"""Tests for the TrendPredictor."""
from __future__ import annotations

import pytest

from backend.ml.models import TrendPredictor, get_predictor


def test_constructable_from_registry():
    p = get_predictor("trend")
    assert isinstance(p, TrendPredictor)
    assert p.name == "trend"


def test_predict_before_train_raises(small_cases):
    p = TrendPredictor()
    with pytest.raises(RuntimeError):
        p.predict(small_cases[:1])


def test_train_empty_raises():
    with pytest.raises(ValueError):
        TrendPredictor().train([])


def test_train_and_predict(small_cases):
    p = TrendPredictor().train(small_cases)
    results = p.predict(small_cases)
    assert len(results) == len(small_cases)
    for r in results:
        assert isinstance(r.value, int)
        assert r.value >= 0
        assert 0.0 <= r.confidence <= 1.0


def test_evaluate_returns_metrics(small_cases):
    p = TrendPredictor().train(small_cases)
    metrics = p.evaluate(small_cases)
    assert "mae" in metrics
    assert "r2" in metrics


def test_save_and_load(small_cases, tmp_path):
    p = TrendPredictor().train(small_cases)
    p.save_to_store(tmp_path)
    p2 = TrendPredictor().load(str(tmp_path / "trend.joblib"))
    assert p2.predict(small_cases[:1])
