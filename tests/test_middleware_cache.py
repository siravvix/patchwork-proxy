"""Tests for cache middleware pre/post hooks."""
from __future__ import annotations

import time

import pytest

from patchwork.cache import CacheConfig, ResponseCache
from patchwork.middleware import RequestContext
from patchwork.middleware_cache import (
    make_cache_middleware,
    build_default_cache_middleware,
)


def make_ctx(method: str = "GET", path: str = "/api/data") -> RequestContext:
    return RequestContext(
        request={"method": method, "path": path, "headers": {}},
        response=None,
        metadata={},
    )


@pytest.fixture()
def cache() -> ResponseCache:
    return ResponseCache(CacheConfig(ttl_seconds=60, max_entries=10))


@pytest.fixture()
def middleware(cache):
    return make_cache_middleware(cache)


def test_pre_cache_miss_sets_flag_false(middleware):
    pre, _ = middleware
    ctx = make_ctx()
    result = pre(ctx)
    assert result.metadata["cache_hit"] is False
    assert result.response is None


def test_pre_cache_hit_sets_response(cache, middleware):
    pre, post = middleware
    # Populate cache manually
    cache.put("GET:/api/data", 200, {"content-type": "application/json"}, b'{"x":1}')
    ctx = make_ctx()
    result = pre(ctx)
    assert result.metadata["cache_hit"] is True
    assert result.response is not None
    assert result.response["status"] == 200
    assert result.response["body"] == b'{"x":1}'
    assert result.response["from_cache"] is True


def test_post_stores_successful_response(cache, middleware):
    pre, post = middleware
    ctx = make_ctx()
    pre(ctx)  # sets cache_hit=False
    ctx.response = {"status": 200, "headers": {}, "body": b"hello"}
    post(ctx)
    cached = cache.get("GET:/api/data")
    assert cached is not None
    assert cached.body == b"hello"


def test_post_does_not_store_non_cacheable_status(cache, middleware):
    pre, post = middleware
    ctx = make_ctx()
    pre(ctx)
    ctx.response = {"status": 500, "headers": {}, "body": b"error"}
    post(ctx)
    assert cache.get("GET:/api/data") is None


def test_post_skips_non_cacheable_method(cache, middleware):
    pre, post = middleware
    ctx = make_ctx(method="POST")
    pre(ctx)
    ctx.response = {"status": 200, "headers": {}, "body": b"created"}
    post(ctx)
    assert cache.get("POST:/api/data") is None


def test_post_skips_when_already_cached(cache, middleware):
    pre, post = middleware
    cache.put("GET:/api/data", 200, {}, b"old")
    ctx = make_ctx()
    pre(ctx)  # cache_hit=True
    ctx.response = {"status": 200, "headers": {}, "body": b"new"}
    post(ctx)
    # Should not overwrite; original value stays
    cached = cache.get("GET:/api/data")
    assert cached.body == b"old"


def test_build_default_returns_callables():
    pre, post = build_default_cache_middleware()
    assert callable(pre)
    assert callable(post)
