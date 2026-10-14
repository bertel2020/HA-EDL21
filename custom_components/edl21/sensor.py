"""Support for EDL21 Smart Meters."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from sml import SmlGetListResponse
from sml.asyncio import SmlProtocol

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import EntityCategory
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.dt import utcnow

from .const import (
    AVAILABILITY_TIMEOUT,
    CHECK_INTERVAL,
    CONF_MIN_CHANGE,
    CONF_SERIAL_PORT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_MIN_CHANGE,
    DEFAULT_UPDATE_INTERVAL,
    LAST_TELEGRAM_MIN_INTERVAL,
    NO_DATA_ISSUE_AFTER,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
    LOGGER,
    SIGNAL_EDL21_ALIVE,
    SIGNAL_EDL21_AVAILABILITY,
    SIGNAL_EDL21_TELEGRAM,
)

# OBIS format: A-B:C.D.E*F
SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    # A=1: Electricity
    # C=0: General purpose objects
    # D=0: Free ID-numbers for utilities
    # E=0 Ownership ID
    SensorEntityDescription(
        key="1-0:0.0.0*255",
        translation_key="ownership_id",
        entity_registry_enabled_default=False,
    ),
    # E=9: Electrity ID
    SensorEntityDescription(
        key="1-0:0.0.9*255",
        translation_key="electricity_id",
    ),
    # D=2: Program entries
    SensorEntityDescription(
        key="1-0:0.2.0*0",
        translation_key="configuration_program_version_number",
    ),
    SensorEntityDescription(
        key="1-0:0.2.0*1",
        translation_key="firmware_version_number",
    ),
    # C=1: Active power +
    # D=7: Current value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:1.7.0*255",
        translation_key="positive_active_instantaneous_power",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    # C=1: Active energy +
    # D=8: Time integral 1
    # E=0: Total
    SensorEntityDescription(
        key="1-0:1.8.0*255",
        translation_key="positive_active_energy_total",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    # E=1: Rate 1
    SensorEntityDescription(
        key="1-0:1.8.1*255",
        translation_key="positive_active_energy_tariff_t1",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    # E=2: Rate 2
    SensorEntityDescription(
        key="1-0:1.8.2*255",
        translation_key="positive_active_energy_tariff_t2",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    # E=3: Rate 3
    SensorEntityDescription(
        key="1-0:1.8.3*255",
        translation_key="positive_active_energy_tariff_t3",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    # D=17: Time integral 7
    # E=0: Total
    SensorEntityDescription(
        key="1-0:1.17.0*255",
        translation_key="last_signed_positive_active_energy_total",
    ),
    # C=2: Active energy -
    # D=8: Time integral 1
    # E=0: Total
    SensorEntityDescription(
        key="1-0:2.8.0*255",
        translation_key="negative_active_energy_total",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    # E=1: Rate 1
    SensorEntityDescription(
        key="1-0:2.8.1*255",
        translation_key="negative_active_energy_tariff_t1",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    # E=2: Rate 2
    SensorEntityDescription(
        key="1-0:2.8.2*255",
        translation_key="negative_active_energy_tariff_t2",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    # E=3: Rate 3
    SensorEntityDescription(
        key="1-0:2.8.3*255",
        translation_key="negative_active_energy_tariff_t3",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    # C=2: Active power -
    # D=7: Current value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:2.7.0*255",
        translation_key="negative_active_instantaneous_power",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    # C=14: Supply frequency
    # D=7: Instantaneous value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:14.7.0*255",
        translation_key="supply_frequency",
    ),
    # C=15: Active power absolute
    # D=7: Instantaneous value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:15.7.0*255",
        translation_key="absolute_active_instantaneous_power",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    # C=16: Active power sum
    # D=7: Instantaneous value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:16.7.0*255",
        translation_key="sum_active_instantaneous_power",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    # C=31: Active amperage L1
    # D=7: Instantaneous value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:31.7.0*255",
        translation_key="l1_active_instantaneous_amperage",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    # C=32: Active voltage L1
    # D=7: Instantaneous value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:32.7.0*255",
        translation_key="l1_active_instantaneous_voltage",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
    ),
    # C=36: Active power L1
    # D=7: Instantaneous value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:36.7.0*255",
        translation_key="l1_active_instantaneous_power",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    # C=51: Active amperage L2
    # D=7: Instantaneous value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:51.7.0*255",
        translation_key="l2_active_instantaneous_amperage",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    # C=52: Active voltage L2
    # D=7: Instantaneous value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:52.7.0*255",
        translation_key="l2_active_instantaneous_voltage",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
    ),
    # C=56: Active power L2
    # D=7: Instantaneous value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:56.7.0*255",
        translation_key="l2_active_instantaneous_power",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    # C=71: Active amperage L3
    # D=7: Instantaneous value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:71.7.0*255",
        translation_key="l3_active_instantaneous_amperage",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    # C=72: Active voltage L3
    # D=7: Instantaneous value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:72.7.0*255",
        translation_key="l3_active_instantaneous_voltage",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
    ),
    # C=76: Active power L3
    # D=7: Instantaneous value
    # E=0: Total
    SensorEntityDescription(
        key="1-0:76.7.0*255",
        translation_key="l3_active_instantaneous_power",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    # C=81: Angles
    # D=7: Instantaneous value
    # E=1:  U(L2) x U(L1)
    # E=2:  U(L3) x U(L1)
    # E=4:  U(L1) x I(L1)
    # E=15: U(L2) x I(L2)
    # E=26: U(L3) x I(L3)
    SensorEntityDescription(
        key="1-0:81.7.1*255",
        translation_key="u_l2_u_l1_phase_angle",
    ),
    SensorEntityDescription(
        key="1-0:81.7.2*255",
        translation_key="u_l3_u_l1_phase_angle",
    ),
    SensorEntityDescription(
        key="1-0:81.7.4*255",
        translation_key="u_l1_i_l1_phase_angle",
    ),
    SensorEntityDescription(
        key="1-0:81.7.15*255",
        translation_key="u_l2_i_l2_phase_angle",
    ),
    SensorEntityDescription(
        key="1-0:81.7.26*255",
        translation_key="u_l3_i_l3_phase_angle",
    ),
    # C=96: Electricity-related service entries
    SensorEntityDescription(
        key="1-0:96.1.0*255",
        translation_key="metering_point_id_1",
    ),
    SensorEntityDescription(
        key="1-0:96.1.1*255",
        translation_key="device_individual_id",
    ),
    SensorEntityDescription(
        key="1-0:96.5.0*255",
        translation_key="internal_operating_status",
    ),
)

SENSORS = {desc.key: desc for desc in SENSOR_TYPES}

# Identifiers, versions and status values: written as soon as they change,
# regardless of the update interval.
STATIC_OBIS = {
    "1-0:0.0.0*255",
    "1-0:0.0.9*255",
    "1-0:0.2.0*0",
    "1-0:0.2.0*1",
    "1-0:96.1.0*255",
    "1-0:96.1.1*255",
    "1-0:96.5.0*255",
}

LAST_TELEGRAM_DESCRIPTION = SensorEntityDescription(
    key="last_telegram",
    translation_key="last_telegram",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_category=EntityCategory.DIAGNOSTIC,
)

SENSOR_UNIT_MAPPING = {
    "Wh": UnitOfEnergy.WATT_HOUR,
    "kWh": UnitOfEnergy.KILO_WATT_HOUR,
    "W": UnitOfPower.WATT,
    "A": UnitOfElectricCurrent.AMPERE,
    "V": UnitOfElectricPotential.VOLT,
    "°": DEGREE,
    "Hz": UnitOfFrequency.HERTZ,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the EDL21 sensor."""
    api = EDL21(hass, config_entry, async_add_entities)
    config_entry.runtime_data = api
    config_entry.async_on_unload(api.disconnect)
    config_entry.async_on_unload(
        async_track_time_interval(
            hass, api.async_check, timedelta(seconds=CHECK_INTERVAL)
        )
    )
    await api.connect()


class EDL21:
    """EDL21 handles telegrams sent by a compatible smart meter."""

    # Manufacturer specific objects that are never exposed.
    _OBIS_BLACKLIST = {
        # C=96: Electricity-related service entries
        "1-0:96.50.1*1",  # Manufacturer specific EFR SGM-C4 Hardware version
        "1-0:96.50.1*4",  # Manufacturer specific EFR SGM-C4 Hardware version
        "1-0:96.50.4*4",  # Manufacturer specific EFR SGM-C4 Parameters version
        "1-0:96.90.2*1",  # Manufacturer specific EFR SGM-C4 Firmware Checksum
        "1-0:96.90.2*2",  # Manufacturer specific EFR SGM-C4 Firmware Checksum
        # C=97: Electricity-related service entries
        "1-0:97.97.0*0",  # Manufacturer specific EFR SGM-C4 Error register
        # A=129: Manufacturer specific
        "129-129:199.130.3*255",  # Iskraemeco: Manufacturer
        "129-129:199.130.5*255",  # Iskraemeco: Public Key
    }

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddConfigEntryEntitiesCallback,
    ) -> None:
        """Initialize an EDL21 object."""
        options = config_entry.options
        self.min_time = timedelta(
            seconds=options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )
        self.min_change: float = options.get(CONF_MIN_CHANGE, DEFAULT_MIN_CHANGE)
        self.available = True
        self.last_telegram = None
        # obis -> True if a known sensor exists, False if exposed as unknown
        self.seen_obis: dict[str, bool] = {}
        self.serial_port = config_entry.data[CONF_SERIAL_PORT]
        self.signal_availability = f"{SIGNAL_EDL21_AVAILABILITY}_{config_entry.entry_id}"
        self.signal_alive = f"{SIGNAL_EDL21_ALIVE}_{config_entry.entry_id}"
        self._issue_id = f"no_data_{config_entry.entry_id}"
        self._issue_active = False
        self._started = utcnow()
        self._registered_obis: set[tuple[str, str]] = set()
        self._alive_entities: set[str] = set()
        self._hass = hass
        self._async_add_entities = async_add_entities
        self._proto = SmlProtocol(self.serial_port)
        self._proto.add_listener(self.event, ["SmlGetListResponse"])
        LOGGER.debug("Initialized EDL21 on %s", self.serial_port)

    async def connect(self) -> None:
        """Connect to an EDL21 reader."""
        await self._proto.connect(self._hass.loop)

    async def disconnect(self) -> None:
        """Stop reading so unloading or removing the entry frees the port."""
        ir.async_delete_issue(self._hass, DOMAIN, self._issue_id)
        impl = self._proto._impl  # noqa: SLF001
        impl._running = False  # noqa: SLF001
        if hasattr(impl, "_disconnect"):
            await impl._disconnect()  # noqa: SLF001

    @callback
    def _set_available(self, available: bool) -> None:
        if available != self.available:
            self.available = available
            async_dispatcher_send(self._hass, self.signal_availability)

    @callback
    def async_check(self, now=None) -> None:
        """Mark sensors unavailable / raise a repair when no data arrives."""
        age = (utcnow() - (self.last_telegram or self._started)).total_seconds()
        self._set_available(age < AVAILABILITY_TIMEOUT)
        if age >= NO_DATA_ISSUE_AFTER and not self._issue_active:
            self._issue_active = True
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                self._issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="no_data",
                translation_placeholders={"port": self.serial_port},
            )

    def event(self, message_body) -> None:
        """Handle events from pysml."""
        assert isinstance(message_body, SmlGetListResponse)
        LOGGER.debug("Received sml message on %s: %s", self.serial_port, message_body)

        self.last_telegram = utcnow()
        if self._issue_active:
            self._issue_active = False
            ir.async_delete_issue(self._hass, DOMAIN, self._issue_id)

        electricity_id = message_body["serverId"]

        if electricity_id is None:
            LOGGER.debug(
                "No electricity id found in sml message on %s", self.serial_port
            )
            return
        electricity_id = electricity_id.replace(" ", "")

        new_entities: list[SensorEntity] = []
        if electricity_id not in self._alive_entities:
            self._alive_entities.add(electricity_id)
            new_entities.append(EDL21LastTelegramEntity(self, electricity_id))
        async_dispatcher_send(self._hass, self.signal_alive)

        for telegram in message_body.get("valList", []):
            if not (obis := telegram.get("objName")):
                continue

            if (electricity_id, obis) in self._registered_obis:
                async_dispatcher_send(
                    self._hass, SIGNAL_EDL21_TELEGRAM, electricity_id, telegram
                )
            elif obis not in self._OBIS_BLACKLIST:
                entity_description = SENSORS.get(obis)
                if entity_description is None:
                    # Unknown object: offer it, but disabled by default.
                    entity_description = SensorEntityDescription(
                        key=obis,
                        name=f"OBIS {obis}",
                        entity_registry_enabled_default=False,
                    )
                    if obis not in self.seen_obis:
                        LOGGER.info("Unknown OBIS %s exposed as disabled sensor", obis)
                self.seen_obis[obis] = obis in SENSORS
                new_entities.append(
                    EDL21Entity(self, electricity_id, obis, entity_description, telegram)
                )
                self._registered_obis.add((electricity_id, obis))

        self._set_available(True)
        if new_entities:
            self._async_add_entities(new_entities, update_before_add=True)


def _device_info(electricity_id: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, electricity_id)},
        name=DEFAULT_DEVICE_NAME,
    )


class EDL21LastTelegramEntity(SensorEntity):
    """Diagnostic sensor: when the last telegram was received."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    entity_description = LAST_TELEGRAM_DESCRIPTION

    def __init__(self, api: EDL21, electricity_id: str) -> None:
        """Initialize the sensor."""
        self._api = api
        self._attr_unique_id = f"{electricity_id}_last_telegram"
        self._attr_device_info = _device_info(electricity_id)
        self._attr_native_value = api.last_telegram
        self._last_write = utcnow()

    async def async_added_to_hass(self) -> None:
        """Subscribe to telegram arrivals."""

        @callback
        def handle_alive() -> None:
            now = utcnow()
            if (now - self._last_write).total_seconds() < LAST_TELEGRAM_MIN_INTERVAL:
                return
            self._last_write = now
            self._attr_native_value = self._api.last_telegram
            self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._api.signal_alive, handle_alive)
        )


class EDL21Entity(SensorEntity):
    """Entity reading values from EDL21 telegram."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, api: EDL21, electricity_id, obis, entity_description, telegram):
        """Initialize an EDL21Entity."""
        self._api = api
        self._electricity_id = electricity_id
        self._obis = obis
        self._telegram = telegram
        self._last_update = utcnow()
        self.entity_description = entity_description
        self._attr_unique_id = f"{electricity_id}_{obis}"
        self._attr_device_info = _device_info(electricity_id)

    @property
    def available(self) -> bool:
        """Unavailable while the meter delivers no data."""
        return self._api.available

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""

        @callback
        def handle_telegram(electricity_id, telegram):
            """Update attributes from last received telegram for this object."""
            if self._electricity_id != electricity_id:
                return
            if self._obis != telegram.get("objName"):
                return
            if self._telegram == telegram:
                return

            now = utcnow()
            static = self._obis in STATIC_OBIS or isinstance(
                telegram.get("value"), str
            )
            if not static and now - self._last_update < self._api.min_time:
                return
            if (
                self._api.min_change
                and self.entity_description.device_class == SensorDeviceClass.POWER
            ):
                try:
                    delta = abs(
                        float(telegram.get("value")) - float(self._telegram.get("value"))
                    )
                except (TypeError, ValueError):
                    delta = None
                if delta is not None and delta < self._api.min_change:
                    return

            self._telegram = telegram
            self._last_update = now
            self.async_write_ha_state()

        @callback
        def handle_availability() -> None:
            self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_EDL21_TELEGRAM, handle_telegram)
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._api.signal_availability, handle_availability
            )
        )

    @property
    def native_value(self) -> str | int | float | None:
        """Return the value of the last received telegram."""
        value = self._telegram.get("value")
        if value is None or isinstance(value, (str, int, float)):
            return value
        return str(value)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        if (unit := self._telegram.get("unit")) is None or unit == 0:
            return None

        return SENSOR_UNIT_MAPPING.get(unit, unit if isinstance(unit, str) else None)
