"""Sensory diagnostyczne: nadwyzka PV, prad glowny/drugi, powod decyzji."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PVChargeCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: PVChargeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PVSurplusSensor(coordinator, entry),
            PVMainCurrentSensor(coordinator, entry),
            PVSecondCurrentSensor(coordinator, entry),
            PVReasonSensor(coordinator, entry),
        ]
    )


class _Base(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: PVChargeCoordinator, entry: ConfigEntry, key: str):
        self._c = coordinator
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "PV Charge Control",
            "manufacturer": "nocon",
        }

    @property
    def should_poll(self) -> bool:
        return True


class PVSurplusSensor(_Base):
    _attr_name = "Nadwyzka PV"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER

    def __init__(self, c, e):
        super().__init__(c, e, "surplus")

    @property
    def native_value(self):
        return round(self._c.surplus_w)


class PVMainCurrentSensor(_Base):
    _attr_name = "Prad ladowarki glownej"
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = SensorDeviceClass.CURRENT

    def __init__(self, c, e):
        super().__init__(c, e, "main_current")

    @property
    def native_value(self):
        return self._c.main_current


class PVSecondCurrentSensor(_Base):
    _attr_name = "Prad ladowarki drugiej"
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = SensorDeviceClass.CURRENT

    def __init__(self, c, e):
        super().__init__(c, e, "second_current")

    @property
    def native_value(self):
        return self._c.second_current


class PVReasonSensor(_Base):
    _attr_name = "Status decyzji"
    _attr_icon = "mdi:information-outline"

    def __init__(self, c, e):
        super().__init__(c, e, "reason")

    @property
    def native_value(self):
        return self._c.last_reason
