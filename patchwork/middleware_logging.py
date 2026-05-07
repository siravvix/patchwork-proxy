"""Request/response logging middleware for patchwork-proxy."""

from __future__ import annotations

import time
from typing import Optional

from patchwork.logger import get_logger
from patchwork.middleware import MiddlewarePipeline, RequestContext

logger = get_logger(__name__)


def _route_id(ctx: RequestContext) -> str:
    method = ctx.request.get("method", "UNKNOWN")
    path = ctx.request.get("path", "/")
    return f"{method} {path}"


def make_logging_middleware(
    log_request_headers: bool = False,
    log_response_headers: bool = False,
    log_body: bool = False,
) -> tuple:
    """Return (pre_middleware, post_middleware) that emit structured log lines."""

    def pre_middleware(ctx: RequestContext) -> Optional[RequestContext]:
        ctx.state["_log_start"] = time.monotonic()
        entry: dict = {
            "event": "request_received",
            "route": _route_id(ctx),
            "target": ctx.request.get("target", ""),
        }
        if log_request_headers:
            entry["request_headers"] = ctx.request.get("headers", {})
        logger.info(entry)
        return ctx

    def post_middleware(ctx: RequestContext) -> Optional[RequestContext]:
        start = ctx.state.get("_log_start")
        elapsed_ms = round((time.monotonic() - start) * 1000, 2) if start is not None else None
        status = ctx.response.get("status") if ctx.response else None
        entry: dict = {
            "event": "request_completed",
            "route": _route_id(ctx),
            "status": status,
            "elapsed_ms": elapsed_ms,
        }
        if log_response_headers and ctx.response:
            entry["response_headers"] = ctx.response.get("headers", {})
        if log_body and ctx.response:
            entry["response_body"] = ctx.response.get("body", "")
        logger.info(entry)
        return ctx

    return pre_middleware, post_middleware


def build_default_logging_middleware(
    pipeline: MiddlewarePipeline,
    log_request_headers: bool = False,
    log_response_headers: bool = False,
    log_body: bool = False,
) -> None:
    """Register logging middleware on *pipeline* with the given options."""
    pre, post = make_logging_middleware(
        log_request_headers=log_request_headers,
        log_response_headers=log_response_headers,
        log_body=log_body,
    )
    pipeline.add_pre(pre)
    pipeline.add_post(post)
