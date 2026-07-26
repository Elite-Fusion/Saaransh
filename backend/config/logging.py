"""
Centralised structured logging configuration.

Supports two formats:
  - text: human-readable format for development
  - json: structured JSON format for production (compatible with log aggregators)

Logs to stdout so it works in containers (Docker/Railway/Render)
without any file-system dependency.

Features:
  - Request/response logging
  - Error tracking with stack traces
  - Authentication event logging
  - AI investigation logging
  - WebSocket event logging
  - Log rotation support via external tools (logrotate, Docker logging drivers)
"""
import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any

from backend.config.settings import settings


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields from structured logging
        for key in ("user_id", "request_id", "method", "path", "status_code",
                     "duration_ms", "ip_address", "event_type", "ai_provider",
                     "ai_model", "sql_query", "error_code"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        return json.dumps(log_entry, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for development."""

    def __init__(self) -> None:
        super().__init__(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


class RequestLoggingFilter(logging.Filter):
    """Filter to add request context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Add default values for structured fields if not present
        if not hasattr(record, "request_id"):
            record.request_id = None
        if not hasattr(record, "user_id"):
            record.user_id = None
        return True


def configure_logging() -> None:
    """Idempotent logger setup. Call once at app startup."""
    root = logging.getLogger()
    if root.handlers:
        # Already configured
        return

    root.setLevel(settings.log_level)

    handler = logging.StreamHandler(stream=sys.stdout)

    if settings.log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Add request context filter
    root.addFilter(RequestLoggingFilter())

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.db_echo else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """Convenience accessor for module-level loggers."""
    return logging.getLogger(name)


# ---- Structured logging helpers ----

def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: int | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
) -> None:
    """Log an HTTP request with structured fields."""
    logger.info(
        "%s %s -> %s (%.1fms)",
        method,
        path,
        status_code,
        duration_ms,
        extra={
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 1),
            "user_id": user_id,
            "request_id": request_id,
            "ip_address": ip_address,
        },
    )


def log_auth_event(
    logger: logging.Logger,
    event: str,
    user_id: int | None = None,
    email: str | None = None,
    success: bool = True,
    ip_address: str | None = None,
    reason: str | None = None,
) -> None:
    """Log an authentication event."""
    level = logging.INFO if success else logging.WARNING
    logger.log(
        level,
        "Auth event: %s (user=%s, success=%s)",
        event,
        user_id or email,
        success,
        extra={
            "event_type": f"auth.{event}",
            "user_id": user_id,
            "success": success,
            "ip_address": ip_address,
            "reason": reason,
        },
    )


def log_ai_investigation(
    logger: logging.Logger,
    question: str,
    sql_query: str | None = None,
    duration_ms: float | None = None,
    success: bool = True,
    user_id: int | None = None,
    error: str | None = None,
) -> None:
    """Log an AI investigation request."""
    level = logging.INFO if success else logging.ERROR
    logger.log(
        level,
        "AI investigation: %s (success=%s)",
        question[:100],
        success,
        extra={
            "event_type": "ai.investigation",
            "user_id": user_id,
            "sql_query": sql_query,
            "duration_ms": duration_ms,
            "success": success,
            "error": error,
        },
    )


def log_prediction_call(
    logger: logging.Logger,
    model: str,
    prediction_type: str,
    duration_ms: float | None = None,
    success: bool = True,
    user_id: int | None = None,
    error: str | None = None,
) -> None:
    """Log a prediction service call."""
    level = logging.INFO if success else logging.ERROR
    logger.log(
        level,
        "Prediction call: %s/%s (success=%s)",
        model,
        prediction_type,
        success,
        extra={
            "event_type": "prediction.call",
            "ai_provider": model,
            "user_id": user_id,
            "duration_ms": duration_ms,
            "success": success,
            "error": error,
        },
    )


def log_websocket_event(
    logger: logging.Logger,
    event_type: str,
    user_id: int | None = None,
    room: str | None = None,
    success: bool = True,
) -> None:
    """Log a WebSocket event."""
    logger.info(
        "WebSocket event: %s (user=%s, room=%s)",
        event_type,
        user_id,
        room,
        extra={
            "event_type": f"websocket.{event_type}",
            "user_id": user_id,
            "room": room,
            "success": success,
        },
    )


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: str | None = None,
    user_id: int | None = None,
    request_id: str | None = None,
) -> None:
    """Log an error with full context."""
    logger.error(
        "Error: %s - %s",
        type(error).__name__,
        str(error),
        exc_info=True,
        extra={
            "event_type": "error",
            "error_code": type(error).__name__,
            "user_id": user_id,
            "request_id": request_id,
            "context": context,
        },
    )
