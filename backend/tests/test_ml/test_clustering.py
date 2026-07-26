"""Tests for the ClusteringPredictor."""
from __future__ import annotations

import pytest

from backend.ml.models import ClusteringPredictor, get_predictor


def test_constructable_from_registry():
    p = get_predictor("clustering")
    assert isinstance(p, ClusteringPredictor)
    assert p.name == "clustering"
    assert p.n_clusters == 5


def test_predict_before_train_raises(small_cases):
    p = ClusteringPredictor()
    with pytest.raises(RuntimeError):
        p.predict(small_cases[:1])


def test_train_empty_raises():
    with pytest.raises(ValueError):
        ClusteringPredictor().train([])


def test_train_and_predict_returns_clusters(small_cases):
    p = ClusteringPredictor().train(small_cases)
    results = p.predict(small_cases)
    assert len(results) == len(small_cases)
    cluster_ids = {r.value for r in results}
    # Should have at least 2 distinct clusters over 50 rows.
    assert len(cluster_ids) >= 2
    assert all(0 <= c < p.n_clusters for c in cluster_ids)


def test_evaluate_returns_silhouette(small_cases):
    p = ClusteringPredictor().train(small_cases)
    metrics = p.evaluate(small_cases)
    assert "k" in metrics
    assert "inertia" in metrics
    assert "silhouette" in metrics
    assert metrics["k"] == p.n_clusters
    # silhouette can be negative on a degenerate dataset,
    # but the metric should always be present.
    assert isinstance(metrics["silhouette"], float)


def test_evidence_attached_to_prediction(small_cases):
    p = ClusteringPredictor().train(small_cases)
    results = p.predict(small_cases[:1])
    assert len(results) == 1
    assert results[0].evidence  # the cluster label is grounded in evidence


def test_save_and_load(small_cases, tmp_path):
    p = ClusteringPredictor().train(small_cases)
    p.save_to_store(tmp_path)
    p2 = ClusteringPredictor().load(str(tmp_path / "clustering.joblib"))
    assert p2.n_clusters == p.n_clusters
