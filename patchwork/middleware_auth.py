"""Authentication middleware integration for patchwork-proxy."""
from __future__ import annotations

from typing import Callable, Optional

from patchwork.auth import AuthConfig, extract_api_key, is_authenticated
from patchwork.middleware import RequestContext


CTX_AUTH_KEY = "auth_key"
CTX_AUTH_RESULT = "auth_ok"


def make_auth_middleware(
    config: AuthConfig,
) -> Callable[[RequestContext], Optional[RequestContext]]:
    """Return a pre-middleware function that validates API key auth.

    If authentication fails, sets ctx.extra['auth_ok'] = False and
    ctx.extra['auth_error'] with a reason string. Callers should
    check this field and return 401 before forwarding the request.
    """

    def _middleware(ctx: RequestContext) -> Optional[RequestContext]:
        if not config.enabled:
            ctx.extra[CTX_AUTH_RESULT] = True
            return ctx

        headers = ctx.extra.get("request_headers", {})
        query_params = ctx.extra.get("query_params", {})
        key = extract_api_key(headers, query_params, config)
        ctx.extra[CTX_AUTH_KEY] = key

        if is_authenticated(key, config):
            ctx.extra[CTX_AUTH_RESULT] = True
        else:
            ctx.extra[CTX_AUTH_RESULT] = False
            ctx.extra["auth_error"] = (
                "Missing or invalid API key"
            )
        return ctx

    return _middleware


def build_default_auth_middleware(
    config: Optional[AuthConfig] = None,
) -> Callable[[RequestContext], Optional[RequestContext]]:
    """Build auth middleware with an optional config (disabled by default)."""
    if config is None:
        config = AuthConfig(enabled=False)
    return make_auth_middleware(config)
