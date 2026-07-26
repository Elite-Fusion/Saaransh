"""
Feature builder for the Phase-9 ML layer.

This module is the only place in the package that knows the
shape of a real :class:`CaseMaster` row. The predictors and
the model store never look at ORM objects; they only see numpy
arrays. The feature builder converts:

* a list of ORM rows (or :class:`SimpleNamespace` mocks in
  tests) into a 2-D numpy matrix, plus a column-order list
  that callers can use to rebuild a feature row at inference
  time.

The builder is **deterministic**: the same input rows
produce the same matrix. It is also **stateless** between
calls, but the categorical-to-int mappings it builds
*during a call* are returned alongside the matrix so the
caller can keep them for the duration of an inference
request.

The builder does not import any scikit-learn code. It only
imports numpy. The :class:`ColumnTransformer` /
:class:`Pipeline` that wrap the builder live in the
predictor modules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


#: Canonical column order for the ML feature matrix. The order
#: matches the one used by :func:`cases_to_feature_matrix` in
#: the synthetic-data generator — the two should never drift.
DEFAULT_COLUMNS: tuple[str, ...] = (
    "month",
    "dow",
    "district_id",
    "crime_head_id",
    "crime_sub_head_id",
    "gravity_id",
    "is_series_crime",
    "latitude_norm",
    "longitude_norm",
)


@dataclass(frozen=True)
class FeatureBuildResult:
    """The output of :func:`build_features`.

    Attributes:
        X: The 2-D numpy array of features.
        columns: The column order used to build ``X``. The
            caller must keep the same order when constructing
            an inference row.
        encoders: The categorical-to-int mappings that were
            used. The caller can reuse them to encode a
            single inference row without rebuilding the
            whole vocabulary.
    """

    X: Any  # numpy.ndarray
    columns: tuple[str, ...]
    encoders: dict[str, dict[str, int]]


def _row_attr(row: Any, *names: str) -> Any:
    """Return the first non-``None`` attribute from ``row``.

    Helper that lets the builder accept both ORM rows
    (camelCase attributes, e.g. ``CrimeMajorHeadID``) and the
    synthetic rows that expose the attribute name directly.
    """
    for name in names:
        value = getattr(row, name, None)
        if value is not None:
            return value
    return None


def _district_id(row: Any, encoders: dict[str, dict[str, int]]) -> int:
    """Resolve a district name or id to the encoder's int code.

    The real :class:`CaseMaster` row has no direct district
    column — district is reached through
    ``police_station.district.DistrictName``. Tests use a
    simpler shape (a ``DistrictName`` attribute or a
    ``DistrictID``).
    """
    if (did := getattr(row, "DistrictID", None)) is not None:
        return int(did)
    name = _row_attr(row, "DistrictName")
    if name is None:
        station = getattr(row, "police_station", None)
        if station is not None:
            station_district = getattr(station, "district", None)
            if station_district is not None:
                name = getattr(station_district, "DistrictName", None)
    if name is None:
        return -1
    table = encoders.setdefault("district", {})
    if name not in table:
        table[name] = len(table)
    return table[name]


def _head_id(row: Any, encoders: dict[str, dict[str, int]]) -> int:
    """Resolve a crime head name to an int code."""
    major = getattr(row, "crime_major_head", None)
    name = None
    if major is not None:
        name = getattr(major, "CrimeGroupName", None)
    if name is None:
        name = _row_attr(row, "CrimeMajorHeadName", "CrimeHeadName")
    if name is None:
        return -1
    table = encoders.setdefault("crime_head", {})
    if name not in table:
        table[name] = len(table)
    return table[name]


def _sub_head_id(row: Any, encoders: dict[str, dict[str, int]]) -> int:
    """Resolve a crime sub-head name to an int code."""
    minor = getattr(row, "crime_minor_head", None)
    name = None
    if minor is not None:
        name = getattr(minor, "CrimeHeadName", None)
    if name is None:
        name = _row_attr(row, "CrimeMinorHeadName", "CrimeSubHeadName")
    if name is None:
        return -1
    table = encoders.setdefault("crime_sub_head", {})
    if name not in table:
        table[name] = len(table)
    return table[name]


def _gravity_id(row: Any, encoders: dict[str, dict[str, int]]) -> int:
    """Resolve a gravity name to an int code."""
    grav = getattr(row, "gravity", None)
    name = None
    if grav is not None:
        name = getattr(grav, "LookupValue", None)
    if name is None:
        name = _row_attr(row, "GravityName", "Gravity")
    if name is None:
        return -1
    table = encoders.setdefault("gravity", {})
    if name not in table:
        table[name] = len(table)
    return table[name]


def _month(row: Any) -> int:
    """Extract a 1..12 month-of-registration from a row."""
    d = getattr(row, "CrimeRegisteredDate", None)
    if d is None:
        return 1
    try:
        return d.month
    except AttributeError:
        try:
            return int(str(d)[5:7])
        except (ValueError, IndexError):
            return 1


def _dow(row: Any) -> int:
    """Day-of-week, Mon=0..Sun=6."""
    d = getattr(row, "CrimeRegisteredDate", None)
    if d is None:
        return 0
    try:
        return d.weekday()
    except AttributeError:
        return 0


def _norm_lat(value: Any) -> float:
    """Normalise a latitude to ``[0, 1]`` over a Karnataka
    bounding box."""
    if value is None:
        return 0.5
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, (v - 11.5) / (18.0 - 11.5)))


def _norm_lng(value: Any) -> float:
    """Normalise a longitude to ``[0, 1]`` over a Karnataka
    bounding box."""
    if value is None:
        return 0.5
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, (v - 74.0) / (78.5 - 74.0)))


def _is_series(row: Any) -> float:
    """Return 1.0 if the row is flagged as a series crime, 0.0 otherwise."""
    if getattr(row, "is_series_crime", None):
        return 1.0
    return 0.0


def build_features(
    rows: Sequence[Any],
    *,
    columns: tuple[str, ...] = DEFAULT_COLUMNS,
) -> FeatureBuildResult:
    """Convert ORM-style rows into a numpy feature matrix.

    Args:
        rows: The rows to convert. Each row may be an ORM
            object or a ``SimpleNamespace`` mock.
        columns: The column order of the output matrix. Use
            :data:`DEFAULT_COLUMNS` for the default order.

    Returns:
        A :class:`FeatureBuildResult` carrying the matrix, the
        column order, and the per-column encoders. The encoders
        are populated as a side effect, so the caller can keep
        them and apply them to a single inference row.
    """
    import numpy as np

    encoders: dict[str, dict[str, int]] = {}
    matrix: list[list[float]] = []
    for row in rows:
        matrix.append([
            float(_month(row)),
            float(_dow(row)),
            float(_district_id(row, encoders)),
            float(_head_id(row, encoders)),
            float(_sub_head_id(row, encoders)),
            float(_gravity_id(row, encoders)),
            _is_series(row),
            _norm_lat(getattr(row, "latitude", None)),
            _norm_lng(getattr(row, "longitude", None)),
        ])
    return FeatureBuildResult(
        X=np.asarray(matrix, dtype=float),
        columns=columns,
        encoders=encoders,
    )


def build_inference_row(
    row: Any,
    encoders: dict[str, dict[str, int]],
    *,
    columns: tuple[str, ...] = DEFAULT_COLUMNS,
) -> Any:
    """Build a single-row feature matrix using the encoders
    fitted during training. Returns a 2-D numpy array of shape
    ``(1, len(columns))``.

    This is the entry point the prediction service calls when
    it wants to score a single :class:`CaseMaster` row.
    """
    import numpy as np

    full = build_features([row], columns=columns)
    # Re-apply the training encoders so the codes match the
    # fitted tree's expectations.
    X = full.X.copy()
    # The categorical columns are at indices 2, 3, 4, 5.
    cat_indices = {
        "district_id": 2,
        "crime_head_id": 3,
        "crime_sub_head_id": 4,
        "gravity_id": 5,
    }
    for col, idx in cat_indices.items():
        if col not in encoders:
            continue
        # Find the row's name for this category and re-encode.
        if col == "district_id":
            name = _row_attr(row, "DistrictName")
            if name is None:
                station = getattr(row, "police_station", None)
                if station is not None and getattr(station, "district", None) is not None:
                    name = getattr(station.district, "DistrictName", None)
        elif col == "crime_head_id":
            major = getattr(row, "crime_major_head", None)
            name = getattr(major, "CrimeGroupName", None) if major is not None else _row_attr(row, "CrimeMajorHeadName")
        elif col == "crime_sub_head_id":
            minor = getattr(row, "crime_minor_head", None)
            name = getattr(minor, "CrimeHeadName", None) if minor is not None else _row_attr(row, "CrimeMinorHeadName")
        else:
            grav = getattr(row, "gravity", None)
            name = getattr(grav, "LookupValue", None) if grav is not None else _row_attr(row, "GravityName")
        if name is None:
            X[0, idx] = -1
        else:
            X[0, idx] = encoders[col].get(name, -1)
    return X


__all__ = [
    "DEFAULT_COLUMNS",
    "FeatureBuildResult",
    "build_features",
    "build_inference_row",
]
