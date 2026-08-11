"""Wat er gebeurt als een wekker afgaat (SPEC 9, 11 en 12).

De planner (`planner.py`) bepaalt **wanneer**; deze module bepaalt **wat**. Die
scheiding is van fase 3b en is in fase 3c niet aangeraakt: de planner is af.

## De negen stappen, in deze volgorde (SPEC 9.1 plus 9.5 en 9.6)

| # | Stap | Waarom hier |
|---|---|---|
| 0 | `last_fired` bijwerken, en `enabled: false` bij een eenmalige | vóór álles wat geluid kan maken — zie hieronder |
| 1 | noodrem vooraf | SPEC 11.1 — alleen `available`; de URI-controle is vervallen |
| 2 | huidig volume **lezen** | SPEC 9.5: vóór stap 3, want daarna is het weg |
| 3 | volume op **0** | vóór stap 6, anders is er één harde uitbarsting |
| 4 | wake-up light aan | SPEC 12, als ingesteld |
| 5 | shuffle **lezen** en aanzetten | SPEC 9.6 — vóór stap 6, want MA schudt bij het laden van de queue |
| 6 | geluid starten | `music_assistant.play_media` |
| 7 | volume-oploop | 20 stappen van 1 s naar het ingestelde niveau |
| 8 | noodrem achteraf | 5 s ná stap 6 (SPEC 11.3) |
| 9 | stoptimer | 30 minuten (SPEC 9.4) |

SPEC 9.1 nummert acht stappen; stap 2 hierboven is het lezen dat SPEC 9.5
uitdrukkelijk **vóór** stap 2 van 9.1 plaatst. Zelfde volgorde, één stap explicieter.

**Stap 5 vóór stap 6 heeft dezelfde vorm als stap 3 vóór stap 6, en dezelfde
strekking:** wat de queue bepaalt moet er zijn vóórdat de queue bestaat. Zet je
shuffle erna, dan is het eerste nummer al gekozen — en dat is precies de klacht die
in productie op 1.0.0 boven kwam. Zie `shuffle.py` voor de regel in MA's broncode.

**Stap 3 vóór stap 5 is de essentie.** Start je het geluid op het oude volume en zet
je het daarna op 0, dan knalt de wekker één keer hard voordat de oploop begint. Dat is
het verschil tussen wakker worden en wakker schrikken.

## Waarom `last_fired` vóór de noodrem staat en niet erna

Fase 3b legde vast: `last_fired` gaat vóór het geluid. Fase 3c zet een noodrem
daartussen, en dan is de vraag of `last_fired` mee opschuift. Nee — en dat is een
keuze met een prijs:

- **Nu:** een noodremfout **verbruikt** het moment. De klant krijgt één melding en de
  wekker probeert het niet opnieuw bij de volgende herstart binnen het respijtvenster.
- **Andersom:** elke herstart binnen 30 minuten zou de mislukking herhalen, met een
  nieuwe melding en een nieuwe `persistent_notification` — en als de speaker
  inmiddels terug is, zou de wekker alsnog afgaan op een moment dat de klant niet
  verwacht.

Het weegpunt is dat een mislukte noodrem **geen geluid** maakt, dus opnieuw proberen
kan nooit "twee keer afgaan" opleveren; en dat is de enige uitkomst die echt erg is.
Het sluit aan bij hoe fase 3b het overslaan behandelt: dat zet `last_fired` ook.

## Waar de meldingen langs elkaar heen kunnen

Er is één veld `last_message` (SPEC 14.2.1), dus de laatste schrijver wint. De
volgorde is daarom niet vrij:

1. **De oude `persistent_notification` wordt gewist zodra de noodrem is gehaald** —
   niet aan het eind. Gebeurt het aan het eind, dan wist het de melding weg die de
   lamp of de tweede noodremcontrole net had gemaakt.
2. **Bij een noodremfout gaat de lamp eerst, de melding daarna.** Faalt de lamp
   *tijdens* een noodremfout, dan moet `last_message` de reden zijn dat de wekker niet
   afging — niet de lamp. Waarom de wekker stil was, is het belangrijkste dat de klant
   's ochtends kan lezen.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from . import (
    abonnement,
    meldingen,
    noodrem,
    oploop as oploop_mod,
    radiomodus,
    shuffle,
    volgende,
)
from .const import (
    DATA_STORE,
    DOMAIN,
    MA_DOMAIN,
    NOODREM_NA_SECONDEN,
    OPLOOP_STAP_SECONDEN,
    STOP_NA_MINUTEN,
    VOLUME_PCT_MAX,
)
from .noodrem import Uitkomst

_LOGGER = logging.getLogger(__name__)

# Sleutels in de context per afgaande wekker (`abonnement.Register.actief`).
CTX_PERSON = "person"
CTX_MOMENT = "moment"
CTX_SPEAKER = "speaker"
CTX_VOLUME_VOOR = "volume_voor"
CTX_SHUFFLE_VOOR = "shuffle_voor"
CTX_OPLOOP = "oploop"
CTX_UNSUB_NOODREM = "unsub_noodrem"
CTX_UNSUB_STOP = "unsub_stop"


# =======================================================================
# Afgaan
# =======================================================================


def velden_bij_verbruikt_moment(
    wekker: dict[str, Any], moment: dt.datetime
) -> dict[str, Any]:
    """Wat er in de opslag verandert zodra een moment verbruikt is (SPEC 14.5).

    Eén functie, gebruikt door het afvuren én door het overslaan in `planner.py`,
    want dat zijn de twee plekken waar een moment opgaat. Zonder die ene plek
    krijgt de ene route wel een uitgezette eenmalige wekker en de andere niet.

    `last_fired` houdt het **bedoelde** moment vast en niet "nu" (fase 3b, regel
    2). `enabled` gaat alleen omlaag bij een eenmalige wekker: een herhalende
    wekker gaat morgen gewoon weer af.
    """
    velden: dict[str, Any] = {"last_fired": moment.isoformat()}
    if volgende.is_eenmalig(wekker):
        velden["enabled"] = False
    return velden


async def async_laat_afgaan(
    hass: HomeAssistant,
    registry_id: str,
    person_entity_id: str,
    wekker: dict[str, Any],
    moment: dt.datetime,
) -> None:
    """Laat één wekker afgaan: de acht stappen uit de moduledocstring.

    :param moment: het **bedoelde** moment, niet "nu". Bij een inhaalslag liggen die
        tot 30 minuten uit elkaar, en `last_fired` moet het bedoelde moment vasthouden
        — anders schuift de vergelijking uit SPEC 13.4 stap 3 elke herstart mee op en
        kan dezelfde wekker alsnog twee keer afgaan.

    Gooit nooit. Een wekker die stukloopt mag de planner niet meeslepen.
    """
    store = hass.data[DOMAIN][DATA_STORE]
    alarm_id = wekker["id"]
    speaker = wekker.get("speaker") or ""

    # --- stap 0: last_fired, vóór alles wat geluid kan maken ------------
    #
    # En bij een eenmalige wekker gaat `enabled` hier op `False` (SPEC 14.5). Dat
    # hoort hier en niet aan het eind, om dezelfde reden als `last_fired`: op dit
    # moment is het ene moment van deze wekker **verbruikt**, ongeacht of het
    # geluid daarna lukt. `one_shot_at` ligt vanaf nu in het verleden, dus hij kan
    # nooit meer afgaan — en een schakelaar die dan nog aan staat, belooft iets
    # wat niet meer komt. Dat is precies wat er in productie op 1.0.0 misging.
    try:
        await store.async_werk_velden_bij(
            registry_id, alarm_id, velden_bij_verbruikt_moment(wekker, moment)
        )
    except Exception:  # noqa: BLE001 - zie docstring
        _LOGGER.exception(
            "Kon last_fired niet bijwerken voor wekker %s; de wekker gaat wél af",
            alarm_id,
        )

    # --- stap 1: noodrem vooraf (SPEC 11.1) -----------------------------
    #
    # Eén controle, en dat is sinds fase 3c-bis een keuze: hier stond ook een
    # URI-controle (SPEC 11.2), en die sloeg vals alarm voor een hele provider. Zie de
    # moduledocstring van `noodrem.py`. Het geluid wordt nu **niet** vooraf gecontroleerd;
    # een dood geluid komt boven bij `play_media` (stap 5) of bij de tweede controle
    # vijf seconden later (stap 7).
    uitkomst, soort = noodrem.controleer_speaker(hass, speaker)
    if uitkomst is Uitkomst.FOUT:
        _LOGGER.warning(
            "Wekker %s gaat NIET af: speaker %s is niet bereikbaar", alarm_id, speaker
        )
        await _async_faal(hass, registry_id, person_entity_id, wekker, soort)
        return

    # De noodrem is gehaald. Nú de melding van een vorige keer opruimen — niet aan het
    # eind, want dan wist hij de melding weg die de lamp hieronder net kan maken.
    meldingen.async_wis_notificatie(hass, alarm_id)

    # --- stap 2: het huidige volume lezen (SPEC 9.5) --------------------
    # Vóór stap 3, want daarna is het onherroepelijk weg. `None` betekent: bij het
    # stoppen wordt er niets teruggezet. Nooit een verzonnen waarde.
    volume_voor = volume_pct_van(hass, speaker)
    if volume_voor is None:
        _LOGGER.debug(
            "Volume van %s is niet te lezen; er wordt bij het stoppen niets teruggezet",
            speaker,
        )

    # --- stap 3: volume op 0 -------------------------------------------
    doel_pct = int(wekker.get("volume_pct") or 0)
    oploop_kan = await async_zet_volume(hass, speaker, 0)
    if not oploop_kan:
        # De speaker neemt geen volume aan. De wekker gaat wél af — het geluid is de
        # wekker — maar dan op het ingestelde niveau en zonder oploop (SPEC 11.7
        # `volume_ramp_unavailable`).
        _LOGGER.warning(
            "Volume van %s is niet te zetten; wekker %s gaat af zonder oploop",
            speaker,
            alarm_id,
        )
        await async_zet_volume(hass, speaker, doel_pct)

    # --- stap 4: wake-up light (SPEC 12) -------------------------------
    await _async_lamp_aan(hass, registry_id, person_entity_id, wekker)

    # --- stap 5: shuffle, vóór het geluid (SPEC 9.6) -------------------
    # Music Assistant past shuffle toe op het moment dat de queue geladen wordt.
    # Ná `play_media` is het eerste nummer al gekozen en schud je alleen de rest —
    # dan begint de wekker elke ochtend hetzelfde. Zie `shuffle.py`.
    #
    # De oude stand gaat mee in de context, net als het volume: bij het stoppen
    # wordt hij teruggezet (SPEC 9.6), want shuffle die aan blijft staan is een
    # bijwerking die de klant niet vroeg.
    shuffle_voor = await async_shuffle_aan_voor(
        hass, speaker, (wekker.get("sound") or {}).get("media_type")
    )

    # --- stap 6: geluid starten ----------------------------------------
    gelukt, ma_reden = await _async_start_geluid(hass, speaker, wekker.get("sound") or {})
    if not gelukt:
        _LOGGER.warning(
            "Wekker %s gaat NIET af: het afspelen van %r op %s is mislukt (%s)",
            alarm_id,
            (wekker.get("sound") or {}).get("uri"),
            speaker,
            ma_reden or "geen reden opgegeven",
        )
        # `sound_gone` en niet `speaker_unavailable`: de speaker is een paar
        # milliseconden eerder nog beschikbaar bevonden (stap 1), dus "de speaker was niet
        # bereikbaar" zou onwaar zijn tegen de klant.
        #
        # **De tekst zegt sinds fase 6 wat er is vastgesteld en niet wat we vermoeden.**
        # Tot dan luidde hij "het gekozen geluid bestaat niet meer", en in productie
        # stuurde dat de eigenaar de verkeerde kant op: het geluid bestond wél, maar
        # Spotify was in MA niet geautoriseerd en gaf "No playable items found". Wat de
        # code weet is dat het **starten** mislukte; de reden van MA gaat mee, want die
        # is voor de eigenaar bruikbaar en voor een klant nog altijd beter dan een
        # onjuiste bewering. Zie SPEC 11.7.
        #
        # De lamp is hierboven al aangegaan als hij was ingesteld — dat is precies wat
        # SPEC 11.6 punt 2 voorschrijft, en hij hoort niet weer uit.
        await _async_faal(
            hass,
            registry_id,
            person_entity_id,
            wekker,
            meldingen.KIND_SOUND_GONE,
            lamp_al_gedaan=True,
            ma_reden=ma_reden or "",
        )
        return

    # De wekker gaat af. In het register, zodat `alarms/get` hem meldt en `alarms/stop`
    # hem kan stoppen; en het `started`-event zodat een open kaart een stopknop wordt.
    register = abonnement.register_van(hass)
    context: dict[str, Any] = {
        CTX_PERSON: person_entity_id,
        CTX_MOMENT: moment.isoformat(),
        CTX_SPEAKER: speaker,
        CTX_VOLUME_VOOR: volume_voor,
        CTX_SHUFFLE_VOOR: shuffle_voor,
        CTX_OPLOOP: None,
        CTX_UNSUB_NOODREM: None,
        CTX_UNSUB_STOP: None,
    }
    register.actief[(registry_id, alarm_id)] = context
    register.stuur(
        {
            "event": abonnement.EVENT_STARTED,
            "person": person_entity_id,
            "alarm_id": alarm_id,
            "name": wekker.get("name"),
            "time": wekker.get("time"),
        }
    )

    # --- stap 7: de volume-oploop (SPEC 9.3) ---------------------------
    if oploop_kan:
        loop = _Oploop(hass, registry_id, alarm_id, speaker, doel_pct)
        context[CTX_OPLOOP] = loop
        loop.start()
    else:
        await meldingen.async_meld(
            hass, store, registry_id, wekker, meldingen.KIND_VOLUME_RAMP_UNAVAILABLE
        )

    # --- stap 8: noodrem achteraf, 5 s later (SPEC 11.3) ---------------
    context[CTX_UNSUB_NOODREM] = async_call_later(
        hass,
        NOODREM_NA_SECONDEN,
        _maak_noodrem_achteraf(hass, registry_id, person_entity_id, wekker),
    )

    # --- stap 9: de stoptimer (SPEC 9.4) -------------------------------
    context[CTX_UNSUB_STOP] = async_call_later(
        hass,
        STOP_NA_MINUTEN * 60,
        _maak_stoptimer(hass, registry_id, person_entity_id, alarm_id),
    )

    _LOGGER.debug(
        "Wekker %s (%s) afgegaan voor moment %s op %s, oploop naar %d%%",
        alarm_id,
        wekker.get("name"),
        moment.isoformat(),
        speaker,
        doel_pct,
    )


async def _async_faal(
    hass: HomeAssistant,
    registry_id: str,
    person_entity_id: str,
    wekker: dict[str, Any],
    kind: str,
    lamp_al_gedaan: bool = False,
    ma_reden: str = "",
) -> None:
    """De wekker gaat niet af (SPEC 11.6). Gooit nooit.

    Drie dingen, in deze volgorde:

    1. **De wake-up light gaat wél aan**, als hij was ingesteld. Vastgelegd in SPEC
       11.6 punt 2: hij had ook aan moeten gaan als het geluid het had gedaan. Wat het
       product **niet** doet, is een lamp verzinnen die de klant niet heeft gekozen.
    2. De melding (SPEC 11.7). Ná de lamp, zodat een lamp die óók faalt niet de reden
       overschrijft waaróm de wekker stil bleef.
    3. Het `failed`-event, zodat een open kaart het meteen toont.

    De wekker komt **niet** in het ringing-register: er is niets om te stoppen. De lamp
    blijft aan en de klant zet hem zelf uit, net als na een gewone wekker (SPEC 12).

    `ma_reden` is de tekst die Music Assistant meegaf. Alleen `sound_gone` gebruikt
    hem; de andere soorten negeren hem stil, want `meldingen.tekst_voor` neemt
    `**extra` en kijkt per soort wat hij nodig heeft.
    """
    store = hass.data[DOMAIN][DATA_STORE]
    if not lamp_al_gedaan:
        await _async_lamp_aan(hass, registry_id, person_entity_id, wekker)

    message = await meldingen.async_meld(
        hass, store, registry_id, wekker, kind, ma_reden=ma_reden
    )

    abonnement.register_van(hass).stuur(
        {
            "event": abonnement.EVENT_FAILED,
            "person": person_entity_id,
            "alarm_id": wekker["id"],
            "reason": kind,
            "text": message["text"],
        }
    )


# =======================================================================
# Het geluid
# =======================================================================


def shuffle_van(hass: HomeAssistant, speaker: str) -> bool | None:
    """De huidige shuffle-stand van de speaker, of `None` (SPEC 9.6).

    Dezelfde drie redenen voor `None` als bij `volume_pct_van`: de speaker is er
    niet, is `unavailable`, of heeft geen `shuffle`-attribuut. Dat laatste hoort bij
    het tweede — extra state attributes verdwijnen zodra een entiteit `unavailable`
    is (valkuil 18) — en het is precies waarom `None` "zet niets terug" betekent en
    niet "hij stond uit". Een verzonnen `False` zou de shuffle van de klant
    uitzetten omdat wíj hem niet konden lezen.
    """
    state = hass.states.get(speaker)
    if state is None or state.state == STATE_UNAVAILABLE:
        return None
    stand = state.attributes.get("shuffle")
    if not isinstance(stand, bool):
        return None
    return stand


async def async_zet_shuffle(hass: HomeAssistant, speaker: str, aan: bool) -> None:
    """Zet shuffle aan of uit. Gooit nooit.

    Shuffle is een verbetering van de wekker en niet de wekker zelf: lukt de aanroep
    niet, dan begint hij bij het eerste nummer — hinderlijk, maar geen stille wekker.
    Daarom wordt de uitkomst niet eens teruggegeven.

    **`blocking=True` en dat is geen detail.** Met `blocking=False` verpakt HA de
    aanroep in `_run_service_call_catch_exceptions` en bereikt de fout ons nooit
    (valkuil 42) — dan lijkt shuffle altijd te lukken en komt niemand er ooit achter
    dat deze speaker het niet kan. Bovendien moet de aanroep áf zijn vóór
    `play_media`: MA past shuffle toe bij het laden van de queue (valkuil 51).
    """
    try:
        await hass.services.async_call(
            "media_player",
            "shuffle_set",
            {ATTR_ENTITY_ID: speaker, "shuffle": aan},
            blocking=True,
        )
    except Exception as fout:  # noqa: BLE001 - zie docstring
        _LOGGER.warning(
            "Shuffle %s zetten op %s is mislukt (%s)",
            "aan" if aan else "uit",
            speaker,
            fout,
        )


async def async_shuffle_aan_voor(
    hass: HomeAssistant, speaker: str, media_type: str | None
) -> bool | None:
    """Zet shuffle aan als het geluid meerdere nummers heeft, en geef de OUDE stand.

    Geeft `None` terug als er niets is aangezet **of** als de oude stand niet te
    lezen was. In beide gevallen betekent dat "zet bij het stoppen niets terug", en
    dat die twee gevallen dezelfde uitkomst delen is met opzet:

    - **niets aangezet** (radio, een los nummer) → dan is er ook niets van ons om
      terug te zetten, en de shuffle-stand van de klant is de zijne. Zou hier tóch
      teruggezet worden, dan draaien we een wijziging terug die de klant zélf tijdens
      de wekker maakte;
    - **niet te lezen** → SPEC 9.5, en nu ook 9.6: nooit een verzonnen waarde
      terugzetten.

    De lezing gebeurt **vóór** het zetten, om dezelfde reden als bij het volume: erna
    lees je je eigen waarde terug.
    """
    if not shuffle.moet_shuffelen(media_type):
        return None
    stand_voor = shuffle_van(hass, speaker)
    if stand_voor is None:
        _LOGGER.debug(
            "Shuffle van %s is niet te lezen; er wordt bij het stoppen niets teruggezet",
            speaker,
        )
    await async_zet_shuffle(hass, speaker, True)
    return stand_voor


async def _async_start_geluid(
    hass: HomeAssistant, speaker: str, geluid: dict[str, Any]
) -> tuple[bool, str | None]:
    """`music_assistant.play_media`, met de voorwaardelijke `radio_mode` (SPEC 8.3.1).

    **De terugval is de garantie, niet de lijst.** `SIMILAR_TRACKS_PROVIDERS` kan stil
    verouderen; blijft een provider erin staan die de feature verliest, dan geeft MA
    HTTP 500 en speelt er **niets** — en dat is erger dan een nummer dat na drie
    minuten stopt. Daarom wordt een mislukte poging mét `radio_mode` **opnieuw
    geprobeerd zonder**, en dat op `WARNING` gelogd zodat de lijst nagelopen kan
    worden.

    Fase 3a mat het verschil op dezelfde track, op dezelfde speaker::

        zonder radio_mode : HTTP 200, queue items=1
        met    radio_mode : HTTP 500, queue items=0, state=idle

    Geeft `(gelukt, reden)` terug. `reden` is de tekst die **Music Assistant zelf**
    meegaf bij de laatste poging, of `None` als er niets bruikbaars was. Die reden
    gaat mee in de melding: in productie op 1.0.0 was hij "No playable items found"
    (Spotify niet geautoriseerd in MA), terwijl de melding beweerde dat het geluid
    niet meer bestond. De reden van de dienst is het enige dat de klant of de
    eigenaar naar de werkelijke oorzaak wijst — zie SPEC 11.7 en `meldingen.py`.

    De reden van de **eerste** poging (mét `radio_mode`) wordt bewust niet bewaard:
    die is meestal `UnsupportedFeaturedException`, en dat is een mededeling over
    onze eigen providerlijst en niet over het geluid.
    """
    uri = geluid.get("uri")
    if not uri:
        _LOGGER.warning("Geen URI om af te spelen op %s", speaker)
        return False, None

    if radiomodus.stuur_radio_mode_mee(uri):
        try:
            await _async_play(hass, speaker, uri, radio_mode=True)
            return True, None
        except Exception as fout:  # noqa: BLE001 - zie docstring
            _LOGGER.warning(
                "Afspelen van %s mét radio_mode is mislukt (%s); opnieuw zonder. "
                "Loop SIMILAR_TRACKS_PROVIDERS na — provider %r hoort er misschien "
                "niet meer in",
                uri,
                fout,
                radiomodus.provider_van(uri),
            )

    try:
        await _async_play(hass, speaker, uri, radio_mode=False)
    except Exception as fout:  # noqa: BLE001 - een mislukte wekker is geen crash
        _LOGGER.error("Afspelen van %s op %s is mislukt: %s", uri, speaker, fout)
        return False, _reden_van(fout)
    return True, None


def _reden_van(fout: BaseException) -> str | None:
    """De tekst van een exceptie, geschikt om aan een klant te tonen.

    Wat MA teruggeeft is niet altijd een zin. `str(fout)` kan leeg zijn (een
    exceptie zonder argumenten), of een meerregelige brok met een stacktrace erin
    wanneer HA de fout van de MA-server doorgeeft. Beide zijn onbruikbaar in een
    melding die op één regel in een kaart staat, dus:

    - leeg of alleen witruimte → `None`, en de melding laat het deel over de reden
      dan weg. Liever geen reden dan een lege haakjesuitdrukking;
    - alleen de **eerste** regel, want daar staat bij MA de mededeling zelf
      ("No playable items found"), en wat erna komt is context voor een log.
    """
    tekst = str(fout).strip()
    if not tekst:
        return None
    return tekst.splitlines()[0].strip() or None


async def _async_play(
    hass: HomeAssistant, speaker: str, uri: str, radio_mode: bool
) -> None:
    """Eén `play_media`-aanroep. `radio_mode` wordt **weggelaten** als hij uit staat.

    Weglaten en niet op `False` zetten: dan houdt Music Assistant zijn eigen standaard
    (SPEC 8.3.1).
    """
    data: dict[str, Any] = {ATTR_ENTITY_ID: speaker, "media_id": uri}
    if radio_mode:
        data["radio_mode"] = True
    await hass.services.async_call(MA_DOMAIN, "play_media", data, blocking=True)


# =======================================================================
# Het volume
# =======================================================================


def volume_pct_van(hass: HomeAssistant, speaker: str) -> int | None:
    """Het huidige volume van de speaker in procenten, of `None`.

    `None` als de speaker er niet is, `unavailable` is, of geen `volume_level` heeft.
    Dat laatste hoort bij het eerste: **extra state attributes verdwijnen zodra een
    entiteit `unavailable` is** (`helpers/entity.py:1118-1124`, valkuil 18), dus juist
    op het moment dat je het volume zou willen kennen is het weg. Vandaar SPEC 9.5:
    niets terugzetten in plaats van een verzonnen waarde.
    """
    state = hass.states.get(speaker)
    if state is None or state.state == STATE_UNAVAILABLE:
        return None
    niveau = state.attributes.get("volume_level")
    if not isinstance(niveau, (int, float)):
        return None
    geclampt, _ = oploop_mod.clamp(round(float(niveau) * VOLUME_PCT_MAX))
    return geclampt


async def async_zet_volume(hass: HomeAssistant, speaker: str, pct: int) -> bool:
    """Zet het volume. Geeft terug of dat lukte; gooit nooit.

    Clampt zelf, en **logt als er geclampt moest worden**. Fase 0b mat dat MA buiten
    bereik stil afkapt met HTTP 200 (`-5` → 0, `150` → 100, `33.7` → 33), dus zonder
    deze regel is een rekenfout in de oploop onzichtbaar.
    """
    waarde, geclampt = oploop_mod.clamp(pct)
    if geclampt:
        _LOGGER.warning(
            "Volume %s valt buiten 0–%d en is afgekapt op %d voor %s. Dit hoort niet "
            "voor te komen; het duidt op een rekenfout in de oploop",
            pct,
            VOLUME_PCT_MAX,
            waarde,
            speaker,
        )
    try:
        await hass.services.async_call(
            "media_player",
            "volume_set",
            {ATTR_ENTITY_ID: speaker, "volume_level": waarde / VOLUME_PCT_MAX},
            blocking=True,
        )
    except Exception as fout:  # noqa: BLE001 - volume is geen reden om te crashen
        _LOGGER.debug("Volume zetten op %s is mislukt: %s", speaker, fout)
        return False
    return True


class _Oploop:
    """De volume-oploop: 20 stappen van 1 seconde naar het ingestelde niveau.

    **Waarom `async_call_later` en niet `asyncio.sleep` in een taak.** Twee redenen, en
    de tweede is de belangrijkste:

    1. Een `async_call_later` levert een unsub op, dus afbreken is één aanroep en er
       blijft nooit een taak hangen die nog één keer het volume zet nadat de wekker is
       gestopt.
    2. Hij loopt op **HA's klok**, en die is in een test met `async_fire_time_changed`
       vooruit te zetten. Een oploop met `asyncio.sleep` zou 20 echte seconden per test
       kosten, en fase 0b heeft laten zien wat er dan gebeurt: dan meet niemand hem
       meer per stap (valkuil 31 — Chrome kneep de cadans af tot sprongen van 2, en
       alleen de totaalduur klopte).

    De oploop breekt af bij drie dingen: de wekker is gestopt, de speaker is weggevallen,
    of de **gebruiker heeft zelf aan het volume gedraaid** (SPEC 9.3).
    """

    __slots__ = (
        "_alarm_id",
        "_hass",
        "_index",
        "_laatst_gezet",
        "_registry_id",
        "_speaker",
        "_unsub",
        "_waarden",
    )

    def __init__(
        self,
        hass: HomeAssistant,
        registry_id: str,
        alarm_id: str,
        speaker: str,
        doel_pct: int,
    ) -> None:
        self._hass = hass
        self._registry_id = registry_id
        self._alarm_id = alarm_id
        self._speaker = speaker
        self._waarden = oploop_mod.stappen(doel_pct)
        self._index = 0
        # Wat de oploop het laatst zélf heeft gezet. Stap 3 van de afvuurvolgorde zette
        # 0, dus daar begint de vergelijking.
        self._laatst_gezet = 0
        self._unsub: Callable[[], None] | None = None

    def start(self) -> None:
        self._plan()

    def stop(self) -> None:
        """Breek de oploop af. Idempotent."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    @property
    def klaar(self) -> bool:
        return self._index >= len(self._waarden)

    def _plan(self) -> None:
        self._unsub = async_call_later(self._hass, OPLOOP_STAP_SECONDEN, self._async_tik)

    async def _async_tik(self, _nu: dt.datetime) -> None:
        self._unsub = None

        register = abonnement.register_van(self._hass)
        if not register.is_afgaand(self._registry_id, self._alarm_id):
            _LOGGER.debug(
                "Oploop van %s stopt: de wekker gaat niet meer af", self._alarm_id
            )
            return

        gelezen = volume_pct_van(self._hass, self._speaker)
        if gelezen is None and _speaker_weg(self._hass, self._speaker):
            # De speaker is weggevallen. Doorgaan met volume zetten heeft geen zin; de
            # melding hoort bij de tweede noodremcontrole (SPEC 11.3) en niet hier,
            # anders staan er twee meldingen over hetzelfde.
            _LOGGER.debug(
                "Oploop van %s stopt: speaker %s is weggevallen",
                self._alarm_id,
                self._speaker,
            )
            return

        if oploop_mod.wijkt_af(gelezen, self._laatst_gezet):
            _LOGGER.debug(
                "Oploop van %s afgebroken: volume staat op %s%% terwijl de oploop "
                "%s%% zette — iemand draait zelf aan de knop",
                self._alarm_id,
                gelezen,
                self._laatst_gezet,
            )
            return

        gezet = self._waarden[self._index]
        self._index += 1
        await async_zet_volume(self._hass, self._speaker, gezet)
        self._laatst_gezet = gezet

        if not self.klaar:
            self._plan()
        else:
            _LOGGER.debug(
                "Oploop van %s klaar op %d%% in %d stappen",
                self._alarm_id,
                gezet,
                len(self._waarden),
            )


def _speaker_weg(hass: HomeAssistant, speaker: str) -> bool:
    state = hass.states.get(speaker)
    return state is None or state.state == STATE_UNAVAILABLE


# =======================================================================
# De wake-up light (SPEC 12)
# =======================================================================


async def _async_lamp_aan(
    hass: HomeAssistant,
    registry_id: str,
    person_entity_id: str,
    wekker: dict[str, Any],
) -> None:
    """`light.turn_on` met `brightness_pct`. Geen `transition`, geen opbouw.

    **Geen `transition` meesturen** en niet `transition: 0`: "geen opbouw" is de eis, en
    een expliciete nul is niet hetzelfde als hem weglaten bij lampen die de parameter
    niet kennen (SPEC 12).

    Faalt de lamp, dan is dat **geen reden om de wekker te laten falen**: het geluid is
    de wekker en het licht is een toevoeging. `WARNING` in het log plus de melding uit
    SPEC 11.7. Gooit nooit.
    """
    lamp = wekker.get("light")
    if not isinstance(lamp, dict) or not lamp.get("entity_id"):
        return

    try:
        await hass.services.async_call(
            "light",
            "turn_on",
            {
                ATTR_ENTITY_ID: lamp["entity_id"],
                "brightness_pct": lamp.get("brightness_pct"),
            },
            blocking=True,
        )
    except Exception as fout:  # noqa: BLE001 - het licht is de wekker niet
        _LOGGER.warning(
            "Wake-up light %s kon niet aangezet worden (%s); de wekker gaat wél af",
            lamp["entity_id"],
            fout,
        )
        store = hass.data[DOMAIN][DATA_STORE]
        await meldingen.async_meld(
            hass, store, registry_id, wekker, meldingen.KIND_LIGHT_FAILED
        )


# =======================================================================
# De tweede noodremcontrole en de stoptimer
# =======================================================================


def _maak_noodrem_achteraf(
    hass: HomeAssistant,
    registry_id: str,
    person_entity_id: str,
    wekker: dict[str, Any],
) -> Callable[[dt.datetime], Any]:
    """De controle van SPEC 11.3, 5 seconden na het starten.

    Dit vangt de speaker die tijdens het starten wegvalt: de aanroep slaagde en er is
    tóch geen geluid. Het is ook het net onder SPEC 11.2.1 — is de URI werkelijk dood,
    dan levert het afspelen niets op en komt het hier alsnog boven.

    **De wekker wordt niet gestopt.** SPEC 11.3 vraagt om opnieuw controleren, niet om
    afbreken: als de speaker terugkomt speelt de queue verder, en tot die tijd hoort de
    kaart een stopknop te blijven zodat de klant het volume teruggezet krijgt.
    """

    async def _controleer(_nu: dt.datetime) -> None:
        register = abonnement.register_van(hass)
        alarm_id = wekker["id"]
        if not register.is_afgaand(registry_id, alarm_id):
            return
        context = register.actief.get((registry_id, alarm_id)) or {}
        context[CTX_UNSUB_NOODREM] = None

        uitkomst, _ = noodrem.controleer_speaker(hass, wekker.get("speaker") or "")
        if uitkomst is not Uitkomst.FOUT:
            return

        _LOGGER.warning(
            "Speaker %s viel weg binnen %s s na het starten van wekker %s",
            wekker.get("speaker"),
            NOODREM_NA_SECONDEN,
            alarm_id,
        )
        store = hass.data[DOMAIN][DATA_STORE]
        message = await meldingen.async_meld(
            hass, store, registry_id, wekker, meldingen.KIND_SPEAKER_LOST_DURING_PLAY
        )
        register.stuur(
            {
                "event": abonnement.EVENT_FAILED,
                "person": person_entity_id,
                "alarm_id": alarm_id,
                "reason": meldingen.KIND_SPEAKER_LOST_DURING_PLAY,
                "text": message["text"],
            }
        )

    return _controleer


def _maak_stoptimer(
    hass: HomeAssistant, registry_id: str, person_entity_id: str, alarm_id: str
) -> Callable[[dt.datetime], Any]:
    """De automatische stop na 30 minuten (SPEC 9.4).

    Dat voorkomt dat de muziek dagenlang doorspeelt in een lege woning. Er is **geen
    snooze** in v1.
    """

    async def _stop(_nu: dt.datetime) -> None:
        context = abonnement.register_van(hass).actief.get((registry_id, alarm_id))
        if context is not None:
            # De unsub van deze timer is nu verlopen; hem laten staan zou `stop`
            # verleiden een afgelopen timer af te zeggen.
            context[CTX_UNSUB_STOP] = None
        _LOGGER.debug(
            "Wekker %s stopt automatisch na %d minuten", alarm_id, STOP_NA_MINUTEN
        )
        await async_stop_afgaan(
            hass, registry_id, person_entity_id, alarm_id, abonnement.REASON_TIMEOUT
        )

    return _stop


# =======================================================================
# Stoppen
# =======================================================================


async def async_stop_afgaan(
    hass: HomeAssistant,
    registry_id: str,
    person_entity_id: str,
    alarm_id: str,
    reason: str | None,
) -> bool:
    """Stop een lopende wekker (SPEC 9.4, 9.5 en 10). Geeft terug of er iets liep.

    :param reason: `"user"`, `"timeout"` of `"deleted"` (SPEC 15.9), of **`None`** om
        géén `stopped`-event te sturen. Dat laatste is er voor het loslaten bij unload:
        SPEC 15.9 kent precies drie redenen, en een vierde verzinnen zou een
        machineleesbaar veld laten liegen tegen een kaart die er drie verwacht. De
        abonnees zijn op dat moment zelf aan het afbreken, dus er is niemand om het
        tegen te zeggen — maar het gelúid moet wél stoppen, want anders speelt het door
        zonder stoptimer en is dat precies de lege woning uit SPEC 9.4.

    In deze volgorde:

    1. **uit het register halen** — als eerste, en dat is de idempotentie (SPEC 15.8):
       een tweede stop vindt niets meer en doet niets, ook als de eerste nog aan het
       afronden is. Een wandtablet en een telefoon kunnen tegelijk drukken;
    2. oploop afbreken en de timers afzeggen, vóór het geluid, zodat er geen stap meer
       tussenkomt die het volume weer omhoog zet;
    3. **geluid stoppen**, en pas daarna het volume terugzetten — andersom klinkt de
       laatste seconde op het oude volume;
    4. volume terugzetten naar wat het vóór de wekker was, of **niets** als dat niet te
       lezen was;
    5. **shuffle** terugzetten, op precies dezelfde voorwaarden (SPEC 9.6);
    6. het `stopped`-event.

    De **wake-up light blijft aan** (SPEC 9.4). De klant zet hem zelf uit. Dat is geen
    vergetelheid: wie om 06:45 gewekt is en om 06:47 op stop drukt, staat anders in het
    donker.
    """
    register = abonnement.register_van(hass)
    context = register.actief.pop((registry_id, alarm_id), None)
    if context is None:
        return False

    loop = context.get(CTX_OPLOOP)
    if loop is not None:
        loop.stop()
    for sleutel in (CTX_UNSUB_NOODREM, CTX_UNSUB_STOP):
        unsub = context.get(sleutel)
        if unsub is not None:
            unsub()
            context[sleutel] = None

    speaker = context.get(CTX_SPEAKER) or ""
    if speaker:
        try:
            await hass.services.async_call(
                "media_player", "media_stop", {ATTR_ENTITY_ID: speaker}, blocking=True
            )
        except Exception as fout:  # noqa: BLE001 - stoppen mag niet stukgaan
            _LOGGER.warning("Geluid stoppen op %s is mislukt: %s", speaker, fout)

        volume_voor = context.get(CTX_VOLUME_VOOR)
        if volume_voor is None:
            # SPEC 9.5: nooit een verzonnen waarde terugzetten. DEBUG en niet WARNING,
            # want dit is de normale uitkomst als de speaker bij het afgaan al weg was.
            _LOGGER.debug(
                "Het volume van %s vóór wekker %s is niet bekend; er wordt niets "
                "teruggezet",
                speaker,
                alarm_id,
            )
        else:
            await async_zet_volume(hass, speaker, volume_voor)

        # Shuffle op dezelfde voorwaarden als het volume (SPEC 9.6). `None` betekent
        # óf "wij hebben hem niet aangezet" óf "de oude stand was niet te lezen", en
        # in beide gevallen is niets doen het juiste — zie `async_shuffle_aan_voor`.
        shuffle_voor = context.get(CTX_SHUFFLE_VOOR)
        if shuffle_voor is None:
            _LOGGER.debug(
                "Shuffle van %s wordt niet teruggezet voor wekker %s", speaker, alarm_id
            )
        else:
            await async_zet_shuffle(hass, speaker, shuffle_voor)

    if reason is not None:
        register.stuur(
            {
                "event": abonnement.EVENT_STOPPED,
                "person": person_entity_id,
                "alarm_id": alarm_id,
                "reason": reason,
            }
        )
    _LOGGER.debug("Wekker %s gestopt (%s)", alarm_id, reason or "unload")
    return True


async def async_stop_alles(hass: HomeAssistant, reason: str | None = None) -> int:
    """Stop alle afgaande wekkers. Geeft terug hoeveel er liepen.

    Nodig bij unload, om twee dingen die elk voor zich al genoeg zijn:

    1. De oploop, de tweede noodremcontrole en de stoptimer zijn `async_call_later`s.
       Blijven die staan, dan tikt de eerste over een `hass.data[DOMAIN]` die net is
       losgelaten.
    2. Zonder stoptimer speelt de muziek **door**, en dan is er niemand meer die hem
       afzet — precies de lege woning waar SPEC 9.4 voor bestaat.
    """
    register = abonnement.register_van(hass)
    gestopt = 0
    for (registry_id, alarm_id), context in list(register.actief.items()):
        if await async_stop_afgaan(
            hass, registry_id, context.get(CTX_PERSON) or "", alarm_id, reason
        ):
            gestopt += 1
    return gestopt
