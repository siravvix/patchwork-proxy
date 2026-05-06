"""Tests for the circuit breaker module."""

import time
import pytest
from patchwork.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
)


@pytest.fixture
def config():
    return CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0, success_threshold=2)


@pytest.fixture
def breaker(config):
    return CircuitBreaker(host="localhost:8080", config=config)


def test_initial_state_is_closed(breaker):
    assert breaker.state == CircuitState.CLOSED
    assert not breaker.is_open()


def test_opens_after_failure_threshold(breaker):
    for _ in range(3):
        breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.is_open()


def test_does_not_open_below_threshold(breaker):
    for _ in range(2):
        breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED
    assert not breaker.is_open()


def test_success_resets_failure_count(breaker):
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_success()
    # failure_count resets on success in CLOSED state
    assert breaker.failure_count == 0
    assert breaker.state == CircuitState.CLOSED


def test_transitions_to_half_open_after_timeout(breaker):
    for _ in range(3):
        breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    # Manually backdate opened_at to simulate timeout
    breaker.opened_at = time.monotonic() - 2.0
    assert not breaker.is_open()
    assert breaker.state == CircuitState.HALF_OPEN


def test_closes_after_successes_in_half_open(breaker):
    for _ in range(3):
        breaker.record_failure()
    breaker.opened_at = time.monotonic() - 2.0
    breaker.is_open()  # triggers HALF_OPEN transition
    breaker.record_success()
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED


def test_reopens_on_failure_in_half_open(breaker):
    for _ in range(3):
        breaker.record_failure()
    breaker.opened_at = time.monotonic() - 2.0
    breaker.is_open()
    assert breaker.state == CircuitState.HALF_OPEN
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN


def test_registry_creates_breaker_on_demand(config):
    registry = CircuitBreakerRegistry(config)
    cb = registry.get("upstream:9000")
    assert isinstance(cb, CircuitBreaker)
    assert cb.host == "upstream:9000"


def test_registry_returns_same_instance(config):
    registry = CircuitBreakerRegistry(config)
    assert registry.get("host:1") is registry.get("host:1")


def test_registry_all_states(config):
    registry = CircuitBreakerRegistry(config)
    registry.get("a:1")
    registry.get("b:2")
    for _ in range(3):
        registry.get("b:2").record_failure()
    states = registry.all_states()
    assert states["a:1"] == "closed"
    assert states["b:2"] == "open"
