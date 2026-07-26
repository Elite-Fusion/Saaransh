"""Tests for the synthetic data generator and the feature builder."""
from __future__ import annotations

from backend.ml.preprocessing.feature_builder import (
    DEFAULT_COLUMNS,
    build_features,
)
from backend.ml.preprocessing.synthetic_data import (
    CRIME_HEADS,
    DISTRICTS,
    GRAVITIES,
    generate_synthetic_cases,
)


def test_generate_synthetic_cases_default_count():
    cases = generate_synthetic_cases(n=100, seed=42)
    assert len(cases) == 100


def test_generate_synthetic_cases_deterministic():
    a = generate_synthetic_cases(n=50, seed=99)
    b = generate_synthetic_cases(n=50, seed=99)
    assert [c.CaseMasterID for c in a] == [c.CaseMasterID for c in b]
    assert [c.CrimeNo for c in a] == [c.CrimeNo for c in b]


def test_generate_synthetic_cases_sorted_by_date():
    cases = generate_synthetic_cases(n=50, seed=42)
    dates = [c.CrimeRegisteredDate for c in cases]
    assert dates == sorted(dates)


def test_generate_synthetic_cases_districts_drawn_from_known():
    cases = generate_synthetic_cases(n=200, seed=42)
    seen = {c.DistrictName for c in cases}
    assert seen.issubset(set(DISTRICTS))


def test_generate_synthetic_cases_uses_all_heads_over_large_n():
    cases = generate_synthetic_cases(n=1000, seed=42)
    seen = {c.CrimeMajorHeadName for c in cases}
    assert seen == set(CRIME_HEADS)


def test_build_features_default_columns():
    cases = generate_synthetic_cases(n=20, seed=42)
    result = build_features(cases)
    assert result.columns == DEFAULT_COLUMNS
    assert result.X.shape == (20, len(DEFAULT_COLUMNS))


def test_build_features_creates_encoders():
    cases = generate_synthetic_cases(n=20, seed=42)
    result = build_features(cases)
    # The four categorical columns are present in encoders.
    assert "district" in result.encoders
    assert "crime_head" in result.encoders
    assert "crime_sub_head" in result.encoders
    assert "gravity" in result.encoders
