# Zion-PySDK Python SDK consuming the `HalService` gRPC endpoint Zion-Client exposes. Distribution
`zion-sdk`, import name `zion_sdk`. ## How you work here * Commands: `.claude/commands/` — check, gen, validate.
* Write: source, tooling, docs, examples and the uv-managed make workflow all live under `zion-sdk/`.
* Test: `make check` is lint + typecheck + test together.
* Regenerate protos with `make gen`; `make gen-check` fails on stale stubs. ## How you validate * Gate: `./.claude/validate.sh quick` (seconds) or `full` (adds build + tests). Run it before you claim done.
* Exit codes: `0` pass, `1`-`76` fail, `77` a check never ran. **77 is not a pass.**
* The gate and everything under `.claude/lib`, `hooks`, `commands`, `settings.json` is human-owned. Run it, never edit it. ## Do * Regenerate protos here — that is by design, and the one place in the fleet where it is. Any change to `hal_service.proto` breaks this repo for real.
* Keep the `acadia_sdk` deprecation shim shipping in the wheel. It lazily re-exports `zion_sdk` for callers still on the old name. ## Don't * **Don't apply the no-regeneration rule here.** It is a C++ ODR constraint that protects Zion-Client and Zion-Server from duplicate proto symbols. Python has no equivalent.
* **Don't gitignore the generated stubs.** They are committed on purpose and `make gen-check` depends on them. *Loop-derived lessons for this repo live in the fence below, pending curation into the lists above.* <!-- BEGIN loop-engine -->
### Loop 20260728-pysdk-package-rename-zion (closed to in-review, try 2 of 2) - Distribution renamed acadia-sdk -> zion-sdk; import package acadia_sdk -> zion_sdk; directory acadia-sdk/ -> zion-sdk/. A acadia_sdk deprecation shim re-exports zion_sdk (lazy PEP 562 __getattr__) and emits a DeprecationWarning at import; the shim ships in the wheel (packages.find include = ["zion_sdk*", "acadia_sdk*"]).
- Generated stubs are committed under zion-sdk/src/zion_sdk/_proto/ and zion-sdk/src/zion_sdk/types/ (~270 files). make gen-check passes. Do NOT add these to .gitignore - the workflow expects committed stubs.
- gen_proto.py now points at Zion-HAL/protos (was Acadia-HAL/protos) and adds -I<grpc_tools/_proto> for well-known protos. If the fleet ever renames HAL again, update DEFAULT_PROTOS here.
- gen_types.py uses fd.is_repeated (bool property), not fd.label == FD.LABEL_REPEATED - protobuf 7.x removed FieldDescriptor.label from the upb descriptor. Any new code comparing repeated-ness must use fd.is_repeated.
- make typecheck runs mypy --config-file zion-sdk/pyproject.toml so the project's [tool.mypy] excludes for generated _proto/types apply. Without --config-file, mypy runs from the Zion-PySDK root and reports ~153 false errors in generated modules.
- The try/except ModuleNotFoundError in zion_sdk/__init__.py tolerates a bootstrap window where stubs are missing, leaving public names unbound. The shim is lazy to match. If you ever make zion_sdk/__init__.py eager, the shim's laziness still holds - but reconsider whether the bootstrap tolerance is still needed.
- Loop artifacts: loop/execution/20260728-pysdk-package-rename-zion/try-2/ in the master repo. Success-criterion commands all PASS on this branch.
<!-- END loop-engine -->
