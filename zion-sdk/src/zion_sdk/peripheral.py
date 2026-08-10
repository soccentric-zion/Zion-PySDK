"""The :class:`Peripheral` handle: maps a HAL module onto Pythonic test-mode
methods. Calling an unsupported mode raises :class:`NotSupported`.

All five test modes are wrappers around ``HalService`` RPCs:

==========================  =================================
SDK method                  Underlying RPC
==========================  =================================
``run_oneshot``             ``RunSingleShot`` (unary)
``self_test``               ``RunSingleShot`` with ``test_names=[]``
``monitor``                 ``StartMonitoring`` (server-stream)
``arm_event``               ``StartEventBased`` (server-stream)
``start_long_running``      ``StartLongTerm`` (server-stream, background)
``query_long_running``      latest queued batch
``stop_long_running``       ``Stop`` + drain
``pause`` / ``resume``      ``Pause`` / ``Resume``
==========================  =================================
"""
from __future__ import annotations

import queue
import threading
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from zion_sdk import _convert, exceptions
from zion_sdk._proto import hal_service_pb2
from zion_sdk.types import common as common_types
from zion_sdk.types import hal_service as hal_types

if TYPE_CHECKING:
    from zion_sdk.client import Device

# Capability names mirror the test modes. Every HAL module supports all four,
# plus Stop/Pause/Resume — so the set is uniform unless the contract grows
# per-module capability bits in the future.
_DEFAULT_CAPABILITIES = frozenset({
    "oneshot",
    "long_running",
    "monitor",
    "event",
    "self_test",
    "pause",
    "resume",
    "stop",
})


def _is_terminal_error(status: common_types.TestStatus) -> bool:
    return status in (
        common_types.TestStatus.TEST_STATUS_ERROR,
        common_types.TestStatus.TEST_STATUS_ABORTED,
    )


def _check_envelope_status(env: Any) -> None:
    status = env.status
    if status == common_types.TestStatus.TEST_STATUS_TIMEOUT:
        raise exceptions.TimeoutError(env.error_message or "test timed out")
    if _is_terminal_error(status):
        raise exceptions.TestError(
            env.error_message or f"test reported {status.name}",
            status=status.name,
        )


def _build_common_config(
    interval_ms: int | None = None,
    duration_ms: int | None = None,
    run_forever: bool = False,
    poll_interval_ms: int | None = None,
) -> Any:
    from zion_sdk._proto import common_pb2

    return common_pb2.CommonConfig(
        interval_ms=interval_ms or 0,
        duration_ms=duration_ms or 0,
        run_forever=run_forever,
        poll_interval_ms=poll_interval_ms or 0,
    )


def _build_module_config(module_id: str, **config_kwargs: Any) -> Any:
    """Build the ``google.protobuf.Any`` carrying a module's Config message."""
    cfg_cls = _convert.load_config_class(module_id)
    # ``test_names`` is the standard per-module configuration knob; allow either
    # ``tests=[...]`` or ``test_names=[...]`` to keep the surface friendly.
    if "tests" in config_kwargs and "test_names" not in config_kwargs:
        config_kwargs["test_names"] = config_kwargs.pop("tests")
    try:
        cfg = cfg_cls(**config_kwargs)
    except TypeError as e:
        raise exceptions.ConfigError(
            f"invalid config for module {module_id!r}: {e}"
        ) from e
    return cfg.to_proto()


# ---------------------------------------------------------------------------
# Long-running session handle
# ---------------------------------------------------------------------------


@dataclass
class LongRunningSession:
    """Handle for a backgrounded :meth:`Peripheral.start_long_running` run.

    The peripheral's :meth:`Peripheral.query_long_running` and
    :meth:`Peripheral.stop_long_running` operate on the active session.
    """

    module_id: str
    session_id: str = ""
    _queue: queue.Queue[Any] | None = None
    _thread: threading.Thread | None = None
    _stop_event: threading.Event | None = None
    _device: Device | None = None
    _latest: Any | None = None
    _terminal_exc: BaseException | None = None

    def __repr__(self) -> str:
        return f"LongRunningSession(module={self.module_id!r}, session={self.session_id!r})"


class Peripheral:
    """A handle to one HAL module on a :class:`Device`.

    Construct via :meth:`Device.peripheral`. Thread-safety mirrors the
    underlying :class:`Device`: at most one test method may be active at a
    time per device (enforced by an internal mutex).
    """

    def __init__(self, device: Device, info: hal_types.ModuleInfo) -> None:
        self._device = device
        self._info = info
        self._long_running: LongRunningSession | None = None

    # ----- introspection -----

    @property
    def id(self) -> str:
        """The module's wire id (e.g. ``"imu"``, ``"cpu"``)."""
        return str(self._info.id)

    @property
    def info(self) -> hal_types.ModuleInfo:
        """The full :class:`ModuleInfo` for this peripheral."""
        return self._info

    def capabilities(self) -> set[str]:
        """Return the set of capability tags this peripheral supports.

        The current Acadia contract advertises uniform per-mode support for
        every module, so every peripheral returns the same set:
        ``{"oneshot", "long_running", "monitor", "event", "self_test", "pause",
        "resume", "stop"}``. A future per-module capability field can refine this.
        """
        return set(_DEFAULT_CAPABILITIES)

    def _require(self, capability: str) -> None:
        if capability not in self.capabilities():
            raise exceptions.NotSupported(
                f"peripheral {self.id!r} does not support capability {capability!r}"
            )

    # ----- test modes -----

    def run_oneshot(
        self,
        *,
        tests: list[str] | None = None,
        interval_ms: int | None = None,
        duration_ms: int | None = None,
        timeout: float | None = None,
        raise_on_failure: bool = False,
        **module_config: Any,
    ) -> Any:
        """Run one cycle of the peripheral's tests and return the result.

        Args:
            tests: List of test names to run; empty/None runs all available tests.
            interval_ms: Optional cycle interval (single-shot largely ignores this).
            duration_ms: Optional total duration (single-shot largely ignores this).
            timeout: Per-call gRPC deadline in seconds.
            raise_on_failure: When True, treat a ``FAIL`` status as an error
                (the default is to *return* the dataclass with status=FAIL).
            **module_config: Extra fields on the module's ``Config`` message.

        Returns:
            The module-specific ``Result`` dataclass (e.g. ``imu.Result``).

        Raises:
            TestError: If the peer reported ``ERROR`` / ``ABORTED``.
            TimeoutError: If the peer reported ``TIMEOUT``, or the gRPC deadline
                elapsed.
            ConfigError: If the configuration was rejected.
        """
        self._require("oneshot")
        cfg_pb = _build_module_config(self.id, test_names=tests or [], **module_config)
        any_pb = self._pack_any(cfg_pb)
        req = hal_service_pb2.SingleShotRequest(
            module_id=self.id,
            common=_build_common_config(interval_ms, duration_ms),
            module_config=any_pb,
        )
        with self._device._serialised():
            env_pb = self._device._call("RunSingleShot", req, timeout=timeout)
        env_dc = common_types.ResultEnvelope.from_proto(env_pb)
        _check_envelope_status(env_dc)
        result = _convert.unpack_result(env_dc)
        if raise_on_failure and self._envelope_failed(env_dc):
            raise exceptions.TestError(
                f"{self.id} test reported FAIL: {env_dc.error_message}",
                status=env_dc.status.name,
            )
        return result

    def self_test(self, *, timeout: float | None = None) -> Any:
        """Run every test in this peripheral once. Returns the module ``Result``."""
        self._require("self_test")
        return self.run_oneshot(tests=[], timeout=timeout)

    def monitor(
        self,
        period_ms: int,
        duration_s: float | None = None,
        *,
        monitor_items: list[str] | None = None,
        timeout: float | None = None,
        **module_config: Any,
    ) -> Iterator[Any]:
        """Stream periodic monitoring samples from this peripheral.

        Args:
            period_ms: Interval between samples, in milliseconds.
            duration_s: Total streaming duration in seconds; ``None`` streams
                until the caller breaks out of the iterator.
            monitor_items: Names of registered monitor items the HAL should
                sample each cycle (sent as ``MonitoringParams.monitor_item_names``).
            timeout: gRPC deadline per stream message.
            **module_config: Extra fields on the module's ``Config``.

        Yields:
            One module-specific ``Result`` dataclass per cycle. The stream
            ends when ``duration_s`` elapses (the peer honours ``duration_ms``
            and closes its side), when the caller breaks out of the iterator
            (the SDK cancels the underlying call), or when the peer closes
            the stream for any other reason.
        """
        self._require("monitor")
        if period_ms <= 0:
            raise exceptions.ConfigError("period_ms must be > 0")
        cfg_pb = _build_module_config(self.id, **module_config)
        any_pb = self._pack_any(cfg_pb)
        duration_ms = int((duration_s or 0) * 1000)
        from zion_sdk._proto import common_pb2

        common_pb = common_pb2.CommonConfig(
            interval_ms=period_ms,
            duration_ms=duration_ms,
            run_forever=duration_s is None,
        )
        params_pb = common_pb2.MonitoringParams(monitor_item_names=monitor_items or [])
        req = hal_service_pb2.MonitoringRequest(
            module_id=self.id,
            common=common_pb,
            monitoring=params_pb,
            module_config=any_pb,
        )
        yield from self._iter_stream("StartMonitoring", req, timeout=timeout)

    def arm_event(
        self,
        *,
        test_name: str = "",
        expected_pass: bool = True,
        expression: str = "",
        poll_interval_ms: int = 1000,
        timeout: float | None = None,
        **module_config: Any,
    ) -> Iterator[Any]:
        """Stream results as a peripheral event fires.

        Provide either ``test_name`` + ``expected_pass`` (simple form), or
        ``expression`` (freeform rule evaluated by the peer).
        """
        self._require("event")
        if not test_name and not expression:
            raise exceptions.ConfigError(
                "arm_event requires either test_name= or expression="
            )
        from zion_sdk._proto import common_pb2

        cfg_pb = _build_module_config(self.id, **module_config)
        any_pb = self._pack_any(cfg_pb)
        common_pb = common_pb2.CommonConfig(poll_interval_ms=poll_interval_ms)
        cond_pb = common_pb2.EventCondition(
            test_name=test_name,
            expected_pass=expected_pass,
            expression=expression,
        )
        req = hal_service_pb2.EventBasedRequest(
            module_id=self.id,
            common=common_pb,
            condition=cond_pb,
            module_config=any_pb,
        )
        yield from self._iter_stream("StartEventBased", req, timeout=timeout)

    def start_long_running(
        self,
        *,
        interval_ms: int = 1000,
        duration_s: float | None = None,
        tests: list[str] | None = None,
        timeout: float | None = None,
        **module_config: Any,
    ) -> LongRunningSession:
        """Kick off a long-term run in a background thread.

        Use :meth:`query_long_running` to fetch the latest result and
        :meth:`stop_long_running` to drain and close the stream.
        """
        self._require("long_running")
        if self._long_running is not None:
            raise exceptions.ConfigError(
                f"a long-running session is already active on {self.id!r}; "
                "call stop_long_running() first"
            )
        from zion_sdk._proto import common_pb2

        cfg_pb = _build_module_config(self.id, test_names=tests or [], **module_config)
        any_pb = self._pack_any(cfg_pb)
        duration_ms = int((duration_s or 0) * 1000)
        common_pb = common_pb2.CommonConfig(
            interval_ms=interval_ms,
            duration_ms=duration_ms,
            run_forever=duration_s is None,
        )
        req = hal_service_pb2.LongTermRequest(
            module_id=self.id,
            common=common_pb,
            module_config=any_pb,
        )
        q: queue.Queue[Any] = queue.Queue()
        stop_evt = threading.Event()
        session = LongRunningSession(
            module_id=self.id,
            session_id=self.id,
            _queue=q,
            _stop_event=stop_evt,
            _device=self._device,
        )

        def _pump() -> None:
            try:
                stream = self._device._stream("StartLongTerm", req, timeout=timeout)
                for env_pb in stream:
                    if stop_evt.is_set():
                        break
                    env_dc = common_types.ResultEnvelope.from_proto(env_pb)
                    session._latest = env_dc
                    q.put(env_dc)
            except BaseException as e:
                session._terminal_exc = e
            finally:
                q.put(None)  # sentinel signalling stream end

        t = threading.Thread(target=_pump, name=f"ivv-long-{self.id}", daemon=True)
        session._thread = t
        self._long_running = session
        t.start()
        return session

    def query_long_running(self, *, block: bool = True, timeout: float | None = None) -> Any:
        """Return the next result from the active long-running session.

        Args:
            block: When True, wait for the next batch. When False, return
                ``None`` immediately if no result is queued.
            timeout: Optional wait timeout in seconds when ``block=True``.
        """
        sess = self._long_running
        if sess is None:
            raise exceptions.ConfigError(
                f"no long-running session active on {self.id!r}"
            )
        assert sess._queue is not None
        try:
            env = sess._queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None
        if env is None:
            # stream ended
            if sess._terminal_exc is not None:
                exc = sess._terminal_exc
                sess._terminal_exc = None
                raise exc
            return None
        _check_envelope_status(env)
        return _convert.unpack_result(env)

    def stop_long_running(self, *, timeout: float | None = 5.0) -> None:
        """Stop the active long-running session and drain its thread."""
        sess = self._long_running
        if sess is None:
            return
        assert sess._stop_event is not None
        sess._stop_event.set()
        # Send a Stop RPC to encourage the peer to close its stream promptly.
        try:
            req = hal_service_pb2.StopRequest(module_id=self.id)
            self._device._call("Stop", req, timeout=timeout)
        except exceptions.IVVError:
            pass  # peer may have already ended the stream
        if sess._thread is not None:
            sess._thread.join(timeout=timeout or 5.0)
        self._long_running = None

    # ----- pause / resume -----

    def pause(self, *, timeout: float | None = None) -> bool:
        """Request the peer to pause this peripheral's current session.

        Returns the ``accepted`` flag from ``PauseResponse``. Note: HAL itself
        does not currently honour pause (see contract_reconciliation CM-11) —
        this is an advisory call that may no-op silently on some peers.
        """
        self._require("pause")
        req = hal_service_pb2.PauseRequest(module_id=self.id)
        resp = self._device._call("Pause", req, timeout=timeout)
        return bool(resp.accepted)

    def resume(self, *, timeout: float | None = None) -> bool:
        """Request the peer to resume this peripheral's paused session."""
        self._require("resume")
        req = hal_service_pb2.ResumeRequest(module_id=self.id)
        resp = self._device._call("Resume", req, timeout=timeout)
        return bool(resp.accepted)

    # ----- internals -----

    def _iter_stream(self, rpc_name: str, request: Any, *, timeout: float | None) -> Iterator[Any]:
        with self._stream_lock():
            stream = self._device._stream(rpc_name, request, timeout=timeout)
            for env_pb in stream:
                env_dc = common_types.ResultEnvelope.from_proto(env_pb)
                _check_envelope_status(env_dc)
                yield _convert.unpack_result(env_dc)

    @contextmanager
    def _stream_lock(self) -> Iterator[None]:
        lock = self._device._serialised()
        lock.acquire()
        try:
            yield
        finally:
            with suppress(RuntimeError):
                lock.release()

    def _envelope_failed(self, env: Any) -> bool:
        return bool(env.status == common_types.TestStatus.TEST_STATUS_FAIL)

    def _pack_any(self, pb_msg: Any) -> Any:
        from google.protobuf import any_pb2

        any_msg = any_pb2.Any()
        any_msg.Pack(pb_msg, type_url_prefix="type.googleapis.com/")
        return any_msg

    def __repr__(self) -> str:
        return f"Peripheral(id={self.id!r}, device={self._device.address!r})"
