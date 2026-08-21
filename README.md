# Zion-PySDK

## Project Summary

Generated files should stay synchronized with proto sources before a package is published.

The test names provide useful behavioral anchors, but they do not guarantee compatibility with every Client or HAL revision. Pin the service endpoint and generated contract when running integration checks or publishing release notes.

Zion-PySDK is the Python SDK leaf for the Zion project. The distributable package lives under `zion-sdk/`; its package name is `zion-sdk` and its import name is `zion_sdk`. The SDK is a Pythonic gRPC client for the HalService endpoint exposed by Zion-Client, with generated protobuf modules, typed wrappers, connection/client code, exceptions, examples, API documentation, and a test suite. The repository retains an `acadia_sdk` deprecation shim for callers using the older package name, so compatibility behavior is part of the public surface. Existing documentation points to quickstart, API reference, error handling, peripheral, versioning, and example material, while examples cover connection/discovery, one-shot IMU access, monitoring, event triggers, long-running tests, self-tests, and application construction. Tests named in the repository cover connect, discovery, events, monitoring, one-shot calls, long-running behavior, types round trips, and the deprecation shim. Generated protobuf code is evidence of a broad HAL contract, but does not mean every generated module is backed by a working adapter or physical device. The practical validation path is package setup followed by the Makefile or pyproject-defined checks; live examples additionally need a reachable Zion-Client HalService and appropriate hardware. This README keeps the package pointers while making those prerequisites explicit. It records implementation and test evidence conservatively and leaves every manual-test cell unverified, including examples that may look runnable from their filenames alone.

## Feature Status

| # | Name / Description | Implemented? | Test Coverage? | Manual Test |
|---:|---|---|---|---|
| 1 | `zion-sdk` package metadata and build configuration | Implemented | Package tests present; build not run | [ ] Manual verification required |
| 2 | gRPC client/channel connection | Implemented | `test_connect.py` | [ ] Manual verification required |
| 3 | Device discovery | Implemented | `test_discovery.py` | [ ] Manual verification required |
| 4 | One-shot peripheral calls | Implemented | `test_oneshot.py` | [ ] Manual verification required |
| 5 | Monitoring streams | Implemented | `test_monitor.py` | [ ] Manual verification required |
| 6 | Event triggers | Implemented | `test_event.py` | [ ] Manual verification required |
| 7 | Long-running test support | Implemented | `test_long_running.py` | [ ] Manual verification required |
| 8 | Typed result/config round trips | Implemented | `test_types_roundtrip.py` | [ ] Manual verification required |
| 9 | Generated protobuf bindings | Implemented | Generation/runtime compatibility unknown | [ ] Manual verification required |
| 10 | `acadia_sdk` deprecation compatibility shim | Implemented | `test_deprecation_shim.py` | [ ] Manual verification required |
| 11 | Self-test and application examples | Implemented | Example execution not confirmed | [ ] Manual verification required |
| 12 | API/error/peripheral/version documentation | Implemented | Documentation review only | [ ] Manual verification required |

## Tests and Commands

```bash
cd zion-sdk
make setup
make gen
make check
make build
pytest
```

Use `pyproject.toml` and the package README as authority if a Make target differs. Live examples require Zion-Client HalService.

## Limitations

No package install, protobuf regeneration, live gRPC connection, physical peripheral, or long-running example was manually verified. Generated bindings may outpace implementations available in the current HAL/client pair.
# Zion-PySDK Python SDK leaf for the **Zion** project (Zynq UltraScale+ + STM32) in the
SiliconCentric `project-managers` fleet. This leaf provides `zion-sdk`, a Pythonic gRPC client for the `HalService`
endpoint exposed by `Zion-Client`. The SDK distribution package is
**`zion-sdk`** (import name `zion_sdk`); a `acadia_sdk` deprecation shim
re-exports the public surface for callers still on the old name. The SDK source, tooling, docs, examples, and test suite live under
[`zion-sdk/`](zion-sdk). See [`zion-sdk/README.md`](zion-sdk/README.md)
for the full API, quickstart, and `make` targets (`setup`, `gen`, `check`,
`build`). ---
Part of the `Zion` project in the `project-managers` fleet. See
`docs/project-managers.md` for the full 9-project/ 8-leaf hierarchy and
shared conventions.