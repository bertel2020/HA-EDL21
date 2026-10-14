"""Config flow for EDL21 integration."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_SERIAL_PORT,
    CONF_MIN_CHANGE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_MIN_CHANGE,
    DEFAULT_TITLE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

DATA_SCHEMA = vol.Schema({vol.Required(CONF_SERIAL_PORT): str})


async def _async_validate(serial_port: str) -> str | None:
    """Return an error key if the port is obviously unusable."""
    url = urlparse(serial_port)
    if url.scheme == "socket":
        if not url.hostname or not url.port:
            return "invalid_port"
        try:
            async with asyncio.timeout(5):
                _, writer = await asyncio.open_connection(url.hostname, url.port)
        except (OSError, TimeoutError):
            return "cannot_connect"
        writer.close()
        return None
    if url.scheme in ("http", "https"):
        return None
    if serial_port.startswith("/") and not await asyncio.to_thread(
        _path_exists, serial_port
    ):
        return "cannot_connect"
    return None


def _path_exists(path: str) -> bool:
    from os.path import exists  # noqa: PLC0415

    return exists(path)


class EDL21OptionsFlow(OptionsFlowWithReload):
    """Options: how often sensor values are written."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the update interval."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_UPDATE_INTERVAL: int(user_input[CONF_UPDATE_INTERVAL]),
                    CONF_MIN_CHANGE: float(user_input[CONF_MIN_CHANGE]),
                }
            )
        current = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        change = self.config_entry.options.get(CONF_MIN_CHANGE, DEFAULT_MIN_CHANGE)
        schema = vol.Schema(
            {
                vol.Required(CONF_UPDATE_INTERVAL, default=current): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=3600,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Required(CONF_MIN_CHANGE, default=change): NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        max=10000,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="W",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


class EDL21ConfigFlow(ConfigFlow, domain=DOMAIN):
    """EDL21 config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> EDL21OptionsFlow:
        """Return the options flow."""
        return EDL21OptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle the user setup step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match(
                {CONF_SERIAL_PORT: user_input[CONF_SERIAL_PORT]}
            )
            if not (error := await _async_validate(user_input[CONF_SERIAL_PORT])):
                return self.async_create_entry(title=DEFAULT_TITLE, data=user_input)
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(DATA_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the serial port / ser2net address of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match(
                {CONF_SERIAL_PORT: user_input[CONF_SERIAL_PORT]}
            )
            if not (error := await _async_validate(user_input[CONF_SERIAL_PORT])):
                return self.async_update_reload_and_abort(
                    entry, data_updates=user_input
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                DATA_SCHEMA, user_input or entry.data
            ),
            errors=errors,
        )
