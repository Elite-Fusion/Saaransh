"""
Saaransh AI — Machine Learning layer (Phase 9).

The ML package is *parallel* to :mod:`backend.ai`. Both consume
services from :mod:`backend.services` and are orchestrated by
routes in :mod:`backend.api.v1`. The two packages never import
each other.

Sub-packages
------------

* :mod:`backend.ml.models`      — the trained predictors (one
  per Phase-9 feature).
* :mod:`backend.ml.preprocessing` — feature builders and the
  deterministic synthetic-data generator.
* :mod:`backend.ml.services`    — model persistence + lazy load.
* :mod:`backend.ml.training`    — CLI entry point that retrains
  every predictor against the synthetic dataset.

Design rules
------------

* Predictors are pure-function classes. They take a 2-D numpy
  array of features plus (when relevant) a target vector and
  return a list of :class:`PredictionResult` objects. No
  SQLAlchemy, no FastAPI.
* Persistence uses :func:`joblib.dump` / :func:`joblib.load`.
  Writes are atomic (write to ``.tmp`` then rename). The model
  store caches loaded predictors in-memory so a hot service
  does not hit disk on every request.
* Training data is produced by a deterministic generator in
  :mod:`backend.ml.preprocessing.synthetic_data`. The real
  KSP seed (30 rows) is too small to train any meaningful
  model; the synthetic dataset (~1000 rows) keeps the demo
  honest. The README documents this caveat.
* No code in this package may import :mod:`fastapi` or
  :mod:`starlette`. Routes call into services, never into
  predictors directly.
"""
