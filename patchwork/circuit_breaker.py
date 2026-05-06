"""Simple circuit breaker for upstream health tracking."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject requests
    HALF_OPEN = "half_open" # Probing if upstream recovered


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5       # failures before opening
    recovery_timeout: float = 30.0   # seconds before half-open probe
    success_threshold: int = 2       # successes in half-open to close


@dataclass
class CircuitBreaker:
    host: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    opened_at: float = 0.0

    def is_open(self) -> bool:
        """Return True if requests should be blocked."""
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.opened_at >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return False
            return True
        return False

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._close()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.state == CircuitState.HALF_OPEN:
            self._open()
        elif (
            self.state == CircuitState.CLOSED
            and self.failure_count >= self.config.failure_threshold
        ):
            self._open()

    def _open(self) -> None:
        self.state = CircuitState.OPEN
        self.opened_at = time.monotonic()
        self.success_count = 0

    def _close(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0


class CircuitBreakerRegistry:
    """Manages circuit breakers keyed by upstream host."""

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get(self, host: str) -> CircuitBreaker:
        if host not in self._breakers:
            self._breakers[host] = CircuitBreaker(host=host, config=self._config)
        return self._breakers[host]

    def reset(self, host: str) -> None:
        if host in self._breakers:
            del self._breakers[host]

    def all_states(self) -> Dict[str, str]:
        return {host: cb.state.value for host, cb in self._breakers.items()}
