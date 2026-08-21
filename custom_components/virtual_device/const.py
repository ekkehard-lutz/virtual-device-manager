"""Constants for the Virtual Device Manager integration."""

from __future__ import annotations

DOMAIN = "virtual_device"
NAME = "Virtual Device Manager"

STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN

PLATFORMS: list[str] = ["sensor"]

AGGREGATIONS: tuple[str, ...] = (
    "sum",
    "avg",
    "min",
    "max",
)

SUPPORTED_DEVICE_CLASSES: dict[str, str | None] = {
    "power": "W",
    "energy": "Wh",
}
