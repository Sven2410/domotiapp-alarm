"""De voorbeeldknop uit de editor (SPEC 5.4 en 15.11).

Het model is de Voorbeeldknop uit DomotiApp Scene: **hij doet het echt**, in
plaats van te beloven wat er zou gebeuren. De klant hoort het geluid op de
speaker die hij net heeft gekozen, op het volume dat hij net heeft ingesteld, met
waarden die nog **niet opgeslagen** zijn.

## Waarom dit een abonnement is en geen paar start/stop-commando's

Dat is de kernbeslissing van deze module, en hij komt uit één eis: **elke manier
van de editor sluiten stopt het voorbeeld** (SPEC 5.4). "Elke manier" is meer dan
de klant kan aanwijzen — de X, Escape en Annuleren kan de kaart afvangen, maar
een tabblad dat wordt weggeklikt, een browser die crasht, een wandtablet dat zijn
wifi verliest of een telefoon die in slaap valt niet.

Met een expliciet `preview/stop` speelt de muziek in al die gevallen **door**, op
een speaker waarvan het volume ook nog eens op het voorbeeldniveau blijft staan.
Dat is precies de lege woning uit SPEC 9.4, alleen dan zonder stoptimer.

Een abonnement heeft dat probleem niet: Home Assistant roept de opgeruimde
callback in `connection.subscriptions` aan zodra de client zich afmeldt **of de
verbinding wegvalt**. De stopknop in de editor is dus een afmelding, en een
weggevallen tabblad is dezelfde afmelding. Eén codepad, en het geval dat je niet
kunt afvangen wordt gratis meegenomen.

De prijs staat in SPEC 15.12: er is geen los `preview/stop`-commando, en wie de
API buiten de kaart om gebruikt moet weten dat afmelden het stoppen ís.

## De tweede rem: een maximum

Een abonnement leeft zolang de verbinding leeft, en een browsertabblad dat
openblijft op een editor kan dagen leven. Daarom stopt een voorbeeld hoe dan ook
na `VOORBEELD_MAX_MINUTEN`. Dat is dezelfde gedachte als de stoptimer van SPEC
9.4 en het is **VOORSTEL**: SPEC 5.4 legt geen maximum vast.

## Wat het voorbeeld NIET doet

- **Geen volume-oploop** (SPEC 5.4, VOORSTEL 1). Het doel van de knop is het
  geluid en het niveau beoordelen; twintig seconden wachten voordat je hoort of
  het te hard is, maakt de knop onbruikbaar.
- **Geen `radio_mode`.** Het voorbeeld duurt kort en wat er ná het item gebeurt
  is niet wat de klant beoordeelt. Meesturen zou er wél een risico bij halen: bij
  een provider zonder `SIMILAR_TRACKS` geeft MA HTTP 500 en speelt er niets
  (SPEC 8.3.1) — dan lijkt de voorbeeldknop stuk terwijl het geluid prima is.
- **Geen wake-up light.** De lamp hoort bij de wekker, niet bij het beoordelen
  van een geluid, en hem aanzetten zou een handeling zijn die de klant niet heeft
  gevraagd.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from . import abonnement, afvuren, entiteiten, noodrem
from .const import DATA_VOORBEELD, DOMAIN, VOORBEELD_MAX_MINUTEN
from .noodrem import Uitkomst

_LOGGER = logging.getLogger(__name__)

# Sleutels in de context per lopend voorbeeld.
CTX_VOLUME_VOOR = "volume_voor"
CTX_UNSUB_MAX = "unsub_max"

REDEN_TIMEOUT = "timeout"
REDEN_VERVANGEN = "vervangen"
REDEN_AFGEMELD = "afgemeld"


class VoorbeeldGeweigerd(Exception):
    """Het voorbeeld kan niet starten. `code` is de WebSocket-foutcode."""

    def __init__(self, code: str, bericht: str) -> None:
        self.code = code
        super().__init__(bericht)


@callback
def _register(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    """Lopende voorbeelden, per speaker-entity-ID."""
    data = hass.data.setdefault(DOMAIN, {})
    register = data.get(DATA_VOORBEELD)
    if register is None:
        register = {}
        data[DATA_VOORBEELD] = register
    return register


def loopt_op(hass: HomeAssistant, speaker: str) -> bool:
    return speaker in _register(hass)


async def async_start(
    hass: HomeAssistant, speaker: str, geluid: dict[str, Any], volume_pct: int
) -> None:
    """Start een voorbeeld. Gooit `VoorbeeldGeweigerd` als dat niet kan.

    De volgorde volgt die van het afvuren (SPEC 9.1), met twee verschillen die er
    toe doen: het volume gaat naar het **ingestelde** niveau in plaats van naar 0,
    en er komt geen oploop achteraan.
    """
    # 1. Is dit wel een speaker die we mogen gebruiken (SPEC 7.2)? Dezelfde
    #    controle als `alarms/save`, want de editor stuurt hier een keuze heen die
    #    nog niet is opgeslagen en dus nog niet is gekeurd.
    geschikt, reden = entiteiten.is_ma_speaker(hass, speaker)
    if not geschikt:
        raise VoorbeeldGeweigerd("not_allowed", str(reden))

    # 2. Gaat er op deze speaker een wékker af, dan gaat die vóór. Een voorbeeld
    #    zou de queue overnemen en bij het stoppen het volume terugzetten naar wat
    #    de oploop op dat moment toevallig had gezet — de wekker zou dan zachtjes
    #    of helemaal niet verder spelen. De wekker is het product; het voorbeeld
    #    is een hulpmiddel.
    register = abonnement.register_van(hass)
    if any(
        context.get(afvuren.CTX_SPEAKER) == speaker
        for context in register.actief.values()
    ):
        raise VoorbeeldGeweigerd(
            "not_allowed",
            "Op deze speaker gaat op dit moment een wekker af. Zet die eerst uit.",
        )

    # 3. Een tweede voorbeeld op dezelfde speaker vervangt het eerste. MA heeft
    #    één queue per player, dus naast elkaar bestaan ze toch niet.
    await async_stop(hass, speaker, reden=REDEN_VERVANGEN)

    # 4. De noodrem (SPEC 11.1). Dit is precies het moment waarop de klant wil
    #    weten dat zijn speaker onbereikbaar is — daarom gaat het voorbeeld er
    #    doorheen en meldt de editor het.
    uitkomst, soort = noodrem.controleer_speaker(hass, speaker)
    if uitkomst is Uitkomst.FOUT:
        raise VoorbeeldGeweigerd(
            soort or "speaker_unavailable",
            f"De speaker '{_naam(hass, speaker)}' is niet bereikbaar.",
        )

    uri = (geluid or {}).get("uri")
    if not uri:
        raise VoorbeeldGeweigerd("invalid_format", "Er is geen geluid gekozen.")

    # 5. Het huidige volume lezen, vóór we het overschrijven (SPEC 9.5). `None`
    #    betekent: bij het stoppen wordt er niets teruggezet. Nooit een verzonnen
    #    waarde.
    volume_voor = afvuren.volume_pct_van(hass, speaker)
    if volume_voor is None:
        _LOGGER.debug(
            "Volume van %s is niet te lezen; na het voorbeeld wordt niets teruggezet",
            speaker,
        )

    await afvuren.async_zet_volume(hass, speaker, volume_pct)

    try:
        await hass.services.async_call(
            "music_assistant",
            "play_media",
            {ATTR_ENTITY_ID: speaker, "media_id": uri},
            blocking=True,
        )
    except Exception as fout:  # noqa: BLE001 - een mislukt voorbeeld is geen crash
        _LOGGER.warning("Voorbeeld van %s op %s is mislukt: %s", uri, speaker, fout)
        # Het volume is al verzet, dus het hoort terug ook al heeft er niets
        # gespeeld. Anders staat de speaker op het voorbeeldniveau na een mislukte
        # poging.
        if volume_voor is not None:
            await afvuren.async_zet_volume(hass, speaker, volume_voor)
        raise VoorbeeldGeweigerd(
            "sound_gone",
            f"Het geluid '{(geluid or {}).get('name') or uri}' kon niet gestart worden.",
        ) from fout

    context: dict[str, Any] = {CTX_VOLUME_VOOR: volume_voor, CTX_UNSUB_MAX: None}
    _register(hass)[speaker] = context
    context[CTX_UNSUB_MAX] = async_call_later(
        hass, VOORBEELD_MAX_MINUTEN * 60, _maak_maximum(hass, speaker)
    )
    _LOGGER.debug(
        "Voorbeeld gestart: %s op %s, volume %d%%, maximaal %d minuten",
        uri,
        speaker,
        volume_pct,
        VOORBEELD_MAX_MINUTEN,
    )


def _naam(hass: HomeAssistant, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    if state is not None:
        naam = state.attributes.get("friendly_name")
        if naam:
            return str(naam)
    return entity_id


def _maak_maximum(hass: HomeAssistant, speaker: str):
    async def _stop(_nu: dt.datetime) -> None:
        context = _register(hass).get(speaker)
        if context is not None:
            # De unsub van deze timer is nu verlopen; hem laten staan zou `stop`
            # verleiden een afgelopen timer af te zeggen.
            context[CTX_UNSUB_MAX] = None
        _LOGGER.debug(
            "Voorbeeld op %s stopt automatisch na %d minuten", speaker, VOORBEELD_MAX_MINUTEN
        )
        await async_stop(hass, speaker, reden=REDEN_TIMEOUT)

    return _stop


async def async_stop(hass: HomeAssistant, speaker: str, *, reden: str) -> bool:
    """Stop het voorbeeld op deze speaker. Geeft terug of er iets liep.

    Idempotent, en om dezelfde reden als `alarms/stop` (SPEC 15.8): het
    afmelden, de maximumtimer en een tweede voorbeeld kunnen alle drie tegelijk
    hier uitkomen.

    Zelfde volgorde als bij een wekker: eerst uit het register, dan de timer,
    dan het geluid, en pas daarna het volume — andersom klinkt de laatste
    seconde op het oude niveau.
    """
    context = _register(hass).pop(speaker, None)
    if context is None:
        return False

    unsub = context.get(CTX_UNSUB_MAX)
    if unsub is not None:
        unsub()

    try:
        await hass.services.async_call(
            "media_player", "media_stop", {ATTR_ENTITY_ID: speaker}, blocking=True
        )
    except Exception as fout:  # noqa: BLE001 - stoppen mag niet stukgaan
        _LOGGER.warning("Voorbeeld stoppen op %s is mislukt: %s", speaker, fout)

    volume_voor = context.get(CTX_VOLUME_VOOR)
    if volume_voor is None:
        _LOGGER.debug(
            "Volume van %s vóór het voorbeeld is niet bekend; er wordt niets teruggezet",
            speaker,
        )
    else:
        await afvuren.async_zet_volume(hass, speaker, volume_voor)

    _LOGGER.debug("Voorbeeld op %s gestopt (%s)", speaker, reden)
    return True


async def async_stop_alles(hass: HomeAssistant) -> int:
    """Stop alle lopende voorbeelden. Geeft terug hoeveel er liepen.

    Nodig bij unload, om dezelfde twee redenen als `afvuren.async_stop_alles`: de
    maximumtimer is een `async_call_later` die anders tikt over een losgelaten
    `hass.data[DOMAIN]`, en zonder die timer speelt het voorbeeld door zonder dat
    er nog iets is dat het afzet.
    """
    gestopt = 0
    for speaker in list(_register(hass)):
        if await async_stop(hass, speaker, reden="unload"):
            gestopt += 1
    return gestopt
