"""CORS (Cross-Origin Resource Sharing) configuration and helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CORSConfig:
    enabled: bool = False
    allow_origins: List[str] = field(default_factory=lambda: ["*"])
    allow_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    allow_headers: List[str] = field(default_factory=lambda: ["Content-Type", "Authorization"])
    expose_headers: List[str] = field(default_factory=list)
    allow_credentials: bool = False
    max_age: int = 600

    def __post_init__(self) -> None:
        if self.allow_credentials and "*" in self.allow_origins:
            raise ValueError("allow_credentials=True is incompatible with allow_origins=['*']")
        if self.max_age < 0:
            raise ValueError("max_age must be >= 0")

    @classmethod
    def from_dict(cls, data: dict) -> "CORSConfig":
        return cls(
            enabled=data.get("enabled", False),
            allow_origins=data.get("allow_origins", ["*"]),
            allow_methods=data.get("allow_methods", ["GET", "POST", "PUT", "DELETE", "OPTIONS"]),
            allow_headers=data.get("allow_headers", ["Content-Type", "Authorization"]),
            expose_headers=data.get("expose_headers", []),
            allow_credentials=data.get("allow_credentials", False),
            max_age=data.get("max_age", 600),
        )


def origin_allowed(config: CORSConfig, origin: Optional[str]) -> bool:
    """Return True if the given origin is permitted by config."""
    if not origin:
        return False
    if "*" in config.allow_origins:
        return True
    return origin in config.allow_origins


def build_cors_headers(config: CORSConfig, origin: Optional[str]) -> dict:
    """Build the CORS response headers for an allowed origin."""
    headers: dict = {}
    if not config.enabled or not origin_allowed(config, origin):
        return headers
    headers["Access-Control-Allow-Origin"] = origin if config.allow_credentials else (origin if "*" not in config.allow_origins else "*")
    headers["Access-Control-Allow-Methods"] = ", ".join(config.allow_methods)
    headers["Access-Control-Allow-Headers"] = ", ".join(config.allow_headers)
    if config.expose_headers:
        headers["Access-Control-Expose-Headers"] = ", ".join(config.expose_headers)
    if config.allow_credentials:
        headers["Access-Control-Allow-Credentials"] = "true"
    headers["Access-Control-Max-Age"] = str(config.max_age)
    return headers
