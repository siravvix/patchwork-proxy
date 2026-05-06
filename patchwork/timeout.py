"""Per-route timeout configuration and enforcement."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TimeoutConfig:
    """Timeout settings for a proxy route."""

    connect_seconds: float = 5.0
    read_seconds: float = 30.0
    total_seconds: Optional[float] = None

    def __post_init__(self) -> None:
        if self.connect_seconds <= 0:
            raise ValueError("connect_seconds must be positive")
        if self.read_seconds <= 0:
            raise ValueError("read_seconds must be positive")
        if self.total_seconds is not None and self.total_seconds <= 0:
            raise ValueError("total_seconds must be positive")

    @property
    def as_tuple(self) -> tuple[float, float]:
        """Return (connect, read) tuple for use with urllib/requests."""
        return (self.connect_seconds, self.read_seconds)

    def is_exceeded(self, elapsed_seconds: float) -> bool:
        """Return True if the total timeout has been exceeded."""
        if self.total_seconds is None:
            return False
        return elapsed_seconds >= self.total_seconds

    @classmethod
    def from_dict(cls, data: dict) -> "TimeoutConfig":
        """Construct from a plain dictionary (e.g. parsed YAML/JSON)."""
        return cls(
            connect_seconds=float(data.get("connect_seconds", 5.0)),
            read_seconds=float(data.get("read_seconds", 30.0)),
            total_seconds=(
                float(data["total_seconds"]) if "total_seconds" in data else None
            ),
        )

    def to_dict(self) -> dict:
        d = {
            "connect_seconds": self.connect_seconds,
            "read_seconds": self.read_seconds,
        }
        if self.total_seconds is not None:
            d["total_seconds"] = self.total_seconds
        return d


DEFAULT_TIMEOUT = TimeoutConfig()
