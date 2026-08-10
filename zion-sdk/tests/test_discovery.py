"""Tests for peripheral discovery and Peripheral handles."""
from __future__ import annotations

import pytest

import zion_sdk


def test_peripherals_lists_active(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        ids = dev.peripherals()
        assert "imu" in ids and "cpu" in ids


def test_peripheral_returns_handle(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        imu = dev.peripheral("imu")
        assert imu.id == "imu"
        assert imu.info.config_type == "hal.modules.imu.Config"


def test_unknown_peripheral_raises(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        with pytest.raises(zion_sdk.PeripheralNotFound):
            dev.peripheral("nonexistent")


def test_capabilities_uniform(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        caps = dev.peripheral("imu").capabilities()
        assert {"oneshot", "monitor", "event", "long_running"} <= caps
