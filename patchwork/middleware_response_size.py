"""Middleware that enforces a maximum response body size limit."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from patchwork.middleware import RequestContext


@dataclass
class ResponseSizeConfig:
    enabled: bool = False
    max_bytes: int = 10 * 1024 * 1024  # 10 MB default
    header_name: str = "X-Response-Size-Limit"

    def __post_init__(self) -> None:
        if self.max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        if not self.header_name:
            raise ValueError("header_name must not be empty")

    @classmethod
    def from_dict(cls, data: dict) -> "ResponseSizeConfig":
        return cls(
            enabled=data.get("enabled", False),
            max_bytes=data.get("max_bytes", 10 * 1024 * 1024),
            header_name=data.get("header_name", "X-Response-Size-Limit"),
        )


def _content_length(ctx: RequestContext) -> Optional[int]:
    """Extract Content-Length from response headers if present."""
    headers = ctx.response_headers or {}
    raw = headers.get("Content-Length") or headers.get("content-length")
    if raw is None:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def _body_size(ctx: RequestContext) -> int:
    """Return the byte length of the response body, 0 if absent."""
    body = ctx.response_body
    if body is None:
        return 0
    if isinstance(body, (bytes, bytearray)):
        return len(body)
    return len(body.encode("utf-8", errors="replace"))


def make_response_size_middleware(config: ResponseSizeConfig):
    """Return a post-middleware function that enforces response size limits."""

    def post_middleware(ctx: RequestContext) -> RequestContext:
        if not config.enabled:
            return ctx

        size = _content_length(ctx)
        if size is None:
            size = _body_size(ctx)

        if size > config.max_bytes:
            ctx.error = (
                f"Response body size {size} bytes exceeds limit of "
                f"{config.max_bytes} bytes"
            )
            ctx.response_status = 502
            ctx.response_body = ctx.error
            ctx.response_headers = {"Content-Type": "text/plain"}
        else:
            if ctx.response_headers is None:
                ctx.response_headers = {}
            ctx.response_headers[config.header_name] = str(config.max_bytes)

        return ctx

    return post_middleware


def build_default_response_size_middleware(proxy_config: dict):
    raw = proxy_config.get("response_size", {})
    cfg = ResponseSizeConfig.from_dict(raw)
    return make_response_size_middleware(cfg)
