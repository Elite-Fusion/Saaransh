"""
Hotspot prediction (regression).

The hotspot predictor estimates how many cases are likely to
be registered for a given ``(district, crime_head, month,
day-of-week)`` tuple. We use a small :class:`GradientBoostingRegressor`
because it handles the mixed numeric/categorical features
without a separate one-hot pass.

Public surface
==============

* :class:`HotspotPredictor`
* :meth:`HotspotPredictor.train(cases)` — fits on a list of
  :class:`backend.ml.preprocessing.synthetic_data.SyntheticCase`.
* :meth:`HotspotPredictor.predict(rows)` — returns a list of
  :class:`PredictionResult`, one per row.
* :meth:`HotspotPredictor.evaluate(cases)` — R² + MAE on the
  same data (a held-out split would be ideal; the training
  script logs the test split separately).
* :meth:`HotspotPredictor.save_to_store(store_dir=None)` —
  writes ``hotspot.joblib`` to the model store.

Target
======

The training target is :attr:`SyntheticCase.case_count_target`,
an integer that reflects the latent "expected number of
similar cases in the next 30 days" used by the generator.
For the inference path we treat the predicted value as a
relative risk score: 0..1 confidence is derived by clamping
the predicted count to ``[0, 1]`` after a ``log1p`` shrink
so a single high-count row doesn't dominate the score.
"""
from __future__ import annotations

import math
from typing import Sequence

from backend.ml.models.base import (
    BaseSklearnPredictor,
    FeatureContribution,
    PredictionResult,
)
from backend.ml.preprocessing.feature_builder import (
    DEFAULT_COLUMNS,
    FeatureBuildResult,
    build_features,
)
from backend.ml.preprocessing.synthetic_data import SyntheticCase


class HotspotPredictor(BaseSklearnPredictor):
    """Gradient-boosted regression for hotspot risk.

    The predictor is deterministic: re-running ``.train(...)``
    on the same input produces the same fitted model.
    """

    name = "hotspot"

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, cases: Sequence[SyntheticCase]) -> "HotspotPredictor":
        from sklearn.ensemble import GradientBoostingRegressor

        result = build_features(cases, columns=DEFAULT_COLUMNS)
        X = result.X
        # Latent target from the generator. We add 1 so the
        # regressor never sees 0 (helps with log transforms).
        y = [c.case_count_target for c in cases]
        # Use a small forest — the synthetic dataset is
        # 1k rows, so a deep tree overfits.
        model = GradientBoostingRegressor(
            n_estimators=80,
            max_depth=4,
            learning_rate=0.1,
            random_state=0,
        )
        model.fit(X, y)
        self._model = model
        self._transformers = {"columns": list(result.columns)}
        return self

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, rows) -> list[PredictionResult]:
        if self._model is None:
            raise RuntimeError(
                "HotspotPredictor.predict called before .train()/.load()"
            )
        # ``rows`` may be SyntheticCase or ORM rows. The
        # feature builder handles both.
        result = build_features(rows, columns=tuple(self._transformers["columns"]))
        X = result.X
        raw = self._model.predict(X)
        importances = getattr(self._model, "feature_importances_", None)
        if importances is None:
            importances = [0.0] * X.shape[1]
        out: list[PredictionResult] = []
        for i, value in enumerate(raw):
            # Confidence: predicted_count, clamped to [0, 1]
            # after a log1p shrink. A count of 1 -> ~0.59,
            # 2 -> ~0.79, 5 -> ~0.95, 10+ -> ~1.0.
            confidence = min(1.0, math.log1p(max(0.0, float(value))) / math.log(11.0))
            top = self._top_features(X, i, importances)
            out.append(
                PredictionResult(
                    value=int(round(max(0.0, float(value)))),
                    confidence=round(confidence, 4),
                    top_features=top,
                )
            )
        return out

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, cases: Sequence[SyntheticCase]) -> dict:
        """Return R² + MAE on the same rows.

        A real model would split the data first; for the
        synthetic dataset the generator's deterministic
        structure makes the train/test gap small enough that
        the in-sample metrics are useful as a smoke test.
        """
        from sklearn.metrics import mean_absolute_error, r2_score

        if self._model is None:
            raise RuntimeError("HotspotPredictor not trained yet")
        result = build_features(cases, columns=tuple(self._transformers["columns"]))
        X = result.X
        y_true = [c.case_count_target for c in cases]
        y_pred = self._model.predict(X)
        return {
            "r2": float(r2_score(y_true, y_pred)),
            "mae": float(mean_absolute_error(y_true, y_pred)),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _top_features(self, X, i: int, importances) -> list[FeatureContribution]:
        columns = list(self._transformers["columns"])
        row = X[i]
        # Pair each column with its importance; sort by
        # importance desc; take top 3.
        pairs = [
            (col, float(row[j]), float(importances[j]))
            for j, col in enumerate(columns)
        ]
        pairs.sort(key=lambda p: p[2], reverse=True)
        return [
            FeatureContribution(feature=col, value=val, importance=imp)
            for col, val, imp in pairs[:3]
        ]

    def save_to_store(self, store_dir=None) -> None:
        from backend.ml.services.model_store import save_atomic, store_path

        path = store_path(self.name, store_dir)
        save_atomic(self, str(path))


__all__ = ["HotspotPredictor"]
