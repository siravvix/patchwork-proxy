"""Integration tests: IP allowlist middleware wired into a MiddlewarePipeline."""
import pytest

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_ip_allowlist import IPAllowlistConfig, make_ip_allowlist_middleware


def _make_ctx(
    forwarded_for: str | None = None,
    remote_addr: str | None = None,
) -> RequestContext:
    headers = {}
    if forwarded_for is not None:
        headers["X-Forwarded-For"] = forwarded_for
    metadata = {}
    if remote_addr is not None:
        metadata["remote_addr"] = remote_addr
    return RequestContext(
        method="GET",
        path="/resource",
        request_headers=headers,
        metadata=metadata,
    )


def _make_pipeline(cidrs: list[str], enabled: bool = True) -> MiddlewarePipeline:
    cfg = IPAllowlistConfig(enabled=enabled, allowed_cidrs=cidrs)
    mw = make_ip_allowlist_middleware(cfg)
    pipeline = MiddlewarePipeline()
    pipeline.add_pre(mw)
    return pipeline


def test_pipeline_disabled_passes_all_ips():
    pipeline = _make_pipeline(cidrs=[], enabled=False)
    ctx = _make_ctx(forwarded_for="8.8.8.8")
    result = pipeline.run_pre(ctx)
    assert "ip_blocked" not in result.metadata


def test_pipeline_allows_ip_in_cidr():
    pipeline = _make_pipeline(cidrs=["192.168.0.0/16"])
    ctx = _make_ctx(forwarded_for="192.168.10.20")
    result = pipeline.run_pre(ctx)
    assert result.metadata["ip_blocked"] is False


def test_pipeline_blocks_ip_outside_cidr():
    pipeline = _make_pipeline(cidrs=["192.168.0.0/16"])
    ctx = _make_ctx(forwarded_for="10.0.0.1")
    result = pipeline.run_pre(ctx)
    assert result.metadata["ip_blocked"] is True


def test_pipeline_uses_remote_addr_fallback():
    pipeline = _make_pipeline(cidrs=["10.0.0.0/8"])
    ctx = _make_ctx(remote_addr="10.5.5.5")  # no X-Forwarded-For
    result = pipeline.run_pre(ctx)
    assert result.metadata["ip_blocked"] is False


def test_pipeline_first_ip_in_forwarded_for_is_used():
    """Only the first (client) IP in X-Forwarded-For should be evaluated."""
    pipeline = _make_pipeline(cidrs=["10.0.0.0/8"])
    # Second IP is in range, first is not — should be blocked.
    ctx = _make_ctx(forwarded_for="172.31.0.1, 10.0.0.1")
    result = pipeline.run_pre(ctx)
    assert result.metadata["ip_blocked"] is True


def test_pipeline_multiple_cidrs_any_match_allowed():
    pipeline = _make_pipeline(cidrs=["10.0.0.0/8", "172.16.0.0/12"])
    ctx = _make_ctx(forwarded_for="172.20.0.5")
    result = pipeline.run_pre(ctx)
    assert result.metadata["ip_blocked"] is False
