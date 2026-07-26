"""
Persistent model store for the Phase-9 ML layer.

Each predictor is saved to a single ``.joblib`` file under
``backend/ml_store/``. The store caches loaded predictors in
memory so a hot FastAPI worker does not hit disk on every
request. The first call to :func:`get_or_load` reads the
file; subsequent calls return the cached instance.

Writes are atomic: the store writes to ``<path>.tmp`` and
renames. A reader that opens ``<path>`` between the write
and the rename will see the old file (joblib's contract is
that the load succeeds or raises a clear ``FileNotFoundError``).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

# Default location: ``backend/ml_store/`` next to the running
# Python process. The training script writes here; the
# service reads from here.
DEFAULT_STORE_DIR = Path(__file__).resolve().parent.parent.parent / "ml_store"

# Module-level cache: ``{path: predictor}``. A single
# instance per process is enough — predictors are stateless
# once trained.
_CACHE: dict[str, Any] = {}


def store_path(name: str, store_dir: Path | None = None) -> Path:
    """Return the canonical on-disk path for a named predictor.

    Args:
        name: The predictor's ``name`` attribute.
        store_dir: Override the default location (used by the
            training script when it writes to a temp dir).

    Returns:
        The :class:`Path` to the ``.joblib`` file. The file
        may or may not exist.
    """
    base = store_dir or DEFAULT_STORE_DIR
    return base / f"{name}.joblib"


def ensure_store_dir(store_dir: Path | None = None) -> Path:
    """Create the store directory if it does not exist.

    Returns the resolved :class:`Path` so callers can
    ``cd`` into it.
    """
    base = store_dir or DEFAULT_STORE_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base


def save_atomic(predictor: Any, path: Path) -> None:
    """Persist ``predictor`` to ``path`` atomically.

    A writer uses ``Path.replace`` to swap the temp file in.
    Readers either see the old file (clean) or the new file
    (clean) — never a half-written one.
    """
    import joblib

    path = Path(path) if not isinstance(path, Path) else path
    ensure_store_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    joblib.dump(predictor, tmp)
    os.replace(tmp, path)


def get_or_load(
    name: str,
    loader: Callable[[Path], Any],
    *,
    store_dir: Path | None = None,
) -> Any:
    """Return the cached predictor for ``name`` or load it.

    Args:
        name: The predictor's filename (e.g. ``"hotspot"``).
        loader: A callable that takes a :class:`Path` and
            returns the loaded predictor. The loader is only
            called when the file is not in the cache.
        store_dir: Override the default location.

    Returns:
        The loaded predictor instance. Subsequent calls with
        the same ``name`` return the same object.
    """
    path = store_path(name, store_dir)
    cache_key = str(path.resolve())
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    instance = loader(path)
    _CACHE[cache_key] = instance
    return instance


def clear_cache() -> None:
    """Empty the in-memory cache.

    Tests use this between runs to avoid stale models bleeding
    between test cases. The on-disk files are untouched.
    """
    _CACHE.clear()


__all__ = [
    "DEFAULT_STORE_DIR",
    "clear_cache",
    "ensure_store_dir",
    "get_or_load",
    "save_atomic",
    "store_path",
]
