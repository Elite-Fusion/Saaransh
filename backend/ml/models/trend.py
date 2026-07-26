"""
Trend forecasting (regression over time).

The trend predictor answers "how many cases of crime head
X are likely to be registered in the next 30 days?" The
synthetic dataset has a flat distribution (no real
seasonality), so a simple linear regression over the
``(month_idx, crime_head_id)`` features is enough to give
plausible numbers for the demo.

The training input is the list of :class:`SyntheticCase`.
The target is the **count of cases per (crime_head, month)**
group — i.e. the predictor learns a per-head, per-month
intensity, not a per-row target.

Public surface
==============

* :class:`TrendPredictor`
* :meth:`train(cases)` — fits a
  :class:`sklearn.linear_model.Ridge` on a count-by-month
  matrix. The model is small and deterministic.
* :meth:`predict(rows)` — accepts a list of
  :class:`SyntheticCase` (or any object exposing
  ``CrimeMajorHeadName`` and ``month``) and returns one
  :class:`PredictionResult` per row.
* :meth:`evaluate(cases)` — MAE + R² of in-sample counts.

Why a Ridge, not Prophet
=========================

Prophet / statsmodels are out of scope (the plan
explicitly excludes them). Ridge gives a deterministic
linear model that the small synthetic dataset can fit
without overfitting, and the coefficients are easy to
inspect in the logs.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from backend.ml.models.base import (
    BaseSklearnPredictor,
    FeatureContribution,
    PredictionResult,
)
from backend.ml.preprocessing.synthetic_data import SyntheticCase


class TrendPredictor(BaseSklearnPredictor):
    """Linear regression for monthly per-head crime counts."""

    name = "trend"

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, cases: Sequence[SyntheticCase]) -> "TrendPredictor":
        from sklearn.linear_model import Ridge

        # Aggregate counts by (head, month_index). The
        # ``month_index`` is the number of months since the
        # first observation in ``cases``.
        if not cases:
            raise ValueError("TrendPredictor.train needs at least 1 case")
        first_month = min(c.CrimeRegisteredDate for c in cases).replace(day=1)
        # Build a sparse matrix: rows = (head, month) cells,
        # columns = [month_idx, head_id, head_one_hot...]
        heads = sorted({c.CrimeMajorHeadName for c in cases})
        head_id = {h: i for i, h in enumerate(heads)}
        counts: dict[tuple[str, int], int] = defaultdict(int)
        for c in cases:
            month_idx = (
                (c.CrimeRegisteredDate.year - first_month.year) * 12
                + (c.CrimeRegisteredDate.month - first_month.month)
            )
            counts[(c.CrimeMajorHeadName, month_idx)] += 1
        # Build X, y. We one-hot the head so the regression
        # has a separate slope per head.
        import numpy as np
        X_rows: list[list[float]] = []
        y_vals: list[int] = []
        for (head, month_idx), count in sorted(counts.items()):
            row = [float(month_idx)] + [
                1.0 if i == head_id[head] else 0.0
                for i in range(len(heads))
            ]
            X_rows.append(row)
            y_vals.append(int(count))
        X = np.asarray(X_rows, dtype=float)
        y = np.asarray(y_vals, dtype=float)
        model = Ridge(alpha=1.0, random_state=0)
        model.fit(X, y)
        self._model = model
        self._transformers = {
            "columns": ["month_idx"] + [f"head_{h}" for h in heads],
            "head_id": head_id,
            "heads": heads,
            "first_month": first_month.isoformat(),
        }
        return self

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, rows) -> list[PredictionResult]:
        if self._model is None:
            raise RuntimeError(
                "TrendPredictor.predict called before .train()/.load()"
            )
        import numpy as np

        heads = list(self._transformers["heads"])
        head_id: dict[str, int] = self._transformers["head_id"]
        first_month = date_from_iso(self._transformers["first_month"])
        X_rows: list[list[float]] = []
        for r in rows:
            d = getattr(r, "CrimeRegisteredDate", None)
            if d is None:
                month_idx = 0
            else:
                month_idx = (
                    (d.year - first_month.year) * 12
                    + (d.month - first_month.month)
                )
            head = getattr(r, "CrimeMajorHeadName", None)
            row = [float(month_idx)] + [
                1.0 if i == head_id.get(head, -1) else 0.0
                for i in range(len(heads))
            ]
            X_rows.append(row)
        X = np.asarray(X_rows, dtype=float)
        preds = self._model.predict(X)
        # Confidence: log1p-based clamping. A prediction of
        # 5 cases -> ~0.85, 20 cases -> ~0.99.
        import math
        out: list[PredictionResult] = []
        for i, value in enumerate(preds):
            v = max(0.0, float(value))
            confidence = min(1.0, math.log1p(v) / math.log(20.0))
            top = [
                FeatureContribution(
                    feature="month_idx",
                    value=float(X[i, 0]),
                    importance=0.5,
                ),
                FeatureContribution(
                    feature="head",
                    value=str(getattr(rows[i], "CrimeMajorHeadName", "?")),
                    importance=0.5,
                ),
            ]
            out.append(
                PredictionResult(
                    value=int(round(v)),
                    confidence=round(confidence, 4),
                    top_features=top,
                )
            )
        return out

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, cases: Sequence[SyntheticCase]) -> dict:
        from sklearn.metrics import mean_absolute_error, r2_score

        if self._model is None:
            raise RuntimeError("TrendPredictor not trained yet")
        # Reuse the training aggregation. Real production
        # code would do a holdout split; the training script
        # logs both train + test stats separately.
        if not cases:
            return {"mae": 0.0, "r2": 0.0}
        first_month = min(c.CrimeRegisteredDate for c in cases).replace(day=1)
        heads = list(self._transformers["heads"])
        head_id: dict[str, int] = self._transformers["head_id"]
        from collections import defaultdict
        counts: dict[tuple[str, int], int] = defaultdict(int)
        for c in cases:
            month_idx = (
                (c.CrimeRegisteredDate.year - first_month.year) * 12
                + (c.CrimeRegisteredDate.month - first_month.month)
            )
            counts[(c.CrimeMajorHeadName, month_idx)] += 1
        import numpy as np
        X_rows: list[list[float]] = []
        y_vals: list[int] = []
        for (head, month_idx), count in sorted(counts.items()):
            row = [float(month_idx)] + [
                1.0 if i == head_id[head] else 0.0
                for i in range(len(heads))
            ]
            X_rows.append(row)
            y_vals.append(int(count))
        X = np.asarray(X_rows, dtype=float)
        y_true = np.asarray(y_vals, dtype=float)
        y_pred = self._model.predict(X)
        return {
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "r2": float(r2_score(y_true, y_pred)),
        }

    def save_to_store(self, store_dir=None) -> None:
        from backend.ml.services.model_store import save_atomic, store_path

        path = store_path(self.name, store_dir)
        save_atomic(self, str(path))


def date_from_iso(s: str):
    """Tiny helper — re-imports the date class without
    polluting the module-level namespace."""
    from datetime import date
    return date.fromisoformat(s)


__all__ = ["TrendPredictor"]
