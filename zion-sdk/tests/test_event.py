"""Tests for arm_event() streaming."""
from __future__ import annotations

import pytest

import zion_sdk


def test_arm_event_with_test_name(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        events = list(dev.peripheral("imu").arm_event(test_name="accel_read"))
        assert len(events) == 2


def test_arm_event_with_expression(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        events = list(dev.peripheral("imu").arm_event(expression="accel_x > 0"))
        assert len(events) == 2


def test_arm_event_requires_a_condition(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        with pytest.raises(zion_sdk.ConfigError):
            list(dev.peripheral("imu").arm_event())
