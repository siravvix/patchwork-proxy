"""Integration tests: TransformConfig + middleware pipeline together."""

from __future__ import annotations

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_transform import make_transform_middleware
from patchwork.transform import TransformConfig


def _make_ctx(**kwargs) -> RequestContext:
    defaults = dict(
        method="GET",
        path="/api/data",
        query="",
        request_headers={"Host": "localhost"},
        response_headers={"Server": "gunicorn"},
        target_url="http://backend:9000/api/data",
        status_code=200,
        response_body=None,
        extra={},
    )
    defaults.update(kwargs)
    return RequestContext(**defaults)


def _make_pipeline(cfg: TransformConfig) -> MiddlewarePipeline:
    pipeline = MiddlewarePipeline()
    pre, post = make_transform_middleware(cfg)
    pipeline.add_pre(pre)
    pipeline.add_post(post)
    return pipeline


def test_pipeline_injects_and_strips_request_headers():
    cfg = TransformConfig(
        set_request_headers={"X-Request-Id": "abc123"},
        remove_request_headers=["Host"],
    )
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx()
    pipeline.run_pre(ctx)
    assert ctx.request_headers.get("X-Request-Id") == "abc123"
    assert "Host" not in ctx.request_headers


def test_pipeline_injects_and_strips_response_headers():
    cfg = TransformConfig(
        set_response_headers={"X-Powered-By": "patchwork"},
        remove_response_headers=["Server"],
    )
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx()
    pipeline.run_post(ctx)
    assert ctx.response_headers.get("X-Powered-By") == "patchwork"
    assert "Server" not in ctx.response_headers


def test_pipeline_combined_request_and_response_transforms():
    cfg = TransformConfig(
        set_request_headers={"X-Forwarded-Proto": "https"},
        remove_request_headers=["Host"],
        set_response_headers={"Cache-Control": "no-store"},
        remove_response_headers=["Server"],
    )
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx()
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    assert ctx.request_headers.get("X-Forwarded-Proto") == "https"
    assert "Host" not in ctx.request_headers
    assert ctx.response_headers.get("Cache-Control") == "no-store"
    assert "Server" not in ctx.response_headers


def test_pipeline_empty_transform_is_identity():
    cfg = TransformConfig()
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx()
    original_req = dict(ctx.request_headers)
    original_res = dict(ctx.response_headers)
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    assert ctx.request_headers == original_req
    assert ctx.response_headers == original_res
