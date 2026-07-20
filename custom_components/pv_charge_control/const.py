"""Constants for PV Charge Control."""

DOMAIN = "pv_charge_control"

# --- Config entry keys (encje wskazywane przez uzytkownika) ---
CONF_SOC = "soc_entity"                       # SoC magazynu [%]
CONF_BATTERY_POWER = "battery_power_entity"   # moc baterii [W] (+ladowanie / -rozladowanie lub odwrotnie, konfigurowalne)
CONF_PV_POWER = "pv_power_entity"             # moc produkcji PV [W]
CONF_HOUSE_POWER = "house_power_entity"       # zuzycie domu [W]

CONF_CHARGE_CURRENT_MAIN = "charge_current_main"     # number, zawsze dostepna 6-16A
CONF_CHARGE_CURRENT_SECOND = "charge_current_second" # number, czasami dostepna 3-16A

CONF_SWITCH_CAR = "switch_car"           # switch wylaczajacy ladowanie z auta (czesto niedostepny)
CONF_SWITCH_CHARGER = "switch_charger"   # switch wylaczajacy ladowanie z ladowarki

# --- Options ---
CONF_VOLTAGE = "voltage"                 # napiecie sieci [V]
CONF_PHASES = "phases"                   # liczba faz
CONF_MIN_SOC = "min_soc"                 # ponizej -> nie laduj z magazynu
CONF_BATTERY_POWER_INVERTED = "battery_power_inverted"  # znak mocy baterii
CONF_UPDATE_INTERVAL = "update_interval" # sekundy
CONF_HYSTERESIS_W = "hysteresis_w"       # margines na podniesienie pradu [W]
CONF_SWITCH_CAR_ON_ALLOWS = "switch_car_on_allows"        # True: on=pozwol ladowac
CONF_SWITCH_CHARGER_ON_ALLOWS = "switch_charger_on_allows"  # True: on=pozwol ladowac

# --- Defaults ---
DEFAULT_VOLTAGE = 230
DEFAULT_PHASES = 3
DEFAULT_MIN_SOC = 20
DEFAULT_UPDATE_INTERVAL = 15
DEFAULT_HYSTERESIS_W = 150
DEFAULT_SWITCH_ON_ALLOWS = True   # domyslnie on = pozwol ladowac

MAIN_MIN_A = 6
MAIN_MAX_A = 16
SECOND_MIN_A = 3
SECOND_MAX_A = 16

# Encje tworzone przez integracje
SWITCH_ENABLE_KEY = "enable"   # switch wlaczajacy sterowanie
