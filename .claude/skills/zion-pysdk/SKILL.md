---
name: zion-pysdk
description: "Use when working on the Zion-PySDK repository: Python SDK APIs, gRPC client behavior, peripherals, protobuf or dataclass generation, tests, packaging, or repository validation."
---

# Zion-PySDK

## Repository Context

- This repository is the Python SDK leaf of the Zion project.
- The distributable package is zion-sdk; the primary import package is zion_sdk.
- acadia_sdk is a compatibility shim. Preserve it when changing public exports and keep its deprecation behavior intact.
- The SDK consumes the HalService gRPC endpoint exposed by Zion-Client.
- The supported runtime is Python 3.10 or newer. Dependencies and development tools are declared in zion-sdk/pyproject.toml.
- The top-level Makefile is the source of truth for setup, generation, checks, tests, and builds.

## Working Rules

1. Read the relevant public API, neighboring tests, and exception definitions before changing behavior.
2. Keep public API changes intentional. Update tests and documentation when names, return values, exceptions, or lifecycle behavior change.
3. Use the existing conversion helpers and typed dataclasses at the Python/protobuf boundary. Do not hand-roll duplicate conversion logic.
4. Keep gRPC transport concerns in the existing channel helpers and client/peripheral abstractions. Do not expose generated protobuf messages through the public API unless the contract requires it.
5. Preserve device lifecycle guarantees: connections are closeable, context-manager compatible, and handshake failures close the channel.
6. Preserve the device-wide serialization contract for operations that use the internal mutex.
7. Avoid unrelated refactors and do not modify generated files by hand.

## Generated Code

Generated protobuf and dataclass bindings are committed under:

- zion-sdk/src/zion_sdk/_proto/
- zion-sdk/src/zion_sdk/types/

When the source proto definitions change or generated output is stale:

1. Ensure the sibling ../Zion-HAL/protos checkout is available.
2. Run make gen from the repository root.
3. Review the generated diff for unexpected changes.
4. Run make gen-check before finishing.

Do not add generated bindings to .gitignore. In type-generation code, use the protobuf descriptor API supported by the installed version, including FieldDescriptor.is_repeated for repeated fields.

## Validation Workflow

Run commands from the repository root:

```sh
make setup       # first run or after dependency changes
make lint        # ruff
make typecheck   # strict mypy with zion-sdk/pyproject.toml
make test        # pytest with coverage
make check       # lint + typecheck + test
make build       # wheel and sdist
```

For changes affecting generated bindings, also run make gen-check. The repository validator may require the sibling HAL checkout and a prepared .venv; treat missing prerequisites as environment blockers, not code failures.

## Testing Guidance

- Add the narrowest regression test that demonstrates the changed behavior.
- Reuse the fake_server and address fixtures in zion-sdk/tests/conftest.py for client/RPC behavior.
- Keep tests focused on the public SDK contract; use generated messages only as test-server plumbing.
- Cover timeout, missing-peripheral, stream, close/idempotency, and compatibility-shim behavior when those paths are affected.
- Run the focused test first, then the relevant lint/typecheck target, and finish with make check when practical.

## Completion Checklist

- Public behavior and compatibility concerns are addressed.
- Tests cover the changed behavior and pass.
- make gen-check passes when generation-related code changed.
- make check passes, or any blocked command and its missing prerequisite are reported clearly.
- Generated output, packaging metadata, docs, and changelog entries are updated only when the change requires them.