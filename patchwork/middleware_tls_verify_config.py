"""Config helpers for TLS-verify middleware integration with ProxyConfig."""
from __future__ import annotations

from dataclasses import dataclass

from patchwork.middleware_tls_verify import TLSVerifyConfig


@dataclass
class TLSVerifyMiddlewareConfig:
    tls_verify: TLSVerifyConfig

    @classmethod
    def from_dict(cls, data: dict) -> "TLSVerifyMiddlewareConfig":
        return cls(tls_verify=TLSVerifyConfig.from_dict(data.get("tls_verify", {})))

    def as_dict(self) -> dict:
        return {
            "tls_verify": {
                "enabled": self.tls_verify.enabled,
                "forwarded_proto_header": self.tls_verify.forwarded_proto_header,
                "reject_status": self.tls_verify.reject_status,
                "reject_reason": self.tls_verify.reject_reason,
            }
        }


def tls_verify_config_from_proxy_config(
    proxy_config: dict,
) -> TLSVerifyMiddlewareConfig:
    """Extract TLS-verify config from a raw proxy config dict."""
    return TLSVerifyMiddlewareConfig.from_dict(proxy_config)
