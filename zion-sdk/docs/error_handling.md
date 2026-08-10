# Error handling

The SDK promises that **no raw gRPC or protobuf exception escapes**.
Every error path is translated to a subclass of `IVVError`.

## The hierarchy

```
IVVError                  ← catch-all base
├── ConnectionError       ← channel down, handshake mismatch
├── PeripheralNotFound    ← unknown module id
├── NotSupported          ← capability not advertised
├── ConfigError           ← peer rejected configuration
├── TestError             ← peer reported ERROR / ABORTED
└── TimeoutError          ← peer reported TIMEOUT or deadline exceeded
```

## What raises what

| Trigger                                              | Exception           |
|------------------------------------------------------|---------------------|
| `connect()` to unreachable address                    | `ConnectionError`   |
| Peer module advertises `version > __contracts_version__` | `ConnectionError`   |
| `device.peripheral("nope")`                           | `PeripheralNotFound`|
| Peer returns gRPC `INVALID_ARGUMENT`                  | `ConfigError`       |
| Peer returns gRPC `UNIMPLEMENTED`                     | `NotSupported`      |
| Peer returns gRPC `NOT_FOUND`                         | `PeripheralNotFound`|
| Peer returns gRPC `DEADLINE_EXCEEDED`                 | `TimeoutError`      |
| Peer returns `TestStatus.TIMEOUT` in envelope         | `TimeoutError`      |
| Peer returns `TestStatus.ERROR` / `ABORTED`           | `TestError`         |
| Peer returns `TestStatus.FAIL`                        | *no exception*      |
| Peer returns `TestStatus.FAIL` + `raise_on_failure=True` | `TestError`      |

## A FAIL is not an exception

`TestStatus.FAIL` is a valid result — a test ran and produced a result
that says "fail". The SDK returns it normally; check
`result.results[i].output.status` and react accordingly. Only `ERROR`,
`ABORTED`, and `TIMEOUT` raise — those mean the test could not produce
a meaningful pass-or-fail answer.

If you want a single style across your script, pass
`raise_on_failure=True` to `run_oneshot()`:

```python
try:
    dev.peripheral("imu").run_oneshot(raise_on_failure=True)
except ivv.TestError as e:
    print("IMU failed:", e, "(status:", e.status, ")")
```

## Stream cancellation

For `monitor()` and `arm_event()`, the underlying gRPC stream is
cancelled cleanly when the generator is closed (via `break`, `.close()`,
or GC).

```python
for s in dev.peripheral("imu").monitor(period_ms=100):
    if condition:
        break  # cancels the stream
```

For `start_long_running()`, call `stop_long_running()` explicitly to
both cancel the stream and drain the background thread.
