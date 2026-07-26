"""
Generate the deterministic synthetic dataset used to train
the Phase-9 ML layer.

This script writes a JSON snapshot of the synthetic cases
to ``backend/ml_store/synthetic_cases.json`` (default). It
exists as a separate CLI so the training run and the
dataset can be reproduced independently — re-running this
script produces a byte-identical file.

Usage::

    python -m scripts.seed_ml_synthetic              # 1000 cases
    python -m scripts.seed_ml_synthetic --n 2000     # larger set
    python -m scripts.seed_ml_synthetic --out path.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.ml.preprocessing.synthetic_data import (
    dataset_summary,
    generate_synthetic_accused,
    generate_synthetic_cases,
)

log = logging.getLogger("seed_ml_synthetic")

DEFAULT_OUT = (
    _PROJECT_ROOT / "backend" / "ml_store" / "synthetic_cases.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the deterministic synthetic dataset "
            "for the Phase-9 ML layer."
        )
    )
    parser.add_argument(
        "--n", type=int, default=1000,
        help="Number of synthetic cases to generate (default: 1000).",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default: 42).",
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT,
        help=f"Output path (default: {DEFAULT_OUT}).",
    )
    parser.add_argument(
        "--verbose", action="store_true",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    log.info("Generating %d synthetic cases (seed=%d)...", args.n, args.seed)
    cases = generate_synthetic_cases(n=args.n, seed=args.seed)
    accused = generate_synthetic_accused(cases, seed=args.seed + 1)

    summary = dataset_summary(cases)
    log.info(
        "Dataset: %d cases, %d districts, %d series crimes, "
        "%d accused",
        summary["count"],
        summary["districts"],
        summary["series_count"],
        len(accused),
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": summary,
        "cases": [asdict(c) for c in cases],
        "accused": [asdict(a) for a in accused],
    }
    # ``asdict`` converts datetimes to strings for JSON.
    with args.out.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)

    log.info("Wrote %s (%d bytes)", args.out, args.out.stat().st_size)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
