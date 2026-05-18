"""Middleware that blocks or allows requests based on a country code header.

The upstream proxy (or CDN) is expected to inject a header such as
``X-Country-Code`` containing the ISO-3166-1 alpha-2 country code for the
client.  This middleware reads that header and either allows or denies the
request according to the configured allowlist / blocklist.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from patchwork.middleware import RequestContext

_DENY_STATUS = 403
_DENY_BODY = b"Forbidden"


@dataclass
class GeoBlockConfig:
    enabled: bool = False
    # Mutually exclusive: supply one or the other, not both.
    allowlist: List[str] = field(default_factory=list)  # allow only these
    blocklist: List[str] = field(default_factory=list)  # block these
    country_header: str = "X-Country-Code"
    reject_status: int = 403
    unknown_country_policy: str = "allow"  # "allow" | "block"

    def __post_init__(self) -> None:
        if self.allowlist and self.blocklist:
            raise ValueError("Specify either allowlist or blocklist, not both")
        if self.reject_status < 400 or self.reject_status > 599:
            raise ValueError("reject_status must be a 4xx or 5xx code")
        if self.country_header == "":
            raise ValueError("country_header must not be empty")
        if self.unknown_country_policy not in ("allow", "block"):
            raise ValueError("unknown_country_policy must be 'allow' or 'block'")
        self.allowlist = [c.upper() for c in self.allowlist]
        self.blocklist = [c.upper() for c in self.blocklist]

    @classmethod
    def from_dict(cls, data: dict) -> "GeoBlockConfig":
        return cls(
            enabled=data.get("enabled", False),
            allowlist=data.get("allowlist", []),
            blocklist=data.get("blocklist", []),
            country_header=data.get("country_header", "X-Country-Code"),
            reject_status=data.get("reject_status", 403),
            unknown_country_policy=data.get("unknown_country_policy", "allow"),
        )


def _is_allowed(config: GeoBlockConfig, country: Optional[str]) -> bool:
    if country is None or country == "":
        return config.unknown_country_policy == "allow"
    country = country.upper()
    if config.allowlist:
        return country in config.allowlist
    if config.blocklist:
        return country not in config.blocklist
    return True


def make_geo_block_middleware(
    config: GeoBlockConfig,
) -> Callable[[RequestContext], RequestContext]:
    def _middleware(ctx: RequestContext) -> RequestContext:
        if not config.enabled:
            return ctx
        country = (ctx.request_headers or {}).get(config.country_header)
        if not _is_allowed(config, country):
            ctx.response_status = config.reject_status
            ctx.response_body = _DENY_BODY
            ctx.response_headers = {"Content-Type": "text/plain"}
        return ctx

    return _middleware


def build_default_geo_block_middleware(
    raw: dict,
) -> Callable[[RequestContext], RequestContext]:
    config = GeoBlockConfig.from_dict(raw.get("geo_block", {}))
    return make_geo_block_middleware(config)
