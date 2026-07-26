"""
Repeat-offender prediction (binary classification).

The predictor answers the question "given an accused
person's profile, will they reoffend within 12 months?"
It is implemented as a :class:`RandomForestClassifier` over
four features:

* ``prior_count`` — number of prior cases the accused was
  involved in (the strongest signal in the synthetic data).
* ``age`` — younger accused reoffend more.
* ``crime_head`` — categorical crime group.
* ``gravity`` — categorical gravity bucket.

Public surface
==============

* :class:`RepeatOffenderPredictor`
* :meth:`train(cases, accused)` — fits on the synthetic
  pair of ``(case, accused)`` lists.
* :meth:`predict(accused)` — returns a list of
  :class:`PredictionResult` ordered like ``accused``.
* :meth:`evaluate(cases, accused)` — accuracy + precision +
  recall on the same data.

The "value" field of the result is the predicted class
(``0`` or ``1``). The "confidence" is the probability the
classifier assigned to the predicted class.
"""
from __future__ import annotations

from typing import Sequence

from backend.ml.models.base import (
    BaseSklearnPredictor,
    FeatureContribution,
    PredictionResult,
)
from backend.ml.preprocessing.synthetic_data import (
    SyntheticAccused,
    SyntheticCase,
)


# Column order for the repeat-offender matrix. Kept as a
# module-level constant so callers can rebuild an inference
# row in the same order.
REPEAT_COLUMNS: tuple[str, ...] = (
    "prior_count",
    "age",
    "is_known_criminal",
    "crime_head_id",
    "gravity_id",
)


def _accused_to_row(
    a: SyntheticAccused,
    encoders: dict[str, dict[str, int]],
) -> list[float]:
    """One feature row for a synthetic accused."""
    head_table = encoders.setdefault("head", {})
    grav_table = encoders.setdefault("grav", {})
    h = a.primary_crime_head
    g = a.primary_gravity
    if h not in head_table:
        head_table[h] = len(head_table)
    if g not in grav_table:
        grav_table[g] = len(grav_table)
    return [
        float(a.prior_count),
        float(a.AgeYear),
        1.0 if a.is_known_criminal else 0.0,
        float(head_table[h]),
        float(grav_table[g]),
    ]


class RepeatOffenderPredictor(BaseSklearnPredictor):
    """Random-forest binary classifier for recidivism risk."""

    name = "repeat_offender"

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        cases: Sequence[SyntheticCase],
        accused: Sequence[SyntheticAccused],
    ) -> "RepeatOffenderPredictor":
        from sklearn.ensemble import RandomForestClassifier

        # ``cases`` is unused at training time; the target
        # lives on the accused. We still accept it so the
        # training script can pass both lists in a single
        # call.
        del cases

        encoders: dict[str, dict[str, int]] = {}
        rows = [_accused_to_row(a, encoders) for a in accused]
        y = [a.reoffended for a in accused]
        import numpy as np
        X = np.asarray(rows, dtype=float)
        y_arr = np.asarray(y, dtype=int)
        model = RandomForestClassifier(
            n_estimators=80,
            max_depth=8,
            random_state=0,
            class_weight="balanced",
        )
        model.fit(X, y_arr)
        self._model = model
        self._transformers = {
            "columns": list(REPEAT_COLUMNS),
            "encoders": encoders,
        }
        return self

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, accused) -> list[PredictionResult]:
        if self._model is None:
            raise RuntimeError(
                "RepeatOffenderPredictor.predict called before .train()/.load()"
            )
        # Build a *new* encoder pass so we don't mutate the
        # training encoders. Then re-encode using the
        # training encoders so the codes match.
        import numpy as np

        encoders = self._transformers["encoders"]
        rows: list[list[float]] = []
        for a in accused:
            # The training encoders are canonical — look up
            # directly. Unknown categories fall back to -1.
            h = a.primary_crime_head
            g = a.primary_gravity
            rows.append([
                float(a.prior_count),
                float(a.AgeYear),
                1.0 if a.is_known_criminal else 0.0,
                float(encoders["head"].get(h, -1)),
                float(encoders["grav"].get(g, -1)),
            ])
        X = np.asarray(rows, dtype=float)
        probs = self._model.predict_proba(X)
        preds = self._model.predict(X)
        importances = getattr(self._model, "feature_importances_", None)
        if importances is None:
            importances = [0.0] * X.shape[1]
        out: list[PredictionResult] = []
        for i, pred in enumerate(preds):
            # confidence is the probability the model gave to
            # the predicted class.
            conf = float(probs[i, int(pred)])
            # Top features: pair the row with importances.
            pairs = list(zip(REPEAT_COLUMNS, X[i], importances))
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
                    value=int(pred),
                    confidence=round(conf, 4),
                    top_features=top,
                )
            )
        return out

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        cases: Sequence[SyntheticCase],
        accused: Sequence[SyntheticAccused],
    ) -> dict:
        from sklearn.metrics import (
            accuracy_score,
            precision_score,
            recall_score,
        )

        del cases
        if self._model is None:
            raise RuntimeError("RepeatOffenderPredictor not trained yet")
        encoders = self._transformers["encoders"]
        rows = []
        for a in accused:
            rows.append([
                float(a.prior_count),
                float(a.AgeYear),
                1.0 if a.is_known_criminal else 0.0,
                float(encoders["head"].get(a.primary_crime_head, -1)),
                float(encoders["grav"].get(a.primary_gravity, -1)),
            ])
        import numpy as np
        X = np.asarray(rows, dtype=float)
        y_true = [a.reoffended for a in accused]
        y_pred = self._model.predict(X)
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(
                precision_score(y_true, y_pred, zero_division=0)
            ),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        }

    def save_to_store(self, store_dir=None) -> None:
        from backend.ml.services.model_store import save_atomic, store_path

        path = store_path(self.name, store_dir)
        save_atomic(self, str(path))


__all__ = ["RepeatOffenderPredictor", "REPEAT_COLUMNS"]
