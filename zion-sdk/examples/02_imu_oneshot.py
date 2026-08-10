"""02 — Run a one-shot test on the IMU peripheral."""
from __future__ import annotations

import sys

import zion_sdk


def main(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        imu = dev.peripheral("imu")
        result = imu.run_oneshot()
        for tr in result.results:
            print(f"{tr.name:<20} status={tr.output.status.name}")
            for key, tv in tr.output.metrics.items():
                print(f"    {key:<18} = {zion_sdk.metric_value(tv)!r}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:50051")
