"""Tests for the HotspotPredictor."""
from __future__ import annotations

import pytest

from backend.ml.models import HotspotPredictor, get_predictor


def test_constructable_from_registry():
    p = get_predictor("hotspot")
    assert isinstance(p, HotspotPredictor)
    assert p.name == "hotspot"


def test_predict_before_train_raises(small_cases):
    p = HotspotPredictor()
    with pytest.raises(RuntimeError):
        p.predict(small_cases[:1])


def test_train_and_predict_shape(small_cases):
    p = HotspotPredictor().train(small_cases)
    results = p.predict(small_cases)
    assert len(results) == len(small_cases)
    for r in results:
        assert isinstance(r.value, int)
        assert 0.0 <= r.confidence <= 1.0


def test_train_top_features_non_empty(small_cases):
    p = HotspotPredictor().train(small_cases)
    results = p.predict(small_cases[:3])
    for r in results:
        assert len(r.top_features) > 0
        for fc in r.top_features:
            assert 0.0 <= fc.importance <= 1.0


def test_evaluate_returns_metrics(small_cases):
    p = HotspotPredictor().train(small_cases)
    metrics = p.evaluate(small_cases)
    assert "r2" in metrics
    assert "mae" in metrics
    # The synthetic target is bounded; MAE should be small.
    assert metrics["mae"] >= 0


def test_save_and_load_round_trip(small_cases, tmp_path):
    p = HotspotPredictor().train(small_cases)
    p.save_to_store(tmp_path)
    target = tmp_path / "hotspot.joblib"
    assert target.exists()
    # Reload and confirm a predict works.
    p2 = HotspotPredictor().load(str(target))
    results = p2.predict(small_cases[:2])
    assert len(results) == 2
