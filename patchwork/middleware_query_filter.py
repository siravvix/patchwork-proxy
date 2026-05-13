"""Middleware for filtering or blocking requests based on query parameter rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional
from urllib.parse import parse_qs, urlparse

from patchwork.middleware import RequestContext


@dataclass
class QueryFilterConfig:
    """Configuration for query parameter filtering middleware."""

    enabled: bool = False
    # Block requests that contain any of these query param keys
    blocked_params: List[str] = field(default_factory=list)
    # Block requests that are missing any of these required param keys
    required_params: List[str] = field(default_factory=list)
    # Status code returned when a request is blocked
    reject_status: int = 400
    # Header name to report the rejection reason
    reason_header: str = "X-Query-Filter-Reason"

    def __post_init__(self) -> None:
        if self.reject_status < 400 or self.reject_status > 599:
            raise ValueError("reject_status must be a 4xx or 5xx HTTP status code")
        if not self.reason_header:
            raise ValueError("reason_header must not be empty")

    @classmethod
    def from_dict(cls, data: dict) -> "QueryFilterConfig":
        return cls(
            enabled=data.get("enabled", False),
            blocked_params=list(data.get("blocked_params", [])),
            required_params=list(data.get("required_params", [])),
            reject_status=int(data.get("reject_status", 400)),
            reason_header=data.get("reason_header", "X-Query-Filter-Reason"),
        )


def _parse_query_keys(url: str) -> set:
    try:
        parsed = urlparse(url)
        return set(parse_qs(parsed.query, keep_blank_values=True).keys())
    except Exception:
        return set()


def make_query_filter_middleware(
    config: QueryFilterConfig,
) -> Callable[[RequestContext], Optional[RequestContext]]:
    """Return a pre-middleware function that enforces query parameter rules."""

    def _middleware(ctx: RequestContext) -> Optional[RequestContext]:
        if not config.enabled:
            return ctx

        url = ctx.request.get("url", "")
        present_keys = _parse_query_keys(url)

        for blocked in config.blocked_params:
            if blocked in present_keys:
                ctx.response = {
                    "status": config.reject_status,
                    "headers": {
                        config.reason_header: f"blocked param: {blocked}",
                        "Content-Type": "text/plain",
                    },
                    "body": f"Query parameter '{blocked}' is not allowed.",
                }
                return ctx

        for required in config.required_params:
            if required not in present_keys:
                ctx.response = {
                    "status": config.reject_status,
                    "headers": {
                        config.reason_header: f"missing required param: {required}",
                        "Content-Type": "text/plain",
                    },
                    "body": f"Required query parameter '{required}' is missing.",
                }
                return ctx

        return ctx

    return _middleware


def build_default_query_filter_middleware(
    config: Optional[QueryFilterConfig] = None,
) -> Callable[[RequestContext], Optional[RequestContext]]:
    cfg = config or QueryFilterConfig()
    return make_query_filter_middleware(cfg)
