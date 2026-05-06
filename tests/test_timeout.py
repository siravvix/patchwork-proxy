"""Tests for patchwork.timeout.TimeoutConfig."""

import pytest

from patchwork.timeout import TimeoutConfig, DEFAULT_TIMEOUT


def test_default_timeout_values():
    cfg = TimeoutConfig()
    assert cfg.connect_seconds == 5.0
    assert cfg.read_seconds == 30.0
    assert cfg.total_seconds is None


def test_as_tuple_returns_connect_read():
    cfg = TimeoutConfig(connect_seconds=2.0, read_seconds=10.0)
    assert cfg.as_tuple == (2.0, 10.0)


def test_is_exceeded_without_total_always_false():
    cfg = TimeoutConfig()
    assert cfg.is_exceeded(9999.0) is False


def test_is_exceeded_with_total():
    cfg = TimeoutConfig(total_seconds=5.0)
    assert cfg.is_exceeded(4.9) is False
    assert cfg.is_exceeded(5.0) is True
    assert cfg.is_exceeded(6.0) is True


def test_invalid_connect_raises():
    with pytest.raises(ValueError, match="connect_seconds"):
        TimeoutConfig(connect_seconds=0)


def test_invalid_read_raises():
    with pytest.raises(ValueError, match="read_seconds"):
        TimeoutConfig(read_seconds=-1)


def test_invalid_total_raises():
    with pytest.raises(ValueError, match="total_seconds"):
        TimeoutConfig(total_seconds=0)


def test_from_dict_full():
    data = {"connect_seconds": 3.0, "read_seconds": 15.0, "total_seconds": 20.0}
    cfg = TimeoutConfig.from_dict(data)
    assert cfg.connect_seconds == 3.0
    assert cfg.read_seconds == 15.0
    assert cfg.total_seconds == 20.0


def test_from_dict_defaults():
    cfg = TimeoutConfig.from_dict({})
    assert cfg.connect_seconds == 5.0
    assert cfg.read_seconds == 30.0
    assert cfg.total_seconds is None


def test_to_dict_omits_none_total():
    cfg = TimeoutConfig(connect_seconds=1.0, read_seconds=2.0)
    d = cfg.to_dict()
    assert "total_seconds" not in d
    assert d["connect_seconds"] == 1.0


def test_to_dict_includes_total_when_set():
    cfg = TimeoutConfig(total_seconds=60.0)
    d = cfg.to_dict()
    assert d["total_seconds"] == 60.0


def test_default_timeout_singleton_is_valid():
    assert isinstance(DEFAULT_TIMEOUT, TimeoutConfig)
