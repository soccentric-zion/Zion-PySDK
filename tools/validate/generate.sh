#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# <repo>/tools/validate/generate.sh — emit this repo's validation gate.
#
# generate.sh [--force]
#
# The repo gate is deliberately NOT composed on the fly. It is the fixed floor
# every loop is measured against, so it has to be the same on every run,
# reproducible by a human, and diffable in review. This script is that standard
# tool: it copies the matching template from tools/validate/templates/, and
# installs the shared library, hook and slash command into .claude/.
#
# The loop's *own* verification is the opposite: generated per loop, from the
# test cases the loop file describes. See Zion-Loop-Orchestration-Spec-v2.md
# §7.4 and §7.5.
#
# What it writes into .claude/:
# validate.sh from templates/<stack>.sh, if absent (or --force)
# lib/validate-lib.sh always refreshed — shared contract, single source
# settings.json Stop hook running `validate.sh quick`
# commands/validate.md the/validate slash command
#
# validate.sh is NOT overwritten without --force: repos accumulate hand-written
# checks that are the whole point of having a gate, and clobbering them silently
# would be worse than not generating at all.
#
# This repo's stack is uv, recorded in tools/validate/stack.txt. Edit that
# file (or pass --stack <name>) to switch; the fleet-level fleet-deps.yaml is
# not read from here.
# ---------------------------------------------------------------------------
set -uo pipefail HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)" EXIT_OK=0
EXIT_ERR=1
EXIT_UNAVAILABLE=77 die { echo "generate.sh: $*" >&2; exit "$EXIT_ERR"; }
gone { echo "generate.sh: $*" >&2; exit "$EXIT_UNAVAILABLE"; } STACK=""
FORCE=0
for a in "$@"; do case "$a" in --force) FORCE=1 ;; --stack) shift; STACK="${1:-}" ; shift ;; -h|--help) sed -n '2,30p' "$0"; exit 0 ;; *) die "unknown argument: $a" ;; esac
done
shift $(($# > 0 ? 0 : 0)) # noop placeholder # Read stack from stack.txt if not given on the command line.
if [ -z "$STACK" ] && [ -f "$HERE/stack.txt" ]; then STACK="$(tr -d '[:space:]' < "$HERE/stack.txt")"
fi
[ -n "$STACK" ] || die "no stack: set it in $HERE/stack.txt or pass --stack <name>" local_tpl="$HERE/templates/${STACK}.sh"
[ -f "$local_tpl" ] || die "no template for stack '$STACK' at $local_tpl" mkdir -p "$REPO/.claude/lib" "$REPO/.claude/commands" # Shared contract: always refreshed, never hand-edited per repo.
cp "$HERE/lib/validate-lib.sh" "$REPO/.claude/lib/validate-lib.sh" if [ -f "$REPO/.claude/validate.sh" ] && [ "$FORCE" != "1" ]; then echo " validate.sh exists, kept (use --force to regenerate); lib refreshed"
else repo_name="$(basename "$REPO")" sed "s/@@REPO@@/$repo_name/g; s|@@STACK@@|$STACK|g" "$local_tpl" > "$REPO/.claude/validate.sh" chmod +x "$REPO/.claude/validate.sh" echo " validate.sh generated from $STACK template"
fi cp "$HERE/templates/settings.json" "$REPO/.claude/settings.json"
cp "$HERE/templates/validate-command.md" "$REPO/.claude/commands/validate.md"
# Hooks: session context + gate guard (and any repo-specific hooks templated
# here). Always refreshed, like the library — the live copies in .claude/hooks/
# and the templates must not drift, or a regeneration silently reverts a fix.
if [ -d "$HERE/templates/hooks" ]; then mkdir -p "$REPO/.claude/hooks" cp "$HERE"/templates/hooks/*.py "$REPO/.claude/hooks/" 2>/dev/null || true echo " hooks refreshed from templates/hooks/"
fi echo " settings.json + commands refreshed. Gate ready: ./.claude/validate.sh quick"
