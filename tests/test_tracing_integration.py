"""Integration tests: tracing middleware wired into MiddlewarePipeline."""
from patchwork.middleware import RequestContext, MiddlewarePipeline
from patchwork.middleware_tracing import TracingConfig, make_tracing_middleware


def _make_ctx(**kwargs) -> RequestContext:
    defaults = dict(
        method="GET",
        path="/ping",
        request_headers={},
        response_headers={},
        metadata={},
    )
    defaults.update(kwargs)
    return RequestContext(**defaults)


def _make_pipeline(config: TracingConfig) -> MiddlewarePipeline:
    pipeline = MiddlewarePipeline()
    pre, post = make_tracing_middleware(config)
    pipeline.add_pre(pre)
    pipeline.add_post(post)
    return pipeline


def test_pipeline_disabled_no_headers():
    pipeline = _make_pipeline(TracingConfig(enabled=False))
    ctx = _make_ctx()
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    assert ctx.response_headers == {}
    assert "trace_id" not in ctx.metadata


def test_pipeline_enabled_ids_round_trip():
    pipeline = _make_pipeline(TracingConfig(enabled=True))
    ctx = _make_ctx()
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    trace_id = ctx.metadata["trace_id"]
    assert ctx.response_headers["X-Trace-Id"] == trace_id
    assert "X-Span-Id" in ctx.response_headers


def test_pipeline_preserves_caller_trace_id():
    pipeline = _make_pipeline(TracingConfig(enabled=True))
    ctx = _make_ctx(request_headers={"X-Trace-Id": "caller-trace-99"})
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    assert ctx.metadata["trace_id"] == "caller-trace-99"
    assert ctx.response_headers["X-Trace-Id"] == "caller-trace-99"


def test_pipeline_custom_headers():
    cfg = TracingConfig(
        enabled=True,
        trace_id_header="Traceparent",
        span_id_header="Tracestate",
        propagate_span=True,
    )
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx()
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    assert "Traceparent" in ctx.response_headers
    assert "Tracestate" in ctx.response_headers
    assert ctx.request_headers.get("Tracestate") == ctx.metadata["span_id"]
