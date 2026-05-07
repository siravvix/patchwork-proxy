"""Tests for patchwork.middleware_health."""

from __future__ import annotations

import json
import pytest

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_health import (
    HealthEndpointConfig,
    _SIGNAL_HEALTH,
    build_default_health_middleware,
    make_health_middleware,
)


def make_ctx(path: str = "/", method: str = "GET") -> RequestContext:
    ctx = RequestContext()
    ctx.request = {"path": path, "method": method, "headers": {}}
    return ctx


# ---------------------------------------------------------------------------
# HealthEndpointConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = HealthEndpointConfig()
    assert cfg.enabled is True
    assert cfg.path == "/__patchwork/health"
    assert cfg.extra == {}


def test_config_invalid_path_raises():
    with pytest.raises(ValueError, match="must start with"):
        HealthEndpointConfig(path="no-leading-slash")


def test_config_from_dict():
    cfg = HealthEndpointConfig.from_dict(
        {"enabled": False, "path": "/healthz", "extra": {"version": "1.2.3"}}
    )
    assert cfg.enabled is False
    assert cfg.path == "/healthz"
    assert cfg.extra == {"version": "1.2.3"}


# ---------------------------------------------------------------------------
# make_health_middleware
# ---------------------------------------------------------------------------

def test_health_path_sets_response():
    cfg = HealthEndpointConfig(path="/healthz")
    mw = make_health_middleware(cfg)
    ctx = make_ctx(path="/healthz")
    result = mw(ctx)
    assert result.response is not None
    assert result.response["status"] == 200
    assert result.response["signal"] == _SIGNAL_HEALTH


def test_health_path_body_is_ok():
    mw = make_health_middleware(HealthEndpointConfig())
    ctx = make_ctx(path="/__patchwork/health")
    result = mw(ctx)
    body = json.loads(result.response["body"])
    assert body["status"] == "ok"


def test_health_path_extra_fields_merged():
    cfg = HealthEndpointConfig(extra={"version": "0.9"})
    mw = make_health_middleware(cfg)
    ctx = make_ctx(path="/__patchwork/health")
    result = mw(ctx)
    body = json.loads(result.response["body"])
    assert body["version"] == "0.9"


def test_non_health_path_passes_through():
    mw = make_health_middleware(HealthEndpointConfig())
    ctx = make_ctx(path="/api/users")
    result = mw(ctx)
    assert result.response is None


def test_disabled_config_skips_interception():
    cfg = HealthEndpointConfig(enabled=False)
    mw = make_health_middleware(cfg)
    ctx = make_ctx(path="/__patchwork/health")
    result = mw(ctx)
    assert result.response is None


# ---------------------------------------------------------------------------
# build_default_health_middleware
# ---------------------------------------------------------------------------

def test_build_default_registers_pre_middleware():
    pipeline = MiddlewarePipeline()
    build_default_health_middleware(pipeline)
    ctx = make_ctx(path="/__patchwork/health")
    result, _ = pipeline.run(ctx)
    assert result.response is not None
    assert result.response["signal"] == _SIGNAL_HEALTH


def test_build_default_accepts_custom_config():
    pipeline = MiddlewarePipeline()
    cfg = HealthEndpointConfig(path="/ping")
    build_default_health_middleware(pipeline, config=cfg)
    ctx = make_ctx(path="/ping")
    result, _ = pipeline.run(ctx)
    assert result.response is not None
