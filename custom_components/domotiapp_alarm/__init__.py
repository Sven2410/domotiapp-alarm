"""DomotiApp Alarm — serveert en registreert zijn eigen Lovelace-kaart.

In fase 1 doet de integratie precies drie dingen, en niets meer:

1. `hass.http.async_register_static_paths()` — het gebundelde JS-bestand op een
   eigen URL zetten.
2. `frontend.add_extra_js_url()` — dat bestand door HA laten importeren in
   `index.html`, zodat de klant géén Lovelace-resource hoeft toe te voegen.
3. **Dezelfde URL óók als Lovelace-resource registreren.** Twee routes, één
   URL: `index.html` dekt HA's ingebouwde panelen, de resource dekt een browser
   die nog een `index.html` van vóór de installatie in zijn service-workercache
   heeft. Zie `resource.py` voor het waarom.

De `?v=` in de frontend-URL is de **hash van het bundelbestand**, niet het
versienummer. Alleen dan verandert de URL precies wanneer de inhoud verandert.
Gevolg voor het ontwikkelen: na elke `npm run build` moet de config entry
herladen worden, anders serveert HA de oude hash (CLAUDE.md, valkuil 2).
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url, remove_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from . import resource, websocket
from .const import (
    CARD_FILENAME,
    CARD_URL_PATH,
    DATA_ENTRY_COUNT,
    DATA_JS_URL,
    DATA_RESOURCE_ID,
    DATA_STATIC_PATH_REGISTERED,
    DATA_STORE,
    DOMAIN,
    HASH_LENGTE,
)
from .store import AlarmStore

_LOGGER = logging.getLogger(__name__)


def _bereken_hash(pad: Path) -> str:
    """SHA-256 van het bundelbestand, afgekapt. Blokkerende I/O."""
    digest = hashlib.sha256(pad.read_bytes()).hexdigest()
    return digest[:HASH_LENGTE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Zet de integratie op."""
    integration = await async_get_integration(hass, DOMAIN)
    bundel = Path(integration.file_path) / "frontend" / CARD_FILENAME

    # Bestand lezen is blokkerende I/O en hoort dus in een executor — dezelfde
    # reden waarom async_register_static_paths er zelf ook een gebruikt.
    bundel_hash = await hass.async_add_executor_job(_bereken_hash, bundel)
    js_url = f"{CARD_URL_PATH}?v={bundel_hash}"
    _LOGGER.debug("Bundelhash %s -> %s", bundel_hash, js_url)

    data = hass.data.setdefault(DOMAIN, {})

    # Guard tegen dubbele registratie van hetzelfde URL-pad: aiohttp weigert een
    # tweede route op dezelfde prefix, en met meerdere config entries zou setup
    # anders de tweede keer stukgaan.
    if not data.get(DATA_STATIC_PATH_REGISTERED):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    CARD_URL_PATH,
                    str(bundel),
                    cache_headers=True,
                )
            ]
        )
        data[DATA_STATIC_PATH_REGISTERED] = True
        _LOGGER.debug("Statisch pad geregistreerd op %s", CARD_URL_PATH)

    # UrlManager houdt een frozenset bij, dus een tweede identieke add() is
    # onschadelijk. Een gewijzigde bundel levert wél een andere URL op; de oude
    # moet dan weg, anders staan er twee import()s in index.html.
    vorige_url = data.get(DATA_JS_URL)
    if vorige_url is not None and vorige_url != js_url:
        remove_extra_js_url(hass, vorige_url)

    if vorige_url != js_url:
        add_extra_js_url(hass, js_url)
        data[DATA_JS_URL] = js_url
        _LOGGER.debug("Kaart aangemeld bij de frontend als %s", js_url)

    # De tweede laadroute. Bewust met dezelfde `js_url`-variabele en niet met
    # een opnieuw opgebouwde string: lopen de twee URL's uit elkaar, dan
    # evalueert de browser de bundel twee keer en klopt de cachebusting niet
    # meer. Deze aanroep gooit nooit.
    data[DATA_RESOURCE_ID] = await resource.async_zorg_voor_resource(hass, js_url)

    # Opslaglaag: één instantie voor alle config entries. Laden gooit nooit; wat er
    # mis is wordt gemarkeerd (SPEC 19.2).
    if DATA_STORE not in data:
        store = AlarmStore(hass)
        await store.async_load()
        data[DATA_STORE] = store

    websocket.async_register(hass)

    data[DATA_ENTRY_COUNT] = data.get(DATA_ENTRY_COUNT, 0) + 1

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Ruim op bij de laatste entry.

    Het statische pad blijft staan: aiohttp kent geen unregister voor routes.
    De vlag blijft daarom ook staan, zodat een herinstallatie binnen dezelfde
    HA-run niet opnieuw registreert. Hetzelfde geldt voor de
    WebSocket-commando's: HA kent geen `async_unregister_command`.

    **De Lovelace-resource blijft hier ook staan.** Unload draait óók bij elke
    reload — de handeling die na iedere rebuild nodig is — en de resource zou
    dan bij elke herstart van de integratie verdwijnen en terugkomen. Weghalen
    gebeurt in `async_remove_entry`.

    De opslaglaag verdwijnt hier wél. Zonder dat blijven de commando's na het
    verwijderen van de integratie lezen én schrijven naar de Store van een
    integratie die er niet meer is.
    """
    data = hass.data.get(DOMAIN, {})
    data[DATA_ENTRY_COUNT] = max(0, data.get(DATA_ENTRY_COUNT, 0) - 1)

    if data[DATA_ENTRY_COUNT] == 0:
        if js_url := data.pop(DATA_JS_URL, None):
            remove_extra_js_url(hass, js_url)
            _LOGGER.debug("Kaart afgemeld bij de frontend: %s", js_url)

        if data.pop(DATA_STORE, None) is not None:
            _LOGGER.debug("Opslaglaag losgelaten")

    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Haal de Lovelace-resource weg als de integratie wordt verwijderd.

    Alleen hier, en alleen als dit de laatste entry was. HA verwijdert de entry
    uit zijn lijst vóórdat het deze callback aanroept
    (`config_entries.py`: `del self._entries[...]` gaat vooraf aan
    `entry.async_remove(...)`), dus wat `async_entries()` teruggeeft zijn de
    entries die blíjven.
    """
    if hass.config_entries.async_entries(DOMAIN):
        return

    await resource.async_verwijder_resource(hass)
    hass.data.get(DOMAIN, {}).pop(DATA_RESOURCE_ID, None)
