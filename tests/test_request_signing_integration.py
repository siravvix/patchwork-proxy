"""Integration tests: request signing middleware wired into a MiddlewarePipeline."""
import time

import pytest

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_request_signing import (
    RequestSigningConfig,
    _compute_signature,
    make_request_signing_middleware,
)


def _make_ctx(method="GET", path="/secure", headers=None) -> RequestContext:
    ctx = RequestContext()
    ctx.method = method
    ctx.path = path
    ctx.request_headers = headers or {}
    return ctx


def _make_pipeline(cfg: RequestSigningConfig) -> MiddlewarePipeline:
    pipeline = MiddlewarePipeline()
    pipeline.add_pre(make_request_signing_middleware(cfg))
    return pipeline


def _valid_headers(secret, method, path, skew=0, extra=None):
    ts = int(time.time()) + skew
    sig = _compute_signature(secret, method, path, str(ts), extra or {})
    return {"X-Signature": sig, "X-Timestamp": str(ts)}


def test_pipeline_disabled_no_signature_needed():
    cfg = RequestSigningConfig(enabled=False)
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx()
    result = pipeline.run_pre(ctx)
    assert result is None
    assert ctx.response_status is None


def test_pipeline_valid_signature_passes():
    cfg = RequestSigningConfig(enabled=True, secret="integration-secret")
    pipeline = _make_pipeline(cfg)
    headers = _valid_headers("integration-secret", "GET", "/secure")
    ctx = _make_ctx(headers=headers)
    result = pipeline.run_pre(ctx)
    assert result is None
    assert ctx.response_status is None


def test_pipeline_invalid_signature_blocked():
    cfg = RequestSigningConfig(enabled=True, secret="integration-secret")
    pipeline = _make_pipeline(cfg)
    ts = int(time.time())
    headers = {"X-Signature": "deadbeef", "X-Timestamp": str(ts)}
    ctx = _make_ctx(headers=headers)
    result = pipeline.run_pre(ctx)
    assert result == "reject"
    assert ctx.response_status == 401


def test_pipeline_expired_timestamp_blocked():
    cfg = RequestSigningConfig(enabled=True, secret="s", max_skew_seconds=5)
    pipeline = _make_pipeline(cfg)
    headers = _valid_headers("s", "GET", "/secure", skew=-60)
    ctx = _make_ctx(headers=headers)
    result = pipeline.run_pre(ctx)
    assert result == "reject"
    assert ctx.response_body == b"timestamp skew too large"


def test_pipeline_custom_reject_status():
    cfg = RequestSigningConfig(enabled=True, secret="s", reject_status=403)
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx(headers={"X-Timestamp": str(int(time.time())), "X-Signature": "bad"})
    pipeline.run_pre(ctx)
    assert ctx.response_status == 403
