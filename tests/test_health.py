"""Tests for the health check module."""

import time
from unittest.mock import MagicMock, patch

import pytest

from patchwork.health import HealthChecker, HealthStatus


@pytest.fixture
def checker():
    return HealthChecker(path="/healthz", timeout=1.0, failure_threshold=3)


def _mock_response(status: int):
    resp = MagicMock()
    resp.status = status
    return resp


def test_initial_is_healthy(checker):
    assert checker.is_healthy("http://localhost:8080") is True


def test_successful_check_marks_healthy(checker):
    with patch("urllib.request.urlopen", return_value=_mock_response(200)):
        status = checker.check("http://localhost:8080")
    assert status.healthy is True
    assert status.consecutive_failures == 0
    assert status.last_error is None


def test_single_failure_does_not_mark_unhealthy(checker):
    with patch("urllib.request.urlopen", side_effect=OSError("refused")):
        status = checker.check("http://localhost:9000")
    assert status.healthy is True  # below threshold
    assert status.consecutive_failures == 1
    assert "refused" in status.last_error


def test_marks_unhealthy_after_threshold(checker):
    target = "http://localhost:9001"
    with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
        for _ in range(3):
            status = checker.check(target)
    assert status.healthy is False
    assert checker.is_healthy(target) is False


def test_recovery_resets_failures(checker):
    target = "http://localhost:9002"
    with patch("urllib.request.urlopen", side_effect=OSError("down")):
        for _ in range(3):
            checker.check(target)
    assert checker.is_healthy(target) is False

    with patch("urllib.request.urlopen", return_value=_mock_response(200)):
        status = checker.check(target)
    assert status.healthy is True
    assert status.consecutive_failures == 0


def test_get_all_returns_dict(checker):
    with patch("urllib.request.urlopen", return_value=_mock_response(200)):
        checker.check("http://localhost:8080")
    result = checker.get_all()
    assert "http://localhost:8080" in result
    assert result["http://localhost:8080"]["healthy"] is True


def test_reset_clears_status(checker):
    target = "http://localhost:9003"
    with patch("urllib.request.urlopen", side_effect=OSError("err")):
        for _ in range(3):
            checker.check(target)
    assert checker.is_healthy(target) is False
    checker.reset(target)
    assert checker.is_healthy(target) is True


def test_last_checked_is_updated(checker):
    before = time.time()
    with patch("urllib.request.urlopen", return_value=_mock_response(204)):
        status = checker.check("http://localhost:8080")
    assert status.last_checked >= before
