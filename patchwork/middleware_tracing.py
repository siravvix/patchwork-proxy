"""Distributed tracing middleware — attaches trace/span IDs to requests."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from patchwork.middleware import RequestContext


@dataclass
class TracingConfig:
    enabled: bool = False
    trace_id_header: str = "X-Trace-Id"
    span_id_header: str = "X-Span-Id"
    propagate_trace: bool = True   # forward trace header to upstream
    propagate_span: bool = False   # forward span header to upstream

    def __post_init__(self) -> None:
        if not self.trace_id_header:
            raise ValueError("trace_id_header must not be empty")
        if not self.span_id_header:
            raise ValueError("span_id_header must not be empty")

    @classmethod
    def from_dict(cls, data: dict) -> "TracingConfig":
        return cls(
            enabled=bool(data.get("enabled", False)),
            trace_id_header=data.get("trace_id_header", "X-Trace-Id"),
            span_id_header=data.get("span_id_header", "X-Span-Id"),
            propagate_trace=bool(data.get("propagate_trace", True)),
            propagate_span=bool(data.get("propagate_span", False)),
        )


def _generate_id() -> str:
    return uuid.uuid4().hex


def make_tracing_middleware(config: TracingConfig):
    """Return (pre, post) middleware callables for distributed tracing."""

    def pre_middleware(ctx: RequestContext) -> Optional[RequestContext]:
        if not config.enabled:
            return None

        # Reuse incoming trace-id or generate a fresh one
        incoming = ctx.request_headers.get(config.trace_id_header.lower())
        trace_id = incoming if incoming else _generate_id()
        span_id = _generate_id()

        ctx.metadata["trace_id"] = trace_id
        ctx.metadata["span_id"] = span_id

        if config.propagate_trace:
            ctx.request_headers[config.trace_id_header] = trace_id
        if config.propagate_span:
            ctx.request_headers[config.span_id_header] = span_id

        return None

    def post_middleware(ctx: RequestContext) -> Optional[RequestContext]:
        if not config.enabled:
            return None

        trace_id = ctx.metadata.get("trace_id")
        span_id = ctx.metadata.get("span_id")

        if trace_id:
            ctx.response_headers[config.trace_id_header] = trace_id
        if span_id:
            ctx.response_headers[config.span_id_header] = span_id

        return None

    return pre_middleware, post_middleware


def build_default_tracing_middleware(cfg: Optional[dict] = None):
    config = TracingConfig.from_dict(cfg or {})
    return make_tracing_middleware(config)
