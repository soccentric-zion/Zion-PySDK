# shellcheck shell=bash
# ---------------------------------------------------------------------------
# Zion per-repo validation library
#
# Sourced by <repo>/.claude/validate.sh. Implements the same three-way exit
# contract the Loop Engine's tools/ layer uses, so QA can consume a repo-level
# validation run exactly like a hardware check.
#
#   0        every check ran and passed          -> QA verdict PASS
#   1..76    a check ran and failed              -> QA verdict FAIL
#   77       a check could not run at all        -> QA verdict GATE-BLOCKED
#
# The whole point of 77 is honesty. A leaf Makefile that skips cppcheck because
# cppcheck isn't installed still exits 0 — a green light that checked nothing.
# This layer refuses to inherit that: an absent toolchain is 77, never PASS.
#
# READ 77 FROM A GATE CORRECTLY. Everywhere else in this engine, 77 means "the
# hardware isn't there, a human must intervene" and QA records a BLOCKED that
# rides along to in-review/ as a checklist item. A 77 from THIS layer means
# something different and stricter: this host was never provisioned to check
# anything, so the repo's baseline is unverified and every acceptance criterion
# measured against it sits on an unknown floor. It is a provisioning failure of
# the host, not a property of the loop, and it must never close a loop.
# See .claude/agents/qa.md ("GATE-BLOCKED") and loop/tools/preflight.sh, which
# runs before the Executor so this case is caught in seconds rather than after
# an hour of work. It went wrong once: 20260728-dashboard-live-run-monitor
# try-1 recorded Zion-Server's 77 (clang-tidy, clang-format absent) as a
# BLOCKED, and the loop closed green with nothing built.
#
# HUMAN-OWNED. The Loop Engine may run these scripts. It may never edit them.
# An agent that can rewrite its own gate does not have a gate.
# ---------------------------------------------------------------------------

set -o pipefail

EXIT_PASS=0
EXIT_FAIL=1
EXIT_BLOCKED=77

_n_pass=0
_n_fail=0
_n_blocked=0
_n_note=0
_lines=()

# Longest single check, in seconds. A build that hangs is a FAIL, not a BLOCKED —
# it consumed the resources and produced no result (see .claude/agents/qa.md).
: "${ARCHES_VALIDATE_TIMEOUT:=900}"

# When 1, a run whose checks all passed except for blocked ones exits 0 instead
# of 77. Off by default: a partial run must not read as a clean pass.
: "${ARCHES_VALIDATE_ALLOW_PARTIAL:=0}"

_repo_root() { cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd; }

# Run from the repo root regardless of where the caller invoked us from, so a
# validate.sh can test relative paths at the top level and not just inside check().
cd "$(_repo_root)" || exit 2

have() { command -v "$1" >/dev/null 2>&1; }

# Echo the subset of "$@" that is not on PATH.
missing_tools() {
  local t missing=()
  for t in "$@"; do have "$t" || missing+=("$t"); done
  echo "${missing[*]-}"
}

_record() {
  local verdict="$1" name="$2" detail="$3"
  _lines+=("[$verdict] $name — $detail")
  case "$verdict" in
    PASS)    _n_pass=$((_n_pass + 1)) ;;
    FAIL)    _n_fail=$((_n_fail + 1)) ;;
    BLOCKED) _n_blocked=$((_n_blocked + 1)) ;;
    NOTE)    _n_note=$((_n_note + 1)) ;;
  esac
}

# check <name> <space-separated required tools> <command>
#
# Blocks (77) if any required tool is absent — that is the case the leaf
# Makefiles get wrong. Otherwise runs the command and reports its real exit code.
check() {
  local name="$1" needs="$2" cmd="$3"
  local missing out rc

  # shellcheck disable=SC2086
  missing="$(missing_tools $needs)"
  if [ -n "$missing" ]; then
    _record BLOCKED "$name" "not run; missing tool(s): $missing"
    return 0
  fi

  out="$(cd "$(_repo_root)" && timeout "$ARCHES_VALIDATE_TIMEOUT" bash -c "$cmd" 2>&1)"
  rc=$?

  if [ "$rc" -eq 0 ]; then
    _record PASS "$name" "\`$cmd\`, exit 0"
  elif [ "$rc" -eq "$EXIT_BLOCKED" ]; then
    # The command itself speaks the contract (e.g. anything under tools/).
    # Honour its 77 rather than flattening it into a FAIL.
    _record BLOCKED "$name" "\`$cmd\`, exit 77: $(printf '%s' "$out" | tail -n 3 | tr '\n' ' ')"
  elif [ "$rc" -eq 127 ]; then
    # Command not found. Definitionally "never ran", so BLOCKED rather than
    # FAIL — this catches tooling that isn't on PATH at all, like a project
    # virtualenv that was never created.
    _record BLOCKED "$name" "\`$cmd\`, exit 127 (command not found): $(printf '%s' "$out" | tail -n 3 | tr '\n' ' ')"
  elif [ "$rc" -eq 124 ]; then
    _record FAIL "$name" "\`$cmd\` timed out after ${ARCHES_VALIDATE_TIMEOUT}s"
    _lines+=("$(printf '%s' "$out" | tail -n 15 | sed 's/^/        /')")
  else
    _record FAIL "$name" "\`$cmd\`, exit $rc:"
    _lines+=("$(printf '%s' "$out" | tail -n 25 | sed 's/^/        /')")
  fi
}

# assert <name> <command> — a check with no external tool dependency.
# Use for repo-shape invariants: a file exists, a manifest parses, a fence is intact.
assert() { check "$1" "" "$2"; }

# Strip // and # line comments from stdin. Rules about what a repo must NOT
# contain are otherwise trivially tripped by a comment explaining the rule.
strip_comments() { sed -E 's://.*$::; s:(^|[[:space:]])#.*$::'; }

# block <name> <reason> — record a BLOCKED explicitly, for a check that is known
# to be unrunnable here (needs hardware, needs a human). Never use this to dodge
# a check that could have run.
block() { _record BLOCKED "$1" "$2"; }

# note <name> <detail> — record a KNOWN, TRACKED divergence without affecting
# the exit code.
#
# This exists for one narrow case: a repo state that is wrong-but-intended, where
# a filed loop already owns the fix. The alternative is a gate that fails every
# run for a reason nobody is going to act on today — and a permanently red gate
# teaches people to ignore gates, which costs more than the check is worth.
#
# The bar is deliberately high. A note MUST name the loop or issue that tracks
# it. If nothing tracks it, it is a FAIL and you should file the loop. Never use
# note() to soften a check you'd rather not see fail, and never for anything the
# loop under test could have caused — that is laundering a regression into a
# footnote, and the auditor reads these lines specifically looking for it.
note() { _record NOTE "$1" "$2"; }

report() {
  local tier="$1" repo
  repo="$(basename "$(_repo_root)")"

  echo "# Validation — $repo ($tier)"
  echo
  printf '%s\n' "${_lines[@]}"
  echo
  if [ "$_n_note" -gt 0 ]; then
    echo "Summary: ${_n_pass} passed, ${_n_fail} failed, ${_n_blocked} blocked," \
         "${_n_note} tracked divergence(s) noted"
  else
    echo "Summary: ${_n_pass} passed, ${_n_fail} failed, ${_n_blocked} blocked"
  fi

  if [ "$_n_fail" -gt 0 ]; then
    echo "Result: FAIL"
    return "$EXIT_FAIL"
  fi
  if [ "$_n_blocked" -gt 0 ] && [ "$ARCHES_VALIDATE_ALLOW_PARTIAL" != "1" ]; then
    echo "Result: GATE-BLOCKED (77) — ${_n_blocked} check(s) never ran, so this"
    echo "        repo's baseline is UNVERIFIED. This is a host-provisioning"
    echo "        failure, not a hardware BLOCKED: it must not close a loop."
    echo "        Install the missing tooling above, or re-run with"
    echo "        ARCHES_VALIDATE_ALLOW_PARTIAL=1 to accept a partial run"
    echo "        knowingly. Never treated as a pass."
    return "$EXIT_BLOCKED"
  fi
  if [ "$_n_pass" -eq 0 ]; then
    echo "Result: GATE-BLOCKED (77) — no check ran at all."
    return "$EXIT_BLOCKED"
  fi
  echo "Result: PASS"
  return "$EXIT_PASS"
}

# Guard against a validate.sh that defines no checks for its tier.
tier_or_die() {
  local tier="$1"
  case "$tier" in
    quick|full) echo "$tier" ;;
    "")         echo "quick" ;;
    *)          echo "usage: validate.sh [quick|full]" >&2; exit 2 ;;
  esac
}
