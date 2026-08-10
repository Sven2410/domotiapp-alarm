"""De negen WebSocket-commando's (SPEC 15).

**Geen enkel commando is admin-only** (SPEC 17). Dat is een bewuste keuze: klanten
draaien Fully Kiosk met een niet-admin account en juist zij moeten hun wekkers
kunnen beheren — en bij `alarms/stop` betekent admin-only dat de klant zijn eigen
wekker niet kan uitzetten. Er staat dus nergens een `@require_admin`.

Overal wordt een persoon aangeduid met **`entity_id`**; de vertaling naar het
registry-entry-ID gebeurt server-side (SPEC 6.2).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from . import entiteiten, ringing
from .const import (
    DATA_STORE,
    DATA_WS_REGISTERED,
    DOMAIN,
    MA_DOMAIN,
    SEARCH_LIMIT_DEFAULT,
    SEARCH_LIMIT_MAX,
    SEARCH_TIMEOUT_SECONDEN,
)
from .store import (
    AlarmStore,
    OpslagOnbruikbaar,
    PersonNietGevonden,
    PersoonOnleesbaar,
    registry_id_van_person,
)
from .validatie import (
    GEBRUIKERSVELDEN,
    SERVERVELDEN,
    ValidatieFout,
    valideer_persoon,
)
from .volgende import eerstvolgende_keer_dat_tijd_voorbijkomt, sorteer, volgende_wekker

_LOGGER = logging.getLogger(__name__)

TYPE_GET = f"{DOMAIN}/alarms/get"
TYPE_SAVE = f"{DOMAIN}/alarms/save"
TYPE_SET_ENABLED = f"{DOMAIN}/alarms/set_enabled"
TYPE_DELETE = f"{DOMAIN}/alarms/delete"
TYPE_SKIP_NEXT = f"{DOMAIN}/alarms/skip_next"
TYPE_SEARCH = f"{DOMAIN}/sound/search"
TYPE_ENTITIES = f"{DOMAIN}/entities/list"
TYPE_STOP = f"{DOMAIN}/alarms/stop"
TYPE_SUBSCRIBE = f"{DOMAIN}/ringing/subscribe"

# De acht emmers die music_assistant.search teruggeeft (SPEC 8.1). De volgorde
# hier is de volgorde in het antwoord: afspeellijsten en radio eerst, want dat is
# wat mensen in de praktijk voor een wekker kiezen (SPEC 15.6).
_SEARCH_EMMERS: tuple[str, ...] = (
    "playlists",
    "radio",
    "artists",
    "albums",
    "tracks",
    "podcasts",
    "audiobooks",
)


def _store(hass: HomeAssistant) -> AlarmStore:
    return hass.data[DOMAIN][DATA_STORE]


def _fout_omzetten(
    handler: Callable[..., Coroutine[Any, Any, None]],
) -> Callable[..., Coroutine[Any, Any, None]]:
    """Zet onze excepties om in de foutcodes uit SPEC 15.

    Eén plek, zodat de codes niet per commando kunnen afwijken.
    """

    async def wrapper(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        try:
            await handler(hass, connection, msg)
        except PersonNietGevonden as fout:
            connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, str(fout))
        except ValidatieFout as fout:
            connection.send_error(
                msg["id"], websocket_api.ERR_INVALID_FORMAT, f"{fout.veld}: {fout.bericht}"
            )
        except (OpslagOnbruikbaar, PersoonOnleesbaar) as fout:
            connection.send_error(
                msg["id"], websocket_api.ERR_HOME_ASSISTANT_ERROR, str(fout)
            )

    wrapper.__name__ = getattr(handler, "__name__", "wrapper")
    return wrapper


def _toestand(hass: HomeAssistant, person_entity_id: str) -> dict[str, Any]:
    """Het antwoord van `alarms/get`, dat ook alle mutaties teruggeven (SPEC 15.2).

    Eén functie, zodat kaart en server na elke handeling over dezelfde toestand
    beschikken en er geen tweede aanroep nodig is.
    """
    registry_id = registry_id_van_person(hass, person_entity_id)
    store = _store(hass)
    wekkers = sorteer(store.wekkers(registry_id))
    nu = dt_util.now()
    volgende = volgende_wekker(wekkers, nu)
    register = ringing.register_van(hass)
    return {
        "alarms": wekkers,
        "next_fire": (
            None
            if volgende is None
            else {
                "at": volgende.at.isoformat(),
                "text": volgende.text,
                "alarm_id": volgende.alarm_id,
            }
        ),
        "ringing": register.afgaand_voor(registry_id),
        "stored": store.heeft_opslag(registry_id),
    }


# --- 15.1 alarms/get ----------------------------------------------------


@websocket_api.websocket_command(
    {vol.Required("type"): TYPE_GET, vol.Required("person"): cv.string}
)
@websocket_api.async_response
@_fout_omzetten
async def _handle_get(hass, connection, msg) -> None:
    connection.send_result(msg["id"], _toestand(hass, msg["person"]))


# --- 15.2 alarms/save ---------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): TYPE_SAVE,
        vol.Required("person"): cv.string,
        vol.Required("alarm"): dict,
    }
)
@websocket_api.async_response
@_fout_omzetten
async def _handle_save(hass, connection, msg) -> None:
    registry_id = registry_id_van_person(hass, msg["person"])
    store = _store(hass)
    aangeleverd: dict[str, Any] = msg["alarm"]

    # De server beheert skip_next, one_shot_at, last_fired en last_message zelf en
    # accepteert ze niet van de kaart (SPEC 15.2). Ze stil negeren zou de kaart
    # laten denken dat ze zijn overgenomen; daarom is het een fout.
    verboden = sorted(set(aangeleverd) & SERVERVELDEN)
    if verboden:
        raise ValidatieFout(
            "alarm", f"deze velden beheert de server zelf en mogen niet worden meegestuurd: {verboden}"
        )
    onbekend = sorted(set(aangeleverd) - GEBRUIKERSVELDEN)
    if onbekend:
        raise ValidatieFout("alarm", f"onbekende velden: {onbekend}")

    alarm_id = aangeleverd.get("id")
    bestaand = None
    if alarm_id is not None:
        if not isinstance(alarm_id, str) or not alarm_id:
            raise ValidatieFout("alarm.id", "moet een niet-lege tekst zijn")
        bestaand = store.wekker(registry_id, alarm_id)
        if bestaand is None:
            raise PersonNietGevonden(f"wekker {alarm_id} bestaat niet bij {msg['person']}")
    else:
        alarm_id = store.nieuw_alarm_id()

    # De boekhoudvelden komen uit de bestaande wekker, of staan op hun beginwaarde.
    samengesteld: dict[str, Any] = {
        **aangeleverd,
        "id": alarm_id,
        "skip_next": bool(bestaand["skip_next"]) if bestaand else False,
        "last_fired": bestaand["last_fired"] if bestaand else None,
        "last_message": bestaand["last_message"] if bestaand else None,
        "one_shot_at": None,
    }

    # **Eerst het schema, dan de toestemming.** Die volgorde is niet willekeurig:
    # SPEC 15.2 zegt dat een `brightness_pct` buiten bereik `invalid_format` geeft
    # en dat een speaker die de eisen van 7.2 niet haalt `not_allowed` geeft. Draait
    # de toestemmingscontrole eerst, dan komt een ongeldige helderheid als
    # `not_allowed` terug zodra het label toevallig ontbreekt — dezelfde afkeuring
    # onder een andere code, afhankelijk van de omgeving.
    gevalideerd = valideer_persoon({"alarms": [samengesteld]}, veld="alarm")["alarms"][0]

    # De speaker moet aan de zes eisen voldoen (SPEC 7.2 en 7.3). Dit is
    # `not_allowed` en niet `invalid_format`: de vorm is goed, de keuze niet.
    geschikt, reden = entiteiten.is_ma_speaker(hass, gevalideerd["speaker"])
    if not geschikt:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_ALLOWED, str(reden))
        return

    if gevalideerd["light"] is not None:
        geschikt, reden = entiteiten.is_wekkerlamp(hass, gevalideerd["light"]["entity_id"])
        if not geschikt:
            connection.send_error(msg["id"], websocket_api.ERR_NOT_ALLOWED, str(reden))
            return

    # one_shot_at wordt server-side berekend als days leeg is (SPEC 15.2).
    if not gevalideerd["days"]:
        moment = eerstvolgende_keer_dat_tijd_voorbijkomt(dt_util.now(), gevalideerd["time"])
        gevalideerd["one_shot_at"] = moment.isoformat()

    await store.async_zet_wekker(registry_id, gevalideerd)
    connection.send_result(msg["id"], _toestand(hass, msg["person"]))


# --- 15.3 alarms/set_enabled -------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): TYPE_SET_ENABLED,
        vol.Required("person"): cv.string,
        vol.Required("alarm_id"): cv.string,
        vol.Required("enabled"): bool,
    }
)
@websocket_api.async_response
@_fout_omzetten
async def _handle_set_enabled(hass, connection, msg) -> None:
    registry_id = registry_id_van_person(hass, msg["person"])
    velden: dict[str, Any] = {"enabled": msg["enabled"]}
    # Een wekker uitzetten wist skip_next: uit-en-weer-aan is de manier waarop
    # iemand "vergeet het maar" intrekt (SPEC 15.3).
    if not msg["enabled"]:
        velden["skip_next"] = False
    bijgewerkt = await _store(hass).async_werk_velden_bij(registry_id, msg["alarm_id"], velden)
    if bijgewerkt is None:
        raise PersonNietGevonden(f"wekker {msg['alarm_id']} bestaat niet bij {msg['person']}")
    connection.send_result(msg["id"], _toestand(hass, msg["person"]))


# --- 15.4 alarms/delete ------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): TYPE_DELETE,
        vol.Required("person"): cv.string,
        vol.Required("alarm_id"): cv.string,
    }
)
@websocket_api.async_response
@_fout_omzetten
async def _handle_delete(hass, connection, msg) -> None:
    registry_id = registry_id_van_person(hass, msg["person"])
    register = ringing.register_van(hass)

    # Loopt de wekker nu, dan wordt hij eerst gestopt (SPEC 15.4). Zonder dat
    # blijft er geluid draaien voor een wekker die niet meer bestaat. Het
    # daadwerkelijke stoppen — geluid, oploop, volume terugzetten — zit in fase 3b;
    # hier verdwijnt hij uit het register en gaat het bericht eruit.
    if register.is_afgaand(registry_id, msg["alarm_id"]):
        register.actief.pop((registry_id, msg["alarm_id"]), None)
        register.stuur(
            {
                "event": ringing.EVENT_STOPPED,
                "person": msg["person"],
                "alarm_id": msg["alarm_id"],
                "reason": ringing.REASON_DELETED,
            }
        )

    if not await _store(hass).async_verwijder_wekker(registry_id, msg["alarm_id"]):
        raise PersonNietGevonden(f"wekker {msg['alarm_id']} bestaat niet bij {msg['person']}")
    connection.send_result(msg["id"], _toestand(hass, msg["person"]))


# --- 15.5 alarms/skip_next ---------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): TYPE_SKIP_NEXT,
        vol.Required("person"): cv.string,
        vol.Required("alarm_id"): cv.string,
        vol.Required("skip"): bool,
    }
)
@websocket_api.async_response
@_fout_omzetten
async def _handle_skip_next(hass, connection, msg) -> None:
    registry_id = registry_id_van_person(hass, msg["person"])
    bijgewerkt = await _store(hass).async_werk_velden_bij(
        registry_id, msg["alarm_id"], {"skip_next": msg["skip"]}
    )
    if bijgewerkt is None:
        raise PersonNietGevonden(f"wekker {msg['alarm_id']} bestaat niet bij {msg['person']}")
    connection.send_result(msg["id"], _toestand(hass, msg["person"]))


# --- 15.6 sound/search -------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): TYPE_SEARCH,
        vol.Required("query"): cv.string,
        vol.Optional("media_types"): [cv.string],
        vol.Optional("limit", default=SEARCH_LIMIT_DEFAULT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=SEARCH_LIMIT_MAX)
        ),
    }
)
@websocket_api.async_response
async def _handle_search(hass, connection, msg) -> None:
    """Proxy naar `music_assistant.search` (SPEC 15.6).

    De kaart praat niet rechtstreeks met Music Assistant: dan zou de kaart de
    MA-config-entry moeten opzoeken en zou de filtering in twee talen bestaan.
    """
    entries = hass.config_entries.async_loaded_entries(MA_DOMAIN)
    if not entries:
        connection.send_error(
            msg["id"],
            websocket_api.ERR_NOT_FOUND,
            "Music Assistant is niet beschikbaar. Zonder Music Assistant kan er geen "
            "geluid gekozen worden.",
        )
        return
    if len(entries) > 1:
        _LOGGER.debug(
            "Er zijn %d Music Assistant-config-entries; de eerste wordt gebruikt (%s)",
            len(entries),
            entries[0].entry_id,
        )

    data: dict[str, Any] = {
        "config_entry_id": entries[0].entry_id,
        "name": msg["query"],
        "limit": msg["limit"],
    }
    if msg.get("media_types"):
        data["media_type"] = msg["media_types"]

    try:
        # Time-out van 10 s (SPEC 15.6): een trage zoekopdracht mag de editor niet
        # laten hangen. MA's eigen zoekopdracht ging in fase 0b in tientallen
        # milliseconden, maar RadioBrowser was wisselvallig en gaf minutenlang
        # fouten.
        async with asyncio.timeout(SEARCH_TIMEOUT_SECONDEN):
            antwoord = await hass.services.async_call(
                MA_DOMAIN,
                "search",
                data,
                blocking=True,
                return_response=True,
            )
    except TimeoutError:
        connection.send_error(
            msg["id"],
            websocket_api.ERR_HOME_ASSISTANT_ERROR,
            "Zoeken duurt te lang. Probeer het opnieuw.",
        )
        return
    except HomeAssistantError as fout:
        connection.send_error(msg["id"], websocket_api.ERR_HOME_ASSISTANT_ERROR, str(fout))
        return

    connection.send_result(msg["id"], {"results": _plat(antwoord or {})})


def _plat(antwoord: dict[str, Any]) -> list[dict[str, Any]]:
    """Eén platte lijst uit de acht emmers van MA (SPEC 15.6).

    De kaart toont een zoekresultaat en niet acht koppen; `media_type` per treffer
    houdt het onderscheid vast.
    """
    resultaten: list[dict[str, Any]] = []
    for emmer in _SEARCH_EMMERS:
        for item in antwoord.get(emmer) or []:
            if not isinstance(item, dict):
                continue
            resultaten.append(
                {
                    "name": item.get("name"),
                    "uri": item.get("uri"),
                    "media_type": item.get("media_type"),
                    "image": item.get("image"),
                    "artists": item.get("artists"),
                    "album": item.get("album"),
                }
            )
    return resultaten


# --- 15.7 entities/list ------------------------------------------------


@websocket_api.websocket_command({vol.Required("type"): TYPE_ENTITIES})
@callback
def _handle_entities(hass, connection, msg) -> None:
    connection.send_result(
        msg["id"],
        {
            "speakers": entiteiten.speakers(hass).as_dict(),
            "lights": entiteiten.lampen(hass).as_dict(),
        },
    )


# --- 15.8 alarms/stop --------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): TYPE_STOP,
        vol.Required("person"): cv.string,
        vol.Required("alarm_id"): cv.string,
    }
)
@websocket_api.async_response
@_fout_omzetten
async def _handle_stop(hass, connection, msg) -> None:
    """Stop een lopende wekker (SPEC 15.8).

    **Idempotent:** een wekker stoppen die niet loopt is geen fout en geeft gewoon
    de huidige toestand terug. Een wandtablet en een telefoon kunnen tegelijk
    drukken.

    Het daadwerkelijke stoppen van geluid, oploop en volume zit in fase 3b. Hier
    verdwijnt de wekker uit het register en gaat het bericht naar de abonnees.
    """
    registry_id = registry_id_van_person(hass, msg["person"])
    register = ringing.register_van(hass)
    if register.is_afgaand(registry_id, msg["alarm_id"]):
        register.actief.pop((registry_id, msg["alarm_id"]), None)
        register.stuur(
            {
                "event": ringing.EVENT_STOPPED,
                "person": msg["person"],
                "alarm_id": msg["alarm_id"],
                "reason": ringing.REASON_USER,
            }
        )
    connection.send_result(msg["id"], _toestand(hass, msg["person"]))


# --- 15.9 ringing/subscribe --------------------------------------------


@websocket_api.websocket_command(
    {vol.Required("type"): TYPE_SUBSCRIBE, vol.Optional("person"): cv.string}
)
@callback
def _handle_subscribe(hass, connection, msg) -> None:
    """Abonneer op afgaan-gebeurtenissen (SPEC 15.9)."""
    gewenste_persoon: str | None = msg.get("person")

    @callback
    def doorsturen(bericht: dict[str, Any]) -> None:
        if gewenste_persoon is not None and bericht.get("person") != gewenste_persoon:
            return
        connection.send_message(websocket_api.event_message(msg["id"], bericht))

    afmelden = ringing.register_van(hass).abonneer(doorsturen)
    connection.subscriptions[msg["id"]] = afmelden
    connection.send_result(msg["id"])


# --- registratie -------------------------------------------------------

_COMMANDOS = (
    _handle_get,
    _handle_save,
    _handle_set_enabled,
    _handle_delete,
    _handle_skip_next,
    _handle_search,
    _handle_entities,
    _handle_stop,
    _handle_subscribe,
)


@callback
def async_register(hass: HomeAssistant) -> None:
    """Registreer de negen commando's, één keer per HA-run.

    HA kent geen `async_unregister_command`, dus een tweede registratie zou de
    eerste overschrijven. De vlag voorkomt dat bij een tweede config entry.
    """
    data = hass.data.setdefault(DOMAIN, {})
    if data.get(DATA_WS_REGISTERED):
        return
    for commando in _COMMANDOS:
        websocket_api.async_register_command(hass, commando)
    data[DATA_WS_REGISTERED] = True
    _LOGGER.debug("%d WebSocket-commando's geregistreerd", len(_COMMANDOS))
