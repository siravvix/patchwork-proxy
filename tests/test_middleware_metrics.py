"""Tests for patchwork.middleware_metrics."""

from __future__ import annotations

import time

import pytest

from patchwork.metrics import MetricsCollector
from patchwork.middleware import RequestContext
from patchwork.middleware_metrics import (
    _route_id,
    make_metrics_middleware,
    build_default_metrics_middleware,
)


def make_ctx(
    path: str = "/api/test",
    method: str = "GET",
    status: int = 200,
) -> RequestContext:
    ctx = RequestContext(
        target_path=path,
        request_headers={"X-Method": method},
        response_status=status,
    )
    return ctx


# ---------------------------------------------------------------------------
# _route_id
# ---------------------------------------------------------------------------

def test_route_id_uses_method_and_path():
    ctx = make_ctx(path="/health", method="GET")
    assert _route_id(ctx) == "GET /health"


def test_route_id_falls_back_for_missing_method():
    ctx = RequestContext(target_path="/x", request_headers={}, response_status=200)
    assert _route_id(ctx) == "UNKNOWN /x"


# ---------------------------------------------------------------------------
# make_metrics_middleware
# ---------------------------------------------------------------------------

def test_pre_middleware_stamps_start_time():
    collector = MetricsCollector()
    pre, _post = make_metrics_middleware(collector)
    ctx = make_ctx()
    before = time.monotonic()
    ctx = pre(ctx)
    after = time.monotonic()
    assert "_metrics_start" in ctx.extra
    assert before <= ctx.extra["_metrics_start"] <= after


def test_post_middleware_records_request():
    collector = MetricsCollector()
    pre, post = make_metrics_middleware(collector)
    ctx = make_ctx(path="/ping", method="GET", status=200)
    ctx = pre(ctx)
    ctx = post(ctx)
    stats = collector.get_stats()
    assert "GET /ping" in stats
    assert stats["GET /ping"].total_requests == 1
    assert stats["GET /ping"].error_count == 0


def test_post_middleware_records_error_on_5xx():
    collector = MetricsCollector()
    pre, post = make_metrics_middleware(collector)
    ctx = make_ctx(status=503)
    ctx = pre(ctx)
    ctx = post(ctx)
    stats = collector.get_stats()
    route = _route_id(ctx)
    assert stats[route].error_count == 1


def test_post_middleware_records_error_on_zero_status():
    collector = MetricsCollector()
    pre, post = make_metrics_middleware(collector)
    ctx = make_ctx(status=0)
    ctx = pre(ctx)
    ctx = post(ctx)
    stats = collector.get_stats()
    route = _route_id(ctx)
    assert stats[route].error_count == 1


def test_post_middleware_elapsed_is_non_negative():
    collector = MetricsCollector()
    pre, post = make_metrics_middleware(collector)
    ctx = make_ctx()
    ctx = pre(ctx)
    time.sleep(0.01)
    ctx = post(ctx)
    stats = collector.get_stats()
    route = _route_id(ctx)
    assert stats[route].avg_ms() >= 0


def test_post_middleware_no_start_does_not_raise():
    """If pre was skipped, post should still record without crashing."""
    collector = MetricsCollector()
    _pre, post = make_metrics_middleware(collector)
    ctx = make_ctx(status=200)
    ctx = post(ctx)  # no pre called
    stats = collector.get_stats()
    assert stats[_route_id(ctx)].total_requests == 1


# ---------------------------------------------------------------------------
# build_default_metrics_middleware
# ---------------------------------------------------------------------------

def test_build_default_creates_collector():
    collector, pre, post = build_default_metrics_middleware()
    assert isinstance(collector, MetricsCollector)


def test_build_default_reuses_provided_collector():
    existing = MetricsCollector()
    collector, _pre, _post = build_default_metrics_middleware(existing)
    assert collector is existing
