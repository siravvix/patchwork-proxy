"""Tests for patchwork.retry module."""

import pytest
from unittest.mock import patch
from patchwork.retry import RetryConfig, RetryResult, with_retry


# ---------------------------------------------------------------------------
# RetryConfig helpers
# ---------------------------------------------------------------------------

def test_backoff_grows_exponentially():
    cfg = RetryConfig(backoff_base_ms=100, backoff_multiplier=2.0)
    assert cfg.backoff_seconds(0) == pytest.approx(0.1)
    assert cfg.backoff_seconds(1) == pytest.approx(0.2)
    assert cfg.backoff_seconds(2) == pytest.approx(0.4)


def test_backoff_capped_at_max():
    cfg = RetryConfig(backoff_base_ms=100, backoff_multiplier=10.0, max_backoff_ms=500)
    assert cfg.backoff_seconds(5) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# with_retry — success on first attempt
# ---------------------------------------------------------------------------

def test_success_on_first_attempt():
    fn = lambda: (200, b"ok")
    with patch("patchwork.retry.time.sleep") as mock_sleep:
        result = with_retry(fn)
    assert result.succeeded
    assert result.attempts == 1
    assert result.value == (200, b"ok")
    mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# with_retry — retryable status code
# ---------------------------------------------------------------------------

def test_retries_on_retryable_status():
    responses = [(503, b"unavailable"), (503, b"unavailable"), (200, b"ok")]
    call_count = {"n": 0}

    def fn():
        r = responses[call_count["n"]]
        call_count["n"] += 1
        return r

    with patch("patchwork.retry.time.sleep"):
        result = with_retry(fn, RetryConfig(max_attempts=3))

    assert result.succeeded
    assert result.attempts == 3
    assert result.value == (200, b"ok")


def test_exhausts_retries_on_persistent_status():
    fn = lambda: (502, b"bad gateway")
    with patch("patchwork.retry.time.sleep"):
        result = with_retry(fn, RetryConfig(max_attempts=3))

    # No exception was raised, but status was never good — last_exception is None
    assert not result.succeeded  # value is set but last_exc may be None; check attempts
    assert result.attempts == 3


# ---------------------------------------------------------------------------
# with_retry — exception handling
# ---------------------------------------------------------------------------

def test_retries_on_exception():
    call_count = {"n": 0}

    def fn():
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise ConnectionError("refused")
        return (200, b"ok")

    with patch("patchwork.retry.time.sleep"):
        result = with_retry(fn, RetryConfig(max_attempts=3))

    assert result.succeeded
    assert result.attempts == 3


def test_returns_last_exception_when_all_attempts_fail():
    def fn():
        raise TimeoutError("timed out")

    with patch("patchwork.retry.time.sleep"):
        result = with_retry(fn, RetryConfig(max_attempts=2))

    assert not result.succeeded
    assert isinstance(result.last_exception, TimeoutError)
    assert result.attempts == 2


# ---------------------------------------------------------------------------
# RetryResult helpers
# ---------------------------------------------------------------------------

def test_retry_result_succeeded_false_when_exception():
    r = RetryResult(value=None, attempts=1, last_exception=RuntimeError("x"))
    assert not r.succeeded


def test_retry_result_succeeded_false_when_no_value():
    r = RetryResult(value=None, attempts=1)
    assert not r.succeeded
