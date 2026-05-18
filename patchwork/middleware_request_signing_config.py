"""Config wrapper for request signing middleware, following the project config convention."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class RequestSigningMiddlewareConfig:
    enabled: bool = False
    secret: str = ""
    header_name: str = "X-Signature"
    timestamp_header: str = "X-Timestamp"
    max_skew_seconds: int = 30
    reject_status: int = 401

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RequestSigningMiddlewareConfig":
        return cls(
            enabled=data.get("enabled", False),
            secret=data.get("secret", ""),
            header_name=data.get("header_name", "X-Signature"),
            timestamp_header=data.get("timestamp_header", "X-Timestamp"),
            max_skew_seconds=data.get("max_skew_seconds", 30),
            reject_status=data.get("reject_status", 401),
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "secret": self.secret,
            "header_name": self.header_name,
            "timestamp_header": self.timestamp_header,
            "max_skew_seconds": self.max_skew_seconds,
            "reject_status": self.reject_status,
        }


def request_signing_config_from_proxy_config(
    proxy_config: Dict[str, Any]
) -> RequestSigningMiddlewareConfig:
    raw = proxy_config.get("request_signing", {})
    return RequestSigningMiddlewareConfig.from_dict(raw)
