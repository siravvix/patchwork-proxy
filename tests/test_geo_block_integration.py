"""Integration tests: GeoBlock middleware wired into a MiddlewarePipeline."""
from __future__ import annotations

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_geo_block import GeoBlockConfig, make_geo_block_middleware


def _make_ctx(country: str | None = None) -> RequestContext:
    ctx = RequestContext()
    ctx.request_headers = {}
    if country is not None:
        ctx.request_headers["X-Country-Code"] = country
    ctx.request_method = "GET"
    ctx.request_path = "/api/data"
    return ctx


def _make_pipeline(config: GeoBlockConfig) -> MiddlewarePipeline:
    pipeline = MiddlewarePipeline()
    pipeline.add_pre(make_geo_block_middleware(config))
    return pipeline


def test_pipeline_disabled_allows_any_country():
    pipeline = _make_pipeline(GeoBlockConfig(enabled=False))
    ctx = _make_ctx("CN")
    result = pipeline.run_pre(ctx)
    assert result.response_status is None


def test_pipeline_allowlist_blocks_foreign_country():
    pipeline = _make_pipeline(
        GeoBlockConfig(enabled=True, allowlist=["US", "CA"])
    )
    ctx = _make_ctx("DE")
    result = pipeline.run_pre(ctx)
    assert result.response_status == 403


def test_pipeline_allowlist_passes_permitted_country():
    pipeline = _make_pipeline(
        GeoBlockConfig(enabled=True, allowlist=["US", "CA"])
    )
    ctx = _make_ctx("US")
    result = pipeline.run_pre(ctx)
    assert result.response_status is None


def test_pipeline_blocklist_blocks_listed_country():
    pipeline = _make_pipeline(
        GeoBlockConfig(enabled=True, blocklist=["CN", "RU"])
    )
    ctx = _make_ctx("RU")
    result = pipeline.run_pre(ctx)
    assert result.response_status == 403


def test_pipeline_missing_header_respects_unknown_policy_block():
    pipeline = _make_pipeline(
        GeoBlockConfig(enabled=True, blocklist=["CN"], unknown_country_policy="block")
    )
    ctx = _make_ctx(country=None)  # no header
    result = pipeline.run_pre(ctx)
    assert result.response_status == 403


def test_pipeline_missing_header_respects_unknown_policy_allow():
    pipeline = _make_pipeline(
        GeoBlockConfig(enabled=True, blocklist=["CN"], unknown_country_policy="allow")
    )
    ctx = _make_ctx(country=None)
    result = pipeline.run_pre(ctx)
    assert result.response_status is None
