"""Integration tests: AuthConfig loaded from dict + middleware pipeline."""
import pytest

from patchwork.auth import AuthConfig
from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_auth import CTX_AUTH_RESULT, make_auth_middleware


def _make_pipeline(config_dict: dict) -> MiddlewarePipeline:
    cfg = AuthConfig.from_dict(config_dict)
    pipeline = MiddlewarePipeline()
    pipeline.add_pre(make_auth_middleware(cfg))
    return pipeline


def _make_ctx(headers: dict | None = None) -> RequestContext:
    ctx = RequestContext(method="GET", path="/api/data", target="http://backend:9000")
    ctx.extra["request_headers"] = headers or {}
    ctx.extra["query_params"] = {}
    return ctx


def test_pipeline_auth_disabled_no_key_needed():
    pipeline = _make_pipeline({"enabled": False})
    ctx = _make_ctx()
    result = pipeline.run_pre(ctx)
    assert result.extra[CTX_AUTH_RESULT] is True


def test_pipeline_auth_enabled_valid_key():
    pipeline = _make_pipeline({"enabled": True, "valid_keys": ["tok-abc"]})
    ctx = _make_ctx(headers={"X-Api-Key": "tok-abc"})
    result = pipeline.run_pre(ctx)
    assert result.extra[CTX_AUTH_RESULT] is True


def test_pipeline_auth_enabled_invalid_key():
    pipeline = _make_pipeline({"enabled": True, "valid_keys": ["tok-abc"]})
    ctx = _make_ctx(headers={"X-Api-Key": "bad"})
    result = pipeline.run_pre(ctx)
    assert result.extra[CTX_AUTH_RESULT] is False


def test_pipeline_auth_custom_header():
    pipeline = _make_pipeline({
        "enabled": True,
        "header_name": "Authorization",
        "valid_keys": ["Bearer secret"],
    })
    ctx = _make_ctx(headers={"Authorization": "Bearer secret"})
    result = pipeline.run_pre(ctx)
    assert result.extra[CTX_AUTH_RESULT] is True


def test_pipeline_multiple_valid_keys():
    pipeline = _make_pipeline({
        "enabled": True,
        "valid_keys": ["key-1", "key-2", "key-3"],
    })
    for k in ["key-1", "key-2", "key-3"]:
        ctx = _make_ctx(headers={"X-Api-Key": k})
        result = pipeline.run_pre(ctx)
        assert result.extra[CTX_AUTH_RESULT] is True, f"Expected key {k!r} to be valid"
