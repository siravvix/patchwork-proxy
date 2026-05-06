"""CORS middleware for the patchwork middleware pipeline."""
from __future__ import annotations

from typing import Callable, Optional

from patchwork.cors import CORSConfig, build_cors_headers, origin_allowed
from patchwork.middleware import RequestContext

_CORS_CONFIG_KEY = "cors_config"
_CORS_HEADERS_KEY = "cors_headers"
_IS_PREFLIGHT_KEY = "cors_preflight"


def make_cors_middleware(config: CORSConfig) -> Callable:
    """Return a pre-middleware function that attaches CORS config and headers to context."""

    def _middleware(ctx: RequestContext) -> Optional[str]:
        if not config.enabled:
            return None

        origin = ctx.request_headers.get("Origin")
        method = ctx.method.upper()

        ctx.metadata[_CORS_CONFIG_KEY] = config

        is_preflight = method == "OPTIONS" and origin_allowed(config, origin)
        ctx.metadata[_IS_PREFLIGHT_KEY] = is_preflight

        headers = build_cors_headers(config, origin)
        ctx.metadata[_CORS_HEADERS_KEY] = headers

        if is_preflight:
            return "preflight"

        return None

    return _middleware


def get_cors_headers(ctx: RequestContext) -> dict:
    """Retrieve CORS headers stored in context metadata, or empty dict."""
    return ctx.metadata.get(_CORS_HEADERS_KEY, {})


def is_preflight(ctx: RequestContext) -> bool:
    """Return True if the request was identified as a CORS preflight."""
    return bool(ctx.metadata.get(_IS_PREFLIGHT_KEY, False))


def build_default_cors_middleware(config_dict: Optional[dict] = None) -> Callable:
    """Convenience factory using a plain dict or defaults."""
    cfg = CORSConfig.from_dict(config_dict or {})
    return make_cors_middleware(cfg)
