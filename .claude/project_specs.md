# Zion-PySDK — specs Remote: `git@github.com:soccentric-zion/Zion-PySDK.git`
Stack: Python, uv-managed, src layout. Consumes the `HalService` gRPC endpoint exposed by Zion-Client — the same wire contract
Zion-Server speaks. ## Layout * `zion-sdk/` — everything: source, tooling, docs, examples, the make workflow (setup/ gen/ check/ build).
* `zion-sdk/src/zion_sdk/` — the package. Import name `zion_sdk`, distribution name `zion-sdk`.
* `zion-sdk/src/zion_sdk/_proto/` and `types/` — generated stubs, ~270 files, **committed on purpose**.
* `acadia_sdk` — deprecation shim re-exporting the public surface for callers on the old name. Lazy PEP 562 `__getattr__`, emits a `DeprecationWarning`, ships in the wheel. ## The regeneration exception This is the one leaf that regenerates protos. Zion-Client and Zion-Server must not, because a
second copy of the generated C++ symbols causes ODR/duplicate-symbol link errors. That is a C++
constraint with no Python equivalent, so it does not apply here.
