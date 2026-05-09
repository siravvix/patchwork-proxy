"""IP allowlist middleware for patchwork-proxy."""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import List, Optional

from patchwork.middleware import RequestContext


@dataclass
class IPAllowlistConfig:
    enabled: bool = False
    allowed_cidrs: List[str] = field(default_factory=list)
    header: str = "X-Forwarded-For"

    def __post_init__(self) -> None:
        if self.enabled and not self.allowed_cidrs:
            raise ValueError("IP allowlist is enabled but no CIDRs are configured")
        for cidr in self.allowed_cidrs:
            try:
                ipaddress.ip_network(cidr, strict=False)
            except ValueError as exc:
                raise ValueError(f"Invalid CIDR {cidr!r}: {exc}") from exc
        if not self.header:
            raise ValueError("header must be a non-empty string")

    @classmethod
    def from_dict(cls, data: dict) -> "IPAllowlistConfig":
        return cls(
            enabled=data.get("enabled", False),
            allowed_cidrs=data.get("allowed_cidrs", []),
            header=data.get("header", "X-Forwarded-For"),
        )


def _parse_client_ip(ctx: RequestContext, header: str) -> Optional[str]:
    """Extract the first IP from the configured header or fall back to remote_addr."""
    raw = ctx.request_headers.get(header, "").strip()
    if raw:
        return raw.split(",")[0].strip()
    return ctx.metadata.get("remote_addr")


def _ip_allowed(ip_str: str, allowed_cidrs: List[str]) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(
        ip in ipaddress.ip_network(cidr, strict=False) for cidr in allowed_cidrs
    )


def make_ip_allowlist_middleware(config: IPAllowlistConfig):
    """Return a pre-middleware function that enforces the IP allowlist."""

    def _middleware(ctx: RequestContext) -> RequestContext:
        if not config.enabled:
            return ctx
        client_ip = _parse_client_ip(ctx, config.header)
        if client_ip is None or not _ip_allowed(client_ip, config.allowed_cidrs):
            ctx.metadata["ip_blocked"] = True
            ctx.metadata["block_reason"] = (
                f"IP {client_ip!r} is not in the allowlist"
            )
        else:
            ctx.metadata["ip_blocked"] = False
        return ctx

    return _middleware


def build_default_ip_allowlist_middleware(data: dict):
    """Convenience builder from a raw config dict."""
    config = IPAllowlistConfig.from_dict(data)
    return make_ip_allowlist_middleware(config)
