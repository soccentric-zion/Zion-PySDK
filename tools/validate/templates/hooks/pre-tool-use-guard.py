#!/usr/bin/env python3
"""PreToolUse hook — protect this repo's validation gate from casual edits.

The Loop Engine's rule is that everything under .claude/ that measures the repo
(validate.sh, lib/, settings.json, hooks/, commands/) plus tools/validate/ is
HUMAN-OWNED: the engine runs these files and never writes them, because an agent
that can rewrite its own gate does not have a gate. The master repo's settings
deny engine edits outright; this hook is the same rule enforced from inside the
leaf, for sessions rooted here.

It asks rather than denies: a human deliberately working on the gate approves
the prompt and proceeds. An agent that wandered here while "fixing" a failing
check gets stopped long enough for someone to notice.

Scope note: this guards the file tools (Edit/Write/NotebookEdit and
multi-replace payloads). It does not parse Bash commands — the Stop-hook gate
and the auditor's attack 7 cover that surface.
"""
import json
import sys

PATH_KEYS = {"filePath", "file_path", "path", "notebook_path"}

GUARDED = (
    "/.claude/validate.sh",
    "/.claude/lib/",
    "/.claude/settings.json",
    "/.claude/hooks/",
    "/.claude/commands/",
    "/tools/validate/",
)
# Relative forms, for payloads that don't carry an absolute path.
GUARDED_REL = tuple(g.lstrip("/") for g in GUARDED)


def find_paths(obj):
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in PATH_KEYS and isinstance(v, str):
                found.append(v)
            else:
                found.extend(find_paths(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(find_paths(item))
    return found


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"continue": True}))
        return

    tool = payload.get("tool_name") or payload.get("toolName") or ""
    if tool not in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
        print(json.dumps({"continue": True}))
        return

    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    for p in find_paths(tool_input):
        norm = p.replace("\\", "/")
        if any(g in norm for g in GUARDED) or norm.startswith(GUARDED_REL):
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": (
                        f"'{p}' is part of this repo's human-owned validation "
                        "gate. The Loop Engine must never edit these files "
                        "(a gate the engine can rewrite is not a gate). If you "
                        "are a human deliberately changing the gate, approve "
                        "this; regenerate afterwards is tools/validate/generate.sh."
                    ),
                }
            }))
            return

    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
