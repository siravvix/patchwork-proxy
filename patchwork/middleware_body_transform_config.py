"""Config bridge: load BodyTransformConfig from ProxyConfig."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from patchwork.middleware_body_transform import BodyTransformConfig


@dataclass
class BodyTransformMiddlewareConfig:
    """Top-level wrapper that can be stored in ProxyConfig extras."""
    body_transform: BodyTransformConfig

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BodyTransformMiddlewareConfig":
        raw = data.get("body_transform", {})
        return cls(body_transform=BodyTransformConfig.from_dict(raw))

    def as_dict(self) -> Dict[str, Any]:
        cfg = self.body_transform
        return {
            "body_transform": {
                "enabled": cfg.enabled,
                "inject_request_fields": cfg.inject_request_fields,
                "remove_request_fields": cfg.remove_request_fields,
                "inject_response_fields": cfg.inject_response_fields,
                "remove_response_fields": cfg.remove_response_fields,
            }
        }


def body_transform_config_from_proxy_config(
    proxy_config: Any,
) -> BodyTransformMiddlewareConfig:
    """Extract BodyTransformMiddlewareConfig from a ProxyConfig instance."""
    raw = getattr(proxy_config, "extras", {}) or {}
    return BodyTransformMiddlewareConfig.from_dict(raw)
