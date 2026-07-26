"""Tests for the model store helpers."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.ml.services import model_store
from backend.ml.services.model_store import (
    DEFAULT_STORE_DIR,
    clear_cache,
    ensure_store_dir,
    get_or_load,
    save_atomic,
    store_path,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Always start with a clean cache so tests don't
    leak loaded predictors into each other."""
    clear_cache()
    yield
    clear_cache()


def test_store_path_default_location():
    p = store_path("hotspot")
    assert p.name == "hotspot.joblib"
    assert p.parent == DEFAULT_STORE_DIR


def test_store_path_with_overrides_dir(tmp_path: Path):
    p = store_path("foo", store_dir=tmp_path)
    assert p.parent == tmp_path


def test_ensure_store_dir_creates(tmp_path: Path):
    nested = tmp_path / "a" / "b"
    out = ensure_store_dir(nested)
    assert out == nested
    assert nested.is_dir()


def test_save_atomic_writes_file(tmp_path: Path):
    payload = {"model": "fake", "transformers": {}}
    target = tmp_path / "model.joblib"
    save_atomic(payload, target)
    assert target.exists()
    assert not target.with_suffix(target.suffix + ".tmp").exists()


def test_save_atomic_overwrites_existing(tmp_path: Path):
    target = tmp_path / "model.joblib"
    save_atomic({"v": 1}, target)
    save_atomic({"v": 2}, target)
    import joblib
    assert joblib.load(target)["v"] == 2


def test_save_atomic_accepts_string_path(tmp_path: Path):
    target = tmp_path / "model.joblib"
    save_atomic({"v": 3}, str(target))  # str path also works
    assert target.exists()


def test_get_or_load_caches(tmp_path: Path):
    target = tmp_path / "cache.joblib"
    save_atomic({"v": 1}, target)
    calls = []

    def loader(p):
        calls.append(p)
        return {"loaded": True}

    a = get_or_load("cache", loader, store_dir=tmp_path)
    b = get_or_load("cache", loader, store_dir=tmp_path)
    assert a is b
    assert calls == [target]


def test_clear_cache_drops_cached_instance(tmp_path: Path):
    target = tmp_path / "cache.joblib"
    save_atomic({"v": 1}, target)
    calls = []

    def loader(p):
        calls.append(p)
        return {"loaded": True}

    get_or_load("cache", loader, store_dir=tmp_path)
    clear_cache()
    get_or_load("cache", loader, store_dir=tmp_path)
    assert len(calls) == 2
