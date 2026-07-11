"""
Alembic environment.

Configured for the Saaransh backend:

  - Reads DATABASE_URL from backend.config.settings (same as the app)
  - Imports every ORM model so autogenerate can diff against Base.metadata
  - Uses schema_transaction for safe migrations with pgvector-aware
    batch operations (if we ever need to alter a vector column)

Run migrations with:
    alembic -c backend/alembic.ini upgrade head
    alembic -c backend/alembic.ini revision --autogenerate -m "msg"
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# --- ensure the project root is on sys.path so ``backend.*`` imports work --
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings  # noqa: E402
from backend.database.session import Base  # noqa: E402
from backend import models  # noqa: E402, F401  (register models on Base.metadata)


# ---- Alembic config object ------------------------------------------------
config = context.config

# Inject our runtime DATABASE_URL so we never have to duplicate it in
# alembic.ini. The % interpolation in alembic.ini is a Python format string
# at this point.
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL to stdout/file."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
