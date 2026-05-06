"""Middleware that enforces per-request timeouts via RequestContext."""

from __future__ import annotations

import time
from typing import Callable, Optional

from patchwork.middleware import RequestContext
from patchwork.timeout import TimeoutConfig, DEFAULT_TIMEOUT


def make_timeout_middleware(
    config: Optional[TimeoutConfig] = None,
) -> Callable[[RequestContext], RequestContext]:
    """Return a pre-middleware that stamps the request start time and attaches
    the active TimeoutConfig so downstream components can query it.

    Args:
        config: TimeoutConfig to attach. Falls back to DEFAULT_TIMEOUT.
    """
    effective = config or DEFAULT_TIMEOUT

    def _middleware(ctx: RequestContext) -> RequestContext:
        # Record wall-clock start if not already set.
        if not hasattr(ctx, "_timeout_start"):
            ctx._timeout_start = time.monotonic()  # type: ignore[attr-defined]
        ctx.extra["timeout_config"] = effective
        ctx.extra["timeout_connect"] = effective.connect_seconds
        ctx.extra["timeout_read"] = effective.read_seconds
        return ctx

    return _middleware


def is_timed_out(ctx: RequestContext) -> bool:
    """Return True if the total timeout has been exceeded for *ctx*."""
    cfg: Optional[TimeoutConfig] = ctx.extra.get("timeout_config")
    if cfg is None:
        return False
    start: Optional[float] = getattr(ctx, "_timeout_start", None)
    if start is None:
        return False
    elapsed = time.monotonic() - start
    return cfg.is_exceeded(elapsed)


def build_default_timeout_middleware() -> Callable[[RequestContext], RequestContext]:
    """Convenience factory using the global DEFAULT_TIMEOUT."""
    return make_timeout_middleware(DEFAULT_TIMEOUT)
