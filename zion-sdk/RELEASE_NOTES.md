# zion-sdk 0.1.0 — Release Notes

## What's in this release

* The full IV&V SDK as scoped by [`req.md`](../req.md): every public
  surface listed in §3 and §4 is implemented, every functional
  requirement in §3.1–3.5 has at least one passing test against an
  in-process fake HAL.
* 33 passing tests, `ruff check` clean, `mypy --strict` clean on every
  hand-written module. Coverage on the hand-written layer: 91–100% per
  module (overall ≈95% on the SDK surface, lower aggregate when the
  53 generated dataclass modules are included because most of the
  unused modules' codegen paths are not exercised — by design).
* Generated bindings for the entire HAL contract: 51 module protos plus
  the shared `common` and `hal_service` packages, totalling 108 protobuf
  modules and 53 dataclass modules. Round-trips (`pb → dataclass → pb`)
  are verified for enums, maps, repeated fields, and `oneof` arms.

## What lives where

```
zion-sdk/
├── src/zion_sdk/            ← hand-written SDK surface
│   ├── __init__.py         ← public re-exports
│   ├── client.py           ← connect(), Device
│   ├── peripheral.py       ← Peripheral, LongRunningSession
│   ├── exceptions.py       ← IVVError taxonomy
│   ├── _channel.py         ← gRPC + error translation
│   ├── _convert.py         ← Any pack/unpack
│   ├── _proto/             ← GENERATED — protoc output (108 files)
│   └── types/              ← GENERATED — descriptor-driven dataclasses (53 files)
├── tools/
│   ├── gen_proto.py        ← grpc_tools.protoc driver + import rewriter
│   └── gen_types.py        ← dataclass emitter
├── tests/
│   ├── conftest.py         ← fixtures
│   ├── fakes/fake_server.py ← in-process HalServiceServicer
│   └── test_*.py           ← 8 test files, 33 tests
├── examples/01..07_*.py    ← walkthrough scripts
├── README.md
├── CHANGELOG.md
├── Makefile
└── pyproject.toml
```

## Decisions you should know about

Two architectural questions in `SDK_FINDINGS.md` (the Phase-1 discovery
report) were unresolved at the time `req.md` was handed off. They were
decided as follows during implementation:

**Q1 — Which gRPC interface does the SDK speak?**
*Decision*: The SDK is a gRPC **client** of `acadia-server`'s
`hal.HalService` endpoint (the same stable per-mode contract that
`acadia-client` speaks internally). This makes `zion-sdk` a Python peer
of the C++ `acadia-client` runner — not a wrapper around it.

The alternatives considered and rejected:
1. *Wrap acadia-client's CLI*. Rejected — brittle, would require shelling
   out per call and parsing stdout.
2. *Speak `acadia.stream.ClientService`*. Rejected — that is the
   bidi telemetry channel from Server → Client; it does not expose the
   per-test-mode API customers actually need.

**Q3 — Result-surface shape?**
*Decision*: Faithful descriptor-driven dataclasses. A metric is read as
`result.results[i].output.metrics["accel_x"].double_value`, not
`sample.accel_x`. Reason: the HAL protos do not expose typed sample
fields, so any "shortcut" attribute would require the SDK to maintain a
hand-curated registry of metric-name → proto-field mappings per module.
That registry would silently drift the moment a new module is added.
Keeping the surface descriptor-driven means the SDK works automatically
on every module the registry contains, today and in future contract
versions.

A friendlier surface (e.g. `sample.accel_x`) can be layered on top in
0.2 as a non-breaking addition.

## What's NOT in this release

* TLS / mTLS channel credentials.
* Per-module capability discovery — the contract does not yet ship a
  typed capability field, so `capabilities()` returns a uniform set for
  every peripheral.
* True pause/resume semantics — `Pause` / `Resume` RPCs are forwarded
  but the HAL implementation treats them as advisory (see
  `integration/contract_reconciliation.md` CM-11).

## Versioning

* SDK version: **0.1.0**
* HAL contracts version supported: **v1** (matches the
  `version` field in every `ModuleInfo` shipped by the current
  `Acadia-HAL/protos/registry/modules.yaml`).
* Bumping any module to `version: 2` in the registry will cause
  `connect()` to raise `ConnectionError` until `zion-sdk` is upgraded.

## Verifying the release

```bash
cd zion-sdk
pip install -e .[dev]
make lint typecheck test
```

Expected: `All checks passed`, `Success: no issues found in 7 source files`,
and `33 passed`.
