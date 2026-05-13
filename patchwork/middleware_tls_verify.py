"""Middleware that enforces TLS/HTTPS-only access for incoming requests."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from patchwork.middleware import RequestContext


@dataclass
class TLSVerifyConfig:
    enabled: bool = False
    # Header set by a TLS-terminating proxy (e.g. nginx) to indicate the scheme
    forwarded_proto_header: str = "X-Forwarded-Proto"
    # HTTP status to return when the request is not HTTPS
    reject_status: int = 403
    reject_reason: str = "HTTPS required"

    def __post_init__(self) -> None:
        if not self.forwarded_proto_header.strip():
            raise ValueError("forwarded_proto_header must not be empty")
        if self.reject_status < 400 or self.reject_status > 599:
            raise ValueError("reject_status must be a 4xx or 5xx code")

    @classmethod
    def from_dict(cls, data: dict) -> "TLSVerifyConfig":
        return cls(
            enabled=bool(data.get("enabled", False)),
            forwarded_proto_header=data.get(
                "forwarded_proto_header", "X-Forwarded-Proto"
            ),
            reject_status=int(data.get("reject_status", 403)),
            reject_reason=data.get("reject_reason", "HTTPS required"),
        )


def _is_secure(ctx: RequestContext, header: str) -> bool:
    """Return True if the request appears to be HTTPS."""
    # Direct HTTPS (scheme in URL)
    scheme = (ctx.request.get("scheme") or "").lower()
    if scheme == "https":
        return True
    # Via forwarded-proto header
    proto = (ctx.request_headers.get(header) or "").lower().strip()
    return proto == "https"


def make_tls_verify_middleware(
    config: TLSVerifyConfig,
) -> Callable[[RequestContext], Optional[RequestContext]]:
    """Return a pre-middleware function that blocks non-HTTPS requests."""

    def _middleware(ctx: RequestContext) -> Optional[RequestContext]:
        if not config.enabled:
            return ctx
        if _is_secure(ctx, config.forwarded_proto_header):
            return ctx
        ctx.response_status = config.reject_status
        ctx.response_headers["X-TLS-Verify"] = "rejected"
        ctx.response_body = config.reject_reason.encode()
        ctx.short_circuit = True
        return ctx

    return _middleware


def build_default_tls_verify_middleware(
    proxy_config: dict,
) -> Callable[[RequestContext], Optional[RequestContext]]:
    raw = proxy_config.get("tls_verify", {})
    cfg = TLSVerifyConfig.from_dict(raw) if raw else TLSVerifyConfig()
    return make_tls_verify_middleware(cfg)
