"""Private gRPC channel management and error translation.

This module is the SDK's single chokepoint for talking to the peer. Every
call goes through :func:`call_unary` or :func:`call_stream`, which catch
``grpc.RpcError`` and translate to :mod:`zion_sdk.exceptions`.
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import suppress
from typing import Any, TypeVar

import grpc

from zion_sdk import exceptions as exc
from zion_sdk._version import __contracts_version__

log = logging.getLogger(__name__)

T = TypeVar("T")

# Mapping from gRPC status codes to SDK exception classes.
_STATUS_TO_EXC: dict[grpc.StatusCode, type[exc.IVVError]] = {
    grpc.StatusCode.UNAVAILABLE: exc.ConnectionError,
    grpc.StatusCode.DEADLINE_EXCEEDED: exc.TimeoutError,
    grpc.StatusCode.NOT_FOUND: exc.PeripheralNotFound,
    grpc.StatusCode.INVALID_ARGUMENT: exc.ConfigError,
    grpc.StatusCode.UNIMPLEMENTED: exc.NotSupported,
    grpc.StatusCode.FAILED_PRECONDITION: exc.ConfigError,
    grpc.StatusCode.PERMISSION_DENIED: exc.ConnectionError,
    grpc.StatusCode.UNAUTHENTICATED: exc.ConnectionError,
    grpc.StatusCode.CANCELLED: exc.IVVError,
    grpc.StatusCode.ABORTED: exc.TestError,
}


def open_channel(address: str, *, options: list[tuple[str, Any]] | None = None) -> grpc.Channel:
    """Open a plaintext gRPC channel.

    TLS is intentionally not configured in v1 — IV&V runs on a closed,
    trusted lab subnet. The ``options`` seam is left so future versions can
    add credentials, interceptors, keepalive tuning, etc., without touching
    callers.
    """
    if not address:
        raise exc.ConnectionError("address must be a non-empty 'host:port' string")
    if ":" not in address:
        raise exc.ConnectionError(f"address must include a port: {address!r}")
    return grpc.insecure_channel(address, options=options or [])


def _translate_rpc_error(rpc_err: grpc.RpcError) -> exc.IVVError:
    code: grpc.StatusCode = rpc_err.code() if hasattr(rpc_err, "code") else grpc.StatusCode.UNKNOWN
    detail: str | None = rpc_err.details() if hasattr(rpc_err, "details") else str(rpc_err)
    cls = _STATUS_TO_EXC.get(code, exc.IVVError)
    msg = f"{code.name if code else 'UNKNOWN'}: {detail or ''}"
    return cls(msg)


def call_unary(stub_method: Callable[..., T], request: Any, *, timeout: float | None = None) -> T:
    """Invoke a unary RPC, translating gRPC errors to SDK exceptions."""
    try:
        return stub_method(request, timeout=timeout)
    except grpc.RpcError as rpc_err:
        raise _translate_rpc_error(rpc_err) from rpc_err


def call_stream(
    stub_method: Callable[..., Iterator[T]],
    request: Any,
    *,
    timeout: float | None = None,
) -> Iterator[T]:
    """Iterate a server-streaming RPC, translating gRPC errors to SDK exceptions.

    The returned generator must be consumed (or explicitly closed) for the
    underlying gRPC call to release resources.
    """
    try:
        call = stub_method(request, timeout=timeout)
    except grpc.RpcError as rpc_err:
        raise _translate_rpc_error(rpc_err) from rpc_err
    try:
        yield from call
    except grpc.RpcError as rpc_err:
        raise _translate_rpc_error(rpc_err) from rpc_err
    finally:
        with suppress(Exception):
            call.cancel()  # type: ignore[attr-defined]


def handshake_modules(modules: list[Any]) -> None:
    """Verify every advertised module's version is within the SDK's support
    window. Raises :class:`ConnectionError` if any module is too new.
    """
    too_new: list[str] = []
    for m in modules:
        if int(getattr(m, "version", 1)) > __contracts_version__:
            too_new.append(f"{m.id}=v{m.version}")
    if too_new:
        joined = ", ".join(too_new)
        raise exc.ConnectionError(
            f"peer advertises modules with contract versions newer than this SDK "
            f"supports (max v{__contracts_version__}): {joined}. "
            "Upgrade zion-sdk to match."
        )
