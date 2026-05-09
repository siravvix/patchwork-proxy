"""Middleware for rewriting request and response headers based on rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List

from patchwork.middleware import MiddlewarePipeline, RequestContext


@dataclass
class HeaderRewriteConfig:
    """Rules for rewriting headers on requests and responses."""

    rename_request: Dict[str, str] = field(default_factory=dict)
    rename_response: Dict[str, str] = field(default_factory=dict)
    force_request: Dict[str, str] = field(default_factory=dict)
    force_response: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for attr in ("rename_request", "rename_response", "force_request", "force_response"):
            val = getattr(self, attr)
            if not isinstance(val, dict):
                raise TypeError(f"{attr} must be a dict, got {type(val).__name__}")
            for k, v in val.items():
                if not isinstance(k, str) or not k:
                    raise ValueError(f"{attr} keys must be non-empty strings")
                if not isinstance(v, str):
                    raise ValueError(f"{attr} values must be strings")

    @classmethod
    def from_dict(cls, data: dict) -> "HeaderRewriteConfig":
        return cls(
            rename_request=dict(data.get("rename_request", {})),
            rename_response=dict(data.get("rename_response", {})),
            force_request=dict(data.get("force_request", {})),
            force_response=dict(data.get("force_response", {})),
        )


def make_header_rewrite_middleware(
    config: HeaderRewriteConfig,
) -> tuple[Callable, Callable]:
    """Return (pre, post) middleware functions for header rewriting."""

    def pre_middleware(ctx: RequestContext) -> None:
        headers: dict = ctx.meta.get("request_headers", {})
        # Apply renames first
        for old, new in config.rename_request.items():
            if old in headers:
                headers[new] = headers.pop(old)
        # Force-set headers
        headers.update(config.force_request)
        ctx.meta["request_headers"] = headers

    def post_middleware(ctx: RequestContext) -> None:
        headers: dict = ctx.meta.get("response_headers", {})
        for old, new in config.rename_response.items():
            if old in headers:
                headers[new] = headers.pop(old)
        headers.update(config.force_response)
        ctx.meta["response_headers"] = headers

    return pre_middleware, post_middleware


def build_default_header_rewrite_middleware(
    pipeline: MiddlewarePipeline,
    config: HeaderRewriteConfig | None = None,
) -> None:
    """Attach header-rewrite middleware to *pipeline* using *config*."""
    if config is None:
        config = HeaderRewriteConfig()
    pre, post = make_header_rewrite_middleware(config)
    pipeline.add_pre(pre)
    pipeline.add_post(post)
