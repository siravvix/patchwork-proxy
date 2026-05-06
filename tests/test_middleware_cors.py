"""Unit tests for patchwork.middleware_cors."""
import pytest
from patchwork.cors import CORSConfig
from patchwork.middleware import RequestContext
from patchwork.middleware_cors import (
    make_cors_middleware,
    get_cors_headers,
    is_preflight,
    build_default_cors_middleware,
)


def make_ctx(method: str = "GET", origin: str = None) -> RequestContext:
    headers = {}
    if origin:
        headers["Origin"] = origin
    return RequestContext(
        method=method,
        path="/api/data",
        request_headers=headers,
        target_url="http://localhost:8080/api/data",
    )


def test_middleware_disabled_cors_does_nothing():
    cfg = CORSConfig(enabled=False)
    mw = make_cors_middleware(cfg)
    ctx = make_ctx(origin="https://example.com")
    result = mw(ctx)
    assert result is None
    assert get_cors_headers(ctx) == {}


def test_middleware_enabled_attaches_headers():
    cfg = CORSConfig(enabled=True, allow_origins=["https://example.com"])
    mw = make_cors_middleware(cfg)
    ctx = make_ctx(origin="https://example.com")
    result = mw(ctx)
    assert result is None
    headers = get_cors_headers(ctx)
    assert "Access-Control-Allow-Origin" in headers


def test_middleware_preflight_returns_preflight_signal():
    cfg = CORSConfig(enabled=True, allow_origins=["*"])
    mw = make_cors_middleware(cfg)
    ctx = make_ctx(method="OPTIONS", origin="https://app.com")
    result = mw(ctx)
    assert result == "preflight"
    assert is_preflight(ctx) is True


def test_middleware_options_without_origin_not_preflight():
    cfg = CORSConfig(enabled=True, allow_origins=["https://allowed.com"])
    mw = make_cors_middleware(cfg)
    ctx = make_ctx(method="OPTIONS", origin=None)
    result = mw(ctx)
    assert result is None
    assert is_preflight(ctx) is False


def test_middleware_disallowed_origin_no_headers():
    cfg = CORSConfig(enabled=True, allow_origins=["https://allowed.com"])
    mw = make_cors_middleware(cfg)
    ctx = make_ctx(origin="https://evil.com")
    mw(ctx)
    assert get_cors_headers(ctx) == {}


def test_build_default_cors_middleware_uses_defaults():
    mw = build_default_cors_middleware()
    ctx = make_ctx(origin="https://example.com")
    result = mw(ctx)
    # disabled by default
    assert result is None
    assert get_cors_headers(ctx) == {}


def test_build_default_cors_middleware_with_config():
    mw = build_default_cors_middleware({"enabled": True, "allow_origins": ["*"]})
    ctx = make_ctx(origin="https://example.com")
    mw(ctx)
    headers = get_cors_headers(ctx)
    assert "Access-Control-Allow-Origin" in headers
