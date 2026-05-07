"""Request ID middleware — attaches a unique trace ID to every request context."""
from __future__ import annotations

import uuid
from typing import Callable, Optional

from patchwork.middleware import MiddlewarePipeline, RequestContext

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_KEY = "request_id"


def _generate_id() -> str:
    return str(uuid.uuid4())


def _extract_or_generate(ctx: RequestContext) -> str:
    """Honour an incoming X-Request-ID header, otherwise mint a new one."""
    headers: dict = ctx.metadata.get("request_headers", {})
    # Headers may be stored with any casing; do a case-insensitive lookup.
    for key, value in headers.items():
        if key.lower() == REQUEST_ID_HEADER.lower():
            if value:
                return value
    return _generate_id()


def make_request_id_middleware(
    propagate: bool = True,
    id_factory: Optional[Callable[[], str]] = None,
) -> tuple:
    """Return a (pre, post) middleware pair that manages request IDs.

    Args:
        propagate: When True, echo the request ID back in the response headers.
        id_factory: Optional callable that returns a unique ID string.
    """
    factory = id_factory or _generate_id

    def pre_middleware(ctx: RequestContext) -> None:
        rid = _extract_or_generate(ctx)
        ctx.metadata[REQUEST_ID_KEY] = rid
        # Inject into outgoing request headers so upstream services can trace.
        req_headers: dict = ctx.metadata.setdefault("request_headers", {})
        req_headers[REQUEST_ID_HEADER] = rid

    def post_middleware(ctx: RequestContext) -> None:
        if not propagate:
            return
        rid = ctx.metadata.get(REQUEST_ID_KEY)
        if rid is None:
            return
        resp_headers: dict = ctx.metadata.setdefault("response_headers", {})
        resp_headers[REQUEST_ID_HEADER] = rid

    return pre_middleware, post_middleware


def build_default_request_id_middleware(
    pipeline: MiddlewarePipeline,
    propagate: bool = True,
) -> None:
    """Attach request-ID pre/post middleware to *pipeline* in place."""
    pre, post = make_request_id_middleware(propagate=propagate)
    pipeline.add_pre(pre)
    pipeline.add_post(post)
