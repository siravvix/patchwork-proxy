"""Tests for retry_policy.py."""
import pytest
from patchwork.retry_policy import RetryPolicy, retry_policy_from_proxy_config


def test_default_policy_values():
    policy = RetryPolicy()
    assert policy.enabled is True
    assert policy.max_attempts == 3
    assert 503 in policy.retryable_statuses
    assert policy.backoff_base == 0.5
    assert policy.backoff_max == 10.0


def test_invalid_max_attempts_raises():
    with pytest.raises(ValueError, match="max_attempts"):
        RetryPolicy(max_attempts=0)


def test_invalid_backoff_base_raises():
    with pytest.raises(ValueError, match="backoff_base"):
        RetryPolicy(backoff_base=-1.0)


def test_invalid_backoff_max_raises():
    with pytest.raises(ValueError, match="backoff_max"):
        RetryPolicy(backoff_base=5.0, backoff_max=1.0)


def test_from_dict_full():
    data = {
        "enabled": False,
        "max_attempts": 5,
        "retryable_statuses": [500, 502],
        "backoff_base": 1.0,
        "backoff_max": 20.0,
    }
    policy = RetryPolicy.from_dict(data)
    assert policy.enabled is False
    assert policy.max_attempts == 5
    assert policy.retryable_statuses == {500, 502}
    assert policy.backoff_base == 1.0
    assert policy.backoff_max == 20.0


def test_from_dict_partial_uses_defaults():
    policy = RetryPolicy.from_dict({"max_attempts": 2})
    assert policy.max_attempts == 2
    assert policy.enabled is True
    assert 504 in policy.retryable_statuses


def test_as_dict_round_trips():
    policy = RetryPolicy(max_attempts=4, retryable_statuses={502, 503})
    d = policy.as_dict()
    restored = RetryPolicy.from_dict(d)
    assert restored.max_attempts == policy.max_attempts
    assert restored.retryable_statuses == policy.retryable_statuses


def test_to_retry_config_maps_correctly():
    policy = RetryPolicy(max_attempts=2, backoff_base=0.2, backoff_max=5.0)
    rc = policy.to_retry_config()
    assert rc.max_attempts == 2
    assert rc.backoff_base == 0.2
    assert rc.backoff_max == 5.0


def test_retry_policy_from_proxy_config_present():
    proxy_cfg = {"retry": {"max_attempts": 4, "enabled": True}}
    policy = retry_policy_from_proxy_config(proxy_cfg)
    assert policy.max_attempts == 4


def test_retry_policy_from_proxy_config_absent():
    policy = retry_policy_from_proxy_config({})
    assert policy.max_attempts == 3
    assert policy.enabled is True
