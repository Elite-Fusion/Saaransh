"""Tests for the SimilarityPredictor."""
from __future__ import annotations

import pytest

from backend.ml.models import SimilarityPredictor, get_predictor


def test_constructable_from_registry():
    p = get_predictor("similarity")
    assert isinstance(p, SimilarityPredictor)
    assert p.name == "similarity"


def test_predict_before_train_raises(small_cases):
    p = SimilarityPredictor()
    with pytest.raises(RuntimeError):
        p.predict(small_cases[0])


def test_train_empty_raises():
    with pytest.raises(ValueError):
        SimilarityPredictor().train([])


def test_train_and_predict_returns_top_k(small_cases):
    p = SimilarityPredictor().train(small_cases)
    results = p.predict(small_cases[0], top_k=5)
    assert 1 <= len(results) <= 5
    for r in results:
        assert isinstance(r.value, int)
        # The score is a cosine value in [0, 1].
        assert 0.0 <= r.confidence <= 1.0
        assert r.evidence  # similar cases are grounded in evidence


def test_excludes_self_from_results(small_cases):
    p = SimilarityPredictor().train(small_cases)
    results = p.predict(small_cases[0], top_k=10)
    returned_ids = {r.value for r in results}
    assert small_cases[0].CaseMasterID not in returned_ids


def test_empty_brief_facts_returns_empty():
    from types import SimpleNamespace
    from backend.ml.models import SimilarityPredictor
    from backend.ml.preprocessing.synthetic_data import generate_synthetic_cases
    cases = generate_synthetic_cases(n=20, seed=42)
    p = SimilarityPredictor().train(cases)
    q = SimpleNamespace(BriefFacts="", CaseMasterID=999)
    assert p.predict(q, top_k=5) == []


def test_evaluate_returns_coverage_and_hit_rate(small_cases):
    p = SimilarityPredictor().train(small_cases)
    metrics = p.evaluate(small_cases)
    assert "coverage" in metrics
    assert "hit_rate" in metrics
    assert 0.0 <= metrics["coverage"] <= 1.0
    assert 0.0 <= metrics["hit_rate"] <= 1.0


def test_save_and_load(small_cases, tmp_path):
    p = SimilarityPredictor().train(small_cases)
    p.save_to_store(tmp_path)
    p2 = SimilarityPredictor().load(str(tmp_path / "similarity.joblib"))
    assert len(p2._corpus) == len(small_cases)
