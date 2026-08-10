"""pytest fixtures: a fresh FakeServer per test."""
from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests.fakes.fake_server import FakeServer


@pytest.fixture
def fake_server() -> Iterator[FakeServer]:
    srv = FakeServer()
    srv.start()
    try:
        yield srv
    finally:
        srv.stop()


@pytest.fixture
def address(fake_server: FakeServer) -> str:
    return f"127.0.0.1:{fake_server._port}"
