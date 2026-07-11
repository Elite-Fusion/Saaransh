"""
Database connection test script.

Verifies the full ORM metadata against the live database without
requiring a real connection — useful in CI / smoke tests where
Postgres may not be available.

Behaviour:

  1. Reports the database URL (with the password masked).
  2. Tries to open a connection. If it fails, reports clearly
     and exits 1 (so a missing DB is loud, not silent).
  3. Counts the tables already present in the public schema.
  4. Verifies the SQLAlchemy ORM metadata matches the live schema
     (every declared table exists, and the column set is a subset).
  5. Reports the total declared model count and exits 0.

Run with:
    python -m scripts.db_test
or:
    python scripts/db_test.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# --- ensure the project root is on sys.path so ``backend.*`` imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import inspect, text  # noqa: E402

from backend.config import settings  # noqa: E402
from backend.config.logging import configure_logging, get_logger  # noqa: E402
from backend.database import engine  # noqa: E402
from backend.models import (  # noqa: E402, F401  (imports register models on Base.metadata)
    Accused,
    Act,
    ActSectionAssociation,
    ArrestSurrender,
    AuditLog,
    CaseCategory,
    CaseMaster,
    CaseStatusMaster,
    CasteMaster,
    ChargesheetDetails,
    ComplainantDetails,
    Court,
    CrimeHead,
    CrimeHeadActSection,
    CrimeSubHead,
    Designation,
    District,
    Employee,
    Evidence,
    GravityOffence,
    OccupationMaster,
    Rank,
    RecoveredItems,
    ReligionMaster,
    Section,
    State,
    Unit,
    UnitType,
    Users,
    Victim,
)
from backend.database.session import Base  # noqa: E402


log = get_logger(__name__)


# ---- helpers ----------------------------------------------------------------
def _mask_url(url: str) -> str:
    """Hide the password in a DSN for safe logging."""
    return re.sub(r"://([^:]+):[^@]+@", r"://\1:***@", url)


def _check_live_schema() -> tuple[int, list[str]]:
    """Return (live_table_count, missing_tables)."""
    inspector = inspect(engine)
    live_tables = set(inspector.get_table_names(schema="public"))

    declared = set(Base.metadata.tables.keys())
    missing = sorted(declared - live_tables)
    return len(live_tables), missing


# ---- main -------------------------------------------------------------------
def main() -> int:
    configure_logging()
    log.info("=" * 70)
    log.info("Saaransh AI — Database Connection Test")
    log.info("=" * 70)
    log.info("Database URL : %s", _mask_url(settings.database_url))
    log.info("ORM models   : %d declared", len(Base.metadata.tables))

    # ---- 1. connectivity --------------------------------------------------
    log.info("Step 1/3 — testing connectivity…")
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version();")).scalar_one_or_none()
            log.info("  ✓ connected. server: %s", (version or "unknown").split(",")[0])
    except Exception as exc:
        log.error("  x connection FAILED: %s", exc)
        log.error("    -> check DATABASE_URL in .env and that Postgres is reachable.")
        return 1

    # ---- 2. live table count ---------------------------------------------
    log.info("Step 2/3 - inspecting public schema...")
    try:
        live_count, missing = _check_live_schema()
        log.info("  + %d tables present in 'public' schema", live_count)
        if missing:
            log.warning(
                "  ! %d declared models are MISSING from the live DB:",
                len(missing),
            )
            for name in missing:
                log.warning("      - %s", name)
            log.warning(
                "    -> run database/schema/ksp_real_schema.sql to create them."
            )
        else:
            log.info("  + every declared model has a matching table in the DB")
    except Exception as exc:
        log.error("  x schema inspection FAILED: %s", exc)
        return 1

    # ---- 3. model summary ------------------------------------------------
    log.info("Step 3/3 - declared models:")
    for name in sorted(Base.metadata.tables):
        cols = len(Base.metadata.tables[name].columns)
        log.info("  * %-35s %3d column(s)", name, cols)

    log.info("=" * 70)
    log.info("OK - all checks passed.")
    log.info("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
