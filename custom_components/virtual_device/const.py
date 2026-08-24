"""Constants for the Virtual Device Manager integration."""

from __future__ import annotations

from .device_class_metadata import DEVICE_CLASS_METADATA

DOMAIN = "virtual_device"
NAME = "Virtual Device Manager"

STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN

PLATFORMS: list[str] = ["sensor"]

AGGREGATIONS: tuple[str, ...] = (
    "avg",
    "max",
    "median",
    "min",
    "sum",
)

SUPPORTED_DEVICE_CLASSES: dict[str, str] = {
    device_class: metadata.native_unit
    for device_class, metadata in DEVICE_CLASS_METADATA.items()
}
