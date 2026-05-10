"""Tests for patchwork.middleware_response_size."""
from __future__ import annotations

import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_response_size import (
    ResponseSizeConfig,
    _body_size,
    _content_length,
    make_response_size_middleware,
)


def make_ctx(**kwargs) -> RequestContext:
    defaults = dict(
        method="GET",
        path="/data",
        headers={},
        query={},
        response_status=200,
        response_headers={"Content-Type": "application/json"},
        response_body=None,
        error=None,
    )
    defaults.update(kwargs)
    return RequestContext(**defaults)


# --- Config tests ---

def test_config_defaults():
    cfg = ResponseSizeConfig()
    assert cfg.enabled is False
    assert cfg.max_bytes == 10 * 1024 * 1024
    assert cfg.header_name == "X-Response-Size-Limit"


def test_config_invalid_max_bytes_raises():
    with pytest.raises(ValueError, match="max_bytes"):
        ResponseSizeConfig(max_bytes=0)


def test_config_empty_header_name_raises():
    with pytest.raises(ValueError, match="header_name"):
        ResponseSizeConfig(header_name="")


def test_config_from_dict():
    cfg = ResponseSizeConfig.from_dict({"enabled": True, "max_bytes": 512})
    assert cfg.enabled is True
    assert cfg.max_bytes == 512


# --- Helper tests ---

def test_content_length_from_headers():
    ctx = make_ctx(response_headers={"Content-Length": "128"})
    assert _content_length(ctx) == 128


def test_content_length_missing_returns_none():
    ctx = make_ctx(response_headers={})
    assert _content_length(ctx) is None


def test_body_size_bytes():
    ctx = make_ctx(response_body=b"hello")
    assert _body_size(ctx) == 5


def test_body_size_str():
    ctx = make_ctx(response_body="hello")
    assert _body_size(ctx) == 5


def test_body_size_none():
    ctx = make_ctx(response_body=None)
    assert _body_size(ctx) == 0


# --- Middleware behaviour tests ---

def test_middleware_disabled_passes_through():
    cfg = ResponseSizeConfig(enabled=False, max_bytes=1)
    mw = make_response_size_middleware(cfg)
    ctx = make_ctx(response_body=b"this is longer than one byte")
    result = mw(ctx)
    assert result.error is None
    assert result.response_status == 200


def test_middleware_within_limit_adds_header():
    cfg = ResponseSizeConfig(enabled=True, max_bytes=1024)
    mw = make_response_size_middleware(cfg)
    ctx = make_ctx(response_body=b"small")
    result = mw(ctx)
    assert result.error is None
    assert result.response_headers["X-Response-Size-Limit"] == "1024"


def test_middleware_exceeds_limit_sets_error():
    cfg = ResponseSizeConfig(enabled=True, max_bytes=4)
    mw = make_response_size_middleware(cfg)
    ctx = make_ctx(response_body=b"toolarge")
    result = mw(ctx)
    assert result.error is not None
    assert result.response_status == 502
    assert "exceeds limit" in result.response_body


def test_middleware_uses_content_length_header():
    cfg = ResponseSizeConfig(enabled=True, max_bytes=10)
    mw = make_response_size_middleware(cfg)
    # Content-Length says 100 even though body is small
    ctx = make_ctx(
        response_body=b"hi",
        response_headers={"Content-Length": "100"},
    )
    result = mw(ctx)
    assert result.response_status == 502
