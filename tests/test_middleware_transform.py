"""Tests for patchwork.middleware_transform."""

from __future__ import annotations

import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_transform import make_transform_middleware, build_default_transform_middleware
from patchwork.transform import TransformConfig


def make_ctx(**kwargs) -> RequestContext:
    defaults = dict(
        method="GET",
        path="/test",
        query="",
        request_headers={},
        response_headers={},
        target_url="http://localhost:8080/test",
        status_code=None,
        response_body=None,
        extra={},
    )
    defaults.update(kwargs)
    return RequestContext(**defaults)


def test_pre_middleware_adds_request_headers():
    cfg = TransformConfig(set_request_headers={"X-Proxy": "patchwork"})
    pre, _ = make_transform_middleware(cfg)
    ctx = make_ctx()
    pre(ctx)
    assert ctx.request_headers.get("X-Proxy") == "patchwork"


def test_pre_middleware_removes_request_headers():
    cfg = TransformConfig(remove_request_headers=["Authorization"])
    pre, _ = make_transform_middleware(cfg)
    ctx = make_ctx(request_headers={"Authorization": "Bearer secret", "Accept": "*/*"})
    pre(ctx)
    assert "Authorization" not in ctx.request_headers
    assert ctx.request_headers.get("Accept") == "*/*"


def test_post_middleware_adds_response_headers():
    cfg = TransformConfig(set_response_headers={"X-Served-By": "patchwork-proxy"})
    _, post = make_transform_middleware(cfg)
    ctx = make_ctx(response_headers={})
    post(ctx)
    assert ctx.response_headers.get("X-Served-By") == "patchwork-proxy"


def test_post_middleware_removes_response_headers():
    cfg = TransformConfig(remove_response_headers=["Server"])
    _, post = make_transform_middleware(cfg)
    ctx = make_ctx(response_headers={"Server": "nginx", "Content-Type": "application/json"})
    post(ctx)
    assert "Server" not in ctx.response_headers
    assert ctx.response_headers.get("Content-Type") == "application/json"


def test_pre_middleware_initialises_missing_request_headers():
    cfg = TransformConfig(set_request_headers={"X-Init": "yes"})
    pre, _ = make_transform_middleware(cfg)
    ctx = make_ctx(request_headers=None)
    pre(ctx)
    assert ctx.request_headers["X-Init"] == "yes"


def test_post_middleware_initialises_missing_response_headers():
    cfg = TransformConfig(set_response_headers={"X-Init": "yes"})
    _, post = make_transform_middleware(cfg)
    ctx = make_ctx(response_headers=None)
    post(ctx)
    assert ctx.response_headers["X-Init"] == "yes"


def test_no_op_when_no_transforms_configured():
    cfg = TransformConfig()
    pre, post = make_transform_middleware(cfg)
    ctx = make_ctx(request_headers={"Accept": "*/*"}, response_headers={"Content-Type": "text/plain"})
    pre(ctx)
    post(ctx)
    assert ctx.request_headers == {"Accept": "*/*"}
    assert ctx.response_headers == {"Content-Type": "text/plain"}


def test_build_default_transform_middleware_empty_dict():
    pre, post = build_default_transform_middleware({})
    ctx = make_ctx()
    pre(ctx)
    post(ctx)
    # no error and headers unchanged
    assert ctx.request_headers == {}


def test_build_default_transform_middleware_with_config():
    pre, post = build_default_transform_middleware(
        {"set_request_headers": {"X-Env": "dev"}}
    )
    ctx = make_ctx()
    pre(ctx)
    assert ctx.request_headers["X-Env"] == "dev"
