"""03 — Stream periodic IMU samples for 2 seconds."""
from __future__ import annotations

import sys

import zion_sdk


def main(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        imu = dev.peripheral("imu")
        for i, snapshot in enumerate(imu.monitor(period_ms=100, duration_s=2.0)):
            metrics = snapshot.results[0].output.metrics
            ax = metrics["accel_x"].double_value
            print(f"sample #{i:>3}  accel_x={ax:+.3f} g")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:50051")
