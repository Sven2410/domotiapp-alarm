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

## Er is één controle vooraf, en dat is sinds fase 3c-bis een keuze

Hier stond ook een **URI-controle**: een zoekopdracht op de opgeslagen naam om te zien
of het geluid nog bestond. Die is vervallen (SPEC 11.2). De reden, gemeten in fase 3c:
de naam die MA teruggeeft voor een SomaFM-kanaal is `"SomaFM: Beat Blender"`, en zoeken
op die string in MA geeft **nul** treffers — `"Beat Blender"` geeft er drie. De
weergavenaam draagt een providerprefix die de zoekindex niet kent, dus de controle kon
per definitie zijn eigen opgeslagen geluid niet terugvinden. Ze sloeg vals alarm voor een
hele provider, en een wekker die niet afgaat is het ergste wat dit product kan doen.

**Wat daarvoor in de plaats komt:** niets vooraf. Het faalgeval verschuift van "de wekker
gaat niet af" naar "de wekker ging af maar was stil", en dat tweede wordt opgevangen door
de tweede controle, vijf seconden ná het starten (SPEC 11.3). Die gebruikt
`controleer_speaker` hieronder en zit in `afvuren._maak_noodrem_achteraf`; hij draagt
sindsdien meer dan hij deed, want hij is nu het enige net onder een dood geluid.

**Zet hier geen nieuwe voorafgaande controle terug zonder SPEC 11.2.2 te lezen.** De enige
route die het probleem hierboven niet heeft is `music/item_by_uri`, en die vraagt naar de
URI in plaats van naar de naam. Zolang MA hem niet als service publiceert, is er geen
voorafgaande controle.

## Wat geen enkele controle hier bewijst

Dat er geluid uit de speaker komt (SPEC 11.5). Een speaker op volume nul, met de
versterker uit, of gedempt, meldt netjes dat hij speelt — en omdat een MA-speaker
geen `TURN_ON` heeft, kan de integratie daar niets aan doen. Dat is een grens van het
systeem en de reden dat de klantdocumentatie zegt: laat de wake-up light meelopen.
"""

from __future__ import annotations

import logging
from enum import Enum

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from . import meldingen
from .const import MA_DOMAIN

_LOGGER = logging.getLogger(__name__)


class Uitkomst(Enum):
    """De uitkomst van een controle.

    Twee waarden sinds fase 3c-bis, en dat is minder dan het was — zie het commentaar
    onderaan deze klasse voordat je er een derde bij zet.
    """

    GOED = "goed"
    """Vastgesteld dat het in orde is."""

    FOUT = "fout"
    """Vastgesteld dat het **niet** in orde is. De wekker gaat niet af."""

    # Hier stond ONBEKEND: "de controle kon niet worden uitgevoerd". Die waarde bestond
    # voor de URI-controle, die als enige kon mislukken zonder iets over het geluid te
    # zeggen. Met het vervallen daarvan (SPEC 11.2) had niemand hem meer nodig, en een
    # enum-waarde die niemand teruggeeft is dode documentatie.
    #
    # Hij komt terug zodra SPEC 11.2.2 in werking treedt: `music/item_by_uri` heeft
    # drie uitkomsten, waaronder `ProviderUnavailableError` — dat de provider weg is
    # bewijst niet dat het nummer weg is, dus de wekker gaat dan wél af. Voeg hem op dat
    # moment terug in plaats van dat geval in een `bool` te persen.


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

    Deze controle kan niet "onbekend" opleveren: `hass.states.get` faalt niet, en een
    ontbrekende state is een vastgestelde fout en geen twijfel. Hij wordt **twee keer**
    gebruikt — vóór het afspelen (SPEC 11.1) en vijf seconden erna (SPEC 11.3) — met een
    verschillende melding bij het tweede geval.
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
