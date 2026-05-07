"""Retry middleware integration for the middleware pipeline."""
from __future__ import annotations

from typing import TYPE_CHECKING

from patchwork.retry import RetryConfig, with_retry
from patchwork.middleware import RequestContext

if TYPE_CHECKING:
    from patchwork.middleware import MiddlewarePipeline

_RETRY_CONFIG_KEY = "retry_config"
_RETRY_ATTEMPTS_KEY = "retry_attempts"
_RETRY_EXHAUSTED_KEY = "retry_exhausted"


def _route_id(ctx: RequestContext) -> str:
    method = ctx.request.get("method", "GET")
    path = ctx.request.get("path", "/")
    return f"{method}:{path}"


def make_retry_middleware(config: RetryConfig):
    """Return (pre, post) middleware functions that implement retry semantics."""

    def pre_middleware(ctx: RequestContext) -> None:
        ctx.meta[_RETRY_CONFIG_KEY] = config
        ctx.meta.setdefault(_RETRY_ATTEMPTS_KEY, 0)

    def post_middleware(ctx: RequestContext) -> None:
        status = ctx.response.get("status") if ctx.response else None
        attempts = ctx.meta.get(_RETRY_ATTEMPTS_KEY, 0)
        retryable = status in config.retryable_statuses if status else False

        ctx.meta[_RETRY_ATTEMPTS_KEY] = attempts + 1

        if retryable and (attempts + 1) < config.max_attempts:
            ctx.meta["should_retry"] = True
            ctx.meta["retry_delay"] = config.backoff_seconds(attempts)
        else:
            ctx.meta["should_retry"] = False
            if retryable:
                ctx.meta[_RETRY_EXHAUSTED_KEY] = True

    return pre_middleware, post_middleware


def build_default_retry_middleware(cfg: dict | None = None) -> RetryConfig:
    """Build a RetryConfig from a plain dict (e.g. parsed from proxy config)."""
    cfg = cfg or {}
    return RetryConfig(
        max_attempts=cfg.get("max_attempts", 3),
        retryable_statuses=set(cfg.get("retryable_statuses", [502, 503, 504])),
        backoff_base=cfg.get("backoff_base", 0.5),
        backoff_max=cfg.get("backoff_max", 10.0),
    )
