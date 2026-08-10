# Changelog

All notable changes to `zion-sdk` are documented here.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased / 0.2.0]

### Changed
* **Breaking rename**: the distribution and import package have been renamed
  from `acadia-sdk` / `acadia_sdk` to `zion-sdk` / `zion_sdk`. The SDK
  is the Zion-Project leaf, so the package name now reflects that.

### Added
* **Deprecation shim**: `import acadia_sdk` still works and emits a
  `DeprecationWarning` directing callers to `import zion_sdk`. The shim
  re-exports the full public surface of `zion_sdk` (mirroring
  `zion_sdk.__all__`). The shim will be removed in a future release;
  migrate imports to `zion_sdk` before then.

### Migration
Replace `import acadia_sdk` / `from acadia_sdk import ...` with the
`zion_sdk` equivalent. No behavioural changes are expected for existing
callers during the deprecation window.

## [0.1.0] — Initial release

### Added
* `ivv.connect(address)` opens a plaintext gRPC channel and performs the
  `ListModules` handshake. The handshake verifies every advertised
  module's `version` is `<= zion_sdk.__contracts_version__` and raises
  `ConnectionError` otherwise.
* `Device` exposes `.peripherals()`, `.module_info(id)`, `.peripheral(id)`,
  and supports use as a context manager.
* `Peripheral` exposes the five HAL test modes — `run_oneshot`, `monitor`,
  `arm_event`, `start_long_running` / `query_long_running` /
  `stop_long_running`, plus `self_test`, `pause`, `resume`, and
  `capabilities()`.
* `Peripheral.monitor()` and `Peripheral.arm_event()` are generators —
  the underlying gRPC stream is cancelled when the generator is closed
  or garbage-collected.
* `Peripheral.start_long_running()` runs the stream on a background worker
  thread, draining into a queue consumed by `query_long_running()`.
* Generated dataclasses for every message in the `hal`, `hal.common`,
  and `hal.modules.*` proto packages (51 modules). Each dataclass has
  `.from_proto(pb)`, `.to_proto()`, `.to_dict()`, and `.to_json()`.
  Enums round-trip as `IntEnum` and serialise to their canonical names
  in JSON. `oneof` fields preserve their active arm across round-trips.
* `Timestamp` and `Duration` ergonomic helpers (`.to_datetime()`,
  `.total_seconds()`).
* `IVVError` taxonomy: `ConnectionError`, `PeripheralNotFound`,
  `NotSupported`, `ConfigError`, `TestError`, `TimeoutError`. No raw
  `grpc.RpcError` escapes the public surface.
* Fake in-process `HalService` (`tests/fakes/fake_server.py`) for offline
  testing.
* Examples 01–07, plus `make` targets for generation, build, test, lint,
  and typecheck.

### Decisions
* **Wire transport**: The SDK speaks `hal.HalService` against
  `acadia-server` (NOT the Server↔Client `acadia.stream.ClientService`
  channel). This makes it a peer to the C++ `acadia-client` runner, not
  a client of it.
* **Result surface**: Metrics are exposed verbatim through the
  descriptor-driven dataclasses (`tr.output.metrics["accel_x"].double_value`)
  rather than via a synthesised typed shortcut like `sample.accel_x`. This
  keeps the SDK loss-less and contract-evolution-safe; convenience layers
  can be added in 0.2 without breaking 0.1 consumers.
* **Single-test-at-a-time per device** is enforced by an internal mutex.

### Known limitations
* TLS is not configured — plaintext on tcp/50051 is the only supported
  transport in v1. The channel-construction helper has a hook for
  future credentials.
* `pause()` / `resume()` are forwarded to the peer, but on the current
  Acadia HAL implementation they are advisory (see
  `integration/contract_reconciliation.md` CM-11).
* Per-module capability bits are not yet advertised by the HAL contract;
  every peripheral therefore reports the same capability set. A future
  contract version that exposes a typed `capabilities` field on
  `ModuleInfo` will refine `Peripheral.capabilities()` automatically.
