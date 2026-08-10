# IV&V Python SDK (`zion-sdk`) A Pythonic, statically-typed client for the [Acadia HAL](../Acadia-HAL)
`HalService` gRPC interface, designed for IV&V customers writing test
benches, certification scripts, and lab automation. * **One import** — `import zion_sdk as ivv`
* **One call to connect** — `ivv.connect("192.168.1.50:50052")`
* **One handle per peripheral** — `dev.peripheral("imu").run_oneshot`
* **All five HAL test modes** — single-shot, monitoring, event-based, long-running, plus pause/resume/stop.
* **Strict types** — generated dataclasses with `.to_dict`/ `.to_json` for every message in the HAL contract; `mypy --strict` clean.
* **No raw protobuf, no raw gRPC** — every exception path is translated to the SDK's `IVVError` taxonomy. > **Connection model:** The SDK connects **directly to the Acadia Client
> (`acadia-client`) on the target board**, not to the Acadia Server.
> The default HalService port is **50052** (configurable via
> `hal_service_port` in `client.conf`). > The Client hosts the `HalService` gRPC endpoint as an always-on inbound
> listener. All test execution flows Client → HAL API → HAL library.
> This path is **off-the-record** — no data is written to the Server's
> database. Use the Server/Dashboard path for on-the-record runs.
>
> Typical address: `"<target-board-ip>:50052"` --- ## Five-minute example ```python
import zion_sdk as ivv # Connect to the HalService running on the target board (Acadia Client).
# Default port is 50052; set hal_service_port in client.conf to change it.
with ivv.connect("192.168.1.50:50052") as dev: print("Peripherals:", dev.peripherals) imu = dev.peripheral("imu") # 1. Run all tests once and read the metrics result = imu.run_oneshot for tr in result.results: print(tr.name, tr.output.status.name) ax = tr.output.metrics["accel_x"].double_value print(f" accel_x = {ax:+.3f} g") # 2. Stream samples for two seconds for sample in imu.monitor(period_ms=100, duration_s=2.0): ax = sample.results[0].output.metrics["accel_x"].double_value print(f" live accel_x = {ax:+.3f} g") # 3. Arm an event trigger for event in imu.arm_event(expression="accel_x > 0.5"): print("Threshold crossed:", event.results[0].name) break # 4. Run a long-term test in the background session = imu.start_long_running(interval_ms=500, duration_s=60) while True: snapshot = imu.query_long_running(block=True, timeout=1.0) if snapshot is None: break print("latest:", snapshot.results[0].output.status.name) imu.stop_long_running
``` A note on result shape: the HAL contract carries metrics inside
`TestResult.output.metrics`, where each value is a `TypedValue` oneof
(`double_value`, `int_value`, `bool_value`, `string_value`). The SDK
exposes those fields verbatim rather than synthesising a typed
`sample.accel_x` shortcut — this keeps the dataclasses lossless and the
contract evolution-safe. See `docs/quickstart.md` for the rationale. --- ## Install The SDK targets Python 3.10+. ```bash
pip install zion-sdk
``` Editable install from this checkout: ```bash
cd zion-sdk
pip install -e .[dev]
``` The generated proto bindings ship inside the wheel; you do **not** need
`grpcio-tools` at runtime. You only need it (and a copy of
`Acadia-HAL/protos/`) if you want to regenerate the bindings (see
`make gen`). --- ## What runs on the wire The SDK speaks to **`acadia-server`** (Acadia's gRPC daemon) over the
stable per-mode contract `hal.HalService`, default plaintext on
`tcp/50051`. This is the same interface `acadia-client` would use; the
SDK is the Python alternative to `acadia-client`'s C++ runner. Specifically: | SDK method | RPC |
|------------------------------------|--------------------|
| `Peripheral.run_oneshot` | `RunSingleShot` |
| `Peripheral.self_test` | `RunSingleShot` (empty `test_names`) |
| `Peripheral.monitor` | `StartMonitoring` |
| `Peripheral.arm_event` | `StartEventBased` |
| `Peripheral.start_long_running` | `StartLongTerm` |
| `Peripheral.stop_long_running` | `Stop` |
| `Peripheral.pause`/ `resume` | `Pause`/ `Resume` |
| `Device.peripherals` | `ListModules` | Per-module `Config` is packed into `google.protobuf.Any` with type URL
`type.googleapis.com/hal.modules.<id>.Config`; the response payload
inside `ResultEnvelope` is unpacked to the corresponding `Result`
dataclass. --- ## Public surface ```python
ivv.connect(address: str, *, timeout: float | None = 5.0) -> Device
ivv.Device .address: str .peripherals -> list[str] .module_info(id) -> ModuleInfo .peripheral(id) -> Peripheral .close/ __enter__/ __exit__
ivv.Peripheral .id: str .info: ModuleInfo .capabilities -> set[str] .run_oneshot(*, tests=None, raise_on_failure=False, **config) -> Result .self_test -> Result .monitor(period_ms, duration_s=None, **config) -> Iterator[Result] .arm_event(*, test_name="", expression="", **config) -> Iterator[Result] .start_long_running(*, interval_ms=1000, duration_s=None, **config) -> LongRunningSession .query_long_running(*, block=True, timeout=None) -> Result | None .stop_long_running .pause -> bool .resume -> bool
ivv.IVVError ← every exception inherits from this ivv.ConnectionError ← channel down, handshake mismatch ivv.PeripheralNotFound ← unknown module id ivv.NotSupported ← capability not advertised ivv.ConfigError ← peer rejected configuration ivv.TestError ← peer reported ERROR/ ABORTED ivv.TimeoutError ← peer reported TIMEOUT or deadline hit
ivv.__version__ "0.1.0"
ivv.__contracts_version__ 1 ← matches Acadia-HAL/protos contract version
``` `FAIL` is a normal status, not an exception. Pass `raise_on_failure=True`
to `run_oneshot` if you want it to raise. --- ## Error model | gRPC status | SDK exception |
|-----------------------|----------------------|
| `UNAVAILABLE` | `ConnectionError` |
| `DEADLINE_EXCEEDED` | `TimeoutError` |
| `NOT_FOUND` | `PeripheralNotFound` |
| `INVALID_ARGUMENT` | `ConfigError` |
| `FAILED_PRECONDITION` | `ConfigError` |
| `UNIMPLEMENTED` | `NotSupported` |
| `ABORTED` | `TestError` |
| other | `IVVError` | Status enums in test envelopes (`TEST_STATUS_TIMEOUT`,
`TEST_STATUS_ERROR`, `TEST_STATUS_ABORTED`) are translated symmetrically. --- ## Versioning `zion_sdk.__contracts_version__` declares the maximum HAL contract version
this SDK can talk to. On `connect`, the SDK calls `ListModules` and
verifies every advertised module's `version` field is `<=` that bound;
if any module is newer, `ConnectionError` is raised and you should
upgrade the SDK. `zion_sdk.__version__` follows [SemVer](https://semver.org). The
contracts-version field bumps independently of the SDK release version. --- ## Threading and concurrency * **One test at a time per `Device`.** Concurrent test-mode calls on the same device serialise on an internal lock. Open a second `Device` to parallelise against a second peer.
* **Long-running sessions run on a worker thread** that produces results into a queue consumed by `query_long_running`.
* **`Device` is fork-unsafe.** Create it after `os.fork` if you need to. --- ## Examples See [examples/](examples) — seven numbered walkthroughs: 1. `01_connect_and_discover.py` — `ivv.connect` + `dev.peripherals`
2. `02_imu_oneshot.py` — Single-shot test, reading metrics
3. `03_imu_monitor_stream.py` — Streaming monitoring loop
4. `04_event_trigger.py` — Event-based mode
5. `05_long_running_test.py` — Long-running session lifecycle
6. `06_self_test_all.py` — Run every peripheral's self-test
7. `07_build_an_app.py` — A small bench tool emitting JSON --- ## Developer workflow ```bash
make gen # regenerate proto stubs + dataclasses from Acadia-HAL/protos
make build # build sdist + wheel
make test # run pytest with coverage
make lint # ruff
make typecheck # mypy --strict
``` --- ## License Apache-2.0. See [LICENSE](LICENSE).
