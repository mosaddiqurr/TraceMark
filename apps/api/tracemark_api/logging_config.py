"""Structured logging that deliberately excludes request bodies and secrets."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
        }
        if record.exc_info:
            exception_type = record.exc_info[0]
            payload["exception_type"] = exception_type.__name__ if exception_type else "unknown"
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # Uvicorn otherwise retains its own traceback formatter after the app starts.
    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers[:] = [handler]
        logger.propagate = False
    logging.getLogger("uvicorn.access").disabled = True
