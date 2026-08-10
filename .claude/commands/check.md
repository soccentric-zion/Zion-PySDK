---
description: The repo's own full gate — lint + typecheck + test via uv
allowed-tools: Bash(make check), Bash(make setup)
--- !`make check` Exit 2 with venv-flavoured errors usually means .venv is missing or half-built —
run make setup first; that is a provisioning problem, not a code failure.
make typecheck must run with --config-file zion-sdk/pyproject.toml (the
Makefile does this) or mypy reports ~153 false errors in generated modules.
