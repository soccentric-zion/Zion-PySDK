"""Typed dataclasses for the IV&V SDK (auto-generated)."""
from zion_sdk.types._runtime import (  # noqa: F401
    Timestamp, Duration, AnyMessage,
)
from zion_sdk.types.common import *  # noqa: F401,F403
from zion_sdk.types.hal_service import *  # noqa: F401,F403

# Module dataclasses are NOT star-imported here; access via
# ``zion_sdk.types.modules.<id>`` to avoid name collisions.
from zion_sdk.types import modules  # noqa: F401

MODULE_TYPES: tuple[str, ...] = ('accelerometer', 'analog_input', 'audio_interfaces', 'battery', 'bluetooth', 'camera_interfaces', 'camera_module3', 'can_bus', 'clock_and_timing', 'communication_interface', 'cpu', 'debug_and_development_interfaces', 'deep_learning_accelerator', 'display_interfaces', 'emmc', 'environmental', 'ethernet', 'ethernet_switch', 'external_connector', 'functional_safety', 'gnss', 'gpio', 'gpu', 'i2c', 'imu', 'mcu_interface', 'mipi_csi', 'mipi_dsi', 'nvme', 'pcie', 'poe_hat', 'power_management', 'pwm_output', 'reliability', 'rs485', 'rtc', 'sd_card', 'security_features', 'sense_hat', 'serializer_deserializer', 'software_interface', 'spi', 'storage', 'system_integration', 'system_memory', 'thermal_management', 'uart', 'usb', 'video_encode_decode', 'vision_accelerator', 'watchdog_and_reset')