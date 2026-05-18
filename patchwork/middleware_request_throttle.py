"""Middleware that adds a configurable artificial delay to proxied requests.

Useful in local development to simulate slow upstream services.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

from patchwork.middleware import MiddlewarePipeline, RequestContext


@dataclass
class RequestThrottleConfig:
    """Configuration for the request throttle middleware."""

    enabled: bool = False
    # Fixed delay in milliseconds applied to every request
    delay_ms: float = 0.0
    # Optional per-path overrides: list of {"path_prefix": str, "delay_ms": float}
    path_overrides: List[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.delay_ms < 0:
            raise ValueError("delay_ms must be >= 0")
        for override in self.path_overrides:
            if "path_prefix" not in override or "delay_ms" not in override:
                raise ValueError(
                    "Each path_override must have 'path_prefix' and 'delay_ms' keys"
                )
            if override["delay_ms"] < 0:
                raise ValueError("path_override delay_ms must be >= 0")

    @classmethod
    def from_dict(cls, data: dict) -> "RequestThrottleConfig":
        return cls(
            enabled=data.get("enabled", False),
            delay_ms=float(data.get("delay_ms", 0.0)),
            path_overrides=list(data.get("path_overrides", [])),
        )

    def resolve_delay_ms(self, path: Optional[str]) -> float:
        """Return the effective delay for *path*, checking overrides first."""
        if path:
            for override in self.path_overrides:
                if path.startswith(override["path_prefix"]):
                    return float(override["delay_ms"])
        return self.delay_ms


def make_throttle_middleware(config: RequestThrottleConfig):
    """Return a pre-middleware function that sleeps for the configured delay."""

    def pre_middleware(ctx: RequestContext) -> None:
        if not config.enabled:
            return
        path: Optional[str] = ctx.request.get("path")
        delay = config.resolve_delay_ms(path)
        if delay > 0:
            time.sleep(delay / 1000.0)
            ctx.metadata["throttle_delay_ms"] = delay

    return pre_middleware


def build_default_throttle_middleware(
    pipeline: MiddlewarePipeline, config: RequestThrottleConfig
) -> None:
    """Attach the throttle pre-middleware to *pipeline*."""
    pipeline.add_pre(make_throttle_middleware(config))
