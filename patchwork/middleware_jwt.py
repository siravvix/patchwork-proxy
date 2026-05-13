"""JWT authentication middleware for patchwork-proxy."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import List, Optional

from patchwork.middleware import RequestContext


@dataclass
class JWTConfig:
    enabled: bool = False
    secret: str = ""
    algorithms: List[str] = field(default_factory=lambda: ["HS256"])
    header_name: str = "Authorization"
    prefix: str = "Bearer"
    claim_header: Optional[str] = "X-JWT-Sub"

    def __post_init__(self) -> None:
        if self.enabled and not self.secret:
            raise ValueError("JWTConfig: secret is required when enabled")
        if not self.header_name:
            raise ValueError("JWTConfig: header_name must not be empty")
        if not self.prefix:
            raise ValueError("JWTConfig: prefix must not be empty")

    @classmethod
    def from_dict(cls, data: dict) -> "JWTConfig":
        return cls(
            enabled=data.get("enabled", False),
            secret=data.get("secret", ""),
            algorithms=data.get("algorithms", ["HS256"]),
            header_name=data.get("header_name", "Authorization"),
            prefix=data.get("prefix", "Bearer"),
            claim_header=data.get("claim_header", "X-JWT-Sub"),
        )


def _b64decode_padding(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _verify_hs256(header_b64: str, payload_b64: str, signature_b64: str, secret: str) -> bool:
    msg = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(secret.encode(), msg, hashlib.sha256).digest()
    try:
        actual = _b64decode_padding(signature_b64)
    except Exception:
        return False
    return hmac.compare_digest(expected, actual)


def decode_jwt(token: str, secret: str, algorithms: List[str]) -> Optional[dict]:
    """Decode and verify a JWT token. Returns payload dict or None on failure."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        header = json.loads(_b64decode_padding(header_b64))
        alg = header.get("alg", "")
        if alg not in algorithms:
            return None
        if alg == "HS256":
            if not _verify_hs256(header_b64, payload_b64, sig_b64, secret):
                return None
        else:
            return None
        return json.loads(_b64decode_padding(payload_b64))
    except Exception:
        return None


def make_jwt_middleware(config: JWTConfig):
    def _middleware(ctx: RequestContext) -> Optional[RequestContext]:
        if not config.enabled:
            return ctx
        raw = ctx.request_headers.get(config.header_name, "")
        if not raw.startswith(config.prefix + " "):
            ctx.response_status = 401
            ctx.response_body = b"Unauthorized"
            ctx.response_headers["WWW-Authenticate"] = f'{config.prefix} realm="patchwork"'
            return ctx
        token = raw[len(config.prefix) + 1:]
        payload = decode_jwt(token, config.secret, config.algorithms)
        if payload is None:
            ctx.response_status = 401
            ctx.response_body = b"Unauthorized"
            return ctx
        if config.claim_header and "sub" in payload:
            ctx.request_headers[config.claim_header] = str(payload["sub"])
        ctx.meta["jwt_payload"] = payload
        return ctx
    return _middleware


def build_default_jwt_middleware(config: JWTConfig):
    return make_jwt_middleware(config)
