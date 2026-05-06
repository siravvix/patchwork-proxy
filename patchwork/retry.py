"""Retry logic for upstream proxy requests."""

import time
from typing import Callable, Optional
from patchwork.logger import get_logger

logger = get_logger(__name__)


class RetryConfig:
    """Configuration for retry behaviour."""

    def __init__(
        self,
        max_attempts: int = 3,
        backoff_base_ms: float = 100.0,
        backoff_multiplier: float = 2.0,
        max_backoff_ms: float = 2000.0,
        retryable_status_codes: Optional[list] = None,
    ):
        self.max_attempts = max_attempts
        self.backoff_base_ms = backoff_base_ms
        self.backoff_multiplier = backoff_multiplier
        self.max_backoff_ms = max_backoff_ms
        self.retryable_status_codes = retryable_status_codes or [502, 503, 504]

    def backoff_seconds(self, attempt: int) -> float:
        """Return sleep duration in seconds for the given attempt (0-indexed)."""
        delay_ms = self.backoff_base_ms * (self.backoff_multiplier ** attempt)
        delay_ms = min(delay_ms, self.max_backoff_ms)
        return delay_ms / 1000.0


class RetryResult:
    """Holds the outcome of a retried call."""

    def __init__(self, value=None, attempts: int = 0, last_exception: Optional[Exception] = None):
        self.value = value
        self.attempts = attempts
        self.last_exception = last_exception

    @property
    def succeeded(self) -> bool:
        return self.last_exception is None and self.value is not None


def with_retry(fn: Callable, config: Optional[RetryConfig] = None) -> RetryResult:
    """Execute *fn* with retry logic defined by *config*.

    *fn* must return a tuple of (status_code: int, body: bytes) or raise an
    exception on hard failure.  A status code present in
    ``config.retryable_status_codes`` is treated as a soft failure and will
    trigger a retry.
    """
    if config is None:
        config = RetryConfig()

    last_exc: Optional[Exception] = None
    last_value = None

    for attempt in range(config.max_attempts):
        try:
            result = fn()
            status_code = result[0] if isinstance(result, tuple) else None
            if status_code in config.retryable_status_codes:
                logger.warning(
                    "retryable_status",
                    extra={"attempt": attempt + 1, "status": status_code},
                )
                last_value = result
                if attempt < config.max_attempts - 1:
                    time.sleep(config.backoff_seconds(attempt))
                continue
            return RetryResult(value=result, attempts=attempt + 1)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "request_exception",
                extra={"attempt": attempt + 1, "error": str(exc)},
            )
            if attempt < config.max_attempts - 1:
                time.sleep(config.backoff_seconds(attempt))

    return RetryResult(value=last_value, attempts=config.max_attempts, last_exception=last_exc)
