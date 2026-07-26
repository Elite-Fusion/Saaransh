"""
Pydantic schemas — prediction / ML response models.

The shapes mirror the :class:`backend.ml.models.base.PredictionResult`
hierarchy (value, confidence, top_features, evidence) but are flat
enough to serialise directly to JSON. All models use
``extra="forbid"`` so a stray field on the wire is rejected at
the boundary.

Public surface:

* :class:`FeatureContributionOut`
* :class:`EvidenceItemOut`
* :class:`HotspotPrediction`
* :class:`RepeatOffenderPrediction`
* :class:`TrendForecast`
* :class:`CrimeCluster`
* :class:`SimilarCase`
* :class:`FIRRiskScore`
* :class:`OfficerRecommendation`
* :class:`PredictionEnvelope`
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------


class _StrictModel(BaseModel):
    """Base for every schema in this module. ``extra="forbid"``
    catches a frontend that drifts from the contract."""

    model_config = ConfigDict(extra="forbid")


class FeatureContributionOut(_StrictModel):
    """One row in a prediction's explanation.

    ``importance`` is normalised to ``[0, 1]`` within a single
    prediction; values are not necessarily comparable across
    predictors.
    """

    feature: str
    value: float | int | str | None
    importance: float = Field(..., ge=0.0, le=1.0)


class EvidenceItemOut(_StrictModel):
    """A supporting case a prediction can be cross-checked
    against. Used by similarity and recommendations."""

    case_id: int | None = None
    fir_number: str | None = None
    label: str = ""


class _PredictionBase(_StrictModel):
    """Common fields every prediction carries."""

    confidence: float = Field(..., ge=0.0, le=1.0)
    top_features: list[FeatureContributionOut] = Field(default_factory=list)
    evidence: list[EvidenceItemOut] = Field(default_factory=list)


# ---------------------------------------------------------------------
# Hotspot
# ---------------------------------------------------------------------


class HotspotPrediction(_PredictionBase):
    """A ``(district, crime_head, month)`` risk estimate."""

    district_id: int | None = None
    district_name: str = ""
    crime_head: str = ""
    month: int = Field(..., ge=1, le=12)
    predicted_count: int = Field(..., ge=0)
    risk_band: str = Field(
        ...,
        description=(
            "'low' | 'medium' | 'high' | 'very_high' — bucketed "
            "from the predicted count for the heat-map UI."
        ),
    )


# ---------------------------------------------------------------------
# Repeat offender
# ---------------------------------------------------------------------


class RepeatOffenderPrediction(_PredictionBase):
    """A per-accused recidivism risk score."""

    accused_id: int | None = None
    accused_name: str = ""
    age: int | None = None
    prior_count: int = Field(..., ge=0)
    will_reoffend: bool
    probability: float = Field(..., ge=0.0, le=1.0)


# ---------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------


class TrendForecast(_PredictionBase):
    """A monthly per-head crime count forecast."""

    crime_head: str
    year: int = Field(..., ge=1900, le=2200)
    month: int = Field(..., ge=1, le=12)
    month_label: str
    predicted_count: int = Field(..., ge=0)
    current_count: int = Field(
        ..., ge=0,
        description=(
            "The count for the same (head, month) one year prior. "
            "Lets the UI show 'up vs. last year' arrows."
        ),
    )


# ---------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------


class CrimeCluster(_PredictionBase):
    """One MO cluster with a few example cases."""

    cluster_id: int = Field(..., ge=0)
    label: str = Field(
        ...,
        description=(
            "Human-readable cluster name — derived from the most "
            "common crime sub-head in the cluster."
        ),
    )
    size: int = Field(..., ge=0)
    top_sub_heads: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------


class SimilarCase(_PredictionBase):
    """One row in the 'similar cases' list."""

    case_id: int
    fir_number: str
    crime_sub_head: str
    district: str = ""
    similarity: float = Field(..., ge=0.0, le=1.0)
    brief_facts: str = ""


# ---------------------------------------------------------------------
# Risk score
# ---------------------------------------------------------------------


class FIRRiskScore(_PredictionBase):
    """The composite risk score for one FIR."""

    case_id: int
    fir_number: str
    risk_label: str = Field(..., description="'low' | 'medium' | 'high'")
    risk_numeric: int = Field(
        ..., ge=0, le=100,
        description="The label mapped to a 0-100 scale for the gauge UI.",
    )
    district: str = ""
    crime_sub_head: str = ""


# ---------------------------------------------------------------------
# Officer recommendation
# ---------------------------------------------------------------------


class OfficerRecommendation(_PredictionBase):
    """A suggested officer for a case.

    The real implementation would pull from the
    :class:`Employee` table; for the demo the recommender
    is a heuristic blend of crime-head specialisation and
    district familiarity.
    """

    officer_id: int
    officer_name: str
    rank: str = ""
    reason: str


# ---------------------------------------------------------------------
# Generic envelope for endpoint responses
# ---------------------------------------------------------------------


class PredictionEnvelope(_StrictModel):
    """Top-level shape every /api/v1/predictions/* endpoint returns.

    The route layer is free to populate only the fields that
    make sense for the call.
    """

    generated_at: str
    predictor: str
    note: str = ""
    hotspots: list[HotspotPrediction] = Field(default_factory=list)
    repeat_offenders: list[RepeatOffenderPrediction] = Field(default_factory=list)
    trends: list[TrendForecast] = Field(default_factory=list)
    clusters: list[CrimeCluster] = Field(default_factory=list)
    similar_cases: list[SimilarCase] = Field(default_factory=list)
    risk_score: FIRRiskScore | None = None
    recommendations: list[OfficerRecommendation] = Field(default_factory=list)
