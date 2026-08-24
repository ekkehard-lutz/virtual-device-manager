"""Translation resource loading for the VDM custom panel."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from homeassistant.core import HomeAssistant

DEFAULT_LANGUAGE = "en"
TRANSLATIONS_PATH = Path(__file__).parent / "translations"


def normalize_language(language: str | None, available: set[str]) -> str:
    """Resolve a Home Assistant language or variant to an available language."""
    normalized = (language or DEFAULT_LANGUAGE).lower().replace("_", "-")
    candidates = (normalized, normalized.split("-", 1)[0], DEFAULT_LANGUAGE)
    return next(
        (candidate for candidate in candidates if candidate in available),
        DEFAULT_LANGUAGE,
    )


def _merge(base: dict, override: dict) -> dict:
    """Recursively merge a translation over the English fallback."""
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _load_resources() -> dict[str, dict]:
    """Read integration translation resources from disk."""
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in TRANSLATIONS_PATH.glob("*.json")
    }


async def async_load_translation_resources(hass: HomeAssistant) -> dict[str, dict]:
    """Load translation resources without blocking Home Assistant's event loop."""
    return await hass.async_add_executor_job(_load_resources)


def panel_translations(resources: dict[str, dict], language: str | None) -> dict:
    """Return panel messages with complete English fallback coverage."""
    selected = normalize_language(language, set(resources))
    english = resources.get(DEFAULT_LANGUAGE, {}).get("panel", {})
    localized = resources.get(selected, {}).get("panel", {})
    return {
        "language": selected,
        "messages": _merge(english, localized),
    }
