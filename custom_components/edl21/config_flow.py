"""Config flow for EDL21 integration."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
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
    SerialPortSelector,
    TextSelector,
)

from .const import (
    CONF_MIN_CHANGE,
    CONF_SERIAL_PORT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_MIN_CHANGE,
    DEFAULT_TITLE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

CONF_HOST = "host"
CONF_PORT = "port"
DEFAULT_TCP_PORT = 2000

USB_SCHEMA = vol.Schema({vol.Required(CONF_SERIAL_PORT): SerialPortSelector()})
TCP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(),
        vol.Required(CONF_PORT, default=DEFAULT_TCP_PORT): NumberSelector(
            NumberSelectorConfig(min=1, max=65535, step=1, mode=NumberSelectorMode.BOX)
        ),
    }
)


async def _async_validate(serial_port: str) -> str | None:
    """Return an error key if the port is obviously unusable."""
    url = urlparse(serial_port)
    if url.scheme == "socket":
        if not url.hostname or not url.port:
            return "invalid_port"
        try:
            async with asyncio.timeout(5):
                _, writer = await asyncio.open_connection(url.hostname, url.port)
        except OSError, TimeoutError:
            return "cannot_connect"
        writer.close()
        return None
    if url.scheme in ("http", "https"):
        return None
    if serial_port.startswith("/") and not await asyncio.to_thread(_path_exists, serial_port):
        return "cannot_connect"
    return None


def _path_exists(path: str) -> bool:
    from os.path import exists  # noqa: PLC0415

    return exists(path)


class EDL21OptionsFlow(OptionsFlowWithReload):
    """Options: how often sensor values are written."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the update interval."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_UPDATE_INTERVAL: int(user_input[CONF_UPDATE_INTERVAL]),
                    CONF_MIN_CHANGE: float(user_input[CONF_MIN_CHANGE]),
                }
            )
        current = self.config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
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

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose how the reading head is connected."""
        return self.async_show_menu(step_id="user", menu_options=["usb", "tcp"])

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the connection type for an existing entry."""
        return self.async_show_menu(step_id="reconfigure", menu_options=["usb", "tcp"])

    async def _async_finish(self, serial_port: str) -> ConfigFlowResult | str:
        """Validate and store the port; return an error key on failure."""
        self._async_abort_entries_match({CONF_SERIAL_PORT: serial_port})
        if error := await _async_validate(serial_port):
            return error
        data = {CONF_SERIAL_PORT: serial_port}
        if self.source == SOURCE_RECONFIGURE:
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(), data_updates=data
            )
        return self.async_create_entry(title=DEFAULT_TITLE, data=data)

    def _current_port(self) -> str | None:
        if self.source == SOURCE_RECONFIGURE:
            return self._get_reconfigure_entry().data.get(CONF_SERIAL_PORT)
        return None

    async def async_step_usb(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Select a USB / serial device."""
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._async_finish(user_input[CONF_SERIAL_PORT])
            if not isinstance(result, str):
                return result
            errors["base"] = result
        suggested = user_input
        if suggested is None and (port := self._current_port()):
            suggested = {} if urlparse(port).scheme else {CONF_SERIAL_PORT: port}
        return self.async_show_form(
            step_id="usb",
            data_schema=self.add_suggested_values_to_schema(USB_SCHEMA, suggested),
            errors=errors,
        )

    async def async_step_tcp(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Enter a ser2net / TCP address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            if not host or "/" in host or ":" in host.strip("[]"):
                errors["base"] = "invalid_port"
            else:
                result = await self._async_finish(f"socket://{host}:{port}")
                if not isinstance(result, str):
                    return result
                errors["base"] = result
        suggested = user_input
        if suggested is None and (current := self._current_port()):
            url = urlparse(current)
            if url.scheme == "socket" and url.hostname and url.port:
                suggested = {CONF_HOST: url.hostname, CONF_PORT: url.port}
        return self.async_show_form(
            step_id="tcp",
            data_schema=self.add_suggested_values_to_schema(TCP_SCHEMA, suggested),
            errors=errors,
        )
