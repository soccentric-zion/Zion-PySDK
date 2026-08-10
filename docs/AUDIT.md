# Acadia-PySDK — Independent Audit

**Repo:** `Acadia-PySDK`
**Branch / commit:** `main` @ `df75926` ("Add CI workflow, update Makefile to use uv, and adjust README connection port")
**Working tree:** clean.
**Auditor:** AI agent, scope per `final_audit.md`.

---

## 1. Verdict

**Health: GREEN with one documentation bug.**

Top 3 findings:

1. **Connection target is correct, but two in-code docstrings show the wrong port.** The SDK's `HalServiceStub` is the right wire interface (`acadia-sdk/src/acadia_sdk/_proto/hal_service_pb2_grpc.py:9`, all eight RPCs: `/hal.HalService/RunSingleShot`, `StartLongTerm`, `StartMonitoring`, `StartEventBased`, `Stop`, `Pause`, `Resume`, `ListModules`). The Client config (`Acadia-Client/conf/client.conf.sample:20`, `Acadia-Client/src/config/client_config.h:19`) makes the Client's HalService listen on **`50052`** (50051 is reserved for the Server's gRPC; the Client connects *outbound* to that). The PySDK README is correct (`acadia-sdk/README.md:8` shows `"192.168.1.50:50052"`), but two in-code docstrings still show the old `:50051`: `acadia-sdk/src/acadia_sdk/__init__.py:12` and `acadia-sdk/src/acadia_sdk/client.py:28,40`. **A user copy-pasting the docstring example will land on the Server, not the Client, and bypass the IV&V invariant.** Doc-only fix, no logic change. The latest commit message (`df75926` — "Add CI workflow, update Makefile to use uv, and adjust README connection port") shows the README was fixed but the module docstrings were missed.
2. **`gen-check` drift guard is real and functional.** Verified empirically: a comment-only proto change still passes (correct — descriptor unchanged), but adding an enum value to `protos/common.proto` (`DRIFT_MODE = 5`) makes `make gen-check` print `gen-check FAILED — stubs are stale; run 'make gen' and commit.` and exit non-zero. The check is not theatre. Both runs reverted; working tree clean.
3. **Public API is hand-written over generated stubs; no raw protobuf leaks.** `__init__.py` `__all__` exports only the curated surface (`Device`, `connect`, `Peripheral`, `LongRunningSession`, `metric_value`, exceptions, version). Generated `_proto/` is private (underscore prefix). Type dataclasses live under `acadia_sdk.types` and are produced by `tools/gen_types.py`, also driven by `gen-check`. Customers see Python dataclasses, not `google.protobuf.Message`.

---

## 2. Build / install

`uv` is used (path `/home/sandesh/.local/bin/uv`); `.venv` exists. `make test` works end-to-end and produces a coverage report. No build failures.

---

## 3. Tests — quoted real output

```
35 passed in 0.54s
```

`make test` from `Acadia-PySDK/`. Test breakdown via `pytest --collect-only -q` (35 collected):

| File | Count | Coverage area |
| --- | --- | --- |
| `tests/test_connect.py` | 6 | smoke, context-manager close, bad address, unreachable, contract-version reject, repr |
| `tests/test_discovery.py` | 4 | list active peripherals, handle return, unknown raises, capability uniformity |
| `tests/test_event.py` | 3 | arm by test_name, by expression, requires-a-condition |
| `tests/test_long_running.py` | 5 | lifecycle, double-start reject, query-without-session, stop-noop, pause/resume |
| `tests/test_monitor.py` | 4 | yields results, early break, bad period, indefinite |
| `tests/test_oneshot.py` | 8 | result return, self_test alias, fail-returns, fail-raises, error-raises, timeout, config-error, named tests |
| `tests/test_types_roundtrip.py` | 5 | TestResult round-trip, JSON enum names, jsonable, oneof arm resolution, oneof unset → None |

All tests run against a `FakeServer` (`tests/fakes/fake_server.py`) — a real gRPC server stood up on a free port, not a mock. So unit assertions exercise the actual `HalServiceStub`. This is good. It does not, however, exercise the real C++ Client; that's the job of E2E (§4 of audit prompt).

---

## 4. Repo-specific findings

### 4.1 Proto stub provenance is enforced

```
==> Checking proto stubs are up-to-date
[gen_proto] 53 proto files from .../Acadia-HAL/protos
[gen_proto] wrote 108 Python files under .../acadia_sdk/_proto
[gen_types] wrote 53 dataclass modules into .../acadia_sdk/types
gen-check passed — stubs are up-to-date.
```

Drift run (added `DRIFT_MODE = 5` to `Acadia-HAL/protos/common.proto`):

```
gen-check FAILED — stubs are stale; run 'make gen' and commit.
make: *** [Makefile:87: gen-check] Error 1
```

Both observed in this audit; the proto file was reverted (`git status` clean).

### 4.2 Public API is Pythonic, not RPC-shaped

`peripheral.py:1-18` documents the mode-to-RPC mapping:

| SDK method | Underlying RPC |
| --- | --- |
| `run_oneshot` | `RunSingleShot` (unary) |
| `self_test` | `RunSingleShot` with empty `test_names` |
| `monitor` | `StartMonitoring` (server-stream) |
| `arm_event` | `StartEventBased` (server-stream) |
| `start_long_running` | `StartLongTerm` (background) |
| `query_long_running` | latest queued batch |
| `stop_long_running` | `Stop` + drain |
| `pause` / `resume` | `Pause` / `Resume` |

15 methods total in `client.py` + 24 in `peripheral.py` (incl. `__init__`/dunders). Surface is small and ergonomic.

### 4.3 Capability set hard-coded

`peripheral.py` declares `_DEFAULT_CAPABILITIES = frozenset({"oneshot", "long_running", "monitor", "event", "self_test", "pause", "resume", "stop"})` and applies uniformly to every module. **This is correct today** — the contract gives every module all four test modes — but any future per-module capability bits would require changes here. Documented inline as such.

### 4.4 Bootstrap-window ImportError tolerance

`__init__.py:35-42` swallows `ModuleNotFoundError` only for `acadia_sdk.types`, `acadia_sdk._proto`, `acadia_sdk.types.common`, `acadia_sdk.types.hal_service` — to allow the codegen tools themselves to import the package before stubs exist. Any other missing module re-raises. Narrow, justified, low risk.

---

## 5. Code health

- Coverage report: 25% TOTAL. **This is misleading** — it includes 53 generated dataclass modules under `acadia_sdk/types/modules/` that are 0% (e.g., `mipi_csi.py 45 stmts 0%`). These are pure dataclasses; they're "tested" implicitly through `test_types_roundtrip.py` against the common types. The five hand-written runtime modules (`client.py`, `peripheral.py`, `_channel.py`, `_convert.py`, `exceptions.py`) appear to have meaningful coverage in the missed-line summary.
- Linter / typing: `make` exposes `lint` and `format` targets; not run in this audit.
- No raw `protobuf` types appear in `__all__`.
- No `print()`/debug residue noted in spot checks.

---

## 6. Claims vs reality

| Source claim | Reality | Verdict |
| --- | --- | --- |
| "35 passing tests" (`SDK_FINDINGS.md`) | `35 passed in 0.54s` | **TRUE** |
| "PySDK connects to `HalService`" | `HalServiceStub` correct, all 8 RPCs wired; **port shown in two in-code docstrings is `50051` (Server) instead of `50052` (Client)** — README is correct | **MOSTLY TRUE — doc bug** |
| "`gen-check` ensures stub freshness" | Verified via real semantic drift | **TRUE** |
| "Public API hides protobuf" | `__all__` curated; generated under `_proto/` (private) | **TRUE** |
| "Pythonic over generated stubs" | `Peripheral` maps modes → RPCs; dataclasses replace messages | **TRUE** |

No PySDK overclaim observed.

---

## 7. Cannot be verified from this repo alone

- **Real-device connect.** `connect()` was not exercised against a live Client — only against `FakeServer`. The first proof of "SDK → Client → adapter → HAL → real data" lives in §4 of the audit prompt and is performed at the root level.
- **Persistence invariant.** The claim "PySDK one-shot leaves no DB row, REST one-shot creates one" is half-PySDK / half-Server. Verified Server-side that the Client's `HalService` does not call `persist_result` (see `Acadia-Client/AUDIT.md` §4); the matching SDK side will be proven during live E2E.
- **Streaming back-pressure.** `monitor` and `arm_event` use a `queue.Queue`-backed background thread. Behaviour under slow consumers / full queues was not stress-tested; existing tests are short and orderly.

---

## 8. Evidence appendix

- Git: `df759260925ca6a5bbc4e0430279e2646af41200` on `main`, clean.
- Tests: `35 passed in 0.54s` (`make test`, captured 2025-XX during this audit).
- gen-check pass: see §4.1 quote.
- gen-check fail (real drift): see §4.1 quote.
- HalServiceStub: `acadia-sdk/src/acadia_sdk/_proto/hal_service_pb2_grpc.py:9` and 8 method strings on lines 25/30/35/40/45/50/55.
- API surface: `acadia-sdk/src/acadia_sdk/__init__.py` `__all__` + module docstring.
- Capability set: `acadia-sdk/src/acadia_sdk/peripheral.py` `_DEFAULT_CAPABILITIES`.
- Test list: `pytest --collect-only -q` (35 collected), full names quoted in §3.
- FakeServer: real gRPC server in `acadia-sdk/tests/fakes/fake_server.py`; not a mock object.
