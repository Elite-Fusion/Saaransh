"""
Predictor package — one module per Phase-9 feature.

The actual classes are implemented in their respective
modules. Importing the package is cheap; loading a trained
model is not (it pulls in joblib + numpy). Callers should
import the specific class they need::

    from backend.ml.models.hotspot import HotspotPredictor

The :func:`get_predictor` factory is the only way the
service layer should construct a predictor — direct
constructor calls would couple callers to the concrete
classes.
"""
from backend.ml.models.base import (
    BaseSklearnPredictor,
    EvidenceItem,
    FeatureContribution,
    PredictionResult,
    Predictor,
)
from backend.ml.models.clustering import ClusteringPredictor
from backend.ml.models.hotspot import HotspotPredictor
from backend.ml.models.repeat_offender import RepeatOffenderPredictor
from backend.ml.models.risk_score import RiskScorePredictor
from backend.ml.models.similarity import SimilarityPredictor
from backend.ml.models.trend import TrendPredictor


_REGISTRY: dict[str, type] = {
    "hotspot": HotspotPredictor,
    "repeat_offender": RepeatOffenderPredictor,
    "trend": TrendPredictor,
    "clustering": ClusteringPredictor,
    "similarity": SimilarityPredictor,
    "risk_score": RiskScorePredictor,
}


def get_predictor(name: str) -> Predictor:
    """Return a fresh, untrained predictor by name."""
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown predictor: {name!r}. "
            f"Known: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]()


def known_predictors() -> list[str]:
    """Return the list of registered predictor names.

    Used by tests to assert the registry stays in sync with
    the public surface.
    """
    return sorted(_REGISTRY)


__all__ = [
    "BaseSklearnPredictor",
    "ClusteringPredictor",
    "EvidenceItem",
    "FeatureContribution",
    "HotspotPredictor",
    "PredictionResult",
    "Predictor",
    "RepeatOffenderPredictor",
    "RiskScorePredictor",
    "SimilarityPredictor",
    "TrendPredictor",
    "get_predictor",
    "known_predictors",
]
