"""Tests for patchwork.middleware_request_size."""
from __future__ import annotations

import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_request_size import (
    RequestSizeConfig,
    _content_length,
    build_default_request_size_middleware,
    make_request_size_middleware,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_ctx(
    content_length: int | None = None,
    extra_headers: dict | None = None,
) -> RequestContext:
    headers: dict = {}
    if content_length is not None:
        headers["content-length"] = str(content_length)
    if extra_headers:
        headers.update(extra_headers)
    return RequestContext(
        method="POST",
        path="/upload",
        request_headers=headers,
        query_string="",
    )


# ---------------------------------------------------------------------------
# RequestSizeConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = RequestSizeConfig()
    assert cfg.enabled is True
    assert cfg.max_bytes == 1_048_576


def test_config_invalid_max_bytes_raises():
    with pytest.raises(ValueError, match="max_bytes"):
        RequestSizeConfig(max_bytes=0)


def test_config_from_dict():
    cfg = RequestSizeConfig.from_dict({"enabled": False, "max_bytes": 512})
    assert cfg.enabled is False
    assert cfg.max_bytes == 512


def test_config_from_dict_defaults():
    cfg = RequestSizeConfig.from_dict({})
    assert cfg.enabled is True
    assert cfg.max_bytes == 1_048_576


# ---------------------------------------------------------------------------
# _content_length helper
# ---------------------------------------------------------------------------

def test_content_length_present():
    ctx = make_ctx(content_length=2048)
    assert _content_length(ctx) == 2048


def test_content_length_absent():
    ctx = make_ctx()
    assert _content_length(ctx) is None


def test_content_length_invalid_string():
    ctx = make_ctx(extra_headers={"content-length": "not-a-number"})
    assert _content_length(ctx) is None


# ---------------------------------------------------------------------------
# make_request_size_middleware
# ---------------------------------------------------------------------------

def test_middleware_allows_request_within_limit():
    cfg = RequestSizeConfig(max_bytes=1000)
    mw = make_request_size_middleware(cfg)
    ctx = make_ctx(content_length=500)
    result = mw(ctx)
    assert result.response_status is None
    assert not getattr(result, "skip_upstream", False)


def test_middleware_blocks_oversized_request():
    cfg = RequestSizeConfig(max_bytes=1000)
    mw = make_request_size_middleware(cfg)
    ctx = make_ctx(content_length=2000)
    result = mw(ctx)
    assert result.response_status == 413
    assert result.skip_upstream is True
    assert "2000" in result.response_body
    assert "1000" in result.response_body


def test_middleware_allows_when_no_content_length():
    cfg = RequestSizeConfig(max_bytes=1000)
    mw = make_request_size_middleware(cfg)
    ctx = make_ctx()  # no Content-Length header
    result = mw(ctx)
    assert result.response_status is None


def test_middleware_disabled_skips_check():
    cfg = RequestSizeConfig(enabled=False, max_bytes=1)
    mw = make_request_size_middleware(cfg)
    ctx = make_ctx(content_length=999_999)
    result = mw(ctx)
    assert result.response_status is None


def test_build_default_middleware_works():
    mw = build_default_request_size_middleware(max_bytes=256)
    ctx = make_ctx(content_length=512)
    result = mw(ctx)
    assert result.response_status == 413
