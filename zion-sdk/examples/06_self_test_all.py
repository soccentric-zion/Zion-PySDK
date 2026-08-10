"""06 — Run the full self-test of every peripheral on the device."""
from __future__ import annotations

import sys

import zion_sdk


def main(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        passes = 0
        fails = 0
        for module_id in dev.peripherals():
            print(f"\n=== {module_id} ===")
            try:
                result = dev.peripheral(module_id).self_test(timeout=10.0)
            except zion_sdk.IVVError as e:
                print(f"  ERROR: {e}")
                fails += 1
                continue
            for tr in result.results:
                status = tr.output.status.name
                marker = "PASS" if "PASS" in status else "FAIL"
                print(f"  [{marker}] {tr.name}")
                if marker == "PASS":
                    passes += 1
                else:
                    fails += 1
        print(f"\nSummary: {passes} pass, {fails} fail")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:50051")
