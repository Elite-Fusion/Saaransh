"""Shared pytest fixtures for the Phase-9 ML tests.

We mirror the rest of the suite: the tests never touch the
database. They build :class:`SyntheticCase` and
:class:`SyntheticAccused` rows in memory and use the
deterministic generator so the inputs are reproducible.
"""
from __future__ import annotations

import pytest

from backend.ml.preprocessing.synthetic_data import (
    generate_synthetic_accused,
    generate_synthetic_cases,
)


@pytest.fixture(scope="module")
def small_cases():
    """50 synthetic cases — enough to fit a model and fast
    to compute. Module-scoped because training is the slow
    step; the suite reuses the same set across tests."""
    return generate_synthetic_cases(n=50, seed=42)


@pytest.fixture(scope="module")
def small_accused(small_cases):
    return generate_synthetic_accused(small_cases, seed=43)


@pytest.fixture(scope="module")
def large_cases():
    """200 cases — the tests that compare metrics across
    models use this to avoid overfitting noise."""
    return generate_synthetic_cases(n=200, seed=42)


@pytest.fixture(scope="module")
def large_accused(large_cases):
    return generate_synthetic_accused(large_cases, seed=43)
