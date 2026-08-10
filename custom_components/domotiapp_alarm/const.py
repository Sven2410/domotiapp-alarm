"""Constanten voor DomotiApp Alarm."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "domotiapp_alarm"

# Bestandsnaam van de gebundelde Lovelace-kaart, en het URL-pad waarop de
# integratie hem serveert.
CARD_FILENAME: Final = "domotiapp-alarm-card.js"
CARD_URL_PATH: Final = f"/{DOMAIN}/{CARD_FILENAME}"

# Sleutels in hass.data[DOMAIN].
DATA_STATIC_PATH_REGISTERED: Final = "static_path_registered"
DATA_JS_URL: Final = "js_url"
DATA_ENTRY_COUNT: Final = "entry_count"
DATA_RESOURCE_ID: Final = "resource_id"

# De tweede laadroute. `module` is het enige type dat een ES-module importeert;
# de andere drie (`js`, `css`, `html`) doen dat niet.
RESOURCE_TYPE: Final = "module"

# Lengte van de hash in de ?v=. De hash is die van het bundelbestand, niet het
# versienummer: alleen dan verandert de URL precies wanneer de inhoud verandert.
HASH_LENGTE: Final = 12
