"""Tests for the EDL21 integration."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.edl21.const import DOMAIN

POWER = {"objName": "1-0:16.7.0*255", "value": 250, "unit": "W"}
UNKNOWN = {"objName": "1-0:99.99.9*255", "value": 7, "unit": None}


async def _setup(hass: HomeAssistant, **options) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data={"serial_port": "socket://1.2.3.4:2000"}, options=options
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_config_flow_and_options(hass: HomeAssistant, hass_client) -> None:
    """Menu -> TCP entry via the real HTTP API (checks form serialization), then options."""
    assert await async_setup_component(hass, "config", {})
    assert await async_setup_component(hass, "usb", {})
    client = await hass_client()
    with (
        patch(
            "custom_components.edl21.config_flow.asyncio.open_connection",
            AsyncMock(return_value=(None, AsyncMock(close=lambda: None))),
        ),
        patch("custom_components.edl21.async_setup_entry", return_value=True),
    ):
        resp = await client.post("/api/config/config_entries/flow", json={"handler": DOMAIN})
        flow = await resp.json()
        assert flow["type"] == "menu"
        assert flow["menu_options"] == ["usb", "tcp"]

        # both forms must serialize (selectors)
        for step in ("usb", "tcp"):
            resp = await client.post(
                f"/api/config/config_entries/flow/{flow['flow_id']}",
                json={"next_step_id": step},
            )
            assert (await resp.json())["type"] == "form"
            resp = await client.post("/api/config/config_entries/flow", json={"handler": DOMAIN})
            flow = await resp.json()

        resp = await client.post(
            f"/api/config/config_entries/flow/{flow['flow_id']}",
            json={"next_step_id": "tcp"},
        )
        resp = await client.post(
            f"/api/config/config_entries/flow/{flow['flow_id']}",
            json={"host": "1.2.3.4", "port": 2000},
        )
        result = await resp.json()
        assert result["type"] == "create_entry"
        entry = hass.config_entries.async_entries(DOMAIN)[0]
        assert entry.data == {"serial_port": "socket://1.2.3.4:2000"}

        resp = await client.post(
            "/api/config/config_entries/options/flow", json={"handler": entry.entry_id}
        )
        flow = await resp.json()
        assert flow["type"] == "form"
        resp = await client.post(
            f"/api/config/config_entries/options/flow/{flow['flow_id']}",
            json={"update_interval": 30, "min_change": 5},
        )
        assert (await resp.json())["type"] == "create_entry"
    assert entry.options == {"update_interval": 30, "min_change": 5.0}


async def test_sensors_availability_and_removal(hass: HomeAssistant, sml, freezer) -> None:
    """Telegrams create sensors; silence makes them unavailable; entry is removable."""
    entry = await _setup(hass, update_interval=1)
    sml([POWER, UNKNOWN])
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    unique_ids = {e.unique_id: e for e in registry.entities.values()}
    assert "0a0145_1-0:16.7.0*255" in unique_ids
    # unknown OBIS: registered but disabled by default
    assert unique_ids["0a0145_1-0:99.99.9*255"].disabled
    assert hass.states.get("sensor.smart_meter_last_telegram") is not None

    power = unique_ids["0a0145_1-0:16.7.0*255"].entity_id
    assert hass.states.get(power).state == "250"

    # identifiers are written on change, ignoring the update interval
    sml([{"objName": "1-0:0.2.0*1", "value": "v1"}])
    await hass.async_block_till_done()
    sml([{"objName": "1-0:0.2.0*1", "value": "v2"}])
    await hass.async_block_till_done()
    firmware = registry.async_get_entity_id("sensor", DOMAIN, "0a0145_1-0:0.2.0*1")
    assert hass.states.get(firmware).state == "v2"

    freezer.tick(timedelta(seconds=400))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(power).state == STATE_UNAVAILABLE
    assert hass.states.get("sensor.smart_meter_last_telegram").state != STATE_UNAVAILABLE

    freezer.tick(timedelta(seconds=300))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"no_data_{entry.entry_id}")

    sml([POWER])
    await hass.async_block_till_done()
    assert hass.states.get(power).state == "250"
    assert not ir.async_get(hass).async_get_issue(DOMAIN, f"no_data_{entry.entry_id}")

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_reconfigure_usb(hass: HomeAssistant, sml, tmp_path) -> None:
    """Reconfigure switches from TCP to a serial device."""
    entry = await _setup(hass)
    device = tmp_path / "ttyUSB0"
    device.touch()
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == "menu"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "usb"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"serial_port": str(device)}
    )
    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["serial_port"] == str(device)


async def test_diagnostics_button_and_multiple_meters(hass: HomeAssistant, sml) -> None:
    """Reconnect counter, test button and two meters on one reading head."""
    entry = await _setup(hass)
    sml([POWER])
    sml([POWER], server_id="0b 02 46")
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    uids = {e.unique_id for e in registry.entities.values()}
    assert {"0a0145_last_telegram", "0b0246_last_telegram"} <= uids
    assert {"0a0145_1-0:16.7.0*255", "0b0246_1-0:16.7.0*255"} <= uids

    # the initial connect is not counted, later ones are
    assert entry.runtime_data.reconnects == 0
    await sml.proto._impl._reconnect(5)  # noqa: SLF001
    assert entry.runtime_data.reconnects == 1
    assert entry.runtime_data.telegram_rate() == 2

    button = registry.async_get_entity_id("button", DOMAIN, f"{entry.entry_id}_test_connection")
    with patch("custom_components.edl21.button.persistent_notification.async_create") as notify:
        task = asyncio.create_task(
            hass.services.async_call("button", "press", {"entity_id": button}, blocking=True)
        )
        await asyncio.sleep(0.1)
        sml([POWER])
        await task
    assert "1-0:16.7.0*255" in notify.call_args.args[1]
