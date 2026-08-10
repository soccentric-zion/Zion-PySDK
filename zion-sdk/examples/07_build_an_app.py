"""07 — Build a small bench tool: dump every peripheral's status to JSON.

Shows how to combine discovery + run_oneshot + result.to_json() in a small
script you might check into a lab's diagnostic toolbox.
"""
from __future__ import annotations

import json
import sys

import zion_sdk


def collect(address: str) -> dict[str, object]:
    report: dict[str, object] = {"address": address, "results": {}}
    with zion_sdk.connect(address) as dev:
        report["sdk_version"] = zion_sdk.__version__
        report["peripherals"] = dev.peripherals()
        for module_id in dev.peripherals():
            try:
                r = dev.peripheral(module_id).run_oneshot(timeout=5.0)
                report["results"][module_id] = r.to_dict() if r is not None else None  # type: ignore[index]
            except zion_sdk.IVVError as e:
                report["results"][module_id] = {"error": str(e)}  # type: ignore[index]
    return report


def main(address: str) -> None:
    report = collect(address)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:50051")
