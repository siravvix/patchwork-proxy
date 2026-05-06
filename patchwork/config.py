"""Routing configuration loader with hot-reload support."""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RouteRule:
    """A single routing rule mapping a path prefix to an upstream target."""

    prefix: str
    target: str
    strip_prefix: bool = False
    methods: Optional[List[str]] = None

    def matches(self, path: str, method: str) -> bool:
        """Return True if this rule matches the given path and HTTP method."""
        if self.methods and method.upper() not in self.methods:
            return False
        return path.startswith(self.prefix)

    def rewrite(self, path: str) -> str:
        """Rewrite path according to strip_prefix setting."""
        if self.strip_prefix:
            return path[len(self.prefix):] or "/"
        return path


@dataclass
class ProxyConfig:
    """Top-level proxy configuration."""

    routes: List[RouteRule] = field(default_factory=list)
    listen_port: int = 8080
    log_level: str = "INFO"

    @classmethod
    def from_dict(cls, data: dict) -> "ProxyConfig":
        routes = [
            RouteRule(
                prefix=r["prefix"],
                target=r["target"],
                strip_prefix=r.get("strip_prefix", False),
                methods=r.get("methods"),
            )
            for r in data.get("routes", [])
        ]
        return cls(
            routes=routes,
            listen_port=data.get("listen_port", 8080),
            log_level=data.get("log_level", "INFO"),
        )

    def match_route(self, path: str, method: str) -> Optional[RouteRule]:
        """Return the first matching route rule or None."""
        for rule in self.routes:
            if rule.matches(path, method):
                return rule
        return None


def load_config(path: str) -> ProxyConfig:
    """Load a ProxyConfig from a JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r") as fh:
        data = json.load(fh)
    config = ProxyConfig.from_dict(data)
    logger.info("Loaded config from %s (%d routes)", path, len(config.routes))
    return config
