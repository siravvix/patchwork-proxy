"""Middleware that short-circuits requests to a built-in health-check endpoint."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

from patchwork.middleware import MiddlewarePipeline, RequestContext


_DEFAULT_PATH = "/__patchwork/health"
_SIGNAL_HEALTH = "__health_check__"


@dataclass
class HealthEndpointConfig:
    enabled: bool = True
    path: str = _DEFAULT_PATH
    # Extra key/value pairs to merge into the JSON response body
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.path.startswith("/"):
            raise ValueError("HealthEndpointConfig.path must start with '/'")

    @classmethod
    def from_dict(cls, data: dict) -> "HealthEndpointConfig":
        return cls(
            enabled=bool(data.get("enabled", True)),
            path=str(data.get("path", _DEFAULT_PATH)),
            extra=dict(data.get("extra", {})),
        )


def make_health_middleware(
    config: HealthEndpointConfig,
) -> Callable[[RequestContext], RequestContext]:
    """Return a *pre* middleware that intercepts health-check requests.

    When the incoming request path matches ``config.path`` the middleware
    sets ``ctx.response`` to a JSON 200 payload and attaches the sentinel
    signal ``_SIGNAL_HEALTH`` so the pipeline can skip proxying.
    """

    def _middleware(ctx: RequestContext) -> RequestContext:
        if not config.enabled:
            return ctx

        if ctx.request.get("path") == config.path:
            body = {"status": "ok", **config.extra}
            ctx.response = {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(body),
                "signal": _SIGNAL_HEALTH,
            }
        return ctx

    return _middleware


def build_default_health_middleware(
    pipeline: MiddlewarePipeline,
    config: HealthEndpointConfig | None = None,
) -> None:
    """Register the health-check pre-middleware on *pipeline*."""
    if config is None:
        config = HealthEndpointConfig()
    pipeline.add_pre(make_health_middleware(config))
