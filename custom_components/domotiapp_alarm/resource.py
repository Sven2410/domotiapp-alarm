"""De tweede laadroute: de kaart óók als Lovelace-resource.

## Waarom dit bestaat

`add_extra_js_url` zet de import in `index.html`. Home Assistant serveert die
`index.html` **zonder cache-validatie-headers** en zijn service worker
beantwoordt de wortel-URL met `StaleWhileRevalidate`. Een browser die Home
Assistant al gebruikte vóórdat deze integratie werd geïnstalleerd, houdt
daardoor een `index.html` van vóór de installatie — zonder onze importregel.
De kaart is dan onvindbaar en elk dashboard toont "Configuratiefout".

Dat is geen fout van ons: het staat als `home-assistant/epics#113` in de
issuelijst van Home Assistant zelf, met `frontend#53208` en `core#176912` als de
twee fixes die het zouden verhelpen. Het onderzoek staat in DomotiApp Scene,
`docs/fase-7` t/m `docs/fase-9`; daar is deze bevinding pas op de laatste ronde
vóór de eerste release gevonden en kostte hij drie fases. Daarom staat deze
route hier al in fase 1.

Een **Lovelace-resource** wordt uit de dashboardconfiguratie geladen, over de
WebSocket, per dashboard — die route raakt `index.html` niet aan en overleeft
een verouderde index.

## Waarom beide routes en niet alleen deze

Op Home Assistants eigen ingebouwde panelen (`/home/overview`) worden
Lovelace-resources helemaal niet geladen. `add_extra_js_url` dekt die; de
resource dekt de kapotte index. Samen zijn ze dekkend.

## Waarom dit niets kost

Beide routes gebruiken **dezelfde URL-string**, inclusief dezelfde `?v=`-hash.
De modulekaart van de browser dedupliceert op URL, dus de bundel wordt één keer
opgehaald en één keer geëvalueerd. Zouden de URL's uit elkaar lopen, dan waren
het er twee — onschadelijk dankzij de guards in `registreer.js`, maar zinloos
werk. Belangrijker: een resource met een oude `?v=` laat de browser een
verouderde bundel uit zijn HTTP-cache halen, precies wat die hash voorkomt.
Daarom wordt een bestaande resource met een afwijkende hash **bijgewerkt**.

## Wat dit nooit doet

De setup laten mislukken. In YAML-resourcemodus is de collectie een
`ResourceYAMLCollection` zonder schrijfmethoden — daar kan een integratie niets
registreren, en dat is het probleem van de beheerder, niet van de kaart. Elke
fout hier wordt gelogd en verder genegeerd.

**Dit is tijdelijk bedoeld.** Landt `frontend#53208` of `core#176912` in een
HA-release, dan volstaat de eerste route weer en kan deze hele module eruit; de
ondergrens `homeassistant` in `hacs.json` is dan het instrument om te bepalen
vanaf welke versie dat mag.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant

from .const import CARD_URL_PATH, RESOURCE_TYPE

_LOGGER = logging.getLogger(__name__)


def _zonder_query(url: str) -> str:
    """Het pad van een resource-URL, zonder de `?v=`-hash."""
    return url.partition("?")[0]


async def _async_lees_collectie(
    hass: HomeAssistant,
) -> tuple[ResourceStorageCollection, list[dict[str, Any]]] | None:
    """De resourcecollectie plus haar inhoud, of None als dat niet kan.

    Twee redenen om None terug te geven, allebei normaal:

    - Lovelace is er niet. Kan alleen bij een uitgeklede installatie; onze
      `dependencies` bevatten `lovelace`, dus in de praktijk niet.
    - Lovelace draait in YAML-resourcemodus. De collectie is dan een
      `ResourceYAMLCollection`, die alleen kan lezen.
    """
    data = hass.data.get(LOVELACE_DATA)
    if data is None:
        _LOGGER.debug("Lovelace is niet geladen; geen resource geregistreerd")
        return None

    collectie = data.resources
    if not isinstance(collectie, ResourceStorageCollection):
        _LOGGER.info(
            "Lovelace beheert zijn resources via YAML; de kaart wordt niet als "
            "resource geregistreerd. Voeg %s desgewenst handmatig toe.",
            CARD_URL_PATH,
        )
        return None

    # De collectie leest zijn opslag pas bij het eerste gebruik. `async_items()`
    # geeft zonder die stap een lege lijst terug — en dan zouden we een tweede
    # resource aanmaken naast de bestaande. `async_get_info()` is de publieke
    # methode die het laden afdwingt. Dit is het soort fout dat er stilletjes
    # weer in sluipt; daarom staat het hier als commentaar en niet alleen in een
    # rapport.
    await collectie.async_get_info()
    return collectie, list(collectie.async_items())


def _onze_resources(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """De resources die naar ons bundelpad wijzen, ongeacht de hash."""
    return [
        item for item in items if _zonder_query(item.get("url", "")) == CARD_URL_PATH
    ]


async def async_zorg_voor_resource(hass: HomeAssistant, js_url: str) -> str | None:
    """Zorg dat er precies één resource is, met exact deze URL.

    Geeft het ID van die resource terug, of None als er niets te registreren
    viel. Gooit nooit.

    :param js_url: dezelfde string die naar `add_extra_js_url` gaat.
    """
    try:
        gelezen = await _async_lees_collectie(hass)
        if gelezen is None:
            return None
        collectie, items = gelezen

        bestaand = _onze_resources(items)

        if not bestaand:
            item = await collectie.async_create_item(
                {"res_type": RESOURCE_TYPE, "url": js_url}
            )
            _LOGGER.debug("Kaart als Lovelace-resource geregistreerd: %s", js_url)
            return item["id"]

        if len(bestaand) > 1:
            # Kan alleen als iemand er handmatig een heeft bijgezet. We werken
            # de eerste bij en laten de rest staan: ongevraagd andermans
            # resources weggooien is erger dan een dubbele import, die dankzij
            # de guards in registreer.js niets kapotmaakt.
            _LOGGER.warning(
                "Er staan %d Lovelace-resources naar %s; alleen de eerste wordt "
                "bijgehouden",
                len(bestaand),
                CARD_URL_PATH,
            )

        item = bestaand[0]
        if item.get("url") == js_url and item.get("type") == RESOURCE_TYPE:
            return item["id"]

        # Een afwijkende hash betekent dat de bundel is veranderd. Laten staan
        # zou de browser onder de oude URL een verouderde bundel uit zijn cache
        # laten halen.
        await collectie.async_update_item(
            item["id"], {"res_type": RESOURCE_TYPE, "url": js_url}
        )
        _LOGGER.debug(
            "Lovelace-resource bijgewerkt van %s naar %s", item.get("url"), js_url
        )
        return item["id"]

    except Exception:  # noqa: BLE001 - de kaart laden mag hier nooit op stuklopen
        _LOGGER.exception(
            "Kon de kaart niet als Lovelace-resource registreren; de kaart blijft "
            "beschikbaar via de import in index.html"
        )
        return None


async def async_verwijder_resource(hass: HomeAssistant) -> int:
    """Haal onze resource(s) weg. Geeft het aantal verwijderde items terug.

    Hoort **alleen** bij `async_remove_entry`. Bij een unload — en dus bij elke
    reload na een rebuild — moet de resource blijven staan, anders verdwijnt en
    verschijnt hij bij elke herstart van de integratie.

    Anders dan het statische pad is een resource wél af te melden:
    `async_delete_item` bestaat en werkt.
    """
    try:
        gelezen = await _async_lees_collectie(hass)
        if gelezen is None:
            return 0
        collectie, items = gelezen

        verwijderd = 0
        for item in _onze_resources(items):
            await collectie.async_delete_item(item["id"])
            verwijderd += 1

        if verwijderd:
            _LOGGER.debug("%d Lovelace-resource(s) verwijderd", verwijderd)
        return verwijderd

    except Exception:  # noqa: BLE001 - opruimen mag het verwijderen niet blokkeren
        _LOGGER.exception("Kon de Lovelace-resource niet verwijderen")
        return 0
