"""01 — Connect and discover the peripherals on an Acadia device.

Run a fake server in another shell, or point at a real Acadia device:
    python 01_connect_and_discover.py 192.168.1.50:50051
"""
from __future__ import annotations

import sys

import zion_sdk


def main(address: str) -> None:
    with zion_sdk.connect(address) as dev:
        print(f"Connected to {dev.address}")
        print(f"SDK version: {zion_sdk.__version__}")
        print(f"Peripherals ({len(dev.peripherals())}):")
        for module_id in dev.peripherals():
            info = dev.module_info(module_id)
            print(f"  - {module_id:>20}  v{info.version}  ({info.proto_package})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:50051")
