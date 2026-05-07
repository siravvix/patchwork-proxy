"""Logging middleware configuration dataclass for patchwork-proxy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class LoggingMiddlewareConfig:
    """Controls which parts of requests/responses are logged."""

    enabled: bool = True
    log_request_headers: bool = False
    log_response_headers: bool = False
    log_body: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if not isinstance(self.log_request_headers, bool):
            raise TypeError("log_request_headers must be a bool")
        if not isinstance(self.log_response_headers, bool):
            raise TypeError("log_response_headers must be a bool")
        if not isinstance(self.log_body, bool):
            raise TypeError("log_body must be a bool")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoggingMiddlewareConfig":
        """Construct from a plain dictionary (e.g. parsed YAML/JSON config)."""
        return cls(
            enabled=data.get("enabled", True),
            log_request_headers=data.get("log_request_headers", False),
            log_response_headers=data.get("log_response_headers", False),
            log_body=data.get("log_body", False),
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "log_request_headers": self.log_request_headers,
            "log_response_headers": self.log_response_headers,
            "log_body": self.log_body,
        }


def logging_config_from_proxy_config(proxy_cfg: Dict[str, Any]) -> LoggingMiddlewareConfig:
    """Extract the logging section from a top-level proxy config dict."""
    section = proxy_cfg.get("logging", {})
    if not isinstance(section, dict):
        raise ValueError("'logging' config section must be a mapping")
    return LoggingMiddlewareConfig.from_dict(section)
