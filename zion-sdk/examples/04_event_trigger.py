"""04 — Arm an event trigger on the IMU and react when it fires."""
from __future__ import annotations

import sys

import zion_sdk


def main(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        imu = dev.peripheral("imu")
        # Simple form: fire whenever the named test PASSES.
        for event in imu.arm_event(test_name="accel_read", expected_pass=True):
            print(f"Event fired: {event.results[0].name}")
            # Break out after the first event for the demo.
            break

        # Freeform expression form (evaluated server-side):
        for event in imu.arm_event(expression="accel_x > 0.5"):
            print(f"Threshold event: {event.results[0].name}")
            break


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:50051")
