"""
SQLAlchemy engine + session factory.

Uses synchronous psycopg2 for simplicity in Phase 1. We can swap to
async (asyncpg + AsyncSession) later without touching call-sites
because everything depends on `get_db()`.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config.settings import settings


class Base(DeclarativeBase):
    """Declarative base — all ORM models inherit from this."""


def _build_engine() -> Engine:
    return create_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_pre_ping=True,  # detects dropped connections before use
    )


engine: Engine = _build_engine()

# `autoflush=False` + `autocommit=False` is the standard SQLAlchemy pattern;
# transactions are managed explicitly in services.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped session.

    Usage in a route:
        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
