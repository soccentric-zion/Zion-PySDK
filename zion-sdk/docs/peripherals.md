# Peripherals Every HAL module advertised in the peer's registry shows up as a
`Peripheral` you can fetch with `device.peripheral(id)`. The SDK does
not hard-code the module list — it asks the peer at `connect` time
via `ListModules` and trusts whatever comes back, so adding a new
module to the HAL registry makes it instantly available through the SDK
without an SDK release. ## Discovering what's available ```python
for pid in dev.peripherals: info = dev.module_info(pid) print(pid, "→", info.proto_package, "v", info.version)
``` ## Per-module `Config` and `Result` Every module ships a `Config` and a `Result` message in
`hal.modules.<id>.*`. The SDK generates dataclasses for both: ```python
from zion_sdk.types.modules import imu # Build a config the verbose way:
cfg = imu.Config(test_names=["accel_read"]) # Or, equivalently, let the SDK build it for you:
imu_p = dev.peripheral("imu")
result = imu_p.run_oneshot(tests=["accel_read"])
``` The keyword arguments to `run_oneshot`, `monitor`, `arm_event`, and
`start_long_running` are passed straight to the per-module `Config`
constructor, so any field name on `imu.Config` is acceptable. ## Capabilities `Peripheral.capabilities` returns the set of supported capability
tags. In contract v1 this is uniform across modules: ```python
{"oneshot", "long_running", "monitor", "event", "self_test", "pause", "resume", "stop"}
``` A future contract version that adds a typed capability field on
`ModuleInfo` will refine this automatically. ## Currently-registered modules The list below was the registry at the time of this release; check
`dev.peripherals` against your peer for the live set. ```
audio, can_bus, cellular_modem, communication, cpu, csv,
data_storage, display, emmc, environmental, ethernet,
ethernet_switch, external_connector, functional_safety,
gnss, gpio, gpu, i2c, imu, mcu_interface, mipi_csi, mipi_dsi,
nvme, pcie, poe_hat, power_management, pwm_output,
reliability, rs485, rtc, sd_card, security_features,
sense_hat, serializer_deserializer, software_interface, spi,
storage, system_integration, system_memory,
thermal_management, uart, usb, video_encode_decode,
vision_accelerator, watchdog_and_reset
```
(51 modules.)
