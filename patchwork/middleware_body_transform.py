"""Middleware for request/response body transformation (e.g. JSON field injection/removal)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

from patchwork.middleware import MiddlewarePipeline, RequestContext


@dataclass
class BodyTransformConfig:
    enabled: bool = False
    inject_request_fields: Dict[str, Any] = field(default_factory=dict)
    remove_request_fields: List[str] = field(default_factory=list)
    inject_response_fields: Dict[str, Any] = field(default_factory=dict)
    remove_response_fields: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.inject_request_fields, dict):
            raise ValueError("inject_request_fields must be a dict")
        if not isinstance(self.remove_request_fields, list):
            raise ValueError("remove_request_fields must be a list")
        if not isinstance(self.inject_response_fields, dict):
            raise ValueError("inject_response_fields must be a dict")
        if not isinstance(self.remove_response_fields, list):
            raise ValueError("remove_response_fields must be a list")

    @classmethod
    def from_dict(cls, data: dict) -> "BodyTransformConfig":
        return cls(
            enabled=data.get("enabled", False),
            inject_request_fields=data.get("inject_request_fields", {}),
            remove_request_fields=data.get("remove_request_fields", []),
            inject_response_fields=data.get("inject_response_fields", {}),
            remove_response_fields=data.get("remove_response_fields", []),
        )


def _transform_json(body: bytes, inject: Dict[str, Any], remove: List[str]) -> bytes:
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return body
    if not isinstance(data, dict):
        return body
    for key in remove:
        data.pop(key, None)
    data.update(inject)
    return json.dumps(data).encode()


def make_body_transform_middleware(cfg: BodyTransformConfig):
    def pre_middleware(ctx: RequestContext) -> None:
        if not cfg.enabled:
            return
        if not (cfg.inject_request_fields or cfg.remove_request_fields):
            return
        body = ctx.request.get("body", b"")
        if body:
            ctx.request["body"] = _transform_json(
                body, cfg.inject_request_fields, cfg.remove_request_fields
            )

    def post_middleware(ctx: RequestContext) -> None:
        if not cfg.enabled:
            return
        if not (cfg.inject_response_fields or cfg.remove_response_fields):
            return
        body = ctx.response.get("body", b"")
        if body:
            ctx.response["body"] = _transform_json(
                body, cfg.inject_response_fields, cfg.remove_response_fields
            )

    return pre_middleware, post_middleware


def build_default_body_transform_middleware(
    pipeline: MiddlewarePipeline, cfg: BodyTransformConfig
) -> None:
    pre, post = make_body_transform_middleware(cfg)
    pipeline.add_pre(pre)
    pipeline.add_post(post)
