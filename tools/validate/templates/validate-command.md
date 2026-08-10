---
description: Run this repo's sanity + validation gate (quick | full)
argument-hint: [quick|full]
allowed-tools: Bash(./.claude/validate.sh:*)
---

Run the repo's validation gate:

!`./.claude/validate.sh ${ARGUMENTS:-quick}`

Interpret the exit code using the fleet-wide contract:

- `0` — every check ran and passed. PASS.
- `1`–`76` — a check ran and failed. FAIL. Report the failing check and its
  output; do not fix anything unless asked.
- `77` — one or more checks never ran (missing toolchain, or a step that needs
  hardware). BLOCKED, **not** a pass. Say which checks were skipped and what
  would need installing to run them.

Never report a `77` as success, and never substitute your own judgement for a
check that did not run.
