"""Integration tests for compression middleware in a full pipeline."""

from __future__ import annotations

import gzip

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_compression import (
    CompressionConfig,
    build_default_compression_middleware,
)


def _make_ctx(
    body: bytes = b"",
    accept_encoding: str = "gzip",
    content_type: str = "application/json",
    status: int = 200,
) -> RequestContext:
    return RequestContext(
        method="GET",
        path="/api/data",
        request_headers={"Accept-Encoding": accept_encoding},
        response_headers={"Content-Type": content_type},
        response_body=body,
        response_status=status,
    )


def _make_pipeline(cfg: CompressionConfig | None = None) -> MiddlewarePipeline:
    pipeline = MiddlewarePipeline()
    build_default_compression_middleware(pipeline, cfg)
    return pipeline


def test_pipeline_compresses_eligible_response():
    body = b"hello world " * 200
    pipeline = _make_pipeline(CompressionConfig(min_bytes=128))
    ctx = _make_ctx(body=body)
    pipeline.run_pre(ctx)
    out = pipeline.run_post(ctx)
    assert out.response_headers["Content-Encoding"] == "gzip"
    assert gzip.decompress(out.response_body) == body


def test_pipeline_skips_compression_for_non_accepting_client():
    body = b"hello world " * 200
    pipeline = _make_pipeline(CompressionConfig(min_bytes=128))
    ctx = _make_ctx(body=body, accept_encoding="identity")
    pipeline.run_pre(ctx)
    out = pipeline.run_post(ctx)
    assert "Content-Encoding" not in out.response_headers
    assert out.response_body == body


def test_pipeline_does_not_compress_image_response():
    body = b"\x89PNG" + b"\x00" * 2000
    pipeline = _make_pipeline(CompressionConfig(min_bytes=128))
    ctx = _make_ctx(body=body, content_type="image/png")
    pipeline.run_pre(ctx)
    out = pipeline.run_post(ctx)
    assert "Content-Encoding" not in out.response_headers


def test_pipeline_disabled_compression_passthrough():
    body = b"data " * 500
    pipeline = _make_pipeline(CompressionConfig(enabled=False))
    ctx = _make_ctx(body=body)
    pipeline.run_pre(ctx)
    out = pipeline.run_post(ctx)
    assert "Content-Encoding" not in out.response_headers
    assert out.response_body == body
