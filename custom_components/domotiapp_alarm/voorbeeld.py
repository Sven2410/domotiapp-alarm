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
## De wake-up light hoort er WEL bij, sinds fase 8

Tot dan deed het voorbeeld alleen het geluid, en SPEC 5.4 schreef dat ook zo voor.
De eigenaar verwacht iets anders, en hij heeft gelijk: wie 100 % helderheid instelt
wil zien of dat niet te fel is, precies zoals hij het volume wil horen. Een
voorbeeld dat de helft van de wekker weglaat, is geen voorbeeld.

**Bij het stoppen gaat de lamp terug**, en dat wijkt af van een echte wekker — die
laat hem aan (SPEC 12). Dat verschil is bewust: bij een wekker word je wakker, bij
een voorbeeld wil je je kamer niet op vol licht achterlaten omdat je even iets
uitprobeerde. Het is dezelfde redenering als het volume in SPEC 9.5.

**Wat er van de lamp bewaard wordt is minimaal**: aan of uit, en de helderheid.
Geen kleur, geen kleurtemperatuur, geen effect. Die bewaren zou betekenen dat we ze
ook moeten kunnen terugzetten, en een half herstelde kleur is erger dan een
helderheid die terugkomt. Wie een gekleurde lamp als wake-up light gebruikt, houdt
na een voorbeeld zijn kleur maar krijgt de helderheid van vóór het voorbeeld
terug.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from . import abonnement, afvuren, entiteiten, noodrem
from .const import DATA_VOORBEELD, DOMAIN, VOORBEELD_MAX_MINUTEN
from .noodrem import Uitkomst

_LOGGER = logging.getLogger(__name__)

# Sleutels in de context per lopend voorbeeld.
CTX_VOLUME_VOOR = "volume_voor"
CTX_SHUFFLE_VOOR = "shuffle_voor"
CTX_LAMP = "lamp"
CTX_LAMP_VOOR = "lamp_voor"
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
    hass: HomeAssistant,
    speaker: str,
    geluid: dict[str, Any],
    volume_pct: int,
    lamp: dict[str, Any] | None = None,
) -> None:
    """Start een voorbeeld. Gooit `VoorbeeldGeweigerd` als dat niet kan.

    De volgorde volgt die van het afvuren (SPEC 9.1), met twee verschillen die er
    toe doen: het volume gaat naar het **ingestelde** niveau in plaats van naar 0,
    en er komt geen oploop achteraan.

    :param lamp: `{"entity_id", "brightness_pct"}` of `None`. Sinds fase 8 doet het
        voorbeeld **ook** de wake-up light (SPEC 5.4): wie 100 % instelt wil zien of
        dat niet te fel is, net zoals hij het volume wil horen. `None` betekent dat
        er geen lamp gekozen is, en dan wordt er geen enkele lamp aangeraakt.
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

    # 6. Shuffle, net als bij het afgaan (SPEC 9.6) en om dezelfde reden vóór
    #    `play_media`. Een voorbeeld dat altijd met nummer 1 begint terwijl de
    #    wekker schudt, laat iets anders horen dan wat er 's ochtends gebeurt —
    #    en dan is het geen voorbeeld. De oude stand gaat mee terug bij het
    #    stoppen, net als het volume.
    shuffle_voor = await afvuren.async_shuffle_aan_voor(
        hass, speaker, (geluid or {}).get("media_type")
    )

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
        # Zelfde redenering voor shuffle: hij is al verzet, dus hij hoort terug ook
        # al heeft er niets gespeeld. Er komt hierna geen `async_stop` die het nog
        # doet — dit voorbeeld heeft nooit in het register gestaan.
        if shuffle_voor is not None:
            await afvuren.async_zet_shuffle(hass, speaker, shuffle_voor)
        raise VoorbeeldGeweigerd(
            "sound_gone",
            f"Het geluid '{(geluid or {}).get('name') or uri}' kon niet gestart worden.",
        ) from fout

    # 7. De wake-up light (SPEC 5.4 en 12), en die komt **ná** het geluid.
    #
    #    Bij een wekker gaat de lamp vóór het geluid, omdat het geluid daar 2,1-2,6 s
    #    kan blokkeren en de lamp niet mag wachten op iets dat kan mislukken. Bij een
    #    voorbeeld ligt het andersom: mislukt `play_media`, dan wordt het voorbeeld
    #    geweigerd, en dan hoort er geen lamp te hebben geflitst die we meteen weer
    #    uitzetten. Het scheelt ook een derde terugzetting in het faalpad hierboven.
    lamp_entity, lamp_voor = await _async_lamp_aan(hass, lamp)

    context: dict[str, Any] = {
        CTX_VOLUME_VOOR: volume_voor,
        CTX_SHUFFLE_VOOR: shuffle_voor,
        CTX_LAMP: lamp_entity,
        CTX_LAMP_VOOR: lamp_voor,
        CTX_UNSUB_MAX: None,
    }
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


def lampstand_van(hass: HomeAssistant, entity_id: str) -> dict[str, Any] | None:
    """Hoe staat deze lamp nu? `None` als dat niet te lezen is.

    Dezelfde drie redenen voor `None` als bij `volume_pct_van` en `shuffle_van`: de
    entiteit bestaat niet, is `unavailable`, of heeft een toestand die we niet
    kennen. En dezelfde consequentie: **niets terugzetten** is dan het juiste, want
    een verzonnen stand zet het licht van de klant op iets wat hij niet had.

    Wat er in de stand zit is bewust minimaal: aan of uit, en de helderheid als de
    lamp die heeft. Kleur, kleurtemperatuur en effecten worden **niet** gelezen en
    dus ook niet teruggezet — zie de moduledocstring. Ze bewaren zou betekenen dat
    we ze ook moeten kunnen herstellen, en een half herstelde kleur is erger dan
    een helderheid die terugkomt.
    """
    state = hass.states.get(entity_id)
    if state is None or state.state not in (STATE_ON, STATE_OFF):
        return None
    if state.state == STATE_OFF:
        return {"aan": False, "brightness": None}
    helderheid = state.attributes.get("brightness")
    return {
        "aan": True,
        "brightness": int(helderheid) if isinstance(helderheid, (int, float)) else None,
    }


async def _async_lamp_aan(
    hass: HomeAssistant, lamp: dict[str, Any] | None
) -> tuple[str | None, dict[str, Any] | None]:
    """Zet de wake-up light aan voor het voorbeeld. Gooit nooit.

    Geeft `(entity_id, stand_ervoor)` terug. `entity_id` is `None` als er geen lamp
    gekozen is; dan is er ook niets aangeraakt en niets terug te zetten.

    **Een falende lamp stopt het voorbeeld niet.** Het geluid is het voorbeeld, net
    zoals het geluid de wekker is (SPEC 12). Er komt een `WARNING` in het log en
    verder gaat alles door.

    De stand wordt **vóór** het zetten gelezen, om dezelfde reden als bij het volume
    (SPEC 9.5): erna lees je je eigen waarde terug, en dan zet het stoppen de lamp
    van iedereen op het voorbeeldniveau.
    """
    if not isinstance(lamp, dict):
        return None, None
    # Geen aparte controle op een lege `entity_id`. Nagerekend in de mutatieproef
    # van fase 8 (M11): er is geen invoer waarbij die regel iets verandert. De enige
    # weg hierheen is `preview/start`, en die haalt de lamp door `valideer_light` —
    # die eist een `entity_id` in het `light.`-domein en gooit anders
    # `invalid_format`. Een controle die niets kan vangen suggereert dekking die er
    # niet is (valkuil 34, derde rij).
    entity_id = lamp["entity_id"]

    stand_voor = lampstand_van(hass, entity_id)
    if stand_voor is None:
        _LOGGER.debug(
            "Stand van lamp %s is niet te lezen; na het voorbeeld wordt niets teruggezet",
            entity_id,
        )

    try:
        await hass.services.async_call(
            "light",
            "turn_on",
            {ATTR_ENTITY_ID: entity_id, "brightness_pct": lamp.get("brightness_pct")},
            blocking=True,
        )
    except Exception as fout:  # noqa: BLE001 - het licht is het voorbeeld niet
        _LOGGER.warning(
            "Lamp %s kon niet aangezet worden voor het voorbeeld (%s); het geluid "
            "speelt gewoon door",
            entity_id,
            fout,
        )
    return entity_id, stand_voor


async def _async_lamp_terug(
    hass: HomeAssistant, entity_id: str | None, stand: dict[str, Any] | None
) -> None:
    """Zet de lamp terug zoals hij stond. Gooit nooit.

    `None` op een van beide betekent niets doen: er was geen lamp gekozen, of zijn
    stand was niet te lezen. Nooit een verzonnen waarde (SPEC 9.5).

    Stond hij **uit**, dan gaat hij uit. Stond hij **aan**, dan gaat hij aan op zijn
    oude helderheid — en had de lamp die niet, dan gaat hij aan zonder er een te
    noemen. `brightness: None` meesturen zou een lamp zonder dimmer een waarde geven
    die hij niet kent.
    """
    if not entity_id or stand is None:
        return
    try:
        if not stand["aan"]:
            await hass.services.async_call(
                "light", "turn_off", {ATTR_ENTITY_ID: entity_id}, blocking=True
            )
            return
        data: dict[str, Any] = {ATTR_ENTITY_ID: entity_id}
        if stand["brightness"] is not None:
            data["brightness"] = stand["brightness"]
        await hass.services.async_call("light", "turn_on", data, blocking=True)
    except Exception as fout:  # noqa: BLE001 - terugzetten mag niet stukgaan
        _LOGGER.warning("Lamp %s terugzetten is mislukt: %s", entity_id, fout)


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
    dan het geluid, en pas daarna het volume en de shuffle — andersom klinkt de
    laatste seconde op het oude niveau.
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

    # Shuffle op precies dezelfde voorwaarden (SPEC 9.6). `None` is óf "wij hebben
    # hem niet aangezet" óf "de oude stand was niet te lezen"; niets doen is dan het
    # juiste, want anders zetten we een keuze van de klant terug die wij niet maakten.
    shuffle_voor = context.get(CTX_SHUFFLE_VOOR)
    if shuffle_voor is not None:
        await afvuren.async_zet_shuffle(hass, speaker, shuffle_voor)

    # De lamp gaat terug naar hoe hij stond, en dat wijkt bewust af van een echte
    # wekker (SPEC 12: die laat hem aan). Bij een wekker word je wakker; bij een
    # voorbeeld wil je je kamer niet op vol licht achterlaten omdat je even iets
    # uitprobeerde. Zelfde redenering als het volume in SPEC 9.5.
    await _async_lamp_terug(hass, context.get(CTX_LAMP), context.get(CTX_LAMP_VOOR))

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
