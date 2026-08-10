"""De noodrem: de controles vóór en ná het afspelen (SPEC 11).

De rode draad van SPEC 11: **een wekker die niet afgaat moet luider falen dan een
wekker die afgaat.** Dit is de module die het bestaansrecht van het product
beschermt, en daarom staat er per controle bij waarom hij bestaat en wat hij níet
bewijst.

## Wat hier NOOIT gebruikt wordt

`playback_state` en `"playing"` (SPEC 11.4). Fase 0b mat het: nadat het afspeelproces
van een spelende speaker was gedood, meldde MA nog steeds `playback_state: "playing"`
met een **doorlopende** `elapsed_time` van 220,3 s, terwijl `available` op `false`
stond. De queue weet niet of er iemand luistert. `available` is het signaal.

## De twee controles vallen NIET dezelfde kant op

| Controle | Kan niet vaststellen dat het goed gaat | Gedrag |
|---|---|---|
| speaker `available` | speaker of MA is weg | **niet afgaan** |
| URI bestaat nog | de zoekopdracht zelf faalde | **wél afgaan** (SPEC 11.2.1) |

Dat is geen inconsistentie. De eerste stelt iets vast over de kans op geluid; de
tweede over een **hulpaanroep die zelf kan falen** zonder dat er met het geluid iets
aan de hand is. Een controle die de wekker tegenhoudt omdat de controle stuk is, is
erger dan geen controle.

De twee zien er in code op elkaar lijken. Ze staan hieronder daarom met hun uitkomst
als **expliciete waarde** (`Uitkomst`) in plaats van als `bool`, zodat "onbekend"
niet stilletjes als "fout" of "goed" door het leven gaat.

## Wat geen enkele controle hier bewijst

Dat er geluid uit de speaker komt (SPEC 11.5). Een speaker op volume nul, met de
versterker uit, of gedempt, meldt netjes dat hij speelt — en omdat een MA-speaker
geen `TURN_ON` heeft, kan de integratie daar niets aan doen. Dat is een grens van het
systeem en de reden dat de klantdocumentatie zegt: laat de wake-up light meelopen.
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from . import meldingen
from .const import MA_DOMAIN, SEARCH_LIMIT_MAX, SEARCH_TIMEOUT_SECONDEN

_LOGGER = logging.getLogger(__name__)


class Uitkomst(Enum):
    """De uitkomst van een controle. Drie waarden, want twee is er één te weinig."""

    GOED = "goed"
    """Vastgesteld dat het in orde is."""

    FOUT = "fout"
    """Vastgesteld dat het **niet** in orde is. De wekker gaat niet af."""

    ONBEKEND = "onbekend"
    """De controle kon niet worden uitgevoerd. Wat dat betekent, hangt af van de
    controle — en juist daarom is dit een eigen waarde en geen `False`."""


def controleer_speaker(hass: HomeAssistant, speaker_entity_id: str) -> tuple[Uitkomst, str]:
    """Is de speaker bereikbaar? (SPEC 11.1) Geeft `(uitkomst, meldingssoort)`.

    Deze ene controle dekt **twee** storingen, gemeten in fase 0b: MA's `available` is
    `self.player.available and bool(self.mass.connection.connected)`
    (`components/music_assistant/entity.py:72-74`), dus zowel een dode speaker als een
    dode MA-server komt hier uit.

    **Waarom dit niet aan HA's service-dispatch overgelaten mag worden.** HA filtert
    onbeschikbare entiteiten weg vóórdat de integratie ze ziet (`helpers/service.py`),
    **zonder exceptie**. Bij targeting op `entity_id` komt er nog één `WARNING` in het
    log; bij targeting op een **label** komt er helemaal geen logregel
    (`helpers/target.py:136-155`) — gemeten in fase 0: nul waarschuwingen. Een wekker
    die zo faalt, faalt volkomen stil. Dit is de stilste faalmodus in het product.

    Er is geen `ONBEKEND` bij deze controle: `hass.states.get` faalt niet, en een
    ontbrekende state is een vastgestelde fout en geen twijfel.
    """
    state = hass.states.get(speaker_entity_id)
    if state is None or state.state == STATE_UNAVAILABLE:
        # Onderscheid tussen "de speaker is weg" en "Music Assistant is weg", zodat de
        # klant iets bruikbaars leest. `available` kan de twee niet scheiden, maar de
        # aanwezigheid van een geladen MA-config-entry wel — en dat is precies het
        # verschil tussen "zet je speaker aan" en "je server ligt eruit".
        if not hass.config_entries.async_loaded_entries(MA_DOMAIN):
            return Uitkomst.FOUT, meldingen.KIND_MA_UNAVAILABLE
        return Uitkomst.FOUT, meldingen.KIND_SPEAKER_UNAVAILABLE
    return Uitkomst.GOED, ""


async def async_controleer_uri(hass: HomeAssistant, geluid: dict[str, Any]) -> Uitkomst:
    """Bestaat het opgeslagen geluid nog? (SPEC 11.2) Via de zoekroute.

    **GEMETEN in fase 0b:** de MA-server op schema 31 valideert de URI **niet** vóór
    het afspelen — `verify_item_uri` bestaat pas vanaf schema 33, en op 31 wordt een
    URI die `://` bevat direct geaccepteerd
    (`components/music_assistant/media_player.py:494-498`). Een verouderde URI faalt
    daardoor stil, en dat is waarom deze controle bestaat.

    **Dit is geen identiteitscontrole, en dat hoort in de code te staan.** De meting
    uit SPEC 8.2.1 liet twee albums met dezelfde naam van verschillende artiesten
    zien: een naam identificeert een item niet uniek. Daarom wordt er vergeleken op de
    **URI-string** en dient de naam alleen om de zoekopdracht te richten. Dat sluit een
    vals positief niet uit — een provider die dezelfde URI hergebruikt komt erdoor —
    maar het maakt het onwaarschijnlijk.

    Het **vals negatief** is het ergste geval: is het item er nog maar geeft de
    zoekopdracht het niet terug (andere sortering, wisselvallige provider zoals
    RadioBrowser in fase 0b), dan zou de controle onterecht zeggen dat het geluid weg
    is en van een werkende wekker een stille maken. Dat risico is de reden dat een
    **mislukte** controle `ONBEKEND` teruggeeft en niet `FOUT`.

    Geeft nooit een exceptie door: elke fout wordt `ONBEKEND`.
    """
    uri = geluid.get("uri")
    if not uri:
        # Geen URI is geen twijfel maar een vastgestelde fout: hier valt niets af te
        # spelen. Validatie zou dit moeten tegenhouden; komt het er tóch door, dan is
        # stil doorgaan het slechtste antwoord.
        return Uitkomst.FOUT

    entries = hass.config_entries.async_loaded_entries(MA_DOMAIN)
    if not entries:
        # Zonder MA valt er niets te controleren. Dat is ONBEKEND en niet FOUT — maar
        # het maakt hier niets uit, want `controleer_speaker` heeft dit geval dan al
        # afgekeurd. Deze regel bestaat voor de aanroeporde die ik niet heb voorzien.
        _LOGGER.debug("Geen Music Assistant-entry; URI-controle overgeslagen")
        return Uitkomst.ONBEKEND

    data: dict[str, Any] = {
        "config_entry_id": entries[0].entry_id,
        "name": geluid.get("name") or "",
        # Ruime limiet (SPEC 11.2): het maximum uit 15.6. Een krappe limiet vergroot
        # juist het vals negatief.
        "limit": SEARCH_LIMIT_MAX,
    }
    media_type = geluid.get("media_type")
    if media_type:
        data["media_type"] = [media_type]

    try:
        async with asyncio.timeout(SEARCH_TIMEOUT_SECONDEN):
            antwoord = await hass.services.async_call(
                MA_DOMAIN, "search", data, blocking=True, return_response=True
            )
    except TimeoutError:
        _LOGGER.debug(
            "URI-controle voor %s liep in de time-out van %s s; de wekker gaat wél af "
            "(SPEC 11.2.1)",
            uri,
            SEARCH_TIMEOUT_SECONDEN,
        )
        return Uitkomst.ONBEKEND
    # Alles wat hierna nog komt is ONBEKEND, en dat is met opzet zo breed: een
    # `HomeAssistantError` van MA, een provider die iets onverwachts teruggeeft, een
    # `KeyError` diep in de client — het zijn alle drie "de controle kon niet worden
    # uitgevoerd", en geen van drieën zegt iets over het geluid (SPEC 11.2.1).
    except Exception as fout:  # noqa: BLE001 - zie docstring
        _LOGGER.debug(
            "URI-controle voor %s kon niet worden uitgevoerd (%s); de wekker gaat wél "
            "af (SPEC 11.2.1)",
            uri,
            fout,
        )
        return Uitkomst.ONBEKEND

    if _uri_in_treffers(antwoord, uri):
        return Uitkomst.GOED

    # De zoekopdracht is gelukt en de URI staat er niet tussen: vastgesteld negatief.
    _LOGGER.debug("URI %s komt niet voor in de zoekresultaten op %r", uri, data["name"])
    return Uitkomst.FOUT


def _uri_in_treffers(antwoord: Any, uri: str) -> bool:
    """Komt `uri` letterlijk voor in het antwoord van `music_assistant.search`?

    MA geeft acht emmers terug (SPEC 8.1); ze worden alle acht doorlopen omdat een
    provider een item soms in een andere emmer plaatst dan het opgeslagen
    `media_type` doet vermoeden — en een emmer overslaan zou een vals negatief
    opleveren, precies wat SPEC 11.2 als het ergste geval aanmerkt.
    """
    if not isinstance(antwoord, dict):
        return False
    for treffers in antwoord.values():
        if not isinstance(treffers, list):
            continue
        for item in treffers:
            if isinstance(item, dict) and item.get("uri") == uri:
                return True
    return False
