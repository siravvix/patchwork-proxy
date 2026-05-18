"""Thin config-layer wrapper that reads geo_block settings from ProxyConfig."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from patchwork.middleware_geo_block import GeoBlockConfig


@dataclass
class GeoBlockMiddlewareConfig:
    geo_block: GeoBlockConfig

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeoBlockMiddlewareConfig":
        return cls(geo_block=GeoBlockConfig.from_dict(data.get("geo_block", {})))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "geo_block": {
                "enabled": self.geo_block.enabled,
                "allowlist": self.geo_block.allowlist,
                "blocklist": self.geo_block.blocklist,
                "country_header": self.geo_block.country_header,
                "reject_status": self.geo_block.reject_status,
                "unknown_country_policy": self.geo_block.unknown_country_policy,
            }
        }


def geo_block_config_from_proxy_config(
    proxy_config: Any,
) -> GeoBlockMiddlewareConfig:
    raw = getattr(proxy_config, "extra", {}) or {}
    return GeoBlockMiddlewareConfig.from_dict(raw)
