"""Unit tests for patchwork.request_id."""
from __future__ import annotations

import uuid

import pytest

from patchwork.middleware import RequestContext
from patchwork.request_id import (
    REQUEST_ID_HEADER,
    REQUEST_ID_KEY,
    _extract_or_generate,
    make_request_id_middleware,
    build_default_request_id_middleware,
)
from patchwork.middleware import MiddlewarePipeline


def make_ctx(**meta) -> RequestContext:
    ctx = RequestContext(source_path="/test", target_url="http://backend/test")
    ctx.metadata.update(meta)
    return ctx


# ---------------------------------------------------------------------------
# _extract_or_generate
# ---------------------------------------------------------------------------

def test_extract_uses_incoming_header():
    ctx = make_ctx(request_headers={REQUEST_ID_HEADER: "my-trace-id"})
    result = _extract_or_generate(ctx)
    assert result == "my-trace-id"


def test_extract_is_case_insensitive():
    ctx = make_ctx(request_headers={"x-request-id": "lower-case-id"})
    result = _extract_or_generate(ctx)
    assert result == "lower-case-id"


def test_generate_when_no_header():
    ctx = make_ctx()
    result = _extract_or_generate(ctx)
    # Should be a valid UUID
    uuid.UUID(result)  # raises if invalid


def test_generate_when_empty_header_value():
    ctx = make_ctx(request_headers={REQUEST_ID_HEADER: ""})
    result = _extract_or_generate(ctx)
    uuid.UUID(result)


# ---------------------------------------------------------------------------
# make_request_id_middleware — pre
# ---------------------------------------------------------------------------

def test_pre_sets_request_id_in_metadata():
    pre, _ = make_request_id_middleware()
    ctx = make_ctx()
    pre(ctx)
    assert REQUEST_ID_KEY in ctx.metadata
    uuid.UUID(ctx.metadata[REQUEST_ID_KEY])


def test_pre_injects_header_into_request_headers():
    pre, _ = make_request_id_middleware()
    ctx = make_ctx()
    pre(ctx)
    assert ctx.metadata["request_headers"][REQUEST_ID_HEADER] == ctx.metadata[REQUEST_ID_KEY]


def test_pre_honours_existing_incoming_id():
    pre, _ = make_request_id_middleware()
    ctx = make_ctx(request_headers={REQUEST_ID_HEADER: "keep-me"})
    pre(ctx)
    assert ctx.metadata[REQUEST_ID_KEY] == "keep-me"


def test_pre_uses_custom_factory():
    pre, _ = make_request_id_middleware(id_factory=lambda: "fixed-id")
    ctx = make_ctx()
    pre(ctx)
    assert ctx.metadata[REQUEST_ID_KEY] == "fixed-id"


# ---------------------------------------------------------------------------
# make_request_id_middleware — post
# ---------------------------------------------------------------------------

def test_post_propagates_id_to_response_headers():
    pre, post = make_request_id_middleware(propagate=True)
    ctx = make_ctx()
    pre(ctx)
    post(ctx)
    assert ctx.metadata["response_headers"][REQUEST_ID_HEADER] == ctx.metadata[REQUEST_ID_KEY]


def test_post_no_propagate_skips_response_header():
    pre, post = make_request_id_middleware(propagate=False)
    ctx = make_ctx()
    pre(ctx)
    post(ctx)
    assert REQUEST_ID_HEADER not in ctx.metadata.get("response_headers", {})


def test_post_safe_when_no_request_id_in_metadata():
    _, post = make_request_id_middleware(propagate=True)
    ctx = make_ctx()
    # pre was never called — should not raise
    post(ctx)


# ---------------------------------------------------------------------------
# build_default_request_id_middleware
# ---------------------------------------------------------------------------

def test_build_default_attaches_to_pipeline():
    pipeline = MiddlewarePipeline()
    build_default_request_id_middleware(pipeline)
    ctx = make_ctx()
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    assert REQUEST_ID_KEY in ctx.metadata
    assert ctx.metadata["response_headers"][REQUEST_ID_HEADER] == ctx.metadata[REQUEST_ID_KEY]
