"""Tests for patchwork.middleware_request_throttle."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_request_throttle import (
    RequestThrottleConfig,
    build_default_throttle_middleware,
    make_throttle_middleware,
)


def make_ctx(path: str = "/api/test", method: str = "GET") -> RequestContext:
    return RequestContext(request={"path": path, "method": method})


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = RequestThrottleConfig()
    assert cfg.enabled is False
    assert cfg.delay_ms == 0.0
    assert cfg.path_overrides == []


def test_config_invalid_delay_raises():
    with pytest.raises(ValueError, match="delay_ms must be >= 0"):
        RequestThrottleConfig(delay_ms=-1)


def test_config_invalid_override_missing_key_raises():
    with pytest.raises(ValueError, match="path_prefix"):
        RequestThrottleConfig(path_overrides=[{"path_prefix": "/slow"}])


def test_config_invalid_override_negative_delay_raises():
    with pytest.raises(ValueError, match="path_override delay_ms"):
        RequestThrottleConfig(
            path_overrides=[{"path_prefix": "/slow", "delay_ms": -5}]
        )


def test_config_from_dict():
    cfg = RequestThrottleConfig.from_dict(
        {"enabled": True, "delay_ms": 200, "path_overrides": []}
    )
    assert cfg.enabled is True
    assert cfg.delay_ms == 200.0


def test_config_from_dict_defaults():
    cfg = RequestThrottleConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.delay_ms == 0.0


# ---------------------------------------------------------------------------
# resolve_delay_ms tests
# ---------------------------------------------------------------------------

def test_resolve_delay_returns_base_when_no_overrides():
    cfg = RequestThrottleConfig(enabled=True, delay_ms=50)
    assert cfg.resolve_delay_ms("/anything") == 50.0


def test_resolve_delay_uses_override_for_matching_prefix():
    cfg = RequestThrottleConfig(
        enabled=True,
        delay_ms=10,
        path_overrides=[{"path_prefix": "/slow", "delay_ms": 300}],
    )
    assert cfg.resolve_delay_ms("/slow/endpoint") == 300.0


def test_resolve_delay_falls_back_for_non_matching_prefix():
    cfg = RequestThrottleConfig(
        enabled=True,
        delay_ms=10,
        path_overrides=[{"path_prefix": "/slow", "delay_ms": 300}],
    )
    assert cfg.resolve_delay_ms("/fast/endpoint") == 10.0


# ---------------------------------------------------------------------------
# Middleware behaviour tests
# ---------------------------------------------------------------------------

def test_disabled_does_not_sleep():
    cfg = RequestThrottleConfig(enabled=False, delay_ms=500)
    ctx = make_ctx()
    with patch("patchwork.middleware_request_throttle.time.sleep") as mock_sleep:
        make_throttle_middleware(cfg)(ctx)
    mock_sleep.assert_not_called()
    assert "throttle_delay_ms" not in ctx.metadata


def test_zero_delay_does_not_sleep():
    cfg = RequestThrottleConfig(enabled=True, delay_ms=0)
    ctx = make_ctx()
    with patch("patchwork.middleware_request_throttle.time.sleep") as mock_sleep:
        make_throttle_middleware(cfg)(ctx)
    mock_sleep.assert_not_called()


def test_positive_delay_sleeps_correct_duration():
    cfg = RequestThrottleConfig(enabled=True, delay_ms=150)
    ctx = make_ctx()
    with patch("patchwork.middleware_request_throttle.time.sleep") as mock_sleep:
        make_throttle_middleware(cfg)(ctx)
    mock_sleep.assert_called_once_with(0.15)
    assert ctx.metadata["throttle_delay_ms"] == 150.0


def test_path_override_delay_used():
    cfg = RequestThrottleConfig(
        enabled=True,
        delay_ms=10,
        path_overrides=[{"path_prefix": "/heavy", "delay_ms": 400}],
    )
    ctx = make_ctx(path="/heavy/compute")
    with patch("patchwork.middleware_request_throttle.time.sleep") as mock_sleep:
        make_throttle_middleware(cfg)(ctx)
    mock_sleep.assert_called_once_with(0.4)
    assert ctx.metadata["throttle_delay_ms"] == 400.0


def test_build_default_attaches_pre_middleware():
    cfg = RequestThrottleConfig(enabled=True, delay_ms=20)
    pipeline = MiddlewarePipeline()
    build_default_throttle_middleware(pipeline, cfg)
    ctx = make_ctx()
    with patch("patchwork.middleware_request_throttle.time.sleep"):
        pipeline.run_pre(ctx)
    assert ctx.metadata.get("throttle_delay_ms") == 20.0
