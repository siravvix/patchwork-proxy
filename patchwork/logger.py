"""Structured request logging utilities for patchwork-proxy."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str = "INFO", fmt: str = "text") -> None:
    """Configure root logger for patchwork.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR).
        fmt:   Output format – "text" for human-readable, "json" for structured.
    """
    handler = logging.StreamHandler(sys.stdout)

    if fmt == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger namespaced under 'patchwork'."""
    return logging.getLogger(f"patchwork.{name}")
