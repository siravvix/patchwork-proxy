"""High-level retry policy helpers that bridge RetryConfig and ProxyConfig."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Set

from patchwork.retry import RetryConfig


@dataclass
class RetryPolicy:
    """Per-route retry policy parsed from proxy configuration."""

    enabled: bool = True
    max_attempts: int = 3
    retryable_statuses: Set[int] = field(default_factory=lambda: {502, 503, 504})
    backoff_base: float = 0.5
    backoff_max: float = 10.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.backoff_base < 0:
            raise ValueError("backoff_base must be non-negative")
        if self.backoff_max < self.backoff_base:
            raise ValueError("backoff_max must be >= backoff_base")

    def to_retry_config(self) -> RetryConfig:
        return RetryConfig(
            max_attempts=self.max_attempts,
            retryable_statuses=set(self.retryable_statuses),
            backoff_base=self.backoff_base,
            backoff_max=self.backoff_max,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "RetryPolicy":
        return cls(
            enabled=data.get("enabled", True),
            max_attempts=data.get("max_attempts", 3),
            retryable_statuses=set(data.get("retryable_statuses", [502, 503, 504])),
            backoff_base=data.get("backoff_base", 0.5),
            backoff_max=data.get("backoff_max", 10.0),
        )

    def as_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "max_attempts": self.max_attempts,
            "retryable_statuses": sorted(self.retryable_statuses),
            "backoff_base": self.backoff_base,
            "backoff_max": self.backoff_max,
        }


def retry_policy_from_proxy_config(proxy_cfg: dict) -> RetryPolicy:
    """Extract retry policy from a top-level proxy config dict."""
    retry_cfg = proxy_cfg.get("retry", {})
    return RetryPolicy.from_dict(retry_cfg)
