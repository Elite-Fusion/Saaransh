"""
Predictor protocol and base classes.

Every Phase-9 predictor follows the same contract:

  * :meth:`train` consumes a 2-D numpy array of features and
    (when relevant) a target vector. The predictor is **not
    responsible** for splitting the data — the training script
    in :mod:`backend.ml.training.train_all` does that.
  * :meth:`predict` consumes a 2-D array and returns a list
    of :class:`PredictionResult` objects. The result list has
    the same length as the input's first axis.
  * :meth:`save` and :meth:`load` round-trip the trained
    model through :mod:`joblib`. They never touch the
    database.

The protocol is small on purpose — it leaves room for
predictors that need a fitted scaler (e.g. the risk-score
classifier) and predictors that don't (e.g. the similarity
search, which only needs the source rows).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class FeatureContribution:
    """One row in a prediction's explanation.

    Attributes:
        feature: The feature name (e.g. ``"prior_count"``).
        value: The feature's value for the predicted row.
        importance: A normalised importance score in ``[0, 1]``.
            The exact semantics depend on the predictor (a
            Random Forest ``feature_importances_`` entry, the
            distance to a KMeans centroid, etc.). The values
            within a single :class:`PredictionResult` are
            comparable but not necessarily across predictors.
    """

    feature: str
    value: float | int | str | None
    importance: float


@dataclass(frozen=True)
class EvidenceItem:
    """A supporting case the prediction can be cross-checked
    against. Used by every predictor that can ground its answer
    in the source data (e.g. the similarity search, the
    repeat-offender classifier).
    """

    case_id: int | None = None
    fir_number: str | None = None
    label: str = ""


@dataclass(frozen=True)
class PredictionResult:
    """The output of every Phase-9 predictor.

    Attributes:
        value: The headline value. Type depends on the
            predictor (int for risk score, str for cluster id,
            list of similar case ids for similarity, etc.).
        confidence: A normalised score in ``[0, 1]``. The
            semantics differ by predictor — a probability
            (Random Forest ``predict_proba``), a silhouette-
            style similarity, or an aggregated R²-derived
            number. The score is always comparable **within**
            a single predictor.
        top_features: The most important features for this
            prediction, sorted by importance descending. The
            first three are surfaced to the frontend.
        evidence: Optional supporting rows. Empty when the
            predictor cannot ground its answer.
    """

    value: Any
    confidence: float
    top_features: list[FeatureContribution] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)


# ---------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------


@runtime_checkable
class Predictor(Protocol):
    """The contract every Phase-9 predictor implements.

    Implementations are normally :class:`BaseSklearnPredictor`
    subclasses. Tests may use a simple in-memory stub.
    """

    name: str

    def train(self, X: Any, y: Any = None) -> "Predictor":
        """Fit the underlying model. Returns ``self``."""
        ...

    def predict(self, X: Any) -> list[PredictionResult]:
        """Run inference on a 2-D feature matrix."""
        ...

    def save(self, path: str) -> None:
        """Persist the trained model to ``path``."""
        ...

    def load(self, path: str) -> "Predictor":
        """Load a previously-saved model from ``path``."""
        ...


# ---------------------------------------------------------------------
# Convenience base
# ---------------------------------------------------------------------


class BaseSklearnPredictor:
    """Common scaffolding for scikit-learn-backed predictors.

    Subclasses set :attr:`_model` after :meth:`train` and may
    stash fitted transformers in :attr:`_transformers` (a
    free-form dict keyed by name). The default
    :meth:`save` / :meth:`load` round-trips both fields.
    """

    name: str = "base"

    def __init__(self) -> None:
        self._model: Any = None
        self._transformers: dict[str, Any] = {}

    def save(self, path: str) -> None:
        import joblib

        # Persist the whole predictor instance — including
        # any per-instance state (e.g. ``_corpus`` on the
        # similarity predictor). Round-tripping the dict
        # alone would lose that state.
        joblib.dump(self, path)

    def load(self, path: str) -> "BaseSklearnPredictor":
        import joblib

        loaded = joblib.load(path)
        # ``loaded`` is a fresh predictor instance. We
        # transfer its fitted state onto ``self`` so the
        # caller's reference keeps working.
        self._model = getattr(loaded, "_model", None)
        self._transformers = getattr(loaded, "_transformers", {})
        # Some predictors (similarity) keep extra state on
        # the instance — copy those too.
        for attr in ("_corpus", "_matrix"):
            if hasattr(loaded, attr):
                setattr(self, attr, getattr(loaded, attr))
        return self


__all__ = [
    "BaseSklearnPredictor",
    "EvidenceItem",
    "FeatureContribution",
    "PredictionResult",
    "Predictor",
]
