"""Tests for patchwork.middleware_compression."""

from __future__ import annotations

import gzip

import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_compression import (
    CompressionConfig,
    build_default_compression_middleware,
    make_compression_middleware,
)
from patchwork.middleware import MiddlewarePipeline


def make_ctx(
    body: str | bytes = "",
    accept_encoding: str = "gzip",
    content_type: str = "application/json",
) -> RequestContext:
    ctx = RequestContext(
        method="GET",
        path="/test",
        request_headers={"Accept-Encoding": accept_encoding},
        response_headers={"Content-Type": content_type},
        response_body=body.encode() if isinstance(body, str) else body,
        response_status=200,
    )
    return ctx


def test_config_defaults():
    cfg = CompressionConfig()
    assert cfg.enabled is True
    assert cfg.min_bytes == 1024
    assert "application/json" in cfg.compressible_types


def test_config_invalid_min_bytes_raises():
    with pytest.raises(ValueError, match="min_bytes"):
        CompressionConfig(min_bytes=-1)


def test_config_empty_types_raises():
    with pytest.raises(ValueError, match="compressible_types"):
        CompressionConfig(compressible_types=set())


def test_config_from_dict():
    cfg = CompressionConfig.from_dict({"enabled": False, "min_bytes": 512})
    assert cfg.enabled is False
    assert cfg.min_bytes == 512


def test_compresses_large_json_body():
    body = b"x" * 2000
    cfg = CompressionConfig(min_bytes=512)
    mw = make_compression_middleware(cfg)
    ctx = make_ctx(body=body)
    result = mw(ctx)
    assert result.response_headers["Content-Encoding"] == "gzip"
    assert gzip.decompress(result.response_body) == body


def test_skips_small_body():
    body = b"small"
    cfg = CompressionConfig(min_bytes=1024)
    mw = make_compression_middleware(cfg)
    ctx = make_ctx(body=body)
    result = mw(ctx)
    assert "Content-Encoding" not in result.response_headers
    assert result.response_body == body


def test_skips_when_client_does_not_accept_gzip():
    body = b"x" * 2000
    cfg = CompressionConfig(min_bytes=512)
    mw = make_compression_middleware(cfg)
    ctx = make_ctx(body=body, accept_encoding="identity")
    result = mw(ctx)
    assert "Content-Encoding" not in result.response_headers


def test_skips_non_compressible_content_type():
    body = b"x" * 2000
    cfg = CompressionConfig(min_bytes=512)
    mw = make_compression_middleware(cfg)
    ctx = make_ctx(body=body, content_type="image/png")
    result = mw(ctx)
    assert "Content-Encoding" not in result.response_headers


def test_disabled_config_does_nothing():
    body = b"x" * 2000
    cfg = CompressionConfig(enabled=False)
    mw = make_compression_middleware(cfg)
    ctx = make_ctx(body=body)
    result = mw(ctx)
    assert "Content-Encoding" not in result.response_headers


def test_content_length_updated_after_compression():
    body = b"x" * 2000
    cfg = CompressionConfig(min_bytes=512)
    mw = make_compression_middleware(cfg)
    ctx = make_ctx(body=body)
    result = mw(ctx)
    assert int(result.response_headers["Content-Length"]) == len(result.response_body)


def test_build_default_registers_post_middleware():
    pipeline = MiddlewarePipeline()
    build_default_compression_middleware(pipeline)
    ctx = make_ctx(body=b"y" * 2000)
    out = pipeline.run_post(ctx)
    assert out.response_headers.get("Content-Encoding") == "gzip"
