"""Button to test the connection to the meter."""

from __future__ import annotations

from homeassistant.components import persistent_notification
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_SERIAL_PORT, DOMAIN, TEST_TIMEOUT

MESSAGES = {
    "en": {
        "title": "EDL21 connection test",
        "ok": "Telegram received. OBIS codes: {obis}.",
        "none": (
            "No telegram within {seconds} s on {port}. Check the reading head, "
            "the USB/ser2net connection and the configured port."
        ),
        "not_ready": "The reader is not running yet.",
    },
    "de": {
        "title": "EDL21-Verbindungstest",
        "ok": "Telegramm empfangen. OBIS-Kennzahlen: {obis}.",
        "none": (
            "Kein Telegramm innerhalb von {seconds} s an {port}. Prüfe Lesekopf, "
            "USB-/ser2net-Verbindung und den konfigurierten Port."
        ),
        "not_ready": "Der Leser läuft noch nicht.",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the test button."""
    async_add_entities([EDL21TestButton(config_entry)])


class EDL21TestButton(ButtonEntity):
    """Waits for the next telegram and reports the result as a notification."""

    _attr_has_entity_name = True
    entity_description = ButtonEntityDescription(
        key="test_connection",
        translation_key="test_connection",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the button."""
        self._entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_test_connection"

    async def async_press(self) -> None:
        """Run the test."""
        texts = MESSAGES.get(self.hass.config.language, MESSAGES["en"])
        api = getattr(self._entry, "runtime_data", None)
        if api is None:
            message = texts["not_ready"]
        elif (obis := await api.async_test()) is None:
            message = texts["none"].format(
                seconds=TEST_TIMEOUT, port=self._entry.data[CONF_SERIAL_PORT]
            )
        else:
            message = texts["ok"].format(obis=", ".join(obis) or "-")
        persistent_notification.async_create(
            self.hass,
            message,
            title=texts["title"],
            notification_id=f"{DOMAIN}_test_{self._entry.entry_id}",
        )
