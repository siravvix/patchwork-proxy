"""Tests for middleware_method_override."""

from __future__ import annotations

import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_method_override import (
    MethodOverrideConfig,
    _resolve_override,
    make_method_override_middleware,
    build_default_method_override_middleware,
)


def make_ctx(
    method="POST",
    headers=None,
    query_params=None,
) -> RequestContext:
    ctx = RequestContext(
        request_method=method,
        request_path="/test",
        request_headers=headers or {},
    )
    ctx.extra["query_params"] = query_params or {}
    return ctx


# --- Config validation ---

def test_config_defaults():
    cfg = MethodOverrideConfig()
    assert cfg.enabled is True
    assert cfg.header_name == "X-HTTP-Method-Override"
    assert cfg.query_param == "_method"
    assert cfg.allowed_source_methods == ["POST"]


def test_config_empty_header_raises():
    with pytest.raises(ValueError, match="header_name"):
        MethodOverrideConfig(header_name="")


def test_config_empty_query_param_raises():
    with pytest.raises(ValueError, match="query_param"):
        MethodOverrideConfig(query_param="")


def test_config_empty_source_methods_raises():
    with pytest.raises(ValueError, match="allowed_source_methods"):
        MethodOverrideConfig(allowed_source_methods=[])


def test_config_from_dict():
    cfg = MethodOverrideConfig.from_dict({
        "enabled": False,
        "header_name": "X-Override",
        "query_param": "method",
        "allowed_source_methods": ["POST", "GET"],
    })
    assert cfg.enabled is False
    assert cfg.header_name == "X-Override"
    assert cfg.query_param == "method"
    assert cfg.allowed_source_methods == ["POST", "GET"]


# --- _resolve_override ---

def test_resolve_override_from_header():
    cfg = MethodOverrideConfig()
    ctx = make_ctx(method="POST", headers={"X-HTTP-Method-Override": "DELETE"})
    assert _resolve_override(ctx, cfg) == "DELETE"


def test_resolve_override_from_query_param():
    cfg = MethodOverrideConfig()
    ctx = make_ctx(method="POST", query_params={"_method": "PUT"})
    assert _resolve_override(ctx, cfg) == "PUT"


def test_resolve_override_header_takes_precedence():
    cfg = MethodOverrideConfig()
    ctx = make_ctx(
        method="POST",
        headers={"X-HTTP-Method-Override": "PATCH"},
        query_params={"_method": "DELETE"},
    )
    assert _resolve_override(ctx, cfg) == "PATCH"


def test_resolve_override_disallowed_source_returns_none():
    cfg = MethodOverrideConfig(allowed_source_methods=["POST"])
    ctx = make_ctx(method="GET", headers={"X-HTTP-Method-Override": "DELETE"})
    assert _resolve_override(ctx, cfg) is None


def test_resolve_override_invalid_target_returns_none():
    cfg = MethodOverrideConfig()
    ctx = make_ctx(method="POST", headers={"X-HTTP-Method-Override": "SUPERDELETE"})
    assert _resolve_override(ctx, cfg) is None


# --- Middleware behaviour ---

def test_middleware_overrides_method():
    mw = make_method_override_middleware(MethodOverrideConfig())
    ctx = make_ctx(method="POST", headers={"X-HTTP-Method-Override": "DELETE"})
    result = mw(ctx)
    assert result.request_method == "DELETE"
    assert result.extra["original_method"] == "POST"


def test_middleware_disabled_does_not_override():
    mw = make_method_override_middleware(MethodOverrideConfig(enabled=False))
    ctx = make_ctx(method="POST", headers={"X-HTTP-Method-Override": "DELETE"})
    result = mw(ctx)
    assert result.request_method == "POST"
    assert "original_method" not in result.extra


def test_middleware_no_override_header_unchanged():
    mw = make_method_override_middleware(MethodOverrideConfig())
    ctx = make_ctx(method="POST")
    result = mw(ctx)
    assert result.request_method == "POST"
    assert "original_method" not in result.extra


def test_build_default_returns_callable():
    mw = build_default_method_override_middleware()
    assert callable(mw)
