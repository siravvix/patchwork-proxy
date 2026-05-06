"""Tests for patchwork.middleware_auth module."""
import pytest

from patchwork.auth import AuthConfig
from patchwork.middleware import RequestContext
from patchwork.middleware_auth import (
    CTX_AUTH_KEY,
    CTX_AUTH_RESULT,
    build_default_auth_middleware,
    make_auth_middleware,
)


def make_ctx(
    headers: dict | None = None,
    query_params: dict | None = None,
) -> RequestContext:
    ctx = RequestContext(method="GET", path="/test", target="http://localhost:8080")
    ctx.extra["request_headers"] = headers or {}
    ctx.extra["query_params"] = query_params or {}
    return ctx


def test_middleware_disabled_auth_passes_all():
    cfg = AuthConfig(enabled=False)
    mw = make_auth_middleware(cfg)
    ctx = make_ctx()
    result = mw(ctx)
    assert result is not None
    assert result.extra[CTX_AUTH_RESULT] is True


def test_middleware_valid_key_in_header():
    cfg = AuthConfig(enabled=True, valid_keys={"my-key"})
    mw = make_auth_middleware(cfg)
    ctx = make_ctx(headers={"X-Api-Key": "my-key"})
    result = mw(ctx)
    assert result.extra[CTX_AUTH_RESULT] is True
    assert result.extra[CTX_AUTH_KEY] == "my-key"


def test_middleware_valid_key_in_query_param():
    cfg = AuthConfig(enabled=True, valid_keys={"qkey"})
    mw = make_auth_middleware(cfg)
    ctx = make_ctx(query_params={"api_key": "qkey"})
    result = mw(ctx)
    assert result.extra[CTX_AUTH_RESULT] is True


def test_middleware_missing_key_fails():
    cfg = AuthConfig(enabled=True, valid_keys={"secret"})
    mw = make_auth_middleware(cfg)
    ctx = make_ctx()
    result = mw(ctx)
    assert result.extra[CTX_AUTH_RESULT] is False
    assert "auth_error" in result.extra


def test_middleware_wrong_key_fails():
    cfg = AuthConfig(enabled=True, valid_keys={"correct"})
    mw = make_auth_middleware(cfg)
    ctx = make_ctx(headers={"X-Api-Key": "wrong"})
    result = mw(ctx)
    assert result.extra[CTX_AUTH_RESULT] is False
    assert result.extra[CTX_AUTH_KEY] == "wrong"


def test_build_default_auth_middleware_no_config():
    mw = build_default_auth_middleware()
    ctx = make_ctx()
    result = mw(ctx)
    assert result.extra[CTX_AUTH_RESULT] is True


def test_build_default_auth_middleware_with_config():
    cfg = AuthConfig(enabled=True, valid_keys={"k"})
    mw = build_default_auth_middleware(cfg)
    ctx = make_ctx(headers={"X-Api-Key": "k"})
    result = mw(ctx)
    assert result.extra[CTX_AUTH_RESULT] is True
