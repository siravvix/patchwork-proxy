"""Integration tests: TLS-verify middleware wired into a MiddlewarePipeline."""
import pytest

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_tls_verify import TLSVerifyConfig, make_tls_verify_middleware


def _make_ctx(scheme: str = "", forwarded_proto: str = "") -> RequestContext:
    ctx = RequestContext()
    ctx.request = {"scheme": scheme}
    ctx.request_headers = {}
    ctx.response_headers = {}
    if forwarded_proto:
        ctx.request_headers["X-Forwarded-Proto"] = forwarded_proto
    return ctx


def _make_pipeline(enabled: bool = True, reject_status: int = 403) -> MiddlewarePipeline:
    pipeline = MiddlewarePipeline()
    cfg = TLSVerifyConfig(enabled=enabled, reject_status=reject_status)
    pipeline.add_pre(make_tls_verify_middleware(cfg))
    return pipeline


def test_pipeline_disabled_passes_http():
    pipeline = _make_pipeline(enabled=False)
    ctx = _make_ctx(scheme="http")
    pipeline.run_pre(ctx)
    assert not getattr(ctx, "short_circuit", False)


def test_pipeline_allows_https_scheme():
    pipeline = _make_pipeline(enabled=True)
    ctx = _make_ctx(scheme="https")
    pipeline.run_pre(ctx)
    assert not getattr(ctx, "short_circuit", False)


def test_pipeline_allows_https_via_header():
    pipeline = _make_pipeline(enabled=True)
    ctx = _make_ctx(forwarded_proto="https")
    pipeline.run_pre(ctx)
    assert not getattr(ctx, "short_circuit", False)


def test_pipeline_blocks_plain_http():
    pipeline = _make_pipeline(enabled=True, reject_status=403)
    ctx = _make_ctx(scheme="http")
    pipeline.run_pre(ctx)
    assert ctx.short_circuit is True
    assert ctx.response_status == 403


def test_pipeline_custom_status_426():
    pipeline = _make_pipeline(enabled=True, reject_status=426)
    ctx = _make_ctx(scheme="http")
    pipeline.run_pre(ctx)
    assert ctx.response_status == 426
    assert ctx.response_headers.get("X-TLS-Verify") == "rejected"
