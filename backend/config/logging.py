"""
Centralised logging configuration.

Logs to stdout so it works in containers (Railway/Render/Docker)
without any file-system dependency. Format is configurable via
`LOG_FORMAT` env var (json for prod, text for dev).
"""
import logging
import sys

from backend.config.settings import settings


def configure_logging() -> None:
    """Idempotent logger setup. Call once at app startup."""
    root = logging.getLogger()
    if root.handlers:
        # Already configured (e.g. uvicorn imported this module twice).
        return

    root.setLevel(settings.log_level)

    handler = logging.StreamHandler(stream=sys.stdout)

    if settings.log_format == "json":
        formatter = logging.Formatter(
            '{"ts":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","msg":"%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Quiet noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.db_echo else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """Convenience accessor for module-level loggers."""
    return logging.getLogger(name)
