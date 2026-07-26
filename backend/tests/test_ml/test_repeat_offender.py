"""Tests for the RepeatOffenderPredictor."""
from __future__ import annotations

import pytest

from backend.ml.models import RepeatOffenderPredictor, get_predictor


def test_constructable_from_registry():
    p = get_predictor("repeat_offender")
    assert isinstance(p, RepeatOffenderPredictor)
    assert p.name == "repeat_offender"


def test_predict_before_train_raises(small_accused):
    p = RepeatOffenderPredictor()
    with pytest.raises(RuntimeError):
        p.predict(small_accused[:1])


def test_train_and_predict_shape(small_cases, small_accused):
    p = RepeatOffenderPredictor().train(small_cases, small_accused)
    results = p.predict(small_accused)
    assert len(results) == len(small_accused)
    for r in results:
        assert r.value in (0, 1)
        assert 0.0 <= r.confidence <= 1.0


def test_evaluate_metrics_present(small_cases, small_accused):
    p = RepeatOffenderPredictor().train(small_cases, small_accused)
    metrics = p.evaluate(small_cases, small_accused)
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics


def test_top_features_sorted_by_importance(small_cases, small_accused):
    p = RepeatOffenderPredictor().train(small_cases, small_accused)
    results = p.predict(small_accused[:3])
    for r in results:
        if len(r.top_features) >= 2:
            importances = [fc.importance for fc in r.top_features]
            assert importances == sorted(importances, reverse=True)


def test_save_and_load(small_cases, small_accused, tmp_path):
    p = RepeatOffenderPredictor().train(small_cases, small_accused)
    p.save_to_store(tmp_path)
    p2 = RepeatOffenderPredictor().load(str(tmp_path / "repeat_offender.joblib"))
    results = p2.predict(small_accused[:1])
    assert len(results) == 1
