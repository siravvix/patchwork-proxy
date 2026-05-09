"""Integration tests: header-rewrite middleware wired into a MiddlewarePipeline."""

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_header_rewrite import (
    HeaderRewriteConfig,
    build_default_header_rewrite_middleware,
)


def _make_ctx(
    request_headers: dict | None = None,
    response_headers: dict | None = None,
) -> RequestContext:
    ctx = RequestContext(method="GET", path="/api/test", target="http://backend")
    ctx.meta["request_headers"] = dict(request_headers or {})
    ctx.meta["response_headers"] = dict(response_headers or {})
    return ctx


def _make_pipeline(config: HeaderRewriteConfig) -> MiddlewarePipeline:
    pipeline = MiddlewarePipeline()
    build_default_header_rewrite_middleware(pipeline, config)
    return pipeline


def test_pipeline_renames_request_header():
    cfg = HeaderRewriteConfig(rename_request={"Authorization": "X-Auth-Token"})
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx(request_headers={"Authorization": "Bearer abc"})
    pipeline.run_pre(ctx)
    assert ctx.meta["request_headers"].get("X-Auth-Token") == "Bearer abc"
    assert "Authorization" not in ctx.meta["request_headers"]


def test_pipeline_forces_and_renames_request_headers():
    cfg = HeaderRewriteConfig(
        rename_request={"X-Old-Id": "X-Request-Id"},
        force_request={"X-Proxy": "patchwork"},
    )
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx(request_headers={"X-Old-Id": "req-1"})
    pipeline.run_pre(ctx)
    hdrs = ctx.meta["request_headers"]
    assert hdrs["X-Request-Id"] == "req-1"
    assert hdrs["X-Proxy"] == "patchwork"


def test_pipeline_renames_response_header():
    cfg = HeaderRewriteConfig(rename_response={"X-Internal-Error": "X-Error"})
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx(response_headers={"X-Internal-Error": "db timeout"})
    pipeline.run_post(ctx)
    assert ctx.meta["response_headers"].get("X-Error") == "db timeout"
    assert "X-Internal-Error" not in ctx.meta["response_headers"]


def test_pipeline_combined_request_and_response_rewrites():
    cfg = HeaderRewriteConfig(
        force_request={"X-Forwarded-By": "patchwork-proxy"},
        force_response={"X-Frame-Options": "SAMEORIGIN"},
    )
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx()
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    assert ctx.meta["request_headers"]["X-Forwarded-By"] == "patchwork-proxy"
    assert ctx.meta["response_headers"]["X-Frame-Options"] == "SAMEORIGIN"


def test_pipeline_empty_config_is_noop():
    cfg = HeaderRewriteConfig()
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx(
        request_headers={"Accept": "application/json"},
        response_headers={"Content-Type": "application/json"},
    )
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    assert ctx.meta["request_headers"] == {"Accept": "application/json"}
    assert ctx.meta["response_headers"] == {"Content-Type": "application/json"}
