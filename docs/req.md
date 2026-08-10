# Agent Prompt — Generate the IV&V Python SDK **You are an expert Python SDK engineer.** Your task is to build a complete, customer-ready Python SDK for the SiliconCentric IV&V platform. You have direct filesystem access to the real source repositories. Do not invent interfaces, proto definitions, peripheral types, or field names — **discover them from the actual code.** Where this prompt and the real code disagree, the real code wins; flag the disagreement in your notes. --- ## 0. Context you need The IV&V platform validates SiliconCentric embedded hardware. Its on-target architecture is three layers: - **OS** — the platform operating system/ base environment.
- **HAL** — platform-dependent C++ codebase (drivers + user-space drivers/services) that executes hardware-level test cases. Reached by Client via a C++ HAL API.
- **Client** — an application running on the target that talks to HAL via the HAL API (southbound) and to a Server via **gRPC + protobuf** (northbound). Normally the flow is: Web → Server → Client → HAL. The **Python SDK you are building replaces Server** as the caller: it is a gRPC client that speaks the **same protobuf contract to Client** that Server does. Client cannot tell the difference between Server and the SDK. **The SDK's purpose:** let a customer integrate the SiliconCentric platform into *their own* codebase and run tests — e.g., exercise an IMU — without standing up the full IV&V stack (no Server, no Web, no database). It is an *integration* tool, not a validation-with-evidence tool. Evidence/audit/persistence are explicitly NOT the SDK's job. --- ## 1. Repositories you have access to The user will point you at these. Confirm the actual paths before starting: - `OS` repo — Acadia-OS
- `HAL` repo — Acadia-HAL
- `Client` repo — Acadia-Client If a separate contracts/proto repo exists, note it. Otherwise locate the `.proto` files wherever they live (likely in or referenced by the Client repo, since Client is the gRPC/protobuf speaker). --- ## 2. Phase 1 — Review, before writing anything **Do not generate code yet.** First, read the repositories and produce a written findings report. Specifically: ### 2.1 Locate and read the protobuf contract
- Find every `.proto` file the Client uses to talk to Server.
- For each: list the messages, enums, services, and RPC methods.
- Identify which RPCs are **commands** (caller → Client) and which are **streaming** (Client → caller telemetry).
- Map each RPC to a test mode if applicable (one-shot, monitoring, event-based, long-running) and to peripheral configuration/ discovery/ lifecycle.
- Record the exact field names and types of every **sample/result message** — these become the typed Python dataclasses. ### 2.2 Review the Client code
- How does Client expose its gRPC service? (async/sync, streaming patterns, server reflection available?)
- What is the connection model — host:port, default port, any handshake/hello exchange on connect?
- How does Client identify peripherals? (string IDs like `imu0`? a discovery/enumerate RPC?)
- What is the lifecycle of a test? (configure → run → drain? open/close semantics?)
- What capabilities does a peripheral advertise, and how? (capability bitmask? per-peripheral?)
- How are errors returned? (gRPC status codes, error messages, structured error payloads?)
- How are streaming/monitoring sessions started and stopped? Backpressure? Drop reporting? ### 2.3 Review the HAL code (for understanding, not for SDK surface)
- The SDK does NOT call HAL directly. But read HAL to understand what each peripheral *is* and what its sample data *means*, so the typed dataclasses and docstrings are accurate.
- Enumerate the peripheral types that exist (IMU, motor, Ethernet, storage, camera, etc.) and what data each produces.
- Note units, ranges, and semantics for sample fields (e.g., "accel in milli-g", "temp in millidegrees C") so the SDK's typed classes can document them. ### 2.4 Review the OS repo (for environment/assumptions)
- Note anything that affects how the SDK connects (network setup, default addresses, ports, mDNS, etc.).
- Note platform/version assumptions the SDK should document. ### 2.5 Deliver the findings report
Write `SDK_FINDINGS.md` containing:
- The complete proto inventory (messages, RPCs, enums).
- The peripheral inventory with sample-field semantics.
- The connection and test-lifecycle model.
- The error model.
- **A list of open questions/ ambiguities** you need the user to resolve before building.
- **A list of any places where the real code differs from this prompt's assumptions.** **Stop here and present the findings report. Wait for the user to confirm before proceeding to Phase 2.** --- ## 3. SDK design requirements (the target you are building toward) Once findings are confirmed, build an SDK with these properties. These are binding. ### 3.1 Core ergonomics — the five-minute test
A customer must be able to test a peripheral in five lines, with no protobuf, no gRPC channels, no status codes visible: ```python
import acadia_sdk as ivv dev = ivv.connect("192.168.1.50:50051")
imu = dev.peripheral("imu0")
sample = imu.run_oneshot
print(sample.accel_x, sample.accel_y, sample.accel_z)
dev.close
``` Every design choice is judged against: *does this keep that example short and clear?* ### 3.2 Architecture (binding)
- **Synchronous/ blocking API by default.** No asyncio in the primary surface. Test code is sequential; keep it readable top-to-bottom.
- **Single device, single test at a time.** No connection pools, no concurrency abstractions, no multiplexing. One connection, one peripheral, one test.
- **Three layers:** 1. *Generated gRPC stubs* (`protoc` output) — vendored as a **private** submodule. Customers never import these. 2. *Generated typed dataclasses* — produced by your codegen step from the proto descriptors (see 3.4). One sample/result class per peripheral data type. 3. *Hand-written Pythonic SDK layer* — `connect`, `Device`, peripheral objects, exceptions. This is what the customer imports. ### 3.3 The object model
- `ivv.connect(address) -> Device` — opens the gRPC channel; returns a `Device`. Also usable as a context manager (`with ivv.connect(...) as dev:`).
- `Device.peripherals -> list[str]` — discover available peripheral IDs (via the real discovery RPC).
- `Device.peripheral(id) -> Peripheral` — returns a peripheral object that knows its capabilities and exposes only the test modes it supports.
- `Peripheral` methods map to the four test modes (use the real RPC names/semantics discovered in Phase 1): - `.run_oneshot(**config) -> <TypedSample>` - `.monitor(period_ms, duration_s=None, **config) -> Iterator[<TypedSample>]` — a Python generator yielding typed samples until duration elapses or the caller breaks. - `.arm_event(**trigger) -> Iterator[<TypedEvent>]` — yields events as they fire. - `.start_long_running(**params)`, `.query_long_running`, `.stop_long_running` — lifecycle for long tests. - `.self_test -> <TypedResult>` - `.configure(**config)` — if the real lifecycle requires explicit configure. - `.capabilities -> set[str]` — what this peripheral supports.
- Calling an unsupported mode raises a clean exception (e.g., `ivv.NotSupported`), not a gRPC error. ### 3.4 Typed dataclasses via codegen (binding)
- Write a **build-time generator** (`tools/gen_types.py`) that: - Compiles the protos (you already do this for stubs) and reads the **protobuf descriptors** reflectively — do NOT hand-parse `.proto` text. - Emits one Python `@dataclass` per sample/result/event message, with type hints, field docstrings (units/semantics from the HAL review), and a converter function `from_proto(msg) -> dataclass`. - Maps types correctly: `uint64`→`int`, `float`→`float`, nested message→nested dataclass, `repeated`→`list[...]`, enums→Python `Enum`. - Emits, for every dataclass, three universal freebies and nothing peripheral-specific: a clean `__repr__`, `.to_dict`, `.to_json`.
- Generated output is committed (or generated on build) and shipped inside the package. Customers never run codegen.
- **Adding a peripheral must be "update the contract, regenerate"** — never hand-editing dataclasses. ### 3.5 Errors (binding)
A small, clear exception hierarchy the customer can `try/except`:
```
ivv.IVVError (base) ├── ivv.ConnectionError ├── ivv.PeripheralNotFound ├── ivv.NotSupported ├── ivv.ConfigError ├── ivv.TestError └── ivv.TimeoutError
```
All gRPC status codes and protobuf error payloads are translated into these. No raw gRPC exceptions escape the SDK. ### 3.6 Versioning & distribution (binding)
- pip-installable package named `acadia-sdk` (import as `acadia_sdk`).
- Pin the `ivv-contracts`/proto version the SDK was generated against; expose it as `acadia_sdk.__contracts_version__`.
- On connect, if Client reports an incompatible contract version, raise `ivv.ConnectionError` with a clear message — never a mysterious crash.
- Semantic versioning. Document the compatibility policy in the README.
- Security is NOT a v1 concern (closed-loop trusted network) — plain gRPC, no TLS/auth required, but leave a documented seam for adding it later. --- ## 4. Phase 2 — Build the SDK After findings are confirmed, generate the complete, releasable SDK. Produce **every file**, not snippets. Build it in this order and keep it compiling/importable at each step. ### 4.1 Repository layout to produce
```
acadia-sdk/
├── pyproject.toml # packaging, deps, build config
├── README.md # install + 5-minute quickstart + every module example
├── LICENSE
├── CHANGELOG.md
├── .gitignore
├── Makefile # gen, build, test, lint, publish targets
├── src/
│ └── acadia_sdk/
│ ├── __init__.py # public API: connect, exceptions, version
│ ├── _version.py
│ ├── client.py # Device + connect
│ ├── peripheral.py # Peripheral object + test-mode methods
│ ├── exceptions.py # the exception hierarchy
│ ├── _channel.py # gRPC channel mgmt, version handshake (private)
│ ├── _convert.py # proto <-> dataclass conversion helpers (private)
│ ├── types/ # GENERATED typed dataclasses
│ │ ├── __init__.py
│ │ ├── imu.py # e.g. IMUSample
│ │ ├── motor.py
│ │ └── ... # one per peripheral data type discovered
│ └── _proto/ # GENERATED gRPC stubs (private, vendored)
│ ├── __init__.py
│ ├── *_pb2.py
│ └── *_pb2_grpc.py
├── tools/
│ ├── gen_proto.py # runs protoc -> _proto/
│ └── gen_types.py # descriptor-driven dataclass generator -> types/
├── tests/
│ ├── conftest.py # spins up a fake Client (gRPC server) for tests
│ ├── fakes/fake_client.py # in-process fake implementing the real proto service
│ ├── test_connect.py
│ ├── test_peripheral_discovery.py
│ ├── test_oneshot.py
│ ├── test_monitor_stream.py
│ ├── test_event_mode.py
│ ├── test_long_running.py
│ ├── test_errors.py
│ └── test_types_roundtrip.py # proto -> dataclass -> dict/json
├── examples/
│ ├── 01_connect_and_discover.py
│ ├── 02_imu_oneshot.py
│ ├── 03_imu_monitor_stream.py
│ ├── 04_event_trigger.py
│ ├── 05_long_running_test.py
│ ├── 06_self_test_all.py
│ ├── 07_build_an_app.py # a small real app: poll IMU, log to CSV
│ └── README.md
└── docs/ ├── quickstart.md ├── api_reference.md # every public class + method ├── peripherals.md # per-peripheral: fields, units, supported modes ├── error_handling.md └── versioning.md
``` ### 4.2 Required: one runnable example per module
For **each peripheral type discovered in the real code**, produce a worked example in `examples/` showing its supported test modes. Also produce the seven numbered examples above. Each example must be a complete, runnable `.py` file with a docstring explaining what it does and what hardware/connection it assumes. ### 4.3 Required: tests against a fake Client
- The tests must NOT require real hardware.
- Build `tests/fakes/fake_client.py` — an in-process gRPC server implementing the **real** discovered proto service, returning canned-but-realistic data.
- Tests exercise: connect + version handshake, discovery, each test mode, streaming iteration + early break, every exception path, and dataclass round-trips.
- All tests pass under `pytest`. Target ≥ 90% coverage of the hand-written SDK layer. ### 4.4 Required: the README quickstart
The README must open with the five-minute example (3.1), then show one short snippet per test mode, then installation, then the version-compatibility policy. It is the customer's first contact — make it excellent. --- ## 5. Quality bar (binding) - **Type hints everywhere.** The SDK must pass `mypy --strict` on the hand-written layer.
- **Docstrings on every public class and method** — Google or NumPy style, consistent.
- **No protobuf/gRPC types in any public signature.** Inputs and outputs are Python primitives and the generated dataclasses only.
- **`ruff`/`black` clean.** Include config in `pyproject.toml`.
- **No TODOs or placeholders in shipped code.** If something can't be determined from the repos, raise it in the findings report (Phase 1), don't stub it silently.
- **Python 3.10+.**
- The package must `pip install -e .` and `import acadia_sdk` cleanly with no extra steps. --- ## 6. What NOT to do - Do **not** invent proto messages, RPC names, peripheral types, or field names. Discover them. If you cannot find them, stop and ask.
- Do **not** expose generated gRPC stubs or protobuf objects in the public API.
- Do **not** add async, threading, connection pools, or multi-device support in v1.
- Do **not** add evidence capture, databases, or persistence — that's IV&V Server's job, not the SDK's.
- Do **not** hand-write the typed dataclasses — generate them from proto descriptors.
- Do **not** call HAL directly — the SDK speaks gRPC to Client only.
- Do **not** require real hardware to run the test suite.
- Do **not** add TLS/auth machinery in v1, but leave a clean seam for it.
- Do **not** leave the build in a non-importable or non-compiling state between steps. --- ## 7. Execution order (follow exactly) 1. Confirm the OS/HAL/Client repo paths with the user.
2. **Phase 1:** review all repos, produce `SDK_FINDINGS.md`, list open questions and prompt-vs-reality discrepancies. **Stop and wait for confirmation.**
3. After confirmation: scaffold the repo, packaging, and `tools/gen_proto.py`; generate stubs into `_proto/`. Verify import.
4. Write `tools/gen_types.py`; generate typed dataclasses into `types/`. Verify round-trip on one peripheral.
5. Build the hand-written layer: exceptions, `_channel.py`, `client.py`, `peripheral.py`, `__init__.py`.
6. Build the fake Client and the full test suite. Make everything pass.
7. Write all examples (one per peripheral + the seven numbered ones).
8. Write README and `docs/`.
9. Run `mypy --strict`, `ruff`, `pytest` — all clean. Fix until green.
10. Produce a final `RELEASE_NOTES.md` summarizing what was built, the contracts version it targets, and any caveats. **Begin with step 1: confirm the repository paths, then start the Phase 1 review. Do not write SDK code until the findings report is confirmed.**