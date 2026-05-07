"""Middleware that enforces a maximum request body size limit."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from patchwork.middleware import RequestContext


@dataclass
class RequestSizeConfig:
    enabled: bool = True
    max_bytes: int = 1_048_576  # 1 MiB default

    def __post_init__(self) -> None:
        if self.max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")

    @classmethod
    def from_dict(cls, data: dict) -> "RequestSizeConfig":
        return cls(
            enabled=data.get("enabled", True),
            max_bytes=data.get("max_bytes", 1_048_576),
        )


def _content_length(ctx: RequestContext) -> Optional[int]:
    """Return the Content-Length header value, or None if absent/invalid."""
    raw = ctx.request_headers.get("content-length") or ctx.request_headers.get(
        "Content-Length"
    )
    if raw is None:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def make_request_size_middleware(config: RequestSizeConfig):
    """Return a pre-middleware function that rejects oversized requests."""

    def _middleware(ctx: RequestContext) -> RequestContext:
        if not config.enabled:
            return ctx

        length = _content_length(ctx)
        if length is not None and length > config.max_bytes:
            ctx.response_status = 413
            ctx.response_body = (
                f"Request body too large: {length} bytes "
                f"(limit {config.max_bytes} bytes)"
            )
            ctx.response_headers = {"Content-Type": "text/plain"}
            ctx.skip_upstream = True
        return ctx

    return _middleware


def build_default_request_size_middleware(max_bytes: int = 1_048_576):
    """Convenience builder used by the proxy bootstrap."""
    cfg = RequestSizeConfig(enabled=True, max_bytes=max_bytes)
    return make_request_size_middleware(cfg)
