# Zion-PySDK

Python SDK leaf for the **Zion** project (NVIDIA Jetson + STM32) in the
SiliconCentric `project-managers` fleet.

This leaf provides `zion-sdk`, a Pythonic gRPC client for the `HalService`
endpoint exposed by `Zion-Client`. The SDK distribution package is
**`zion-sdk`** (import name `zion_sdk`); a `acadia_sdk` deprecation shim
re-exports the public surface for callers still on the old name.

The SDK source, tooling, docs, examples, and test suite live under
[`zion-sdk/`](zion-sdk/). See [`zion-sdk/README.md`](zion-sdk/README.md)
for the full API, quickstart, and `make` targets (`setup`, `gen`, `check`,
`build`).

---
Part of the `Zion` project in the `project-managers` fleet. See
`docs/project-managers.md` for the full 9-project / 8-leaf hierarchy and
shared conventions.