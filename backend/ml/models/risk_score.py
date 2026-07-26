"""
Per-FIR risk score (multi-class classification).

The risk-score predictor classifies each FIR into one of
three risk buckets — ``high``, ``medium``, ``low`` — using
the same features as the repeat-offender classifier plus
spatial features (``latitude``, ``longitude``). The model
is a :class:`RandomForestClassifier`.

Public surface
==============

* :class:`RiskScorePredictor`
* :meth:`train(cases)` — fits on the synthetic dataset.
* :meth:`predict(rows)` — returns a list of
  :class:`PredictionResult`, one per row. ``value`` is the
  predicted label (``"high"``, ``"medium"``, or ``"low"``).
  ``confidence`` is the model's probability for the
  predicted class.
* :meth:`evaluate(cases)` — accuracy + macro-F1.

The target labels come from :attr:`SyntheticCase.risk_label`,
which the generator populates deterministically: high
recidivism + violent crime -> ``high``; recidivism without
violent crime -> ``medium``; otherwise ``low``.
"""
from __future__ import annotations

from typing import Sequence

from backend.ml.models.base import (
    BaseSklearnPredictor,
    FeatureContribution,
    PredictionResult,
)
from backend.ml.preprocessing.synthetic_data import SyntheticCase


RISK_COLUMNS: tuple[str, ...] = (
    "month",
    "dow",
    "crime_head_id",
    "crime_sub_head_id",
    "gravity_id",
    "is_series_crime",
    "latitude_norm",
    "longitude_norm",
)


def _row_for(c: SyntheticCase, encoders: dict[str, dict[str, int]]) -> list[float]:
    head = c.CrimeMajorHeadName
    sub = c.CrimeMinorHeadName
    grav = c.GravityName
    enc = encoders.setdefault("head", {})
    enc_s = encoders.setdefault("sub", {})
    enc_g = encoders.setdefault("grav", {})
    enc.setdefault(head, len(enc))
    enc_s.setdefault(sub, len(enc_s))
    enc_g.setdefault(grav, len(enc_g))
    return [
        float(c.month),
        float(c.dow),
        float(enc[head]),
        float(enc_s[sub]),
        float(enc_g[grav]),
        1.0 if c.is_series_crime else 0.0,
        (c.latitude - 11.5) / (18.0 - 11.5),
        (c.longitude - 74.0) / (78.5 - 74.0),
    ]


class RiskScorePredictor(BaseSklearnPredictor):
    """Random-forest risk-bucket classifier."""

    name = "risk_score"

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, cases: Sequence[SyntheticCase]) -> "RiskScorePredictor":
        from sklearn.ensemble import RandomForestClassifier

        if not cases:
            raise ValueError("RiskScorePredictor.train needs at least 1 case")
        encoders: dict[str, dict[str, int]] = {}
        X = [_row_for(c, encoders) for c in cases]
        y = [c.risk_label for c in cases]
        import numpy as np
        X_arr = np.asarray(X, dtype=float)
        # The labels are string-typed; the classifier
        # handles that natively.
        model = RandomForestClassifier(
            n_estimators=80,
            max_depth=8,
            random_state=0,
            class_weight="balanced",
        )
        model.fit(X_arr, y)
        self._model = model
        self._transformers = {
            "columns": list(RISK_COLUMNS),
            "encoders": encoders,
        }
        return self

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, rows) -> list[PredictionResult]:
        if self._model is None:
            raise RuntimeError(
                "RiskScorePredictor.predict called before .train()/.load()"
            )
        encoders = self._transformers["encoders"]
        X = [_inference_row(r, encoders) for r in rows]
        import numpy as np
        X_arr = np.asarray(X, dtype=float)
        preds = self._model.predict(X_arr)
        probs = self._model.predict_proba(X_arr)
        classes = list(self._model.classes_)
        importances = getattr(self._model, "feature_importances_", None)
        if importances is None:
            importances = [0.0] * X_arr.shape[1]
        out: list[PredictionResult] = []
        for i, pred in enumerate(preds):
            cls_idx = classes.index(pred)
            conf = float(probs[i, cls_idx])
            pairs = list(zip(RISK_COLUMNS, X_arr[i], importances))
            pairs.sort(key=lambda p: p[2], reverse=True)
            top = [
                FeatureContribution(
                    feature=col,
                    value=float(val),
                    importance=float(imp),
                )
                for col, val, imp in pairs[:3]
            ]
            out.append(
                PredictionResult(
                    value=str(pred),
                    confidence=round(conf, 4),
                    top_features=top,
                )
            )
        return out

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, cases: Sequence[SyntheticCase]) -> dict:
        from sklearn.metrics import accuracy_score, f1_score

        if self._model is None:
            raise RuntimeError("RiskScorePredictor not trained yet")
        encoders = self._transformers["encoders"]
        X = [_inference_row(c, encoders) for c in cases]
        import numpy as np
        X_arr = np.asarray(X, dtype=float)
        y_true = [c.risk_label for c in cases]
        y_pred = self._model.predict(X_arr)
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        }

    def save_to_store(self, store_dir=None) -> None:
        from backend.ml.services.model_store import save_atomic, store_path

        path = store_path(self.name, store_dir)
        save_atomic(self, str(path))


def _inference_row(row, encoders: dict[str, dict[str, int]]) -> list[float]:
    """Build a row using the training encoders. Accepts
    either a :class:`SyntheticCase` or an ORM row with
    matching attributes."""
    head = getattr(row, "CrimeMajorHeadName", None)
    sub = getattr(row, "CrimeMinorHeadName", None)
    grav = getattr(row, "GravityName", None)
    month = getattr(row, "month", 0)
    dow = getattr(row, "dow", 0)
    is_series = bool(getattr(row, "is_series_crime", False))
    lat = getattr(row, "latitude", 14.5)
    lng = getattr(row, "longitude", 76.0)
    return [
        float(month or 1),
        float(dow or 0),
        float(encoders["head"].get(head, -1)),
        float(encoders["sub"].get(sub, -1)),
        float(encoders["grav"].get(grav, -1)),
        1.0 if is_series else 0.0,
        (lat - 11.5) / (18.0 - 11.5),
        (lng - 74.0) / (78.5 - 74.0),
    ]


__all__ = ["RiskScorePredictor", "RISK_COLUMNS"]
