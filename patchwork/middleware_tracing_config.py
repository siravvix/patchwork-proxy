"""Load TracingConfig from a ProxyConfig-like dict."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from patchwork.middleware_tracing import TracingConfig


@dataclass
class TracingMiddlewareConfig:
    """Thin wrapper that lives in the top-level proxy config."""
    tracing: TracingConfig

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TracingMiddlewareConfig":
        tracing_data = data.get("tracing", {})
        return cls(tracing=TracingConfig.from_dict(tracing_data))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "tracing": {
                "enabled": self.tracing.enabled,
                "trace_id_header": self.tracing.trace_id_header,
                "span_id_header": self.tracing.span_id_header,
                "propagate_trace": self.tracing.propagate_trace,
                "propagate_span": self.tracing.propagate_span,
            }
        }


def tracing_config_from_proxy_config(
    proxy_config: Dict[str, Any]
) -> Optional[TracingConfig]:
    """Extract TracingConfig from a raw proxy config dict, or return None."""
    raw = proxy_config.get("tracing")
    if raw is None:
        return None
    return TracingConfig.from_dict(raw)
