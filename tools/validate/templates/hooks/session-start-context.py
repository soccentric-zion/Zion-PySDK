#!/usr/bin/env python3
"""SessionStart hook — inject the repo state the model would otherwise spend
several tool calls discovering: branch, origin, dirty files, recent commits,
and whether the last gate concern is worth knowing about before editing."""
import json
import os
import subprocess


def git(*args):
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""


root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
if os.path.isdir(root):
    os.chdir(root)

repo = os.path.basename(root)
branch = git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
origin = git("remote", "get-url", "origin") or "none"
dirty = git("status", "--porcelain")
n_dirty = len([l for l in dirty.splitlines() if l.strip()])
recent = git("log", "--oneline", "-3") or "(no commits)"

lines = [
    f"[{repo}] branch: {branch} | origin: {origin} | dirty files: {n_dirty}",
    "recent commits:",
]
lines += [f"  {l}" for l in recent.splitlines()]
if branch.startswith("feature/"):
    slug = branch.split("/", 1)[1]
    lines.append(
        f"NOTE: on a Loop Engine feature branch — commits here must be prefixed [{slug}]."
    )
if branch == "HEAD":
    lines.append("WARNING: detached HEAD — fix before any branch work (make loop-doctor in the master repo).")
lines.append(
    "gate: ./.claude/validate.sh quick (seconds) | full (build+test). "
    "Exit 0 pass, 1-76 fail, 77 GATE-BLOCKED (baseline unverified, never a pass)."
)

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "\n".join(lines),
    }
}))
