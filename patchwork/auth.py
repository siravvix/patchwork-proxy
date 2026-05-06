"""Simple authentication middleware for patchwork-proxy.

Supports static API key authentication via header or query param.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Set


@dataclass
class AuthConfig:
    """Configuration for API key authentication."""
    enabled: bool = False
    header_name: str = "X-Api-Key"
    query_param: str = "api_key"
    valid_keys: Set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.enabled and not self.valid_keys:
            raise ValueError("AuthConfig: at least one valid key is required when enabled")
        if not self.header_name:
            raise ValueError("AuthConfig: header_name must not be empty")

    @classmethod
    def from_dict(cls, data: dict) -> "AuthConfig":
        return cls(
            enabled=data.get("enabled", False),
            header_name=data.get("header_name", "X-Api-Key"),
            query_param=data.get("query_param", "api_key"),
            valid_keys=set(data.get("valid_keys", [])),
        )


def extract_api_key(
    headers: dict,
    query_params: dict,
    config: AuthConfig,
) -> Optional[str]:
    """Extract API key from headers or query params."""
    key = headers.get(config.header_name) or headers.get(config.header_name.lower())
    if key:
        return key
    return query_params.get(config.query_param)


def is_authenticated(key: Optional[str], config: AuthConfig) -> bool:
    """Return True if the key is valid or auth is disabled."""
    if not config.enabled:
        return True
    if key is None:
        return False
    return key in config.valid_keys
