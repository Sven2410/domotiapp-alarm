"""DomotiApp Alarm — serveert en registreert zijn eigen Lovelace-kaart.

De frontendkant bestaat uit drie stukken, en sinds fase 11 zijn dat er drie en
niet meer twee:

1. `hass.http.async_register_static_paths()` — het gebundelde JS-bestand op een
   eigen URL zetten, met de bundelhash in de `?v=`.
2. `frontend.add_extra_js_url()` — maar **niet** met die gehashte URL. HA zet de
   import letterlijk in het HTML-document, en dat document wordt door de service
   worker gecachet; na een update kreeg de klant dan de oude hash terug. Wat er
   nu in `index.html` staat is een **stabiele lader** onder `/api/`, die de hash
   van dít moment teruggeeft. Zie `loader.py` — daar staat de meting.
3. **De gehashte URL óók als Lovelace-resource registreren.** Die lijst komt
   over de WebSocket en is dus nooit verouderd. `index.html` dekt HA's
   ingebouwde panelen, de resource dekt een browser met een oude index. Zie
   `resource.py`.

De `?v=` is de **hash van het bundelbestand**, niet het versienummer. Alleen dan
verandert de URL precies wanneer de inhoud verandert. Gevolg voor het
ontwikkelen: na elke `npm run build` moet de config entry herladen worden,
anders serveert HA de oude hash (CLAUDE.md, valkuil 2).
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

from . import afvuren, loader, meldingen, planner as planner_mod, resource, voorbeeld, websocket
from .const import (
    CARD_FILENAME,
    CARD_URL_PATH,
    DATA_ENTRY_COUNT,
    DATA_JS_URL,
    DATA_LOADER_REGISTERED,
    DATA_PLANNER,
    DATA_RESOURCE_ID,
    DATA_STATIC_PATH_REGISTERED,
    DATA_STORE,
    DOMAIN,
    HASH_LENGTE,
    LOADER_URL_PATH,
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

    # De lader die in index.html terechtkomt (fase 11). Zijn URL is CONSTANT en
    # de hash zit in zijn antwoord, niet in zijn adres. Daarmee kan een
    # verouderde index.html ons niet meer op een oude bundel zetten: hij verwijst
    # naar dezelfde lader, en die wordt nooit gecachet. Zie loader.py voor de
    # meting waar dit uit voortkomt.
    loader.async_registreer(hass, bundel_hash)

    # UrlManager houdt een frozenset bij, dus een tweede identieke add() is
    # onschadelijk. Vóór fase 11 stond hier de gehashte bundel-URL en moest de
    # vorige verwijderd worden bij elke wijziging; nu verandert deze URL nooit.
    # `vorige_url` blijft staan voor precies één geval: een installatie die van
    # vóór fase 11 komt heeft binnen dezelfde HA-run nog de gehashte URL
    # geregistreerd, en die moet weg, anders staan er twee import()s.
    vorige_url = data.get(DATA_JS_URL)
    if vorige_url is not None and vorige_url != LOADER_URL_PATH:
        remove_extra_js_url(hass, vorige_url)

    if vorige_url != LOADER_URL_PATH:
        add_extra_js_url(hass, LOADER_URL_PATH)
        data[DATA_JS_URL] = LOADER_URL_PATH
        _LOGGER.debug("Lader aangemeld bij de frontend als %s", LOADER_URL_PATH)

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

    # Reparatiemeldingen voor onleesbare opslag (SPEC 19.2 geval B regel 4 en geval C
    # regel 3). Idempotent: issues die er niet meer horen te zijn worden opgeruimd.
    meldingen.async_werk_reparatiemeldingen_bij(hass, data[DATA_STORE])

    # De planner. Ná de frontend-registratie, zodat een inhaalslag het laden van de
    # kaart niet ophoudt. Doet bij het starten eerst de inhaalslag uit SPEC 13.4 en
    # plant daarna vooruit.
    if DATA_PLANNER not in data:
        planner = planner_mod.Planner(hass)
        data[DATA_PLANNER] = planner
        await planner.async_start()

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
        # Eerst de planner: een listener die na het loslaten van de opslag nog vuurt,
        # zou op een Store lezen die er niet meer is (SPEC 13.5, unload).
        if (planner := data.pop(DATA_PLANNER, None)) is not None:
            planner.async_stop()
            _LOGGER.debug("Planner gestopt en listeners opgezegd")

        # Dan de wekkers die op dit moment afgaan. Hun oploop, tweede noodremcontrole
        # en stoptimer zijn `async_call_later`s: laat je die staan, dan tikt de eerste
        # over een `hass.data` die hieronder wordt losgelaten. En zonder stoptimer
        # speelt de muziek door zonder dat er nog iemand is die hem afzet (SPEC 9.4).
        if gestopt := await afvuren.async_stop_alles(hass):
            _LOGGER.debug("%d afgaande wekker(s) gestopt bij unload", gestopt)

        # Zelfde reden als hierboven: de maximumtimer van een voorbeeld is een
        # async_call_later die anders tikt over een losgelaten hass.data[DOMAIN],
        # en zonder die timer speelt het voorbeeld door zonder dat er nog iets is
        # dat het afzet (SPEC 15.11).
        if gestopt := await voorbeeld.async_stop_alles(hass):
            _LOGGER.debug("%d lopend(e) voorbeeld(en) gestopt bij unload", gestopt)

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
