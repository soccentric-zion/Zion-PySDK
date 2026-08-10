# Zion-PySDK — top-level orchestration (uv-managed)
#
# Uses `uv` (https://github.com/astral-sh/uv) for fast, reproducible venvs.
#
# Usage:
# make # setup + check (lint + typecheck + test)
# make setup # create uv venv and install zion-sdk[dev] in editable mode
# make gen # regenerate proto + dataclass bindings
# make gen-check # fail if committed stubs are stale (regen → diff → revert)
# make gen-clean # wipe generated stubs + full regen
# make test # run pytest suite
# make lint # ruff
# make typecheck # mypy --strict
# make check # lint + typecheck + test
# make build # build wheel + sdist
# make shell # drop into a uv-activated subshell
# make clean # remove build artefacts
# make distclean # also remove the venv SHELL :=/bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all UV ?= uv
VENV ?= .venv
SDK_DIR := zion-sdk
STAMP_DIR := $(VENV)/.stamps
INSTALL_STAMP := $(STAMP_DIR)/installed # Generated output directory (must match tools/gen_proto.py OUT_DIR)
PROTO_OUT := $(SDK_DIR)/src/zion_sdk/_proto # ANSI colours
ifneq (,$(findstring xterm,$(TERM))) C_BOLD := \033[1m C_OK := \033[32m C_DIM := \033[2m C_END := \033[0m
else C_BOLD := C_OK := C_DIM := C_END :=
endif define banner @printf "$(C_BOLD)==> %s$(C_END)\n" "$(1)"
endef # ── Aggregate ─────────────────────────────────────────────────────────────────
.PHONY: all help check
all: check help: ## Show this help @printf "$(C_BOLD)Zion-PySDK$(C_END) — uv-managed targets\n\n" @awk 'BEGIN {FS=":.*##"}/^[a-zA-Z_-]+:.*##/ {printf " $(C_OK)%-14s$(C_END) %s\n", $$1, $$2}' $(MAKEFILE_LIST) check: lint typecheck test ## Run lint + typecheck + test # ── Environment ───────────────────────────────────────────────────────────────
.PHONY: setup venv install
setup: $(INSTALL_STAMP) ## Create uv venv + install zion-sdk[dev] in editable mode venv: $(VENV)/bin/python ## Create the virtualenv only $(VENV)/bin/python: $(call banner,Creating uv venv at $(VENV)) @$(UV) venv $(VENV) $(INSTALL_STAMP): $(VENV)/bin/python $(SDK_DIR)/pyproject.toml $(call banner,Installing zion-sdk[dev] in editable mode via uv) @$(UV) pip install --python $(VENV)/bin/python -e "$(SDK_DIR)[dev]" @mkdir -p $(STAMP_DIR) @touch $(INSTALL_STAMP) # ── Proto generation ──────────────────────────────────────────────────────────
.PHONY: gen gen-check gen-clean gen: $(INSTALL_STAMP) ## Regenerate proto + dataclass bindings from Acadia-HAL/protos $(call banner,Regenerating proto bindings) @$(VENV)/bin/python $(SDK_DIR)/tools/gen_proto.py $(call banner,Regenerating dataclass bindings) @$(VENV)/bin/python $(SDK_DIR)/tools/gen_types.py gen-check: $(INSTALL_STAMP) ## Fail if committed stubs are stale $(call banner,Checking proto stubs are up-to-date) @tmpdir=$$(mktemp -d); \ cp -a $(PROTO_OUT) "$$tmpdir/proto_before"; \ $(VENV)/bin/python $(SDK_DIR)/tools/gen_proto.py 2>/dev/null; \ $(VENV)/bin/python $(SDK_DIR)/tools/gen_types.py 2>/dev/null; \ if ! diff -rq --exclude="__pycache__" "$$tmpdir/proto_before" $(PROTO_OUT) >/dev/null 2>&1; then \ echo "gen-check FAILED — stubs are stale; run 'make gen' and commit."; \ rm -rf "$$tmpdir"; \ exit 1; \ fi; \ rm -rf "$$tmpdir"; \ echo "gen-check passed — stubs are up-to-date." gen-clean: ## Wipe generated stubs and do a full clean regen $(call banner,Removing generated stubs) @rm -rf $(PROTO_OUT) @$(MAKE) gen # ── Tests + linting ───────────────────────────────────────────────────────────
.PHONY: test lint typecheck build test: $(INSTALL_STAMP) ## Run pytest with coverage $(call banner,Running test suite) @cd $(SDK_DIR) && ../$(VENV)/bin/python -m pytest tests \ --cov=zion_sdk --cov-report=term-missing -q lint: $(INSTALL_STAMP) ## Run ruff $(call banner,Linting with ruff) @$(VENV)/bin/python -m ruff check $(SDK_DIR)/src/zion_sdk typecheck: $(INSTALL_STAMP) ## Run mypy --strict $(call banner,Type-checking with mypy --strict) @$(VENV)/bin/python -m mypy --strict --config-file $(SDK_DIR)/pyproject.toml $(SDK_DIR)/src/zion_sdk build: $(INSTALL_STAMP) ## Build sdist + wheel $(call banner,Building distribution artefacts) @$(UV) pip install --python $(VENV)/bin/python --quiet build @$(VENV)/bin/python -m build --outdir $(SDK_DIR)/dist $(SDK_DIR) # ── Convenience ───────────────────────────────────────────────────────────────
.PHONY: shell
shell: $(INSTALL_STAMP) ## Drop into a uv-activated subshell @source $(VENV)/bin/activate && exec $${SHELL:-bash} # ── Cleanup ───────────────────────────────────────────────────────────────────
.PHONY: clean distclean
clean: ## Remove build artefacts (keeps venv) @rm -rf $(SDK_DIR)/build $(SDK_DIR)/dist $(SDK_DIR)/*.egg-info @rm -rf $(SDK_DIR)/.pytest_cache $(SDK_DIR)/.mypy_cache $(SDK_DIR)/.ruff_cache @rm -rf $(SDK_DIR)/htmlcov $(SDK_DIR)/.coverage @find $(SDK_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true distclean: clean ## Also remove the uv venv $(call banner,Removing venv) @rm -rf $(VENV) $(STAMP_DIR)
