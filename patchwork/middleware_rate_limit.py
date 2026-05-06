"""Rate-limiting middleware integration for the patchwork middleware pipeline."""

from http import HTTPStatus
from typing import Callable, Optional

from patchwork.middleware import RequestContext
from patchwork.rate_limiter import RateLimiter, RateLimitConfig
from patchwork.logger import get_logger

logger = get_logger(__name__)


def _route_id(ctx: RequestContext) -> str:
    """Derive a stable route identifier from the request context."""
    target = ctx.target_url or ""
    method = ctx.method or "GET"
    return f"{method}:{target}"


def make_rate_limit_middleware(
    limiter: RateLimiter,
    route_id_fn: Optional[Callable[[RequestContext], str]] = None,
) -> Callable[[RequestContext], None]:
    """Return a pre-middleware function that enforces rate limits.

    If the request is throttled, ``ctx.response_status`` and
    ``ctx.response_body`` are set so the pipeline can short-circuit.
    """
    id_fn = route_id_fn or _route_id

    def _middleware(ctx: RequestContext) -> None:
        rid = id_fn(ctx)
        if not limiter.is_allowed(rid):
            logger.warning("rate_limited", extra={"route_id": rid, "path": ctx.path})
            ctx.response_status = HTTPStatus.TOO_MANY_REQUESTS.value
            ctx.response_body = b"429 Too Many Requests - rate limit exceeded"

    return _middleware


def build_default_rate_limiter(
    routes: dict[str, dict],
    default_rps: float = 50.0,
    default_burst: int = 100,
) -> RateLimiter:
    """Construct a RateLimiter from a route config mapping.

    Each entry in *routes* may contain an optional ``rate_limit`` sub-dict
    with ``requests_per_second`` and ``burst`` keys.
    """
    default_cfg = RateLimitConfig(
        requests_per_second=default_rps,
        burst=default_burst,
    )
    limiter = RateLimiter(default_config=default_cfg)

    for route_id, route_cfg in routes.items():
        rl = route_cfg.get("rate_limit")
        if rl:
            cfg = RateLimitConfig(
                requests_per_second=float(rl.get("requests_per_second", default_rps)),
                burst=int(rl.get("burst", default_burst)),
            )
            limiter.configure_route(route_id, cfg)
            logger.debug(
                "rate_limit_configured",
                extra={"route_id": route_id, "rps": cfg.requests_per_second, "burst": cfg.burst},
            )

    return limiter
