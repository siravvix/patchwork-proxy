"""Cache middleware: serve cached responses and store new ones."""
from __future__ import annotations

from typing import Callable

from patchwork.cache import CacheConfig, ResponseCache
from patchwork.middleware import RequestContext

_CACHE_KEY = "cache_hit"
_CACHED_RESPONSE_KEY = "cached_response"


def _route_id(ctx: RequestContext) -> str:
    method = ctx.request.get("method", "GET").upper()
    path = ctx.request.get("path", "/")
    return f"{method}:{path}"


def make_cache_middleware(
    cache: ResponseCache,
) -> tuple[Callable, Callable]:
    """Return (pre_middleware, post_middleware) pair for response caching."""

    def pre_middleware(ctx: RequestContext) -> RequestContext:
        method = ctx.request.get("method", "GET").upper()
        if method not in cache.config.cacheable_methods:
            ctx.metadata[_CACHE_KEY] = False
            return ctx

        key = _route_id(ctx)
        cached = cache.get(key)
        if cached is not None:
            ctx.metadata[_CACHE_KEY] = True
            ctx.metadata[_CACHED_RESPONSE_KEY] = cached
            ctx.response = {
                "status": cached.status_code,
                "headers": dict(cached.headers),
                "body": cached.body,
                "from_cache": True,
            }
        else:
            ctx.metadata[_CACHE_KEY] = False
        return ctx

    def post_middleware(ctx: RequestContext) -> RequestContext:
        if ctx.metadata.get(_CACHE_KEY, False):
            return ctx

        method = ctx.request.get("method", "GET").upper()
        if method not in cache.config.cacheable_methods:
            return ctx

        response = ctx.response or {}
        status = response.get("status", 0)
        if status not in cache.config.cacheable_statuses:
            return ctx

        key = _route_id(ctx)
        cache.put(
            key,
            status_code=status,
            headers=response.get("headers", {}),
            body=response.get("body", b""),
        )
        return ctx

    return pre_middleware, post_middleware


def build_default_cache_middleware(
    config: CacheConfig | None = None,
) -> tuple[Callable, Callable]:
    cfg = config or CacheConfig()
    cache = ResponseCache(cfg)
    return make_cache_middleware(cache)
