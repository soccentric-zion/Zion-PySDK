"""05 — Long-running test in the background while doing other work."""
from __future__ import annotations

import sys
import time

import zion_sdk


def main(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        cpu = dev.peripheral("cpu")
        session = cpu.start_long_running(interval_ms=500, duration_s=5.0)
        print(f"Started {session}")
        try:
            deadline = time.time() + 4.0
            while time.time() < deadline:
                latest = cpu.query_long_running(block=True, timeout=1.0)
                if latest is None:
                    break
                print(f"  latest: {latest.results[0].output.status.name}")
        finally:
            cpu.stop_long_running()
            print("Session stopped.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:50051")
