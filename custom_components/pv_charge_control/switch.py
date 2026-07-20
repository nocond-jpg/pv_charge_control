"""Switch wlaczajacy sterowanie ladowaniem."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SWITCH_ENABLE_KEY
from .coordinator import PVChargeCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: PVChargeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PVChargeEnableSwitch(coordinator, entry)])


class PVChargeEnableSwitch(SwitchEntity):
    """Glowny wlacznik integracji."""

    _attr_has_entity_name = True
    _attr_name = "Sterowanie ladowaniem PV"
    _attr_icon = "mdi:solar-power"

    def __init__(self, coordinator: PVChargeCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_{SWITCH_ENABLE_KEY}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "PV Charge Control",
            "manufacturer": "nocon",
        }

    @property
    def is_on(self) -> bool:
        return self._coordinator.enabled

    async def async_turn_on(self, **kwargs) -> None:
        await self._coordinator.async_set_enabled(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self._coordinator.async_set_enabled(False)
        self.async_write_ha_state()
