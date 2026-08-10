"""Tests for run_oneshot and self_test."""
from __future__ import annotations

import pytest

import zion_sdk


def test_run_oneshot_returns_result(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        result = dev.peripheral("imu").run_oneshot()
        assert result is not None
        assert len(result.results) == 1
        tr = result.results[0]
        assert tr.module_id == "imu"
        assert tr.output.metrics["accel_x"].double_value == pytest.approx(0.1)
        assert tr.output.metrics["accel_z"].double_value == pytest.approx(9.8)


def test_self_test_alias(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        result = dev.peripheral("cpu").self_test()
        assert result.results[0].module_id == "cpu"


def test_oneshot_fail_returns_normally(fake_server, address: str) -> None:
    fake_server.servicer.fail_mode = "test_fail"
    with zion_sdk.connect(address) as dev:
        result = dev.peripheral("imu").run_oneshot()
        # FAIL status doesn't raise by default
        assert result is not None


def test_oneshot_fail_raises_when_requested(fake_server, address: str) -> None:
    fake_server.servicer.fail_mode = "test_fail"
    with zion_sdk.connect(address) as dev:
        with pytest.raises(zion_sdk.TestError):
            dev.peripheral("imu").run_oneshot(raise_on_failure=True)


def test_oneshot_error_raises(fake_server, address: str) -> None:
    fake_server.servicer.fail_mode = "test_error"
    with zion_sdk.connect(address) as dev:
        with pytest.raises(zion_sdk.TestError):
            dev.peripheral("imu").run_oneshot()


def test_oneshot_timeout_raises(fake_server, address: str) -> None:
    fake_server.servicer.fail_mode = "test_timeout"
    with zion_sdk.connect(address) as dev:
        with pytest.raises(zion_sdk.TimeoutError):
            dev.peripheral("imu").run_oneshot()


def test_oneshot_config_error(fake_server, address: str) -> None:
    fake_server.servicer.fail_mode = "config"
    with zion_sdk.connect(address) as dev:
        with pytest.raises(zion_sdk.ConfigError):
            dev.peripheral("imu").run_oneshot()


def test_oneshot_with_test_names(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        dev.peripheral("imu").run_oneshot(tests=["accel_read"])
