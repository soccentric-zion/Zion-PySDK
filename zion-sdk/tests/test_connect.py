"""Tests for connect() and the version handshake."""
from __future__ import annotations

import pytest

import zion_sdk
from zion_sdk.exceptions import ConnectionError


def test_connect_smoke(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        assert dev.address == address
        assert not dev.closed
        assert sorted(dev.peripherals()) == ["cpu", "imu"]
    assert dev.closed


def test_connect_context_manager_closes_on_exception(address: str) -> None:
    dev = zion_sdk.connect(address)
    try:
        with pytest.raises(RuntimeError):
            with dev:
                raise RuntimeError("boom")
    finally:
        assert dev.closed


def test_connect_bad_address_raises() -> None:
    with pytest.raises(ConnectionError):
        zion_sdk.connect("")
    with pytest.raises(ConnectionError):
        zion_sdk.connect("no-port")


def test_connect_unreachable_raises() -> None:
    # 127.0.0.1:1 should refuse instantly
    with pytest.raises(ConnectionError):
        zion_sdk.connect("127.0.0.1:1", timeout=1.0)


def test_handshake_rejects_too_new_contract(fake_server, address: str) -> None:
    fake_server.servicer.peripheral_versions["imu"] = 99
    with pytest.raises(ConnectionError, match="contract versions"):
        zion_sdk.connect(address)


def test_repr(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        s = repr(dev)
        assert "Device" in s and "open" in s
