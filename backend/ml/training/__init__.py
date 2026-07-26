"""Training scripts for the Phase-9 ML layer.

The package exposes a single CLI entry point, ``train_all``,
that trains every predictor against the synthetic dataset
and persists them to ``backend/ml_store/`` via the atomic
model store. The entry point is also re-exported as a
``__main__`` module so the script can be invoked with
``python -m backend.ml.training.train_all``.
"""
from backend.ml.training.train_all import main as train_all_main

__all__ = ["train_all_main"]
