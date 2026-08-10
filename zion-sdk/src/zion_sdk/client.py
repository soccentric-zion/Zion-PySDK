"""The :class:`Device` and :func:`connect` entry-point.

A ``Device`` wraps one persistent gRPC channel to an Acadia ``HalService``
endpoint. Discovery (``peripherals()``) is performed on connect and cached.
"""
from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import suppress
from types import TracebackType
from typing import TYPE_CHECKING, Any

import grpc

from zion_sdk import _channel, exceptions
from zion_sdk._proto import hal_service_pb2, hal_service_pb2_grpc
from zion_sdk.types import hal_service as hal_types

if TYPE_CHECKING:
    from zion_sdk.peripheral import Peripheral


def connect(address: str, *, timeout: float | None = 5.0) -> Device:
    """Connect to an Acadia ``HalService`` endpoint.

    Args:
        address: Host:port string, e.g. ``"192.168.1.50:50051"``.
        timeout: Seconds to wait for the initial ``ListModules`` handshake.
            ``None`` means wait forever.

    Returns:
        A live :class:`Device`. Always close it (or use as a context manager).

    Raises:
        ConnectionError: If the channel can't be opened or the handshake fails.

    Example:
        >>> import zion_sdk as ivv
        >>> with ivv.connect("192.168.1.50:50051") as dev:
        ...     for module_id in dev.peripherals():
        ...         print(module_id)
    """
    channel = _channel.open_channel(address)
    dev = Device(channel=channel, address=address)
    try:
        dev._handshake(timeout=timeout)
    except Exception:
        dev.close()
        raise
    return dev


class Device:
    """A live connection to one Acadia ``HalService`` peer.

    Single device, single test at a time: concurrent calls on the same device
    are serialised by an internal mutex (per the v1 design contract). Open a
    second :class:`Device` if you need parallel execution against a second peer.
    """

    def __init__(self, channel: grpc.Channel, address: str) -> None:
        self._channel = channel
        self._address = address
        self._stub = hal_service_pb2_grpc.HalServiceStub(channel)
        self._modules: dict[str, hal_types.ModuleInfo] = {}
        self._lock = threading.Lock()
        self._closed = False

    # ----- handshake / discovery -----

    def _handshake(self, *, timeout: float | None) -> None:
        """Call ``ListModules`` and cache the registry."""
        req = hal_service_pb2.ListModulesRequest()
        resp = _channel.call_unary(self._stub.ListModules, req, timeout=timeout)
        dc_resp = hal_types.ListModulesResponse.from_proto(resp)
        self._modules = {m.id: m for m in dc_resp.modules}
        _channel.handshake_modules(dc_resp.modules)

    # ----- public API -----

    @property
    def address(self) -> str:
        """The ``host:port`` string this device is connected to."""
        return self._address

    def peripherals(self) -> list[str]:
        """List the IDs of every module the peer advertises (active only)."""
        return [
            m_id for m_id, info in sorted(self._modules.items())
            if getattr(info, "status", "active") != "deprecated"
        ]

    def module_info(self, peripheral_id: str) -> hal_types.ModuleInfo:
        """Return the full :class:`ModuleInfo` dataclass for ``peripheral_id``.

        Raises:
            PeripheralNotFound: If ``peripheral_id`` is not registered.
        """
        try:
            return self._modules[peripheral_id]
        except KeyError as e:
            raise exceptions.PeripheralNotFound(
                f"no such peripheral: {peripheral_id!r}. "
                f"Known peripherals: {sorted(self._modules)}"
            ) from e

    def peripheral(self, peripheral_id: str) -> Peripheral:
        """Return a :class:`Peripheral` handle bound to this device."""
        from zion_sdk.peripheral import Peripheral

        info = self.module_info(peripheral_id)
        return Peripheral(device=self, info=info)

    # ----- internal RPC plumbing (used by Peripheral) -----

    def _call(self, name: str, request: Any, *, timeout: float | None) -> Any:
        method = getattr(self._stub, name)
        return _channel.call_unary(method, request, timeout=timeout)

    def _stream(self, name: str, request: Any, *, timeout: float | None) -> Iterator[Any]:
        method = getattr(self._stub, name)
        return _channel.call_stream(method, request, timeout=timeout)

    def _serialised(self) -> threading.Lock:
        """The device-wide mutex enforcing one-test-at-a-time semantics."""
        return self._lock

    # ----- lifecycle -----

    def close(self) -> None:
        """Close the underlying gRPC channel. Idempotent."""
        if self._closed:
            return
        self._closed = True
        with suppress(Exception):
            self._channel.close()

    @property
    def closed(self) -> bool:
        return self._closed

    def __enter__(self) -> Device:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        state = "closed" if self._closed else "open"
        return f"Device(address={self._address!r}, peripherals={len(self._modules)}, {state})"
