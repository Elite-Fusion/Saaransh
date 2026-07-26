"""
Service layer — Phase-9 predictive intelligence.

The :class:`PredictionService` is the only public entry point
the API layer uses to call the ML predictors. It:

  1. Loads the data the predictor needs from the ORM
     (cases, accused, employees, …).
  2. Lazily instantiates the underlying scikit-learn
     predictor and loads its saved state from the model
     store (see :mod:`backend.ml.services.model_store`).
  3. Translates the predictor's
     :class:`~backend.ml.models.base.PredictionResult` into
     the corresponding Pydantic response model.

The service is **FastAPI-independent**: it never imports
``fastapi`` or ``starlette``. The Gemini AI provider (and
any future call site) can drive the same methods.

Fallback behaviour
==================

The model store is a directory of ``.joblib`` files. If a
model has never been trained (no file on disk) the
predictor returns an empty list. This keeps the API
contract stable during demos: the endpoint returns 200 with
``items: []`` rather than 500.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.ml.models import (
    BaseSklearnPredictor,
    ClusteringPredictor,
    HotspotPredictor,
    RepeatOffenderPredictor,
    RiskScorePredictor,
    SimilarityPredictor,
    TrendPredictor,
)
from backend.ml.services.model_store import (
    clear_cache,
    get_or_load,
    store_path,
)
from backend.models.case import Accused, CaseMaster
from backend.models.organisation import Employee
from backend.schemas.prediction import (
    CrimeCluster,
    EvidenceItemOut,
    FeatureContributionOut,
    FIRRiskScore,
    HotspotPrediction,
    OfficerRecommendation,
    RepeatOffenderPrediction,
    SimilarCase,
    TrendForecast,
)
from backend.services.base import BaseService

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------


class CaseNotTrainedError(Exception):
    """Raised by :meth:`PredictionService.score_fir_risk` and
    :meth:`PredictionService.recommend_officers` when the
    requested case id has no rows in the real database."""

    def __init__(self, case_id: int) -> None:
        super().__init__(f"Case {case_id} not found")
        self.case_id = case_id


# ---------------------------------------------------------------------
# Lazy model loader
# ---------------------------------------------------------------------


def _loader_for(predictor_cls: type[BaseSklearnPredictor]):
    """Build a ``joblib.load``-shaped loader for the given
    predictor class.

    The returned callable knows how to deserialise a saved
    predictor file and return a fresh instance of the
    correct class. The cache in
    :func:`backend.ml.services.model_store.get_or_load`
    ensures we only hit disk once per process.
    """

    def _loader(path):
        instance = predictor_cls()
        return instance.load(str(path))

    return _loader


def _load(predictor_name: str, predictor_cls: type[BaseSklearnPredictor]):
    """Return the trained predictor for ``predictor_name`` or
    a fresh, untrained one if no file exists on disk.

    The "untrained" branch lets the API return ``items: []``
    instead of 500ing during demos.
    """
    path = store_path(predictor_name)
    if not path.exists():
        log.warning(
            "predictor %s: no saved model at %s; returning empty",
            predictor_name, path,
        )
        return predictor_cls()
    return get_or_load(predictor_name, _loader_for(predictor_cls))


# ---------------------------------------------------------------------
# Feature adapter — ORM row -> predictor-friendly object
# ---------------------------------------------------------------------


def _case_to_features(case: CaseMaster) -> dict:
    """Pull every field a predictor might want from a
    :class:`CaseMaster` row, falling back gracefully when
    a relationship is null.

    The result is a flat dict; the predictor modules
    consume it via duck-typing (``getattr(row, "X", None)``).
    """
    return {
        "CaseMasterID": case.CaseMasterID,
        "CrimeNo": case.CrimeNo,
        "CrimeRegisteredDate": case.CrimeRegisteredDate,
        "latitude": float(case.latitude) if case.latitude is not None else None,
        "longitude": float(case.longitude) if case.longitude is not None else None,
        "BriefFacts": case.BriefFacts or "",
        "is_series_crime": bool(case.is_series_crime),
        "series_id": case.series_id,
        "month": case.CrimeRegisteredDate.month,
        "dow": case.CrimeRegisteredDate.weekday(),
        "CrimeMajorHeadName": (
            case.crime_major_head.CrimeGroupName
            if case.crime_major_head is not None else None
        ),
        "CrimeMinorHeadName": (
            case.crime_minor_head.CrimeHeadName
            if case.crime_minor_head is not None else None
        ),
        "GravityName": (
            case.gravity.LookupValue
            if case.gravity is not None else None
        ),
        "DistrictName": (
            case.police_station.district.DistrictName
            if case.police_station is not None
            and case.police_station.district is not None
            else None
        ),
        "mo_embedding": list(case.mo_embedding) if case.mo_embedding else None,
    }


# ---------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------


class PredictionService(BaseService):
    """The single entry point the API layer uses for ML.

    Each public method corresponds to one of the 8 ML
    features in the plan. Methods are read-only and
    stateless beyond the lazy-loaded predictors.
    """

    # ------------------------------------------------------------------
    # 1. Hotspot
    # ------------------------------------------------------------------

    def predict_hotspots(
        self,
        top_n: int = 10,
    ) -> list[HotspotPrediction]:
        """Return the top-N ``(district, crime_head, month)``
        combinations ranked by predicted case count.

        The model was trained on the synthetic dataset; the
        real data only informs the district / head labels. If
        the model has not been trained yet, this method
        returns an empty list.
        """
        cases = self._load_cases(limit=500)
        if not cases:
            return []
        predictor = _load("hotspot", HotspotPredictor)
        if predictor._model is None:
            return []
        # Convert ORM rows to predictor-friendly dicts.
        feature_rows = [_SimpleNamespace(**_case_to_features(c)) for c in cases]
        results = predictor.predict(feature_rows)
        # Aggregate by (district, crime_head, month).
        grouped: dict[tuple[str, str, int], list] = {}
        for case, r in zip(cases, results):
            key = (
                _case_to_features(case).get("DistrictName") or "?",
                _case_to_features(case).get("CrimeMajorHeadName") or "?",
                case.CrimeRegisteredDate.month,
            )
            grouped.setdefault(key, []).append(r)
        out: list[HotspotPrediction] = []
        for (district, head, month), rs in grouped.items():
            avg = sum(r.value for r in rs) / max(1, len(rs))
            conf = max(r.confidence for r in rs)
            out.append(
                HotspotPrediction(
                    district_name=district,
                    crime_head=head,
                    month=month,
                    predicted_count=int(round(avg)),
                    risk_band=_band(int(round(avg))),
                    confidence=round(conf, 4),
                    top_features=[
                        FeatureContributionOut(
                            feature=fc.feature,
                            value=fc.value,
                            importance=fc.importance,
                        )
                        for fc in rs[0].top_features
                    ],
                )
            )
        out.sort(key=lambda h: h.predicted_count, reverse=True)
        return out[:top_n]

    # ------------------------------------------------------------------
    # 2. Repeat offender
    # ------------------------------------------------------------------

    def predict_repeat_offenders(
        self,
        top_n: int = 20,
    ) -> list[RepeatOffenderPrediction]:
        """Return the top-N accused ranked by reoffending
        probability."""
        accused = self._load_accused(limit=500)
        if not accused:
            return []
        predictor = _load("repeat_offender", RepeatOffenderPredictor)
        if predictor._model is None:
            return []
        rows = [_AccusedSnapshot(a) for a in accused]
        results = predictor.predict(rows)
        out: list[RepeatOffenderPrediction] = []
        for a, r in zip(accused, results):
            out.append(
                RepeatOffenderPrediction(
                    accused_id=a.AccusedMasterID,
                    accused_name=a.AccusedName or "",
                    age=a.AgeYear,
                    prior_count=_prior_count(a),
                    will_reoffend=bool(int(r.value)),
                    probability=r.confidence,
                    confidence=r.confidence,
                    top_features=[
                        FeatureContributionOut(
                            feature=fc.feature,
                            value=fc.value,
                            importance=fc.importance,
                        )
                        for fc in r.top_features
                    ],
                )
            )
        out.sort(key=lambda r: r.probability, reverse=True)
        return out[:top_n]

    # ------------------------------------------------------------------
    # 3. Trend forecasting
    # ------------------------------------------------------------------

    def predict_trends(
        self,
        horizon_months: int = 1,
    ) -> list[TrendForecast]:
        """Forecast the next ``horizon_months`` months of
        case counts, broken down by crime head."""
        cases = self._load_cases(limit=1000)
        if not cases:
            return []
        predictor = _load("trend", TrendPredictor)
        if predictor._model is None:
            return []
        # Score the same set of cases; the predictor returns
        # one prediction per row. We then aggregate.
        feature_rows = [_SimpleNamespace(**_case_to_features(c)) for c in cases]
        results = predictor.predict(feature_rows)
        # Aggregate by (head, year, month) of registration.
        from collections import defaultdict
        agg: dict[tuple[str, int, int], int] = defaultdict(int)
        for c, r in zip(cases, results):
            agg[
                (
                    _case_to_features(c).get("CrimeMajorHeadName") or "?",
                    c.CrimeRegisteredDate.year,
                    c.CrimeRegisteredDate.month,
                )
            ] += max(0, int(r.value))
        out: list[TrendForecast] = []
        for (head, year, month), count in sorted(agg.items()):
            # Current count: same (head, month) one year prior.
            current = agg.get((head, year - 1, month), 0)
            conf = min(1.0, count / 10.0) if count else 0.3
            out.append(
                TrendForecast(
                    crime_head=head,
                    year=year,
                    month=month,
                    month_label=_month_label(month),
                    predicted_count=count,
                    current_count=current,
                    confidence=round(conf, 4),
                )
            )
        return out[-12:]  # last year of activity

    # ------------------------------------------------------------------
    # 4. Clustering
    # ------------------------------------------------------------------

    def cluster_patterns(
        self,
        top_n: int = 5,
    ) -> list[CrimeCluster]:
        """Group cases into MO clusters and return a label +
        size for each."""
        cases = self._load_cases(limit=500)
        if not cases:
            return []
        predictor = _load("clustering", ClusteringPredictor)
        if predictor._model is None:
            return []
        feature_rows = [_SimpleNamespace(**_case_to_features(c)) for c in cases]
        results = predictor.predict(feature_rows)
        # Bucket by cluster id.
        from collections import Counter, defaultdict
        groups: dict[int, list[int]] = defaultdict(list)
        for case, r in zip(cases, results):
            groups[int(r.value)].append(case.CaseMasterID)
        sub_heads_per_cluster: dict[int, Counter] = {
            cid: Counter() for cid in groups
        }
        for case, r in zip(cases, results):
            sub = _case_to_features(case).get("CrimeMinorHeadName") or "?"
            sub_heads_per_cluster[int(r.value)][sub] += 1
        out: list[CrimeCluster] = []
        for cid in sorted(groups):
            size = len(groups[cid])
            sub_counter = sub_heads_per_cluster[cid]
            top_subs = [s for s, _ in sub_counter.most_common(3)]
            label = top_subs[0] if top_subs else f"Cluster {cid}"
            conf = max(r.confidence for r, c in zip(results, cases) if c.CaseMasterID in groups[cid]) \
                if groups[cid] else 0.0
            out.append(
                CrimeCluster(
                    cluster_id=cid,
                    label=label,
                    size=size,
                    top_sub_heads=top_subs,
                    confidence=round(conf, 4),
                    evidence=[
                        EvidenceItemOut(
                            case_id=case_id,
                            label=f"cluster {cid}",
                        )
                        for case_id in groups[cid][:3]
                    ],
                )
            )
        out.sort(key=lambda c: c.size, reverse=True)
        return out[:top_n]

    # ------------------------------------------------------------------
    # 5. Similarity
    # ------------------------------------------------------------------

    def find_similar_cases(
        self,
        case_id: int,
        top_k: int = 10,
    ) -> list[SimilarCase]:
        """Return the top-k cases most similar to ``case_id``.

        Raises :class:`CaseNotTrainedError` if the case id
        is unknown.
        """
        case = self._get_case(case_id)
        cases_pool = self._load_cases(limit=1000)
        if not cases_pool:
            return []
        predictor = _load("similarity", SimilarityPredictor)
        if predictor._model is None or not getattr(predictor, "_corpus", []):
            return []
        query = _SimpleNamespace(**_case_to_features(case))
        results = predictor.predict(query, top_k=top_k)
        # Map ids back to FIR numbers.
        id_to_case = {c.CaseMasterID: c for c in cases_pool}
        out: list[SimilarCase] = []
        for r in results:
            c = id_to_case.get(r.value)
            if c is None:
                continue
            feats = _case_to_features(c)
            out.append(
                SimilarCase(
                    case_id=c.CaseMasterID,
                    fir_number=c.CrimeNo,
                    crime_sub_head=feats.get("CrimeMinorHeadName") or "",
                    district=feats.get("DistrictName") or "",
                    similarity=r.confidence,
                    confidence=r.confidence,
                    brief_facts=(c.BriefFacts or "")[:200],
                    top_features=[
                        FeatureContributionOut(
                            feature=fc.feature,
                            value=fc.value,
                            importance=fc.importance,
                        )
                        for fc in r.top_features
                    ],
                )
            )
        return out

    # ------------------------------------------------------------------
    # 6. Risk score
    # ------------------------------------------------------------------

    def score_fir_risk(self, case_id: int) -> FIRRiskScore:
        """Return a composite risk score (low/medium/high)
        for a single FIR.

        Raises :class:`CaseNotTrainedError` if the case id
        is unknown.
        """
        case = self._get_case(case_id)
        predictor = _load("risk_score", RiskScorePredictor)
        if predictor._model is None:
            # Fallback: a neutral medium score so the UI has
            # something to render.
            feats = _case_to_features(case)
            return FIRRiskScore(
                case_id=case_id,
                fir_number=case.CrimeNo,
                risk_label="medium",
                risk_numeric=50,
                district=feats.get("DistrictName") or "",
                crime_sub_head=feats.get("CrimeMinorHeadName") or "",
                confidence=0.5,
            )
        row = _SimpleNamespace(**_case_to_features(case))
        results = predictor.predict([row])
        r = results[0]
        label = str(r.value)
        numeric = {"low": 25, "medium": 55, "high": 85}.get(label, 50)
        feats = _case_to_features(case)
        return FIRRiskScore(
            case_id=case_id,
            fir_number=case.CrimeNo,
            risk_label=label,
            risk_numeric=numeric,
            district=feats.get("DistrictName") or "",
            crime_sub_head=feats.get("CrimeMinorHeadName") or "",
            confidence=r.confidence,
            top_features=[
                FeatureContributionOut(
                    feature=fc.feature,
                    value=fc.value,
                    importance=fc.importance,
                )
                for fc in r.top_features
            ],
        )

    # ------------------------------------------------------------------
    # 7. Officer recommendations
    # ------------------------------------------------------------------

    def recommend_officers(
        self,
        case_id: int,
        top_n: int = 3,
    ) -> list[OfficerRecommendation]:
        """Return ``top_n`` officers best suited to handle
        ``case_id``.

        The recommender is a heuristic blend of crime-head
        specialisation and recent caseload. It is exposed
        as a service method so the route layer is decoupled
        from the scoring formula.
        """
        case = self._get_case(case_id)
        employees = self._load_employees(limit=50)
        if not employees:
            return []
        from collections import Counter
        # Build a "case type -> count" map for each officer
        # from the recent cases.
        recent = self._load_cases(limit=200)
        head_counts: dict[int, Counter] = {e.EmployeeID: Counter() for e in employees}
        for c in recent:
            if c.PolicePersonID in head_counts and c.crime_major_head is not None:
                head_counts[c.PolicePersonID][c.crime_major_head.CrimeGroupName] += 1
        target_head = (
            case.crime_major_head.CrimeGroupName
            if case.crime_major_head is not None else None
        )
        # Score: 1 if the officer has handled the same head,
        # 0.5 if they handled a related head, 0.1 baseline.
        ranked: list[tuple[float, Employee]] = []
        for e in employees:
            counts = head_counts[e.EmployeeID]
            if target_head and counts.get(target_head, 0) > 0:
                score = 1.0
            elif counts:
                score = 0.5
            else:
                score = 0.1
            ranked.append((score, e))
        ranked.sort(key=lambda x: x[0], reverse=True)
        out: list[OfficerRecommendation] = []
        for score, e in ranked[:top_n]:
            head_hits = (
                head_counts[e.EmployeeID].get(target_head, 0)
                if target_head else 0
            )
            reason = (
                f"Handled {head_hits} similar case(s) recently"
                if head_hits > 0
                else "Available with relevant experience"
            )
            rank_name = (
                e.rank.RankName
                if e.rank is not None and getattr(e.rank, "RankName", None)
                else ""
            )
            officer_name = (
                e.FirstName.strip()
                if e.FirstName
                else f"Officer #{e.EmployeeID}"
            )
            out.append(
                OfficerRecommendation(
                    officer_id=e.EmployeeID,
                    officer_name=officer_name,
                    rank=rank_name,
                    reason=reason,
                    confidence=round(min(1.0, score), 4),
                )
            )
        return out

    # ------------------------------------------------------------------
    # Internal loaders
    # ------------------------------------------------------------------

    def _get_case(self, case_id: int) -> CaseMaster:
        stmt = (
            select(CaseMaster)
            .where(CaseMaster.CaseMasterID == case_id)
            .options(
                selectinload(CaseMaster.police_station),
                selectinload(CaseMaster.crime_major_head),
                selectinload(CaseMaster.crime_minor_head),
                selectinload(CaseMaster.gravity),
            )
        )
        result = self._session.execute(stmt).scalar_one_or_none()
        if result is None:
            raise CaseNotTrainedError(case_id)
        return result

    def _load_cases(self, limit: int = 500) -> list[CaseMaster]:
        stmt = (
            select(CaseMaster)
            .limit(limit)
            .options(
                selectinload(CaseMaster.police_station),
                selectinload(CaseMaster.crime_major_head),
                selectinload(CaseMaster.crime_minor_head),
                selectinload(CaseMaster.gravity),
            )
        )
        return list(self._session.execute(stmt).scalars().all())

    def _load_accused(self, limit: int = 500) -> list[Accused]:
        stmt = select(Accused).limit(limit)
        return list(self._session.execute(stmt).scalars().all())

    def _load_employees(self, limit: int = 100) -> list[Employee]:
        stmt = select(Employee).limit(limit)
        return list(self._session.execute(stmt).scalars().all())


# ---------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------


def _band(count: int) -> str:
    """Bucket a predicted count into a public risk band."""
    if count <= 0:
        return "low"
    if count <= 2:
        return "low"
    if count <= 4:
        return "medium"
    if count <= 6:
        return "high"
    return "very_high"


def _prior_count(a: Accused) -> int:
    """Best-effort "prior_count" for an accused row. The real
    schema does not track prior cases directly, so we use
    the ``is_known_criminal`` flag as a proxy. The synthetic
    training data uses the real number; this is just for
    the public response shape."""
    return 1 if a.is_known_criminal else 0


def _month_label(m: int) -> str:
    return ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m]


class _SimpleNamespace:
    """Tiny stand-in for :class:`types.SimpleNamespace` that
    survives being passed through joblib's pickler."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _AccusedSnapshot:
    """Adapter that exposes the fields the repeat-offender
    predictor expects, derived from an :class:`Accused` row.

    The real schema has no ``primary_crime_head`` /
    ``primary_gravity`` / ``prior_count`` columns — those
    exist in the synthetic data only. We synthesise them
    from the closest available fields so the predictor can
    at least be invoked against the real database.
    """

    def __init__(self, a: Accused) -> None:
        self.AccusedMasterID = a.AccusedMasterID
        self.AccusedName = a.AccusedName
        self.AgeYear = a.AgeYear or 30
        self.GenderID = a.GenderID or 1
        self.is_known_criminal = bool(a.is_known_criminal)
        self.criminal_history = a.criminal_history or ""
        self.reoffended = int(bool(a.is_known_criminal))
        self.prior_count = 2 if a.is_known_criminal else 0
        self.primary_crime_head = (
            a.case.crime_major_head.CrimeGroupName
            if a.case is not None and a.case.crime_major_head is not None
            else "Crimes Against Property"
        )
        self.primary_gravity = (
            a.case.gravity.LookupValue
            if a.case is not None and a.case.gravity is not None
            else "Non-Heinous"
        )


# ---------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------


__all__ = [
    "CaseNotTrainedError",
    "PredictionService",
    "clear_cache",
]
