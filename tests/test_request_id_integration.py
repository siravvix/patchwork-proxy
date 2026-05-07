"""Integration tests: request-ID middleware wired into a full pipeline."""
from __future__ import annotations

import uuid

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.request_id import (
    REQUEST_ID_HEADER,
    REQUEST_ID_KEY,
    build_default_request_id_middleware,
)


def _make_pipeline(propagate: bool = True) -> MiddlewarePipeline:
    pipeline = MiddlewarePipeline()
    build_default_request_id_middleware(pipeline, propagate=propagate)
    return pipeline


def _make_ctx(**meta) -> RequestContext:
    ctx = RequestContext(source_path="/api/data", target_url="http://backend/api/data")
    ctx.metadata.update(meta)
    return ctx


def test_pipeline_generates_id_when_none_provided():
    pipeline = _make_pipeline()
    ctx = _make_ctx()
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)

    rid = ctx.metadata[REQUEST_ID_KEY]
    uuid.UUID(rid)  # valid UUID
    assert ctx.metadata["request_headers"][REQUEST_ID_HEADER] == rid
    assert ctx.metadata["response_headers"][REQUEST_ID_HEADER] == rid


def test_pipeline_preserves_caller_supplied_id():
    pipeline = _make_pipeline()
    ctx = _make_ctx(request_headers={REQUEST_ID_HEADER: "caller-supplied"})
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)

    assert ctx.metadata[REQUEST_ID_KEY] == "caller-supplied"
    assert ctx.metadata["response_headers"][REQUEST_ID_HEADER] == "caller-supplied"


def test_pipeline_no_propagation_omits_response_header():
    pipeline = _make_pipeline(propagate=False)
    ctx = _make_ctx()
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)

    assert REQUEST_ID_KEY in ctx.metadata  # still set internally
    assert REQUEST_ID_HEADER not in ctx.metadata.get("response_headers", {})


def test_pipeline_id_consistent_across_pre_and_post():
    """The same ID stamped in pre must appear in post without mutation."""
    pipeline = _make_pipeline()
    ctx = _make_ctx()
    pipeline.run_pre(ctx)
    id_after_pre = ctx.metadata[REQUEST_ID_KEY]
    pipeline.run_post(ctx)
    assert ctx.metadata["response_headers"][REQUEST_ID_HEADER] == id_after_pre
