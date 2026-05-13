"""Unit tests for patchwork.middleware_tracing."""
import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_tracing import (
    TracingConfig,
    make_tracing_middleware,
)


def make_ctx(**kwargs) -> RequestContext:
    defaults = dict(
        method="GET",
        path="/api/test",
        request_headers={},
        response_headers={},
        metadata={},
    )
    defaults.update(kwargs)
    return RequestContext(**defaults)


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = TracingConfig()
    assert cfg.enabled is False
    assert cfg.trace_id_header == "X-Trace-Id"
    assert cfg.span_id_header == "X-Span-Id"
    assert cfg.propagate_trace is True
    assert cfg.propagate_span is False


def test_config_empty_trace_header_raises():
    with pytest.raises(ValueError, match="trace_id_header"):
        TracingConfig(enabled=True, trace_id_header="")


def test_config_empty_span_header_raises():
    with pytest.raises(ValueError, match="span_id_header"):
        TracingConfig(enabled=True, span_id_header="")


def test_config_from_dict():
    cfg = TracingConfig.from_dict({"enabled": True, "propagate_span": True})
    assert cfg.enabled is True
    assert cfg.propagate_span is True


# ---------------------------------------------------------------------------
# Middleware behaviour tests
# ---------------------------------------------------------------------------

def test_disabled_tracing_does_nothing():
    cfg = TracingConfig(enabled=False)
    pre, post = make_tracing_middleware(cfg)
    ctx = make_ctx()
    pre(ctx)
    post(ctx)
    assert "trace_id" not in ctx.metadata
    assert ctx.response_headers == {}


def test_pre_generates_trace_and_span_ids():
    cfg = TracingConfig(enabled=True)
    pre, _ = make_tracing_middleware(cfg)
    ctx = make_ctx()
    pre(ctx)
    assert "trace_id" in ctx.metadata
    assert "span_id" in ctx.metadata
    assert len(ctx.metadata["trace_id"]) == 32  # uuid hex


def test_pre_reuses_incoming_trace_id():
    cfg = TracingConfig(enabled=True)
    pre, _ = make_tracing_middleware(cfg)
    ctx = make_ctx(request_headers={"X-Trace-Id": "abc123"})
    pre(ctx)
    assert ctx.metadata["trace_id"] == "abc123"


def test_pre_propagates_trace_header_to_upstream():
    cfg = TracingConfig(enabled=True, propagate_trace=True)
    pre, _ = make_tracing_middleware(cfg)
    ctx = make_ctx()
    pre(ctx)
    assert ctx.request_headers.get("X-Trace-Id") == ctx.metadata["trace_id"]


def test_pre_does_not_propagate_span_by_default():
    cfg = TracingConfig(enabled=True, propagate_span=False)
    pre, _ = make_tracing_middleware(cfg)
    ctx = make_ctx()
    pre(ctx)
    assert "X-Span-Id" not in ctx.request_headers


def test_post_attaches_ids_to_response_headers():
    cfg = TracingConfig(enabled=True)
    pre, post = make_tracing_middleware(cfg)
    ctx = make_ctx()
    pre(ctx)
    post(ctx)
    assert ctx.response_headers.get("X-Trace-Id") == ctx.metadata["trace_id"]
    assert ctx.response_headers.get("X-Span-Id") == ctx.metadata["span_id"]


def test_two_requests_get_different_span_ids():
    cfg = TracingConfig(enabled=True)
    pre, _ = make_tracing_middleware(cfg)
    ctx1, ctx2 = make_ctx(), make_ctx()
    pre(ctx1)
    pre(ctx2)
    assert ctx1.metadata["span_id"] != ctx2.metadata["span_id"]
