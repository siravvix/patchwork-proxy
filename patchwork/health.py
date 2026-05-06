"""Health check module for upstream targets."""

import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Dict, Optional

from patchwork.logger import get_logger

logger = get_logger(__name__)


@dataclass
class HealthStatus:
    target: str
    healthy: bool
    last_checked: float = field(default_factory=time.time)
    last_error: Optional[str] = None
    consecutive_failures: int = 0

    def as_dict(self) -> dict:
        return {
            "target": self.target,
            "healthy": self.healthy,
            "last_checked": self.last_checked,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
        }


class HealthChecker:
    def __init__(self, path: str = "/healthz", timeout: float = 2.0, failure_threshold: int = 3):
        self.path = path
        self.timeout = timeout
        self.failure_threshold = failure_threshold
        self._statuses: Dict[str, HealthStatus] = {}

    def check(self, target: str) -> HealthStatus:
        url = target.rstrip("/") + self.path
        status = self._statuses.get(target, HealthStatus(target=target, healthy=True))

        try:
            req = urllib.request.urlopen(url, timeout=self.timeout)
            if req.status < 500:
                status.healthy = True
                status.consecutive_failures = 0
                status.last_error = None
            else:
                raise ValueError(f"HTTP {req.status}")
        except Exception as exc:
            status.consecutive_failures += 1
            status.last_error = str(exc)
            if status.consecutive_failures >= self.failure_threshold:
                status.healthy = False
                logger.warning("health_check_failed", extra={"target": target, "error": str(exc)})

        status.last_checked = time.time()
        self._statuses[target] = status
        return status

    def is_healthy(self, target: str) -> bool:
        status = self._statuses.get(target)
        if status is None:
            return True  # assume healthy until proven otherwise
        return status.healthy

    def get_all(self) -> Dict[str, dict]:
        return {t: s.as_dict() for t, s in self._statuses.items()}

    def reset(self, target: str) -> None:
        if target in self._statuses:
            self._statuses[target] = HealthStatus(target=target, healthy=True)
