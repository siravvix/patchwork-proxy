"""Integration tests: retry middleware wired into a MiddlewarePipeline."""
import pytest
from patchwork.middleware import RequestContext, MiddlewarePipeline
from patchwork.retry import RetryConfig
from patchwork.middleware_retry import (
    make_retry_middleware,
    _RETRY_ATTEMPTS_KEY,
    _RETRY_EXHAUSTED_KEY,
)


def _make_config(**kwargs):
    defaults = dict(
        max_attempts=3,
        retryable_statuses={502, 503},
        backoff_base=0.1,
        backoff_max=2.0,
    )
    defaults.update(kwargs)
    return RetryConfig(**defaults)


def _make_pipeline(config: RetryConfig) -> MiddlewarePipeline:
    pipeline = MiddlewarePipeline()
    pre, post = make_retry_middleware(config)
    pipeline.add_pre(pre)
    pipeline.add_post(post)
    return pipeline


def _make_ctx(status=None):
    return RequestContext(
        request={"method": "GET", "path": "/test"},
        response={"status": status} if status else None,
    )


def test_pipeline_success_no_retry():
    pipeline = _make_pipeline(_make_config())
    ctx = _make_ctx(status=200)
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    assert ctx.meta["should_retry"] is False
    assert _RETRY_EXHAUSTED_KEY not in ctx.meta


def test_pipeline_first_failure_schedules_retry():
    pipeline = _make_pipeline(_make_config())
    ctx = _make_ctx(status=503)
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    assert ctx.meta["should_retry"] is True
    assert ctx.meta["retry_delay"] >= 0


def test_pipeline_exhausted_after_max_attempts():
    config = _make_config(max_attempts=2)
    pipeline = _make_pipeline(config)
    ctx = _make_ctx(status=502)
    # Simulate two full cycles
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)  # attempt 1 -> should_retry=True
    assert ctx.meta["should_retry"] is True
    pipeline.run_post(ctx)  # attempt 2 -> exhausted
    assert ctx.meta["should_retry"] is False
    assert ctx.meta[_RETRY_EXHAUSTED_KEY] is True


def test_pipeline_non_retryable_status_never_retries():
    pipeline = _make_pipeline(_make_config())
    ctx = _make_ctx(status=404)
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    assert ctx.meta["should_retry"] is False
    assert _RETRY_EXHAUSTED_KEY not in ctx.meta


def test_pipeline_retry_delay_grows():
    config = _make_config(max_attempts=5, backoff_base=1.0)
    pipeline = _make_pipeline(config)
    delays = []
    ctx = _make_ctx(status=503)
    pipeline.run_pre(ctx)
    for _ in range(3):
        pipeline.run_post(ctx)
        if ctx.meta.get("should_retry"):
            delays.append(ctx.meta["retry_delay"])
    assert delays == sorted(delays), "Delays should be non-decreasing"
