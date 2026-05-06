"""Token-bucket rate limiter for per-route request throttling."""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class RateLimitConfig:
    requests_per_second: float = 10.0
    burst: int = 20

    def __post_init__(self):
        if self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        if self.burst < 1:
            raise ValueError("burst must be at least 1")


class TokenBucket:
    """Thread-safe token bucket implementation."""

    def __init__(self, config: RateLimitConfig):
        self._config = config
        self._tokens: float = float(config.burst)
        self._last_refill: float = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        added = elapsed * self._config.requests_per_second
        self._tokens = min(self._config.burst, self._tokens + added)
        self._last_refill = now

    def acquire(self) -> bool:
        """Try to consume one token. Returns True if allowed, False if throttled."""
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    @property
    def available_tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens


class RateLimiter:
    """Manages per-route token buckets."""

    def __init__(self, default_config: RateLimitConfig | None = None):
        self._default_config = default_config or RateLimitConfig()
        self._buckets: Dict[str, TokenBucket] = {}
        self._route_configs: Dict[str, RateLimitConfig] = {}
        self._lock = threading.Lock()

    def configure_route(self, route_id: str, config: RateLimitConfig) -> None:
        with self._lock:
            self._route_configs[route_id] = config
            self._buckets[route_id] = TokenBucket(config)

    def is_allowed(self, route_id: str) -> bool:
        with self._lock:
            if route_id not in self._buckets:
                cfg = self._route_configs.get(route_id, self._default_config)
                self._buckets[route_id] = TokenBucket(cfg)
            bucket = self._buckets[route_id]
        return bucket.acquire()

    def reset(self, route_id: str) -> None:
        with self._lock:
            self._buckets.pop(route_id, None)
