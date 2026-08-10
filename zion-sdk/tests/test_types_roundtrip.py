"""Tests for the generated dataclass round-trip and JSON serialisation."""
from __future__ import annotations

import json

from zion_sdk._proto import common_pb2
from zion_sdk.types import common as common_types


def test_test_result_roundtrip() -> None:
    pb = common_pb2.TestResult(module_id="imu", test_id="t", name="accel_read")
    pb.output.status = common_pb2.TEST_STATUS_PASS
    pb.output.metrics["x"].double_value = 1.5
    pb.output.metrics["calibrated"].bool_value = True
    dc = common_types.TestResult.from_proto(pb)
    assert dc.module_id == "imu"
    assert dc.output.metrics["x"].double_value == 1.5
    # round-trip preserves oneof arm
    pb2 = dc.to_proto()
    assert pb2.output.metrics["x"].double_value == 1.5
    assert pb2.output.metrics["calibrated"].bool_value is True


def test_to_json_serialises_enum_names() -> None:
    pb = common_pb2.TestResult(module_id="imu")
    pb.output.status = common_pb2.TEST_STATUS_PASS
    dc = common_types.TestResult.from_proto(pb)
    payload = json.loads(dc.to_json())
    assert payload["output"]["status"] == "TEST_STATUS_PASS"


def test_to_dict_is_jsonable() -> None:
    pb = common_pb2.TestResult(module_id="imu")
    dc = common_types.TestResult.from_proto(pb)
    d = dc.to_dict()
    json.dumps(d)  # must not raise


def test_metric_value_resolves_oneof_arms() -> None:
    """A zero double is a *real* value, not 'unset'. ``metric_value`` must
    return 0.0 in that case, not fall through to ``string_value=''``."""
    import zion_sdk

    pb = common_pb2.TestResult(module_id="imu", test_id="t", name="accel_read")
    pb.output.metrics["accel_y"].double_value = 0.0   # legitimate zero
    pb.output.metrics["accel_x"].double_value = 0.1
    pb.output.metrics["calibrated"].bool_value = True
    pb.output.metrics["label"].string_value = "ok"
    pb.output.metrics["count"].int_value = 7
    dc = common_types.TestResult.from_proto(pb)

    m = dc.output.metrics
    assert zion_sdk.metric_value(m["accel_y"]) == 0.0
    assert m["accel_y"]._oneofs == {"value": "double_value"}
    assert zion_sdk.metric_value(m["accel_x"]) == 0.1
    assert zion_sdk.metric_value(m["calibrated"]) is True
    assert zion_sdk.metric_value(m["label"]) == "ok"
    assert zion_sdk.metric_value(m["count"]) == 7


def test_metric_value_returns_none_for_unset_oneof() -> None:
    """An unconstructed TypedValue (no arm ever set) yields ``None``."""
    import zion_sdk
    from zion_sdk.types.common import TypedValue

    assert zion_sdk.metric_value(TypedValue()) is None
