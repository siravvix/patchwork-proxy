"""Tests for circuit breaker middleware."""

import pytest

from patchwork.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from patchwork.middleware import RequestContext
from patchwork.middleware_circuit_breaker import (
    CIRCUIT_OPEN_STATUS,
    make_circuit_breaker_middleware,
)


def make_ctx(method="GET", target="/api", response_status=200):
    ctx = RequestContext(
        request={"method": method, "target": target, "headers": {}},
        response={"status": response_status, "body": b"", "headers": {}},
    )
    return ctx


@pytest.fixture
def config():
    return CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60.0)


@pytest.fixture
def registry():
    return {}


def test_pre_middleware_allows_closed_circuit(config, registry):
    pre, _ = make_circuit_breaker_middleware(config, registry)
    ctx = make_ctx()
    result = pre(ctx)
    assert result.metadata["circuit_breaker_open"] is False
    assert "circuit_breaker_route" in result.metadata


def test_pre_middleware_blocks_open_circuit(config, registry):
    breaker = CircuitBreaker(config)
    for _ in range(config.failure_threshold):
        breaker.record_failure()
    registry["GET:/api"] = breaker

    pre, _ = make_circuit_breaker_middleware(config, registry)
    ctx = make_ctx()
    result = pre(ctx)
    assert result.metadata["circuit_breaker_open"] is True
    assert result.response["status"] == CIRCUIT_OPEN_STATUS


def test_post_middleware_records_success(config, registry):
    pre, post = make_circuit_breaker_middleware(config, registry)
    ctx = make_ctx(response_status=200)
    ctx = pre(ctx)
    ctx = post(ctx)
    breaker = registry["GET:/api"]
    assert breaker.state == CircuitState.CLOSED
    assert ctx.metadata["circuit_breaker_state"] == CircuitState.CLOSED.value


def test_post_middleware_records_failure(config, registry):
    pre, post = make_circuit_breaker_middleware(config, registry)
    ctx = make_ctx(response_status=500)
    ctx = pre(ctx)
    ctx = post(ctx)
    breaker = registry["GET:/api"]
    assert breaker.failure_count == 1


def test_post_middleware_skips_when_circuit_was_open(config, registry):
    breaker = CircuitBreaker(config)
    for _ in range(config.failure_threshold):
        breaker.record_failure()
    registry["GET:/api"] = breaker
    initial_failures = breaker.failure_count

    pre, post = make_circuit_breaker_middleware(config, registry)
    ctx = make_ctx()
    ctx = pre(ctx)
    ctx = post(ctx)
    assert breaker.failure_count == initial_failures


def test_post_middleware_opens_after_threshold(config, registry):
    pre, post = make_circuit_breaker_middleware(config, registry)
    for _ in range(config.failure_threshold):
        ctx = make_ctx(response_status=500)
        ctx = pre(ctx)
        ctx = post(ctx)
    breaker = registry["GET:/api"]
    assert breaker.state == CircuitState.OPEN


def test_route_id_uses_method_and_target(config, registry):
    pre, _ = make_circuit_breaker_middleware(config, registry)
    ctx = make_ctx(method="POST", target="/submit")
    pre(ctx)
    assert "POST:/submit" in registry
