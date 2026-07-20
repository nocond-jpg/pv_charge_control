"""Config flow dla PV Charge Control."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigEntry, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_SOC,
    CONF_BATTERY_POWER,
    CONF_PV_POWER,
    CONF_HOUSE_POWER,
    CONF_CHARGE_CURRENT_MAIN,
    CONF_CHARGE_CURRENT_SECOND,
    CONF_SWITCH_CAR,
    CONF_SWITCH_CHARGER,
    CONF_VOLTAGE,
    CONF_PHASES,
    CONF_MIN_SOC,
    CONF_BATTERY_POWER_INVERTED,
    CONF_UPDATE_INTERVAL,
    CONF_HYSTERESIS_W,
    CONF_SWITCH_CAR_ON_ALLOWS,
    CONF_SWITCH_CHARGER_ON_ALLOWS,
    DEFAULT_SWITCH_ON_ALLOWS,
    DEFAULT_VOLTAGE,
    DEFAULT_PHASES,
    DEFAULT_MIN_SOC,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_HYSTERESIS_W,
)


def _sensor(domains):
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=domains)
    )


DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SOC): _sensor(["sensor", "input_number"]),
        vol.Required(CONF_PV_POWER): _sensor(["sensor", "input_number"]),
        vol.Required(CONF_HOUSE_POWER): _sensor(["sensor", "input_number"]),
        vol.Required(CONF_BATTERY_POWER): _sensor(["sensor", "input_number"]),
        vol.Required(CONF_CHARGE_CURRENT_MAIN): _sensor(["number", "input_number"]),
        vol.Optional(CONF_CHARGE_CURRENT_SECOND): _sensor(["number", "input_number"]),
        vol.Optional(CONF_SWITCH_CAR): _sensor(["switch", "input_boolean"]),
        vol.Optional(CONF_SWITCH_CHARGER): _sensor(["switch", "input_boolean"]),
    }
)


class PVChargeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Kreator konfiguracji."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="PV Charge Control", data=user_input
            )
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PVChargeOptionsFlow(config_entry)


class PVChargeOptionsFlow(OptionsFlow):
    """Parametry pracy - zmienialne bez usuwania integracji."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        o = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_MIN_SOC, default=o.get(CONF_MIN_SOC, DEFAULT_MIN_SOC)
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
                vol.Optional(
                    CONF_VOLTAGE, default=o.get(CONF_VOLTAGE, DEFAULT_VOLTAGE)
                ): vol.All(vol.Coerce(int), vol.Range(min=100, max=400)),
                vol.Optional(
                    CONF_PHASES, default=o.get(CONF_PHASES, DEFAULT_PHASES)
                ): vol.In([1, 3]),
                vol.Optional(
                    CONF_BATTERY_POWER_INVERTED,
                    default=o.get(CONF_BATTERY_POWER_INVERTED, False),
                ): bool,
                vol.Optional(
                    CONF_SWITCH_CAR_ON_ALLOWS,
                    default=o.get(CONF_SWITCH_CAR_ON_ALLOWS, DEFAULT_SWITCH_ON_ALLOWS),
                ): bool,
                vol.Optional(
                    CONF_SWITCH_CHARGER_ON_ALLOWS,
                    default=o.get(
                        CONF_SWITCH_CHARGER_ON_ALLOWS, DEFAULT_SWITCH_ON_ALLOWS
                    ),
                ): bool,
                vol.Optional(
                    CONF_HYSTERESIS_W,
                    default=o.get(CONF_HYSTERESIS_W, DEFAULT_HYSTERESIS_W),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=3000)),
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=o.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
