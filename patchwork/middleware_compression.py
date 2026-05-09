"""Response compression middleware (gzip) for patchwork-proxy."""

from __future__ import annotations

import gzip
from dataclasses import dataclass, field
from typing import Set

from patchwork.middleware import MiddlewarePipeline, RequestContext

_DEFAULT_MIN_BYTES = 1024
_DEFAULT_TYPES: Set[str] = {
    "application/json",
    "text/plain",
    "text/html",
    "text/css",
    "application/javascript",
}


@dataclass
class CompressionConfig:
    enabled: bool = True
    min_bytes: int = _DEFAULT_MIN_BYTES
    compressible_types: Set[str] = field(default_factory=lambda: set(_DEFAULT_TYPES))

    def __post_init__(self) -> None:
        if self.min_bytes < 0:
            raise ValueError("min_bytes must be >= 0")
        if not self.compressible_types:
            raise ValueError("compressible_types must not be empty")

    @classmethod
    def from_dict(cls, data: dict) -> "CompressionConfig":
        kwargs: dict = {}
        if "enabled" in data:
            kwargs["enabled"] = bool(data["enabled"])
        if "min_bytes" in data:
            kwargs["min_bytes"] = int(data["min_bytes"])
        if "compressible_types" in data:
            kwargs["compressible_types"] = set(data["compressible_types"])
        return cls(**kwargs)


def _accepts_gzip(ctx: RequestContext) -> bool:
    accept = ctx.request_headers.get("Accept-Encoding", "")
    return "gzip" in accept


def _content_type_compressible(ctx: RequestContext, cfg: CompressionConfig) -> bool:
    ct = ctx.response_headers.get("Content-Type", "")
    base = ct.split(";")[0].strip().lower()
    return any(base == t.lower() for t in cfg.compressible_types)


def make_compression_middleware(cfg: CompressionConfig):
    def post_middleware(ctx: RequestContext) -> RequestContext:
        if not cfg.enabled:
            return ctx
        if not _accepts_gzip(ctx):
            return ctx
        body = ctx.response_body
        if not body or len(body) < cfg.min_bytes:
            return ctx
        if not _content_type_compressible(ctx, cfg):
            return ctx
        compressed = gzip.compress(body if isinstance(body, bytes) else body.encode())
        ctx.response_body = compressed
        ctx.response_headers["Content-Encoding"] = "gzip"
        ctx.response_headers["Content-Length"] = str(len(compressed))
        return ctx

    return post_middleware


def build_default_compression_middleware(
    pipeline: MiddlewarePipeline,
    cfg: CompressionConfig | None = None,
) -> None:
    cfg = cfg or CompressionConfig()
    pipeline.add_post(make_compression_middleware(cfg))
