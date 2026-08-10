"""In-process fake ``HalService`` for SDK tests.

This deliberately uses the generated ``_proto`` stubs directly so the tests
exercise the real wire format end-to-end.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from concurrent import futures
from typing import Any

import grpc
from google.protobuf import any_pb2

from zion_sdk._proto import common_pb2, hal_service_pb2, hal_service_pb2_grpc
from zion_sdk._proto.modules import cpu_pb2, imu_pb2


def _pass_envelope(module_id: str, payload_msg: Any, *, mode: int) -> Any:
    env = common_pb2.ResultEnvelope(
        module_id=module_id,
        module_version="1.0.0",
        mode=mode,
        status=common_pb2.TEST_STATUS_PASS,
    )
    any_msg = any_pb2.Any()
    any_msg.Pack(payload_msg, type_url_prefix="type.googleapis.com/")
    env.payload.CopyFrom(any_msg)
    return env


def _imu_result_pb(*, accel_x: float = 0.1) -> imu_pb2.Result:
    r = imu_pb2.Result()
    tr = r.results.add()
    tr.module_id = "imu"
    tr.test_id = "accel_read"
    tr.name = "accel_read"
    tr.sequence = 1
    tr.output.status = common_pb2.TEST_STATUS_PASS
    tr.output.metrics["accel_x"].double_value = accel_x
    tr.output.metrics["accel_y"].double_value = 0.0
    tr.output.metrics["accel_z"].double_value = 9.8
    return r


def _cpu_result_pb() -> cpu_pb2.Result:
    r = cpu_pb2.Result()
    tr = r.results.add()
    tr.module_id = "cpu"
    tr.test_id = "load_avg"
    tr.name = "load_avg"
    tr.sequence = 1
    tr.output.status = common_pb2.TEST_STATUS_PASS
    tr.output.metrics["load_1m"].double_value = 0.42
    return r


class FakeHalService(hal_service_pb2_grpc.HalServiceServicer):
    """A configurable fake HAL implementation."""

    def __init__(self) -> None:
        self.fail_mode: str | None = None  # e.g. "config", "test_error", "timeout"
        self.peripheral_versions: dict[str, int] = {}
        self.last_requests: list[Any] = []
        self.pause_calls = 0
        self.resume_calls = 0
        self.stop_calls = 0

    # ----- registry -----

    def ListModules(self, request: Any, context: grpc.ServicerContext) -> Any:  # noqa: N802
        modules = [
            hal_service_pb2.ModuleInfo(
                id="imu",
                proto_package="hal.modules.imu",
                config_type="hal.modules.imu.Config",
                result_type="hal.modules.imu.Result",
                version=self.peripheral_versions.get("imu", 1),
                status="active",
            ),
            hal_service_pb2.ModuleInfo(
                id="cpu",
                proto_package="hal.modules.cpu",
                config_type="hal.modules.cpu.Config",
                result_type="hal.modules.cpu.Result",
                version=self.peripheral_versions.get("cpu", 1),
                status="active",
            ),
        ]
        return hal_service_pb2.ListModulesResponse(modules=modules)

    # ----- single-shot -----

    def RunSingleShot(self, request: Any, context: grpc.ServicerContext) -> Any:  # noqa: N802
        self.last_requests.append(request)
        if self.fail_mode == "config":
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("bad config")
            return common_pb2.ResultEnvelope()
        if self.fail_mode == "not_found":
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("no such module")
            return common_pb2.ResultEnvelope()
        if self.fail_mode == "test_error":
            return common_pb2.ResultEnvelope(
                module_id=request.module_id,
                status=common_pb2.TEST_STATUS_ERROR,
                error_message="oh no",
            )
        if self.fail_mode == "test_timeout":
            return common_pb2.ResultEnvelope(
                module_id=request.module_id,
                status=common_pb2.TEST_STATUS_TIMEOUT,
                error_message="too slow",
            )
        if self.fail_mode == "test_fail":
            env = common_pb2.ResultEnvelope(
                module_id=request.module_id,
                status=common_pb2.TEST_STATUS_FAIL,
                error_message="failed gracefully",
            )
            payload = _imu_result_pb() if request.module_id == "imu" else _cpu_result_pb()
            any_msg = any_pb2.Any()
            any_msg.Pack(payload, type_url_prefix="type.googleapis.com/")
            env.payload.CopyFrom(any_msg)
            return env
        payload = _imu_result_pb() if request.module_id == "imu" else _cpu_result_pb()
        return _pass_envelope(
            request.module_id, payload, mode=common_pb2.SINGLE_SHOT
        )

    # ----- streams -----

    def StartMonitoring(self, request: Any, context: grpc.ServicerContext) -> Iterator[Any]:  # noqa: N802
        self.last_requests.append(request)
        cycles = 3 if not request.common.run_forever else 5
        for i in range(cycles):
            if not context.is_active():
                break
            yield _pass_envelope(
                request.module_id,
                _imu_result_pb(accel_x=0.1 + 0.1 * i),
                mode=common_pb2.MONITORING,
            )
            time.sleep(0.001)

    def StartEventBased(self, request: Any, context: grpc.ServicerContext) -> Iterator[Any]:  # noqa: N802
        self.last_requests.append(request)
        for _ in range(2):
            if not context.is_active():
                break
            yield _pass_envelope(
                request.module_id, _imu_result_pb(), mode=common_pb2.EVENT_BASED
            )

    def StartLongTerm(self, request: Any, context: grpc.ServicerContext) -> Iterator[Any]:  # noqa: N802
        self.last_requests.append(request)
        for i in range(4):
            if not context.is_active():
                break
            yield _pass_envelope(
                request.module_id,
                _imu_result_pb(accel_x=float(i)),
                mode=common_pb2.LONG_TERM,
            )
            time.sleep(0.005)

    # ----- lifecycle -----

    def Stop(self, request: Any, context: grpc.ServicerContext) -> Any:  # noqa: N802
        self.stop_calls += 1
        return hal_service_pb2.StopResponse(accepted=True, message="stopped")

    def Pause(self, request: Any, context: grpc.ServicerContext) -> Any:  # noqa: N802
        self.pause_calls += 1
        return hal_service_pb2.PauseResponse(accepted=True)

    def Resume(self, request: Any, context: grpc.ServicerContext) -> Any:  # noqa: N802
        self.resume_calls += 1
        return hal_service_pb2.ResumeResponse(accepted=True)


class FakeServer:
    """Manages the lifecycle of a fake server on an ephemeral port."""

    def __init__(self) -> None:
        self.servicer = FakeHalService()
        self._server: grpc.Server | None = None
        self._port: int = 0

    def start(self) -> str:
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        hal_service_pb2_grpc.add_HalServiceServicer_to_server(self.servicer, self._server)
        self._port = self._server.add_insecure_port("127.0.0.1:0")
        self._server.start()
        return f"127.0.0.1:{self._port}"

    def stop(self) -> None:
        if self._server is not None:
            self._server.stop(grace=0.2)
            self._server = None


# Convenience for tests that want a one-liner.
def run_in_thread(servicer: FakeHalService | None = None) -> tuple[FakeServer, str]:
    srv = FakeServer()
    if servicer is not None:
        srv.servicer = servicer
    addr = srv.start()
    return srv, addr
