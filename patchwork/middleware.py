"""Request/response middleware pipeline for patchwork-proxy."""

from __future__ import annotations

import time
import logging
from typing import Callable, List, Optional
from dataclasses import dataclass, field
from http.client import HTTPResponse

logger = logging.getLogger(__name__)


@dataclass
class RequestContext:
    """Mutable context object passed through the middleware chain."""

    method: str
    path: str
    headers: dict
    body: Optional[bytes] = None
    target_url: str = ""
    start_time: float = field(default_factory=time.monotonic)
    response: Optional[HTTPResponse] = None
    status_code: int = 0
    response_body: Optional[bytes] = None


MiddlewareFn = Callable[[RequestContext], None]


class MiddlewarePipeline:
    """Ordered pipeline of middleware functions applied to each request."""

    def __init__(self) -> None:
        self._pre: List[MiddlewareFn] = []
        self._post: List[MiddlewareFn] = []

    def add_pre(self, fn: MiddlewareFn) -> None:
        """Register a pre-request middleware (runs before proxying)."""
        self._pre.append(fn)

    def add_post(self, fn: MiddlewareFn) -> None:
        """Register a post-response middleware (runs after proxying)."""
        self._post.append(fn)

    def run_pre(self, ctx: RequestContext) -> None:
        for fn in self._pre:
            fn(ctx)

    def run_post(self, ctx: RequestContext) -> None:
        for fn in self._post:
            fn(ctx)


# ---------------------------------------------------------------------------
# Built-in middleware helpers
# ---------------------------------------------------------------------------

def logging_pre(ctx: RequestContext) -> None:
    """Log each incoming request."""
    logger.info("--> %s %s", ctx.method, ctx.path)


def logging_post(ctx: RequestContext) -> None:
    """Log each completed response with elapsed time."""
    elapsed = (time.monotonic() - ctx.start_time) * 1000
    logger.info("<-- %s %s %d (%.1f ms)", ctx.method, ctx.path, ctx.status_code, elapsed)


def cors_post(ctx: RequestContext) -> None:
    """Inject permissive CORS headers into the response headers dict."""
    if not isinstance(ctx.headers, dict):
        return
    ctx.headers.setdefault("Access-Control-Allow-Origin", "*")
    ctx.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, PATCH")
    ctx.headers.setdefault("Access-Control-Allow-Headers", "*")


def build_default_pipeline() -> MiddlewarePipeline:
    pipeline = MiddlewarePipeline()
    pipeline.add_pre(logging_pre)
    pipeline.add_post(logging_post)
    return pipeline
