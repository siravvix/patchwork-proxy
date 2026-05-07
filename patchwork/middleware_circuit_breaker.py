"""Circuit breaker middleware integration for the proxy pipeline."""

from __future__ import annotations

from typing import Callable, Dict, Optional

from patchwork.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from patchwork.middleware import RequestContext

_BREAKER_REGISTRY: Dict[str, CircuitBreaker] = {}

CIRCUIT_OPEN_STATUS = 503
CIRCUIT_OPEN_BODY = b"Service temporarily unavailable (circuit open)"


def _route_id(ctx: RequestContext) -> str:
    method = ctx.request.get("method", "GET")
    target = ctx.request.get("target", "unknown")
    return f"{method}:{target}"


def make_circuit_breaker_middleware(
    config: CircuitBreakerConfig,
    registry: Optional[Dict[str, CircuitBreaker]] = None,
) -> tuple[Callable, Callable]:
    """Return (pre_middleware, post_middleware) for circuit breaker logic."""
    if registry is None:
        registry = _BREAKER_REGISTRY

    def _get_breaker(route: str) -> CircuitBreaker:
        if route not in registry:
            registry[route] = CircuitBreaker(config)
        return registry[route]

    def pre_middleware(ctx: RequestContext) -> RequestContext:
        route = _route_id(ctx)
        breaker = _get_breaker(route)
        if breaker.is_open():
            ctx.response = {
                "status": CIRCUIT_OPEN_STATUS,
                "body": CIRCUIT_OPEN_BODY,
                "headers": {"Content-Type": "text/plain"},
            }
            ctx.metadata["circuit_breaker_open"] = True
        else:
            ctx.metadata["circuit_breaker_route"] = route
            ctx.metadata["circuit_breaker_open"] = False
        return ctx

    def post_middleware(ctx: RequestContext) -> RequestContext:
        if ctx.metadata.get("circuit_breaker_open"):
            return ctx
        route = ctx.metadata.get("circuit_breaker_route")
        if not route:
            return ctx
        breaker = _get_breaker(route)
        status = (ctx.response or {}).get("status", 200)
        if isinstance(status, int) and status >= 500:
            breaker.record_failure()
        else:
            breaker.record_success()
        ctx.metadata["circuit_breaker_state"] = breaker.state.value
        return ctx

    return pre_middleware, post_middleware


def build_default_circuit_breaker_middleware(
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    half_open_max_calls: int = 1,
) -> tuple[Callable, Callable]:
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_max_calls=half_open_max_calls,
    )
    return make_circuit_breaker_middleware(config)
