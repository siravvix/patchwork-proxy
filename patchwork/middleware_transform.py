"""Middleware that applies request/response header transforms from config."""

from __future__ import annotations

from typing import Callable

from patchwork.middleware import RequestContext
from patchwork.transform import TransformConfig, apply_request_transforms, apply_response_transforms


def make_transform_middleware(
    config: TransformConfig,
) -> tuple[Callable[[RequestContext], None], Callable[[RequestContext], None]]:
    """Return (pre_middleware, post_middleware) pair for the given TransformConfig."""

    def pre_middleware(ctx: RequestContext) -> None:
        """Apply request-side transforms (add/remove request headers)."""
        if not ctx.request_headers:
            ctx.request_headers = {}
        ctx.request_headers = apply_request_transforms(config, dict(ctx.request_headers))

    def post_middleware(ctx: RequestContext) -> None:
        """Apply response-side transforms (add/remove response headers)."""
        if ctx.response_headers is None:
            ctx.response_headers = {}
        ctx.response_headers = apply_response_transforms(config, dict(ctx.response_headers))

    return pre_middleware, post_middleware


def build_default_transform_middleware(
    config_dict: dict | None = None,
) -> tuple[Callable[[RequestContext], None], Callable[[RequestContext], None]]:
    """Build transform middleware from an optional config dict (uses defaults if None)."""
    cfg = TransformConfig.from_dict(config_dict or {})
    return make_transform_middleware(cfg)
