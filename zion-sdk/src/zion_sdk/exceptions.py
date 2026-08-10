"""IV&V SDK exception hierarchy.

All exceptions inherit from :class:`IVVError`. No raw gRPC or protobuf
exception ever escapes the public SDK surface — :mod:`zion_sdk._channel`
translates every error path into one of these.
"""
from __future__ import annotations


class IVVError(Exception):
    """Base class for every error raised by the IV&V SDK."""


class ConnectionError(IVVError):
    """The SDK could not reach the peer, the channel dropped mid-call, or the
    peer reported an incompatible contract version on connect."""


class PeripheralNotFound(IVVError):
    """The requested peripheral (module) is not present in the peer's registry."""


class NotSupported(IVVError):
    """The peripheral does not advertise this capability / test mode."""


class ConfigError(IVVError):
    """The peer rejected the configuration with an INVALID_ARGUMENT status."""


class TestError(IVVError):
    """A test execution reported a hard failure (ERROR / ABORTED status).

    Note: a test that completes with ``FAIL`` is NOT an exception — that is a
    valid result. Only ``ERROR`` / ``ABORTED`` raise. ``TIMEOUT`` raises
    :class:`TimeoutError`.
    """

    def __init__(self, message: str, *, status: str | None = None) -> None:
        super().__init__(message)
        self.status = status


class TimeoutError(IVVError):
    """A test exceeded its deadline or the peer reported TIMEOUT status."""


__all__ = [
    "ConfigError",
    "ConnectionError",
    "IVVError",
    "NotSupported",
    "PeripheralNotFound",
    "TestError",
    "TimeoutError",
]
