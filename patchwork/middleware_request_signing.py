"""Request signing middleware: validates HMAC-SHA256 signatures on incoming requests."""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from typing import List, Optional

from patchwork.middleware import RequestContext

_DEFAULT_HEADER = "X-Signature"
_DEFAULT_TIMESTAMP_HEADER = "X-Timestamp"
_DEFAULT_MAX_SKEW_SECONDS = 30
_DEFAULT_REJECT_STATUS = 401


@dataclass
class RequestSigningConfig:
    enabled: bool = False
    secret: str = ""
    header_name: str = _DEFAULT_HEADER
    timestamp_header: str = _DEFAULT_TIMESTAMP_HEADER
    max_skew_seconds: int = _DEFAULT_MAX_SKEW_SECONDS
    reject_status: int = _DEFAULT_REJECT_STATUS
    signed_headers: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.enabled and not self.secret:
            raise ValueError("RequestSigningConfig: 'secret' is required when enabled")
        if not self.header_name:
            raise ValueError("RequestSigningConfig: 'header_name' must not be empty")
        if not self.timestamp_header:
            raise ValueError("RequestSigningConfig: 'timestamp_header' must not be empty")
        if self.max_skew_seconds < 0:
            raise ValueError("RequestSigningConfig: 'max_skew_seconds' must be >= 0")
        if self.reject_status < 400 or self.reject_status > 599:
            raise ValueError("RequestSigningConfig: 'reject_status' must be 4xx or 5xx")

    @classmethod
    def from_dict(cls, data: dict) -> "RequestSigningConfig":
        return cls(
            enabled=data.get("enabled", False),
            secret=data.get("secret", ""),
            header_name=data.get("header_name", _DEFAULT_HEADER),
            timestamp_header=data.get("timestamp_header", _DEFAULT_TIMESTAMP_HEADER),
            max_skew_seconds=data.get("max_skew_seconds", _DEFAULT_MAX_SKEW_SECONDS),
            reject_status=data.get("reject_status", _DEFAULT_REJECT_STATUS),
            signed_headers=data.get("signed_headers", []),
        )


def _compute_signature(secret: str, method: str, path: str, timestamp: str,
                       extra_headers: dict) -> str:
    parts = [method.upper(), path, timestamp]
    for key in sorted(extra_headers):
        parts.append(f"{key.lower()}:{extra_headers[key]}")
    payload = "\n".join(parts).encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def make_request_signing_middleware(cfg: RequestSigningConfig):
    def _middleware(ctx: RequestContext) -> Optional[str]:
        if not cfg.enabled:
            return None
        sig = (ctx.request_headers or {}).get(cfg.header_name, "")
        ts_str = (ctx.request_headers or {}).get(cfg.timestamp_header, "")
        if not sig or not ts_str:
            ctx.response_status = cfg.reject_status
            ctx.response_body = b"missing signature or timestamp"
            return "reject"
        try:
            ts = int(ts_str)
        except ValueError:
            ctx.response_status = cfg.reject_status
            ctx.response_body = b"invalid timestamp"
            return "reject"
        if abs(time.time() - ts) > cfg.max_skew_seconds:
            ctx.response_status = cfg.reject_status
            ctx.response_body = b"timestamp skew too large"
            return "reject"
        extra = {h: (ctx.request_headers or {}).get(h, "") for h in cfg.signed_headers}
        expected = _compute_signature(cfg.secret, ctx.method or "GET", ctx.path or "/", ts_str, extra)
        if not hmac.compare_digest(sig, expected):
            ctx.response_status = cfg.reject_status
            ctx.response_body = b"invalid signature"
            return "reject"
        return None
    return _middleware


def build_default_request_signing_middleware(proxy_config: dict):
    raw = proxy_config.get("request_signing", {})
    cfg = RequestSigningConfig.from_dict(raw)
    return make_request_signing_middleware(cfg)
