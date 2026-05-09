"""Unit tests for patchwork.middleware_header_rewrite."""

import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_header_rewrite import (
    HeaderRewriteConfig,
    make_header_rewrite_middleware,
)


def make_ctx(
    request_headers: dict | None = None,
    response_headers: dict | None = None,
) -> RequestContext:
    ctx = RequestContext(method="GET", path="/test", target="http://localhost")
    ctx.meta["request_headers"] = dict(request_headers or {})
    ctx.meta["response_headers"] = dict(response_headers or {})
    return ctx


# --- HeaderRewriteConfig ---

def test_config_defaults():
    cfg = HeaderRewriteConfig()
    assert cfg.rename_request == {}
    assert cfg.rename_response == {}
    assert cfg.force_request == {}
    assert cfg.force_response == {}


def test_config_invalid_type_raises():
    with pytest.raises(TypeError):
        HeaderRewriteConfig(rename_request="bad")  # type: ignore


def test_config_empty_key_raises():
    with pytest.raises(ValueError):
        HeaderRewriteConfig(force_request={"": "value"})


def test_config_from_dict():
    cfg = HeaderRewriteConfig.from_dict({
        "rename_request": {"X-Old": "X-New"},
        "force_response": {"X-Proxy": "patchwork"},
    })
    assert cfg.rename_request == {"X-Old": "X-New"}
    assert cfg.force_response == {"X-Proxy": "patchwork"}


# --- pre_middleware ---

def test_pre_renames_request_header():
    cfg = HeaderRewriteConfig(rename_request={"X-Old": "X-New"})
    pre, _ = make_header_rewrite_middleware(cfg)
    ctx = make_ctx(request_headers={"X-Old": "hello"})
    pre(ctx)
    assert "X-New" in ctx.meta["request_headers"]
    assert "X-Old" not in ctx.meta["request_headers"]
    assert ctx.meta["request_headers"]["X-New"] == "hello"


def test_pre_force_sets_request_header():
    cfg = HeaderRewriteConfig(force_request={"X-Token": "secret"})
    pre, _ = make_header_rewrite_middleware(cfg)
    ctx = make_ctx()
    pre(ctx)
    assert ctx.meta["request_headers"]["X-Token"] == "secret"


def test_pre_rename_missing_header_is_noop():
    cfg = HeaderRewriteConfig(rename_request={"X-Missing": "X-New"})
    pre, _ = make_header_rewrite_middleware(cfg)
    ctx = make_ctx(request_headers={"X-Other": "val"})
    pre(ctx)
    assert "X-New" not in ctx.meta["request_headers"]
    assert "X-Other" in ctx.meta["request_headers"]


# --- post_middleware ---

def test_post_renames_response_header():
    cfg = HeaderRewriteConfig(rename_response={"Server": "X-Backend"})
    _, post = make_header_rewrite_middleware(cfg)
    ctx = make_ctx(response_headers={"Server": "nginx"})
    post(ctx)
    assert ctx.meta["response_headers"]["X-Backend"] == "nginx"
    assert "Server" not in ctx.meta["response_headers"]


def test_post_force_sets_response_header():
    cfg = HeaderRewriteConfig(force_response={"X-Powered-By": "patchwork"})
    _, post = make_header_rewrite_middleware(cfg)
    ctx = make_ctx(response_headers={})
    post(ctx)
    assert ctx.meta["response_headers"]["X-Powered-By"] == "patchwork"


def test_post_force_overwrites_existing():
    cfg = HeaderRewriteConfig(force_response={"X-Frame-Options": "DENY"})
    _, post = make_header_rewrite_middleware(cfg)
    ctx = make_ctx(response_headers={"X-Frame-Options": "ALLOW"})
    post(ctx)
    assert ctx.meta["response_headers"]["X-Frame-Options"] == "DENY"
