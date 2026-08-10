---
description: Regenerate proto stubs from Zion-HAL — this repo regenerates BY DESIGN
allowed-tools: Bash(make gen), Bash(make gen-check)
--- !`make gen && make gen-check` PySDK is the one leaf that regenerates protos on purpose (the no-regeneration
rule is a C++ ODR constraint for Client/Server and does not apply here).
gen-check failing means stale stubs — a real defect. Generated stubs are
COMMITTED under zion-sdk/src/zion_sdk/_proto/ and types/; never gitignore
them. Generation reads ../Zion-HAL/protos, so a missing sibling checkout is
the first thing to check on failure.
