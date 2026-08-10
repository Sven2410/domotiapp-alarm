"""Constanten voor DomotiApp Alarm."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "domotiapp_alarm"

# --- Frontend (SPEC 2) --------------------------------------------------
# Bestandsnaam van de gebundelde Lovelace-kaart, en het URL-pad waarop de
# integratie hem serveert.
CARD_FILENAME: Final = "domotiapp-alarm-card.js"
CARD_URL_PATH: Final = f"/{DOMAIN}/{CARD_FILENAME}"

# De tweede laadroute. `module` is het enige type dat een ES-module importeert.
RESOURCE_TYPE: Final = "module"

# Lengte van de hash in de ?v=. De hash is die van het bundelbestand, niet het
# versienummer: alleen dan verandert de URL precies wanneer de inhoud verandert.
HASH_LENGTE: Final = 12

# --- Sleutels in hass.data[DOMAIN] --------------------------------------
DATA_STATIC_PATH_REGISTERED: Final = "static_path_registered"
DATA_JS_URL: Final = "js_url"
DATA_ENTRY_COUNT: Final = "entry_count"
DATA_RESOURCE_ID: Final = "resource_id"
DATA_STORE: Final = "store"
DATA_WS_REGISTERED: Final = "ws_registered"
DATA_RINGING: Final = "ringing"
DATA_PLANNER: Final = "planner"

# --- Opslag (SPEC 14.1) -------------------------------------------------
STORAGE_KEY: Final = f"{DOMAIN}.alarms"
STORAGE_VERSION: Final = 1
STORAGE_MINOR_VERSION: Final = 1

# --- Labels (SPEC 7.1) --------------------------------------------------
# De namen die de eigenaar plakt. De integratie zoekt het label_id erbij en
# werkt daarna met dat ID, want hernoemen laat het label_id ongemoeid.
LABEL_SPEAKER_NAAM: Final = "Music Assistant Wekker"
LABEL_LAMP_NAAM: Final = "Verlichting Wekker"

# --- Music Assistant ----------------------------------------------------
MA_DOMAIN: Final = "music_assistant"
# Het attribuut waarin MA het spelertype zet. Let op: extra state attributes
# verdwijnen zodra een entiteit unavailable is (SPEC 7.2), dus dit is nooit de
# enige zeef.
ATTR_MASS_PLAYER_TYPE: Final = "mass_player_type"
MASS_PLAYER_TYPE_GROUP: Final = "group"

# --- Planner (SPEC 13.4) ------------------------------------------------
# Het respijtvenster: een gemiste wekker gaat alsnog af als hij minder dan zoveel
# minuten te laat is. Bewust een eigen constante en niet dezelfde als de
# automatische stop uit SPEC 9.4: dat die ook 30 is, is toeval.
RESPIJT_MINUTEN: Final = 30

# --- Standaardwaarden voor een nieuwe wekker (SPEC 14.3) ----------------
DEFAULT_TIME: Final = "07:00"
DEFAULT_VOLUME_PCT: Final = 40

# --- Grenzen uit het schema (SPEC 14.2) ---------------------------------
VOLUME_PCT_MIN: Final = 1
VOLUME_PCT_MAX: Final = 100
BRIGHTNESS_PCT_MIN: Final = 1
BRIGHTNESS_PCT_MAX: Final = 100
# ISO-weekdagen: 1 = maandag t/m 7 = zondag.
WEEKDAG_MIN: Final = 1
WEEKDAG_MAX: Final = 7

# Zoekopdracht (SPEC 15.6).
SEARCH_LIMIT_DEFAULT: Final = 10
SEARCH_LIMIT_MAX: Final = 50
SEARCH_TIMEOUT_SECONDEN: Final = 10

# --- Meldingen (SPEC 11.7 en 14.2.1) ------------------------------------
SEVERITY_ERROR: Final = "error"
SEVERITY_NOTICE: Final = "notice"

# --- Reparatiemeldingen (SPEC 19.2) -------------------------------------
ISSUE_CORRUPT_PERSON_PREFIX: Final = "corrupte_opslag_"
ISSUE_STORE_UNUSABLE: Final = "opslag_onbruikbaar"
