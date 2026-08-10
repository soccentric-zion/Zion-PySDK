"""Tests for monitor() streaming."""
from __future__ import annotations

import pytest

import zion_sdk


def test_monitor_yields_results(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        results = list(dev.peripheral("imu").monitor(period_ms=10, duration_s=0.1))
        assert len(results) >= 1
        first = results[0]
        assert first.results[0].module_id == "imu"


def test_monitor_early_break(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        count = 0
        for r in dev.peripheral("imu").monitor(period_ms=10, duration_s=1.0):
            count += 1
            if count >= 2:
                break
        assert count == 2


def test_monitor_rejects_bad_period(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        with pytest.raises(zion_sdk.ConfigError):
            list(dev.peripheral("imu").monitor(period_ms=0))


def test_monitor_indefinite(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        gen = dev.peripheral("imu").monitor(period_ms=10)
        first = next(gen)
        assert first is not None
        gen.close()
