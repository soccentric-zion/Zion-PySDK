"""Tests for the long-running test mode."""
from __future__ import annotations

import time

import pytest

import zion_sdk


def test_long_running_lifecycle(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        imu = dev.peripheral("imu")
        session = imu.start_long_running(interval_ms=10, duration_s=0.2)
        assert session.module_id == "imu"
        first = imu.query_long_running(timeout=1.0)
        assert first is not None
        imu.stop_long_running()


def test_long_running_double_start_rejected(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        imu = dev.peripheral("imu")
        imu.start_long_running(interval_ms=10, duration_s=0.2)
        try:
            with pytest.raises(zion_sdk.ConfigError):
                imu.start_long_running(interval_ms=10, duration_s=0.2)
        finally:
            imu.stop_long_running()


def test_query_without_session_raises(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        with pytest.raises(zion_sdk.ConfigError):
            dev.peripheral("imu").query_long_running(block=False)


def test_stop_without_session_is_noop(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        dev.peripheral("imu").stop_long_running()


def test_pause_resume(address: str, fake_server) -> None:
    with zion_sdk.connect(address) as dev:
        imu = dev.peripheral("imu")
        assert imu.pause() is True
        assert imu.resume() is True
        assert fake_server.servicer.pause_calls == 1
        assert fake_server.servicer.resume_calls == 1
