"""Coordinator: cala logika sterowania ladowaniem."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
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
    MAIN_MIN_A,
    MAIN_MAX_A,
    SECOND_MIN_A,
    SECOND_MAX_A,
)

_LOGGER = logging.getLogger(__name__)


class PVChargeCoordinator:
    """Odczytuje encje, wylicza nadwyzke PV i ustawia natezenie ladowania."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._unsub = None

        # Wlaczany przelacznikiem w HA (encja tworzona przez integracje)
        self.enabled: bool = False

        # Diagnostyka (dla sensorow)
        self.surplus_w: float = 0.0
        self.main_current: int = 0
        self.second_current: int = 0
        self.last_reason: str = "init"

    # ---- helpers configu ----
    def _opt(self, key, default):
        return self.entry.options.get(key, self.entry.data.get(key, default))

    def _cfg(self, key):
        return self.entry.data.get(key)

    async def async_start(self) -> None:
        interval = int(self._opt(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        self._unsub = async_track_time_interval(
            self.hass, self._async_tick, timedelta(seconds=interval)
        )

    async def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def async_set_enabled(self, value: bool) -> None:
        self.enabled = value
        if value:
            await self._async_tick(None)
        else:
            # przy wylaczeniu zerujemy natezenie
            await self._set_current(CONF_CHARGE_CURRENT_MAIN, 0)
            await self._set_current(CONF_CHARGE_CURRENT_SECOND, 0)
            self.main_current = 0
            self.second_current = 0
            self.last_reason = "disabled"

    # ---- odczyt liczbowy encji ----
    def _num(self, entity_id: str | None):
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if st is None or st.state in ("unknown", "unavailable", "none", ""):
            return None
        try:
            return float(st.state)
        except (ValueError, TypeError):
            return None

    def _switch_allows(self, entity_id: str | None, on_allows: bool) -> bool:
        """Czy przelacznik pozwala ladowac.

        on_allows=True  -> on = pozwol, off = zablokuj
        on_allows=False -> on = zablokuj, off = pozwol
        Niedostepny / brak encji -> nie blokuje (pozwala).
        """
        if not entity_id:
            return True
        st = self.hass.states.get(entity_id)
        if st is None or st.state in ("unknown", "unavailable"):
            return True
        is_on = st.state == "on"
        return is_on if on_allows else (not is_on)

    def _second_available(self) -> bool:
        eid = self._cfg(CONF_CHARGE_CURRENT_SECOND)
        if not eid:
            return False
        st = self.hass.states.get(eid)
        return st is not None and st.state not in ("unknown", "unavailable")

    @callback
    async def _async_tick(self, _now) -> None:
        if not self.enabled:
            return

        # --- odczyt encji ---
        soc = self._num(self._cfg(CONF_SOC))
        batt = self._num(self._cfg(CONF_BATTERY_POWER)) or 0.0

        min_soc = float(self._opt(CONF_MIN_SOC, DEFAULT_MIN_SOC))
        voltage = float(self._opt(CONF_VOLTAGE, DEFAULT_VOLTAGE))
        phases = int(self._opt(CONF_PHASES, DEFAULT_PHASES))
        hyst = float(self._opt(CONF_HYSTERESIS_W, DEFAULT_HYSTERESIS_W))
        inverted = bool(self._opt(CONF_BATTERY_POWER_INVERTED, False))

        # Znormalizuj moc baterii: dodatnia = ladowanie, ujemna = rozladowanie
        batt_norm = -batt if inverted else batt

        # Aktualnie pobierana moc ladowania auta
        ev_now = self._current_ev_power(voltage, phases)

        # Nadwyzka = moc plynaca do magazynu. To wlasnie te W chcemy oddac autu
        # zamiast ladowac magazyn. Domykamy petle dodajac to, co auto juz bierze:
        # jesli magazyn sie laduje (batt_norm>0) i auto tez laduje, calkowita
        # dostepna nadwyzka to suma obu.
        # Jesli magazyn sie rozladowuje (batt_norm<0), oznacza to ze auto bierze
        # za duzo -> nadwyzka spada ponizej ev_now i prad zostanie zredukowany.
        surplus_for_ev = batt_norm + ev_now

        # Nadwyzke liczymy ZAWSZE, zeby byla widoczna w diagnostyce
        self.surplus_w = surplus_for_ev

        # --- blokady z przelacznikow (on=pozwol wg konfiguracji) ---
        car_allows = self._switch_allows(
            self._cfg(CONF_SWITCH_CAR),
            bool(self._opt(CONF_SWITCH_CAR_ON_ALLOWS, DEFAULT_SWITCH_ON_ALLOWS)),
        )
        charger_allows = self._switch_allows(
            self._cfg(CONF_SWITCH_CHARGER),
            bool(self._opt(CONF_SWITCH_CHARGER_ON_ALLOWS, DEFAULT_SWITCH_ON_ALLOWS)),
        )
        if not (car_allows and charger_allows):
            await self._apply(0, 0, "zablokowane przelacznikiem")
            return

        # ochrona magazynu
        if soc is not None and soc < min_soc:
            await self._apply(0, 0, f"SoC {soc}% < min {min_soc}%")
            return

        main_a, second_a = self._split_current(surplus_for_ev, hyst, voltage, phases)

        if main_a == 0 and second_a == 0:
            min_start_w = (
                SECOND_MIN_A if self._second_available() else MAIN_MIN_A
            ) * voltage * phases
            reason = (
                f"nadwyzka {surplus_for_ev:.0f}W < progu startu {min_start_w:.0f}W"
            )
        else:
            reason = f"nadwyzka {surplus_for_ev:.0f}W"
        await self._apply(main_a, second_a, reason)

    def _current_ev_power(self, voltage, phases) -> float:
        m = self.main_current if self.main_current >= MAIN_MIN_A else 0
        s = self.second_current if self.second_current >= SECOND_MIN_A else 0
        return (m + s) * voltage * phases

    @staticmethod
    def _watt_to_amp(watt, voltage, phases) -> float:
        denom = voltage * phases
        if denom <= 0:
            return 0.0
        return watt / denom

    def _split_current(self, surplus_w: float, hyst_w: float, voltage: float, phases: int):
        """Wyznacz prad dla obu ladowarek na podstawie dostepnej nadwyzki [W].

        Podniesienie pradu o 1A wymaga nadwyzki >= (I+1)*U*fazy + hyst_w.
        Obnizenie nastepuje od razu gdy nadwyzka nie pokrywa aktualnego pradu
        (ochrona magazynu nie moze czekac na margines).
        """
        second_ok = self._second_available()
        w_per_amp = voltage * phases
        if w_per_amp <= 0:
            return 0, 0

        cur_total = self.main_current + self.second_current

        # Minimalny prad startowy: gdy nic nie ladujemy, trzeba od razu skoczyc
        # do minimum ladowarki (6A glowna / 3A druga) - wzrost o 1A nigdy by nie
        # przekroczyl progu i uklad staly by w miejscu.
        min_start = SECOND_MIN_A if second_ok else MAIN_MIN_A

        # Ile amperow pokrywa nadwyzka - do obnizania (tolerancja 1W na
        # bledy zmiennoprzecinkowe, by nie gubic ampera przy rownej mocy)
        affordable = int((surplus_w + 1.0) // w_per_amp)

        if cur_total == 0:
            # start tylko gdy nadwyzka pokrywa minimum + margines
            need_w = min_start * w_per_amp + hyst_w
            target = min_start if surplus_w >= need_w else 0
        elif affordable > cur_total:
            # podnosimy o 1A na tick, tylko z marginesem
            need_w = (cur_total + 1) * w_per_amp + hyst_w
            target = cur_total + 1 if surplus_w >= need_w else cur_total
        else:
            # obnizamy natychmiast do tego, co nadwyzka realnie pokrywa
            target = affordable
            # ponizej minimum -> stop
            if target < min_start:
                target = 0

        max_total = MAIN_MAX_A + (SECOND_MAX_A if second_ok else 0)
        target = max(0, min(target, max_total))

        return self._distribute(target, second_ok)

    @staticmethod
    def _distribute(total: int, second_ok: bool):
        """Rozdziel laczny prad. Priorytet: glowna (6-16A), nadmiar na druga (3-16A).

        Ponizej 6A glowna nie moze pracowac - wtedy caly prad idzie na druga
        (o ile dostepna i >=3A).
        """
        if total >= MAIN_MIN_A:
            main = min(total, MAIN_MAX_A)
            rest = total - main
            second = min(rest, SECOND_MAX_A) if (second_ok and rest >= SECOND_MIN_A) else 0
            return main, second
        # total < 6A: glowna odpada
        if second_ok and total >= SECOND_MIN_A:
            return 0, min(total, SECOND_MAX_A)
        return 0, 0

    async def _apply(self, main_a: int, second_a: int, reason: str) -> None:
        self.last_reason = reason
        if main_a != self.main_current:
            await self._set_current(CONF_CHARGE_CURRENT_MAIN, main_a)
            self.main_current = main_a
        if self._second_available() and second_a != self.second_current:
            await self._set_current(CONF_CHARGE_CURRENT_SECOND, second_a)
            self.second_current = second_a
        elif not self._second_available():
            self.second_current = 0

    async def _set_current(self, conf_key: str, amps: int) -> None:
        entity_id = self._cfg(conf_key)
        if not entity_id:
            return
        st = self.hass.states.get(entity_id)
        if st is None or st.state in ("unavailable", "unknown"):
            return
        await self.hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": entity_id, "value": amps},
            blocking=False,
        )
