# Zion-PySDK Build and Deployment

## Purpose and scope
Zion-PySDK packages the Python `zion-sdk` gRPC client for the HalService exposed by Zion-Client. The package includes generated protobuf/dataclass bindings, typed peripheral operations, examples, and compatibility behavior. The Makefile runs from this repository root and manages the nested `zion-sdk` package.

## 1. Prerequisites
- Python 3.10+ and `uv`.
- A copy of the Zion-HAL protobuf sources for regeneration; `grpcio-tools` and `mypy-protobuf` are development dependencies.
- A reachable Zion-Client HalService and suitable hardware only for live examples/integration checks.

## 2. Setup
Install `uv` and ensure the matching Zion-HAL protobuf sources are available for generation.

## 3. Build and compile
```bash
make setup
make venv
make gen
```
`setup` creates `.venv` and installs `zion-sdk[dev]` editable via uv. `gen` regenerates proto and dataclass bindings using `zion-sdk/tools/gen_proto.py` and `gen_types.py`; review generated diffs before committing.

## 4. Test and lint
```bash
make test
make lint
make typecheck
make check
make gen-check
```
`test` runs pytest with coverage; `lint` runs Ruff; `typecheck` runs strict mypy using the package config; `check` runs all three. `gen-check` fails when committed generated stubs are stale without intentionally retaining the generated changes. `gen-clean` removes and regenerates generated output.

## 5. Packaging and artifacts
```bash
make build
```
The target installs the `build` package into the uv environment and writes wheel and sdist artifacts to `zion-sdk/dist`. Runtime dependencies are grpcio and protobuf; development dependencies are defined in `zion-sdk/pyproject.toml`.

## 6. Deployment, install, and run
Install a built wheel or editable package with pip/uv, then connect to the target's HalService, commonly port 50052. Example scripts under `zion-sdk/examples` exercise discovery, one-shot, monitoring, event, long-running, self-test, and application flows. These commands require a running Zion-Client, network reachability, matching generated contract versions, and real or supported peripheral hardware. The SDK connects directly to the client, not the Server data path.

## 7. Cleanup
```bash
make clean
make distclean
```
`clean` removes package build/dist, caches, coverage, and egg-info while keeping `.venv`; `distclean` also removes the uv venv and stamps. Generated source is not removed by `clean`.

## 8. Hardware, cloud, and manual verification caveats
Unit tests do not establish live gRPC compatibility, physical peripheral behavior, or long-running timing. Keep SDK, Zion-Client, and Zion-HAL contract versions aligned. Treat `gen`, live examples, and package publication as conditional on source availability and a controlled target endpoint.
