# Quickstart

## Install

```bash
pip install zion-sdk
```

The SDK works on Python 3.10+. The wheel bundles all generated proto
bindings, so you do not need `grpcio-tools` at runtime.

## Connect

```python
import zion_sdk as ivv

dev = ivv.connect("192.168.1.50:50051")
# ...do work...
dev.close()
```

Or as a context manager:

```python
with ivv.connect("192.168.1.50:50051") as dev:
    print(dev.peripherals())
```

## Discover peripherals

```python
with ivv.connect("192.168.1.50:50051") as dev:
    for pid in dev.peripherals():
        info = dev.module_info(pid)
        print(pid, info.proto_package, "v", info.version)
```

## Run a one-shot test

```python
imu = dev.peripheral("imu")
result = imu.run_oneshot()
for tr in result.results:
    print(tr.name, tr.output.status.name)
```

## Stream monitoring data

```python
for snapshot in dev.peripheral("imu").monitor(period_ms=100, duration_s=2.0):
    print(snapshot.results[0].output.metrics["accel_x"].double_value)
```

## Arm an event trigger

```python
for event in dev.peripheral("imu").arm_event(expression="accel_x > 0.5"):
    print("fired!")
    break
```

## Long-running test in the background

```python
session = dev.peripheral("cpu").start_long_running(interval_ms=500, duration_s=60)
try:
    while True:
        latest = dev.peripheral("cpu").query_long_running(timeout=1.0)
        if latest is None:
            break
        print(latest.results[0].output.status.name)
finally:
    dev.peripheral("cpu").stop_long_running()
```

## Reading metrics — the explicit shape

The Acadia HAL contract carries metrics inside a generic map of
`TypedValue` oneofs:

```python
metric = tr.output.metrics["accel_x"]
# metric.double_value, metric.int_value, metric.bool_value, metric.string_value
```

The SDK exposes those fields verbatim rather than synthesising a typed
shortcut. This keeps the dataclasses loss-less and makes the SDK
automatically support new modules added to the registry without code
changes here.

If you want a friendlier view, build a one-liner in your code:

```python
def value_of(tv):
    for arm in ("double_value", "int_value", "bool_value", "string_value"):
        v = getattr(tv, arm)
        if v not in (0, 0.0, False, ""):
            return v
    return None
```
