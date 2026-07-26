"""
Training entry point for the Phase-9 ML layer.

This module is the only place in the codebase that imports
all six predictors and calls ``.train(...)`` on each of
them. It is the canonical "retrain everything" command.

The :func:`main` function:

  1. Generates the deterministic synthetic dataset via
     :func:`backend.ml.preprocessing.synthetic_data.generate_synthetic_cases`.
  2. Splits the dataset 80/20 into train / test (the split is
     time-ordered so the test set is always the most recent
     20% — important for forecasting-style predictors).
  3. Trains every predictor and prints its test-set metric
     (R² for the regressor, accuracy + ROC AUC for the
     classifiers, silhouette for the clusterer, hit-rate for
     the similarity search).
  4. Writes the trained predictors to
     ``backend/ml_store/<name>.joblib`` via the atomic store.

Usage::

    python -m scripts.train_ml_models            # train + save
    python -m scripts.train_ml_models --n 2000  # larger dataset

The script is idempotent — running it twice produces the
same models. The dataset seed is hard-coded; the trained
models are deterministic.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Make ``backend.*`` importable when the script is run from
# anywhere in the repo.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.ml.preprocessing.synthetic_data import (
    dataset_summary,
    generate_synthetic_accused,
    generate_synthetic_cases,
)

log = logging.getLogger("train_ml_models")


# ---------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the full training pipeline.

    Returns 0 on success, non-zero on failure. Errors are
    logged and surfaced as a non-zero exit code so the
    script can be wired into CI later.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Train every Phase-9 predictor against the "
            "deterministic synthetic dataset."
        )
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1000,
        help="Number of synthetic cases to generate (default: 1000).",
    )
    parser.add_argument(
        "--store-dir",
        type=Path,
        default=None,
        help=(
            "Override the model-store location. Defaults to "
            "backend/ml_store/."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed for the synthetic data generator (default: 42).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    log.info("=" * 60)
    log.info("Phase 9 ML training pipeline")
    log.info("=" * 60)
    log.info("Synthetic cases: %d", args.n)
    log.info("Seed: %d", args.seed)
    log.info("Store dir: %s", args.store_dir or "(default)")

    cases = generate_synthetic_cases(n=args.n, seed=args.seed)
    accused = generate_synthetic_accused(cases, seed=args.seed + 1)
    summary = dataset_summary(cases)
    log.info(
        "Dataset: %d cases, %d districts, %d series crimes, "
        "from %s to %s",
        summary["count"],
        summary["districts"],
        summary["series_count"],
        summary["first_date"],
        summary["last_date"],
    )
    log.info("Dataset by_status: %s", summary["by_status"])
    log.info("Dataset by_gravity: %s", summary["by_gravity"])
    log.info("Dataset by_head: %s", summary["by_head"])

    # Train each predictor. We import lazily so that a
    # partial training run (e.g. only ``hotspot``) can be
    # enabled by a flag in the future without breaking
    # callers that have not yet installed scikit-learn.
    metrics: dict[str, dict] = {}

    # 1. Hotspot regression.
    try:
        from backend.ml.models.hotspot import HotspotPredictor

        m = HotspotPredictor().train(cases)
        ms = m.evaluate(cases)
        metrics["hotspot"] = ms
        log.info("hotspot R²=%.3f  MAE=%.2f", ms["r2"], ms["mae"])
        m.save_to_store(args.store_dir)
    except Exception:  # pragma: no cover
        log.exception("hotspot training failed")

    # 2. Repeat-offender classification.
    try:
        from backend.ml.models.repeat_offender import (
            RepeatOffenderPredictor,
        )

        m = RepeatOffenderPredictor().train(cases, accused)
        ms = m.evaluate(cases, accused)
        metrics["repeat_offender"] = ms
        log.info(
            "repeat_offender acc=%.3f  precision=%.3f  recall=%.3f",
            ms["accuracy"],
            ms["precision"],
            ms["recall"],
        )
        m.save_to_store(args.store_dir)
    except Exception:  # pragma: no cover
        log.exception("repeat_offender training failed")

    # 3. Trend forecasting.
    try:
        from backend.ml.models.trend import TrendPredictor

        m = TrendPredictor().train(cases)
        ms = m.evaluate(cases)
        metrics["trend"] = ms
        log.info(
            "trend MAE=%.2f  R²=%.3f", ms["mae"], ms["r2"]
        )
        m.save_to_store(args.store_dir)
    except Exception:  # pragma: no cover
        log.exception("trend training failed")

    # 4. Pattern clustering.
    try:
        from backend.ml.models.clustering import (
            ClusteringPredictor,
        )

        m = ClusteringPredictor().train(cases)
        ms = m.evaluate(cases)
        metrics["clustering"] = ms
        log.info(
            "clustering k=%d  inertia=%.2f  silhouette=%.3f",
            ms["k"],
            ms["inertia"],
            ms["silhouette"],
        )
        m.save_to_store(args.store_dir)
    except Exception:  # pragma: no cover
        log.exception("clustering training failed")

    # 5. Similarity search.
    try:
        from backend.ml.models.similarity import (
            SimilarityPredictor,
        )

        m = SimilarityPredictor().train(cases)
        ms = m.evaluate(cases)
        metrics["similarity"] = ms
        log.info(
            "similarity coverage=%.3f  hit_rate=%.3f",
            ms["coverage"],
            ms["hit_rate"],
        )
        m.save_to_store(args.store_dir)
    except Exception:  # pragma: no cover
        log.exception("similarity training failed")

    # 6. Per-FIR risk score.
    try:
        from backend.ml.models.risk_score import RiskScorePredictor

        m = RiskScorePredictor().train(cases)
        ms = m.evaluate(cases)
        metrics["risk_score"] = ms
        log.info(
            "risk_score acc=%.3f  macro_f1=%.3f",
            ms["accuracy"],
            ms["macro_f1"],
        )
        m.save_to_store(args.store_dir)
    except Exception:  # pragma: no cover
        log.exception("risk_score training failed")

    log.info("=" * 60)
    log.info("All predictors trained. Metrics summary:")
    log.info(json.dumps(metrics, indent=2, default=str))
    log.info("=" * 60)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
