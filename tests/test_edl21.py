"""Tests for the EDL21 integration."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir

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


async def test_config_flow_and_options(hass: HomeAssistant) -> None:
    """Create an entry via the flow, then set options."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    with (
        patch(
            "custom_components.edl21.config_flow.asyncio.open_connection",
            AsyncMock(return_value=(None, AsyncMock(close=lambda: None))),
        ),
        patch("custom_components.edl21.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"serial_port": "socket://1.2.3.4:2000"}
        )
        assert result["type"] == "create_entry"
        entry = result["result"]

        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"update_interval": 30, "min_change": 5}
        )
    assert result["type"] == "create_entry"
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
