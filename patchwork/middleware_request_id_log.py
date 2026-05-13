"""Middleware that enriches log records with the current request ID."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from patchwork.middleware import RequestContext
from patchwork.logger import get_logger

logger = get_logger(__name__)

_REQUEST_ID_CTX_KEY = "request_id"
_DEFAULT_LOG_HEADER = "X-Request-ID"


@dataclass
class RequestIdLogConfig:
    """Configuration for request-ID log-enrichment middleware."""

    enabled: bool = True
    header_name: str = _DEFAULT_LOG_HEADER
    log_on_request: bool = True
    log_on_response: bool = True

    def __post_init__(self) -> None:
        if not self.header_name:
            raise ValueError("header_name must not be empty")

    @classmethod
    def from_dict(cls, data: dict) -> "RequestIdLogConfig":
        return cls(
            enabled=data.get("enabled", True),
            header_name=data.get("header_name", _DEFAULT_LOG_HEADER),
            log_on_request=data.get("log_on_request", True),
            log_on_response=data.get("log_on_response", True),
        )


def make_request_id_log_middleware(
    cfg: RequestIdLogConfig,
) -> tuple[Callable, Callable]:
    """Return (pre, post) middleware functions that log the request ID."""

    def pre_middleware(ctx: RequestContext) -> None:
        if not cfg.enabled:
            return
        request_id = ctx.metadata.get(_REQUEST_ID_CTX_KEY, "")
        if cfg.log_on_request and request_id:
            logger.info(
                "request received",
                extra={"request_id": request_id, "method": ctx.method, "path": ctx.path},
            )

    def post_middleware(ctx: RequestContext) -> None:
        if not cfg.enabled:
            return
        request_id = ctx.metadata.get(_REQUEST_ID_CTX_KEY, "")
        if cfg.log_on_response and request_id:
            status = (ctx.response or {}).get("status", 0)
            logger.info(
                "response sent",
                extra={"request_id": request_id, "status": status, "path": ctx.path},
            )

    return pre_middleware, post_middleware


def build_default_request_id_log_middleware(
    cfg: RequestIdLogConfig | None = None,
) -> tuple[Callable, Callable]:
    return make_request_id_log_middleware(cfg or RequestIdLogConfig())
