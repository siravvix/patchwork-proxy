"""Integration tests: circuit breaker middleware inside a full pipeline."""

import pytest

from patchwork.circuit_breaker import CircuitBreakerConfig
from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_circuit_breaker import (
    CIRCUIT_OPEN_STATUS,
    make_circuit_breaker_middleware,
)


def _make_ctx(status: int = 200) -> RequestContext:
    return RequestContext(
        request={"method": "GET", "target": "/svc", "headers": {}},
        response={"status": status, "body": b"ok", "headers": {}},
    )


def _make_pipeline(config: CircuitBreakerConfig, registry: dict) -> MiddlewarePipeline:
    pre, post = make_circuit_breaker_middleware(config, registry)
    pipeline = MiddlewarePipeline()
    pipeline.add_pre(pre)
    pipeline.add_post(post)
    return pipeline


def test_pipeline_passes_healthy_request():
    registry = {}
    config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60.0)
    pipeline = _make_pipeline(config, registry)
    ctx = _make_ctx(200)
    result = pipeline.run_pre(ctx)
    result = pipeline.run_post(result)
    assert result.response["status"] == 200
    assert result.metadata["circuit_breaker_open"] is False


def test_pipeline_opens_circuit_after_failures():
    registry = {}
    config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60.0)
    pipeline = _make_pipeline(config, registry)

    for _ in range(config.failure_threshold):
        ctx = _make_ctx(500)
        ctx = pipeline.run_pre(ctx)
        ctx = pipeline.run_post(ctx)

    ctx = _make_ctx(200)
    ctx = pipeline.run_pre(ctx)
    assert ctx.metadata["circuit_breaker_open"] is True
    assert ctx.response["status"] == CIRCUIT_OPEN_STATUS


def test_pipeline_circuit_open_skips_post_recording():
    registry = {}
    config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60.0)
    pipeline = _make_pipeline(config, registry)

    for _ in range(config.failure_threshold):
        ctx = _make_ctx(500)
        ctx = pipeline.run_pre(ctx)
        ctx = pipeline.run_post(ctx)

    breaker = registry["GET:/svc"]
    failures_before = breaker.failure_count

    ctx = _make_ctx(200)
    ctx = pipeline.run_pre(ctx)
    ctx = pipeline.run_post(ctx)
    assert breaker.failure_count == failures_before


def test_pipeline_separate_routes_independent():
    registry = {}
    config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60.0)
    pre, post = make_circuit_breaker_middleware(config, registry)
    pipeline = MiddlewarePipeline()
    pipeline.add_pre(pre)
    pipeline.add_post(post)

    for _ in range(config.failure_threshold):
        ctx = RequestContext(
            request={"method": "GET", "target": "/bad", "headers": {}},
            response={"status": 500, "body": b"", "headers": {}},
        )
        ctx = pipeline.run_pre(ctx)
        ctx = pipeline.run_post(ctx)

    ctx_good = RequestContext(
        request={"method": "GET", "target": "/good", "headers": {}},
        response={"status": 200, "body": b"ok", "headers": {}},
    )
    ctx_good = pipeline.run_pre(ctx_good)
    assert ctx_good.metadata["circuit_breaker_open"] is False
