"""
Canonical "retrain everything" entry point.

This module is the in-package equivalent of
:mod:`scripts.train_ml_models`. It exists so the training
pipeline can be invoked as ::

    python -m backend.ml.training.train_all

without depending on the ``scripts/`` directory being on
``PYTHONPATH``. The two scripts share the same logic — the
script in :mod:`scripts` is a thin wrapper that wires up
``sys.path`` for direct invocation.

The function logs progress and returns 0 on success. Each
predictor is trained in its own ``try/except`` so a failure
in one (e.g. scikit-learn not installed for that model
class) does not block the others.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from backend.ml.preprocessing.synthetic_data import (
    dataset_summary,
    generate_synthetic_accused,
    generate_synthetic_cases,
)

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Train every Phase-9 predictor.",
    )
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--store-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    cases = generate_synthetic_cases(n=args.n, seed=args.seed)
    accused = generate_synthetic_accused(cases, seed=args.seed + 1)
    summary = dataset_summary(cases)
    log.info(
        "Dataset: %d cases, %d districts, %d series",
        summary["count"], summary["districts"], summary["series_count"],
    )

    metrics: dict[str, dict] = {}

    # 1. Hotspot regression
    try:
        from backend.ml.models.hotspot import HotspotPredictor
        m = HotspotPredictor().train(cases)
        ms = m.evaluate(cases)
        metrics["hotspot"] = ms
        log.info("hotspot R²=%.3f MAE=%.2f", ms["r2"], ms["mae"])
        m.save_to_store(args.store_dir)
    except Exception:  # pragma: no cover
        log.exception("hotspot training failed")

    # 2. Repeat offender
    try:
        from backend.ml.models.repeat_offender import RepeatOffenderPredictor
        m = RepeatOffenderPredictor().train(cases, accused)
        ms = m.evaluate(cases, accused)
        metrics["repeat_offender"] = ms
        log.info("repeat_offender acc=%.3f", ms["accuracy"])
        m.save_to_store(args.store_dir)
    except Exception:  # pragma: no cover
        log.exception("repeat_offender training failed")

    # 3. Trend
    try:
        from backend.ml.models.trend import TrendPredictor
        m = TrendPredictor().train(cases)
        ms = m.evaluate(cases)
        metrics["trend"] = ms
        log.info("trend MAE=%.2f R²=%.3f", ms["mae"], ms["r2"])
        m.save_to_store(args.store_dir)
    except Exception:  # pragma: no cover
        log.exception("trend training failed")

    # 4. Clustering
    try:
        from backend.ml.models.clustering import ClusteringPredictor
        m = ClusteringPredictor().train(cases)
        ms = m.evaluate(cases)
        metrics["clustering"] = ms
        log.info("clustering k=%d silhouette=%.3f",
                 ms["k"], ms["silhouette"])
        m.save_to_store(args.store_dir)
    except Exception:  # pragma: no cover
        log.exception("clustering training failed")

    # 5. Similarity
    try:
        from backend.ml.models.similarity import SimilarityPredictor
        m = SimilarityPredictor().train(cases)
        ms = m.evaluate(cases)
        metrics["similarity"] = ms
        log.info("similarity coverage=%.3f hit_rate=%.3f",
                 ms["coverage"], ms["hit_rate"])
        m.save_to_store(args.store_dir)
    except Exception:  # pragma: no cover
        log.exception("similarity training failed")

    # 6. Risk score
    try:
        from backend.ml.models.risk_score import RiskScorePredictor
        m = RiskScorePredictor().train(cases)
        ms = m.evaluate(cases)
        metrics["risk_score"] = ms
        log.info("risk_score acc=%.3f", ms["accuracy"])
        m.save_to_store(args.store_dir)
    except Exception:  # pragma: no cover
        log.exception("risk_score training failed")

    log.info("Done. Metrics: %s", json.dumps(metrics, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
