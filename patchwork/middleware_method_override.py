"""Middleware that supports HTTP method override via header or query parameter.

Allows clients that only support GET/POST to simulate PUT, PATCH, DELETE, etc.
by passing the desired method in a header (e.g. X-HTTP-Method-Override) or
a query parameter (e.g. _method=DELETE).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from patchwork.middleware import RequestContext

_ALLOWED_OVERRIDES = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


@dataclass
class MethodOverrideConfig:
    enabled: bool = True
    header_name: str = "X-HTTP-Method-Override"
    query_param: str = "_method"
    allowed_source_methods: list = field(default_factory=lambda: ["POST"])

    def __post_init__(self) -> None:
        if not self.header_name:
            raise ValueError("header_name must not be empty")
        if not self.query_param:
            raise ValueError("query_param must not be empty")
        if not self.allowed_source_methods:
            raise ValueError("allowed_source_methods must not be empty")

    @classmethod
    def from_dict(cls, data: dict) -> "MethodOverrideConfig":
        return cls(
            enabled=data.get("enabled", True),
            header_name=data.get("header_name", "X-HTTP-Method-Override"),
            query_param=data.get("query_param", "_method"),
            allowed_source_methods=data.get("allowed_source_methods", ["POST"]),
        )


def _resolve_override(ctx: RequestContext, cfg: MethodOverrideConfig) -> Optional[str]:
    """Return the override method if valid, else None."""
    source = (ctx.request_method or "").upper()
    if source not in [m.upper() for m in cfg.allowed_source_methods]:
        return None

    # Header takes precedence over query param
    headers = ctx.request_headers or {}
    candidate = headers.get(cfg.header_name) or headers.get(cfg.header_name.lower())

    if not candidate:
        params = ctx.extra.get("query_params", {})
        candidate = params.get(cfg.query_param)

    if candidate:
        upper = candidate.upper()
        if upper in _ALLOWED_OVERRIDES:
            return upper
    return None


def make_method_override_middleware(cfg: MethodOverrideConfig):
    def pre_middleware(ctx: RequestContext) -> RequestContext:
        if not cfg.enabled:
            return ctx
        override = _resolve_override(ctx, cfg)
        if override:
            ctx.extra["original_method"] = ctx.request_method
            ctx.request_method = override
        return ctx

    return pre_middleware


def build_default_method_override_middleware():
    cfg = MethodOverrideConfig()
    return make_method_override_middleware(cfg)
