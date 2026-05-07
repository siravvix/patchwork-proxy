"""Integration tests: cache middleware wired into MiddlewarePipeline."""
from __future__ import annotations

import pytest

from patchwork.cache import CacheConfig, ResponseCache
from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_cache import make_cache_middleware


def _make_ctx(method: str = "GET", path: str = "/v1/resource") -> RequestContext:
    return RequestContext(
        request={"method": method, "path": path, "headers": {}},
        response=None,
        metadata={},
    )


def _make_pipeline(cache: ResponseCache) -> MiddlewarePipeline:
    pre, post = make_cache_middleware(cache)
    pipeline = MiddlewarePipeline()
    pipeline.add_pre(pre)
    pipeline.add_post(post)
    return pipeline


def test_pipeline_cache_miss_does_not_set_response():
    cache = ResponseCache(CacheConfig(ttl_seconds=30))
    pipeline = _make_pipeline(cache)
    ctx = _make_ctx()
    result = pipeline.run_pre(ctx)
    assert result.response is None
    assert result.metadata.get("cache_hit") is False


def test_pipeline_stores_and_retrieves_response():
    cache = ResponseCache(CacheConfig(ttl_seconds=30))
    pipeline = _make_pipeline(cache)

    # First request — miss, then store via post
    ctx = _make_ctx()
    ctx = pipeline.run_pre(ctx)
    ctx.response = {"status": 200, "headers": {"x-foo": "bar"}, "body": b"payload"}
    pipeline.run_post(ctx)

    # Second request — should hit cache
    ctx2 = _make_ctx()
    ctx2 = pipeline.run_pre(ctx2)
    assert ctx2.metadata.get("cache_hit") is True
    assert ctx2.response["body"] == b"payload"
    assert ctx2.response["from_cache"] is True


def test_pipeline_non_cacheable_method_never_cached():
    cache = ResponseCache(CacheConfig(ttl_seconds=30))
    pipeline = _make_pipeline(cache)

    ctx = _make_ctx(method="DELETE")
    ctx = pipeline.run_pre(ctx)
    ctx.response = {"status": 200, "headers": {}, "body": b"gone"}
    pipeline.run_post(ctx)

    ctx2 = _make_ctx(method="DELETE")
    ctx2 = pipeline.run_pre(ctx2)
    assert ctx2.metadata.get("cache_hit") is False
    assert ctx2.response is None


def test_pipeline_error_response_not_cached():
    cache = ResponseCache(CacheConfig(ttl_seconds=30))
    pipeline = _make_pipeline(cache)

    ctx = _make_ctx()
    ctx = pipeline.run_pre(ctx)
    ctx.response = {"status": 503, "headers": {}, "body": b"unavailable"}
    pipeline.run_post(ctx)

    ctx2 = _make_ctx()
    ctx2 = pipeline.run_pre(ctx2)
    assert ctx2.metadata.get("cache_hit") is False
