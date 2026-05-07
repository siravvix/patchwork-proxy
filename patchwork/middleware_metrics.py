"""Middleware that records per-route metrics using MetricsCollector."""

from __future__ import annotations

import time
from typing import Callable

from patchwork.metrics import MetricsCollector
from patchwork.middleware import RequestContext


def _route_id(ctx: RequestContext) -> str:
    """Derive a stable route identifier from the request context."""
    method = (ctx.request_headers.get("X-Method") or "UNKNOWN").upper()
    path = ctx.target_path or "/"
    return f"{method} {path}"


def make_metrics_middleware(
    collector: MetricsCollector,
) -> tuple[Callable, Callable]:
    """Return (pre_middleware, post_middleware) that bracket a proxied request.

    The pre-middleware stamps ``_metrics_start`` on the context so the
    post-middleware can compute elapsed time without relying on wall-clock
    drift between separate calls.
    """

    def pre_middleware(ctx: RequestContext) -> RequestContext:
        ctx.extra["_metrics_start"] = time.monotonic()
        return ctx

    def post_middleware(ctx: RequestContext) -> RequestContext:
        start: float | None = ctx.extra.get("_metrics_start")
        elapsed_ms = (time.monotonic() - start) * 1000.0 if start is not None else 0.0

        status = ctx.response_status or 0
        is_error = status >= 500 or status == 0

        route = _route_id(ctx)
        collector.record(route, elapsed_ms=elapsed_ms, is_error=is_error)
        return ctx

    return pre_middleware, post_middleware


def build_default_metrics_middleware(
    collector: MetricsCollector | None = None,
) -> tuple[MetricsCollector, Callable, Callable]:
    """Convenience factory that also creates a fresh collector when needed.

    Returns ``(collector, pre_middleware, post_middleware)`` so callers can
    inspect the collector later (e.g. for a /metrics endpoint).
    """
    if collector is None:
        collector = MetricsCollector()
    pre, post = make_metrics_middleware(collector)
    return collector, pre, post
