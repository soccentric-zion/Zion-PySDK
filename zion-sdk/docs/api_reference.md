# API reference For the full per-symbol reference, see the docstrings — every public
class and method has one, and `mypy --strict` keeps the type
annotations honest. ## `zion_sdk.connect(address, *, timeout=5.0)` → `Device` Open a plaintext gRPC channel to `address` (`"host:port"`) and perform
the `ListModules` handshake. Raises `ConnectionError` if the channel
can't be opened, if the handshake times out, or if the peer advertises a
module with a contract version newer than `zion_sdk.__contracts_version__`. ## `class Device` * `address: str` — the `host:port` this device is connected to.
* `peripherals → list[str]` — active module ids.
* `module_info(id) → ModuleInfo` — the full registry entry (raises `PeripheralNotFound`).
* `peripheral(id) → Peripheral` — handle factory.
* `close` — close the channel. Idempotent. Implicit on `__exit__`.
* Context-manager support: `with ivv.connect(...) as dev:`. ## `class Peripheral` * `id: str` — wire id.
* `info: ModuleInfo` — registry entry.
* `capabilities → set[str]` — supported capability tags.
* **Test modes:** * `run_oneshot(*, tests=None, raise_on_failure=False, **config) → Result` * `self_test → Result` (alias for `run_oneshot(tests=[])`) * `monitor(period_ms, duration_s=None, **config) → Iterator[Result]` * `arm_event(*, test_name="", expected_pass=True, expression="", **config) → Iterator[Result]` * `start_long_running(*, interval_ms=1000, duration_s=None, tests=None, **config) → LongRunningSession` * `query_long_running(*, block=True, timeout=None) → Result | None` * `stop_long_running` — idempotent.
* **Lifecycle:** `pause → bool`, `resume → bool`. The `**config` kwargs are forwarded to the module-specific `Config`
dataclass. Any field name on `hal.modules.<id>.Config` is acceptable. ## Result dataclasses Every message in the HAL proto contract is generated as a Python
`@dataclass`: * `.from_proto(pb_msg)` — classmethod converting a wire message.
* `.to_proto` — return a fresh pb message.
* `.to_dict` — JSON-friendly dict (enums become their `.name`, bytes become base64).
* `.to_json(indent=None)` — convenience over `.to_dict`. `TypedValue` is a oneof; reading an unset arm returns the proto default
(empty string, 0, etc.). The arm set on `from_proto` survives a
round-trip through `to_proto`. ## Exceptions ```
IVVError
├── ConnectionError
├── PeripheralNotFound
├── NotSupported
├── ConfigError
├── TestError
└── TimeoutError
``` `TestError` carries a `.status` attribute (the original
`TEST_STATUS_*` name). ## Constants * `zion_sdk.__version__` — SemVer string.
* `zion_sdk.__contracts_version__` — integer, max HAL contract version supported by this SDK build.
