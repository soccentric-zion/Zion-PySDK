# Versioning Two version numbers ship with the SDK: * `zion_sdk.__version__` — the SDK release version. SemVer.
* `zion_sdk.__contracts_version__` — the maximum HAL contract version this SDK can talk to. Integer. These bump independently. ## What `__contracts_version__` means Every module entry in the HAL registry has a `version` field: ```yaml
- id: imu proto_package: hal.modules.imu version: 1 # ← this number status: active
``` When `connect` is called, the SDK fetches the registry via
`ListModules` and checks that **every active module's `version` is
`<= zion_sdk.__contracts_version__`**. If any module is newer, the SDK
refuses to connect: ```
ConnectionError: peer advertises modules with contract versions newer
than this SDK supports (max v1): foo=v2. Upgrade zion-sdk to match.
``` This is intentionally strict — the SDK would rather refuse than silently
serialise the wrong shape. ## Compatibility policy * The SDK guarantees backwards compatibility within a single contract version. Adding a new field to a `Config` or `Result` message at a higher proto field number does NOT bump the contract version, and older SDKs will simply ignore the new field.
* Renaming a field, repurposing a field number, or removing a field bumps the contract version. After such a bump: * Old SDKs refuse to connect (as above). * A new SDK release ships with the bumped `__contracts_version__` and the regenerated dataclasses. ## SDK release bumps | Change | Bump |
|---------------------------------------------------------------|------|
| Pure proto regeneration (new fields, new modules) | minor (0.1 → 0.2) |
| New convenience method on `Peripheral` | minor |
| New required argument on an existing method | major |
| Renaming/removing a public symbol | major |
| Bumping `__contracts_version__` | major |
| Internal bug fix, doc tweak, generator improvement | patch |
