"""Tests for patchwork.middleware pipeline."""

import time
import pytest
from patchwork.middleware import (
    RequestContext,
    MiddlewarePipeline,
    logging_pre,
    logging_post,
    cors_post,
    build_default_pipeline,
)


def make_ctx(**kwargs) -> RequestContext:
    defaults = dict(method="GET", path="/api/test", headers={})
    defaults.update(kwargs)
    return RequestContext(**defaults)


def test_pre_middleware_runs_in_order():
    order = []
    pipeline = MiddlewarePipeline()
    pipeline.add_pre(lambda ctx: order.append("first"))
    pipeline.add_pre(lambda ctx: order.append("second"))

    ctx = make_ctx()
    pipeline.run_pre(ctx)
    assert order == ["first", "second"]


def test_post_middleware_runs_in_order():
    order = []
    pipeline = MiddlewarePipeline()
    pipeline.add_post(lambda ctx: order.append("a"))
    pipeline.add_post(lambda ctx: order.append("b"))

    ctx = make_ctx()
    pipeline.run_post(ctx)
    assert order == ["a", "b"]


def test_middleware_can_mutate_context():
    def set_target(ctx: RequestContext) -> None:
        ctx.target_url = "http://localhost:8080" + ctx.path

    pipeline = MiddlewarePipeline()
    pipeline.add_pre(set_target)

    ctx = make_ctx(path="/foo")
    pipeline.run_pre(ctx)
    assert ctx.target_url == "http://localhost:8080/foo"


def test_cors_post_injects_headers():
    ctx = make_ctx(headers={})
    cors_post(ctx)
    assert "Access-Control-Allow-Origin" in ctx.headers
    assert ctx.headers["Access-Control-Allow-Origin"] == "*"


def test_cors_post_does_not_overwrite_existing():
    ctx = make_ctx(headers={"Access-Control-Allow-Origin": "https://example.com"})
    cors_post(ctx)
    assert ctx.headers["Access-Control-Allow-Origin"] == "https://example.com"


def test_logging_post_records_status(caplog):
    import logging
    ctx = make_ctx()
    ctx.status_code = 200
    with caplog.at_level(logging.INFO):
        logging_post(ctx)
    assert "200" in caplog.text


def test_build_default_pipeline_has_pre_and_post():
    pipeline = build_default_pipeline()
    assert len(pipeline._pre) >= 1
    assert len(pipeline._post) >= 1
