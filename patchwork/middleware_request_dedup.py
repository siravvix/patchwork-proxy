"""Request deduplication middleware.

Detects duplicate in-flight requests by a configurable key (default:
method + path + body hash) and returns a 429 or a cached in-flight
response instead of forwarding the same request twice.
"""
from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional

from patchwork.middleware import RequestContext


@dataclass
class RequestDedupConfig:
    enabled: bool = False
    include_body: bool = True
    include_query: bool = True
    reject_status: int = 429
    reason_header: str = "X-Dedup-Reason"

    def __post_init__(self) -> None:
        if self.reject_status < 400 or self.reject_status > 599:
            raise ValueError("reject_status must be a 4xx or 5xx code")
        if not self.reason_header.strip():
            raise ValueError("reason_header must not be empty")

    @classmethod
    def from_dict(cls, data: dict) -> "RequestDedupConfig":
        return cls(
            enabled=data.get("enabled", False),
            include_body=data.get("include_body", True),
            include_query=data.get("include_query", True),
            reject_status=data.get("reject_status", 429),
            reason_header=data.get("reason_header", "X-Dedup-Reason"),
        )


def _request_key(ctx: RequestContext, cfg: RequestDedupConfig) -> str:
    method = (ctx.request_headers.get("X-Method") or ctx.request_headers.get("method") or "").upper()
    path = ctx.target or ""
    parts = [method, path]
    if cfg.include_query:
        parts.append(ctx.request_headers.get("X-Query-String", ""))
    if cfg.include_body and ctx.request_body:
        body_hash = hashlib.sha256(
            ctx.request_body if isinstance(ctx.request_body, bytes) else ctx.request_body.encode()
        ).hexdigest()[:16]
        parts.append(body_hash)
    return "|".join(parts)


def make_request_dedup_middleware(
    cfg: RequestDedupConfig,
    registry: Optional[Dict[str, bool]] = None,
    lock: Optional[threading.Lock] = None,
):
    _registry: Dict[str, bool] = registry if registry is not None else {}
    _lock = lock if lock is not None else threading.Lock()

    def pre_middleware(ctx: RequestContext) -> RequestContext:
        if not cfg.enabled:
            return ctx
        key = _request_key(ctx, cfg)
        with _lock:
            if key in _registry:
                ctx.response_status = cfg.reject_status
                ctx.response_headers[cfg.reason_header] = "duplicate-in-flight"
                ctx.response_body = b"duplicate request"
                ctx.skip_upstream = True
                return ctx
            _registry[key] = True
        ctx.metadata["dedup_key"] = key
        return ctx

    def post_middleware(ctx: RequestContext) -> RequestContext:
        key = ctx.metadata.get("dedup_key")
        if key:
            with _lock:
                _registry.pop(key, None)
        return ctx

    return pre_middleware, post_middleware


def build_default_dedup_middleware(cfg: Optional[RequestDedupConfig] = None):
    cfg = cfg or RequestDedupConfig()
    return make_request_dedup_middleware(cfg)
