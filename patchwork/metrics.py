"""In-memory request metrics collector for patchwork-proxy."""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class RouteStats:
    requests: int = 0
    errors: int = 0
    total_ms: float = 0.0

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.requests if self.requests else 0.0


class MetricsCollector:
    """Thread-safe collector for per-route request metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stats: Dict[str, RouteStats] = defaultdict(RouteStats)

    def record(self, route_key: str, elapsed_ms: float, is_error: bool = False) -> None:
        with self._lock:
            s = self._stats[route_key]
            s.requests += 1
            s.total_ms += elapsed_ms
            if is_error:
                s.errors += 1

    def snapshot(self) -> Dict[str, RouteStats]:
        """Return a shallow copy of current stats."""
        with self._lock:
            return {k: RouteStats(v.requests, v.errors, v.total_ms) for k, v in self._stats.items()}

    def reset(self) -> None:
        with self._lock:
            self._stats.clear()

    def summary(self) -> str:
        lines = ["Route Metrics:", "-" * 40]
        for key, s in sorted(self.snapshot().items()):
            lines.append(
                f"  {key}: {s.requests} req, {s.errors} err, avg {s.avg_ms:.1f} ms"
            )
        return "\n".join(lines)


# Module-level singleton
_collector: MetricsCollector = MetricsCollector()


def get_collector() -> MetricsCollector:
    return _collector
