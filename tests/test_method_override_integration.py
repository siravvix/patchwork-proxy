"""Integration tests: MethodOverride middleware wired into MiddlewarePipeline."""

from __future__ import annotations

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_method_override import (
    MethodOverrideConfig,
    make_method_override_middleware,
)


def _make_ctx(method="POST", headers=None, query_params=None) -> RequestContext:
    ctx = RequestContext(
        request_method=method,
        request_path="/resource",
        request_headers=headers or {},
    )
    ctx.extra["query_params"] = query_params or {}
    return ctx


def _make_pipeline(cfg: MethodOverrideConfig) -> MiddlewarePipeline:
    pipeline = MiddlewarePipeline()
    pipeline.add_pre(make_method_override_middleware(cfg))
    return pipeline


def test_pipeline_post_to_delete_via_header():
    pipeline = _make_pipeline(MethodOverrideConfig())
    ctx = _make_ctx(method="POST", headers={"X-HTTP-Method-Override": "DELETE"})
    out = pipeline.run_pre(ctx)
    assert out.request_method == "DELETE"
    assert out.extra["original_method"] == "POST"


def test_pipeline_post_to_put_via_query_param():
    pipeline = _make_pipeline(MethodOverrideConfig())
    ctx = _make_ctx(method="POST", query_params={"_method": "PUT"})
    out = pipeline.run_pre(ctx)
    assert out.request_method == "PUT"


def test_pipeline_get_not_overridden_by_default():
    """GET is not in allowed_source_methods by default."""
    pipeline = _make_pipeline(MethodOverrideConfig())
    ctx = _make_ctx(method="GET", headers={"X-HTTP-Method-Override": "DELETE"})
    out = pipeline.run_pre(ctx)
    assert out.request_method == "GET"


def test_pipeline_custom_source_allows_get():
    cfg = MethodOverrideConfig(allowed_source_methods=["GET", "POST"])
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx(method="GET", query_params={"_method": "DELETE"})
    out = pipeline.run_pre(ctx)
    assert out.request_method == "DELETE"


def test_pipeline_disabled_passes_original_method():
    cfg = MethodOverrideConfig(enabled=False)
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx(method="POST", headers={"X-HTTP-Method-Override": "PATCH"})
    out = pipeline.run_pre(ctx)
    assert out.request_method == "POST"
    assert "original_method" not in out.extra


def test_pipeline_custom_header_name():
    cfg = MethodOverrideConfig(header_name="X-Override-Method")
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx(method="POST", headers={"X-Override-Method": "PATCH"})
    out = pipeline.run_pre(ctx)
    assert out.request_method == "PATCH"


def test_pipeline_custom_query_param_name():
    cfg = MethodOverrideConfig(query_param="override")
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx(method="POST", query_params={"override": "DELETE"})
    out = pipeline.run_pre(ctx)
    assert out.request_method == "DELETE"
