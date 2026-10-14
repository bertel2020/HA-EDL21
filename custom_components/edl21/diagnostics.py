"""Diagnostics for EDL21."""

from __future__ import annotations

from importlib.metadata import version
from typing import Any
from urllib.parse import urlparse

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .sensor import EDL21


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics; host, port and meter id are not included."""
    api: EDL21 = config_entry.runtime_data
    scheme = urlparse(api.serial_port).scheme or "serial"
    return {
        "pysml_version": await hass.async_add_executor_job(version, "pysml"),
        "connection_type": scheme,
        "options": dict(config_entry.options),
        "available": api.available,
        "last_telegram": api.last_telegram.isoformat() if api.last_telegram else None,
        "reconnects": api.reconnects,
        "telegrams_last_minute": api.telegram_rate(),
        "seen_obis": api.seen_obis,
    }
