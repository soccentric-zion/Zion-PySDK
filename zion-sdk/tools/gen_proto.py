#!/usr/bin/env python3
"""Generate gRPC stubs into ``src/zion_sdk/_proto``.

Reads the canonical proto contracts from ``../Zion-HAL/protos`` (relative to
the repo root containing this SDK), runs ``grpc_tools.protoc``, and post-processes
the generated files so their imports work as a vendored sub-package.

Run from the SDK repo root:

    python tools/gen_proto.py
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SDK_ROOT = HERE.parent
# Zion-PySDK/zion-sdk → Zion-PySDK → Zion (which holds the HAL protos).
DEFAULT_PROTOS = (SDK_ROOT.parent.parent / "Zion-HAL" / "protos").resolve()
OUT_DIR = SDK_ROOT / "src" / "zion_sdk" / "_proto"

# Proto files we consume (we DO NOT vendor client_service.proto — the SDK
# replaces Server by speaking HalService directly; ClientService is Server's
# inbound bidi stream, out of scope).
TOP_LEVEL_PROTOS = ["common.proto", "hal_service.proto"]
MODULES_GLOB = "modules/*.proto"

# Imports we rewrite. Generated files emit ``import common_pb2 as ...`` and
# ``import hal_service_pb2 as ...`` at top level; we make them package-qualified.
IMPORT_REWRITES = {
    "common_pb2": "zion_sdk._proto.common_pb2",
    "hal_service_pb2": "zion_sdk._proto.hal_service_pb2",
}


def rewrite_imports(path: Path) -> None:
    text = path.read_text()
    original = text
    for short, full in IMPORT_REWRITES.items():
        # ``import common_pb2 as common__pb2`` → ``from zion_sdk._proto import common_pb2 as common__pb2``
        text = re.sub(
            rf"^import {re.escape(short)} as (\S+)$",
            rf"from zion_sdk._proto import {short} as \1",
            text,
            flags=re.MULTILINE,
        )
        # Bare ``import common_pb2`` (grpc files)
        text = re.sub(
            rf"^import {re.escape(short)}$",
            rf"from zion_sdk._proto import {short}",
            text,
            flags=re.MULTILINE,
        )
    # Module pb2 files reference each module's sibling — rewrite ``import modules.<name>_pb2``
    text = re.sub(
        r"^from modules import (\S+_pb2) as (\S+)$",
        r"from zion_sdk._proto.modules import \1 as \2",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^import modules\.(\S+_pb2)$",
        r"from zion_sdk._proto.modules import \1",
        text,
        flags=re.MULTILINE,
    )
    if text != original:
        path.write_text(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protos",
        type=Path,
        default=DEFAULT_PROTOS,
        help=f"Path to the HAL protos directory (default: {DEFAULT_PROTOS}).",
    )
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    protos_dir: Path = args.protos.resolve()
    out_dir: Path = args.out.resolve()

    if not protos_dir.exists():
        print(f"error: protos dir not found: {protos_dir}", file=sys.stderr)
        return 2

    # Discover proto files.
    proto_files: list[Path] = []
    for p in TOP_LEVEL_PROTOS:
        full = protos_dir / p
        if not full.exists():
            print(f"error: missing proto: {full}", file=sys.stderr)
            return 2
        proto_files.append(full)
    module_protos = sorted((protos_dir / "modules").glob("*.proto"))
    proto_files.extend(module_protos)
    print(f"[gen_proto] {len(proto_files)} proto files from {protos_dir}")

    # Wipe + recreate output dir (preserves __init__.py via re-creation below).
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    (out_dir / "modules").mkdir()

    # Add venv bin to PATH so protoc can find mypy plugins
    venv_bin = SDK_ROOT.parent / ".venv" / "bin"
    if venv_bin.exists():
        os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"

    # protoc invocation. Use grpc_tools.protoc programmatically.
    from grpc_tools import protoc  # type: ignore[import-untyped]
    import grpc_tools  # type: ignore[import-untyped]

    # Well-known protos (google/protobuf/timestamp.proto etc.) ship with
    # grpc_tools under ``grpc_tools/_proto``; add them as a second include path
    # so protoc can resolve ``import "google/protobuf/timestamp.proto"``.
    well_known_include = Path(grpc_tools.__file__).resolve().parent / "_proto"

    argv = [
        "protoc",
        f"-I{protos_dir}",
        f"-I{well_known_include}",
        f"--python_out={out_dir}",
        f"--grpc_python_out={out_dir}",
        f"--mypy_out={out_dir}",
        f"--mypy_grpc_out={out_dir}",
        *[str(p.relative_to(protos_dir)) for p in proto_files],
    ]
    # grpc_tools.protoc needs argv0 + the well-known proto include path.
    rc = protoc.main(argv)
    if rc != 0:
        print(f"error: protoc failed with exit code {rc}", file=sys.stderr)
        return rc

    # Make ``modules/`` a real package and post-process every generated file.
    (out_dir / "modules" / "__init__.py").write_text(
        '"""Generated per-module protobuf bindings (vendored).\n\nDo not import directly — use ``zion_sdk.types`` instead.\n"""\n'
    )
    for f in out_dir.rglob("*.py"):
        rewrite_imports(f)
    # Also rewrite imports in .pyi stub files
    for f in out_dir.rglob("*.pyi"):
        rewrite_imports(f)

    # Top-level package __init__.
    (out_dir / "__init__.py").write_text(
        '"""Vendored gRPC stubs for the Zion HAL contract (PRIVATE).\n\nCustomers MUST NOT import from this package. Use ``zion_sdk`` instead.\n"""\n'
    )

    n_py_files = sum(1 for _ in out_dir.rglob("*.py"))
    n_pyi_files = sum(1 for _ in out_dir.rglob("*.pyi"))
    print(f"[gen_proto] wrote {n_py_files} Python files and {n_pyi_files} stub files under {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
