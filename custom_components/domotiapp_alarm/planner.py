"""De planner: wekkers op tijd plannen, herplannen en inhalen (SPEC 13).

## Wat deze module wél en niet doet

Hij bepaalt **wanneer** een wekker afgaat en roept dan `afvuren.async_laat_afgaan`
aan. Wat er dan gebeurt staat in `afvuren.py`; deze module raakt geen speaker en
geen lamp.

## De twee planners, en waarom

**GEMETEN** in fase 0 (`docs/fase-0/ONDERZOEK.md` E1.1), en het is de keuze die HA's
eigen tijdtrigger ook maakt:

| Geval | Planner | HA's eigen keuze |
|---|---|---|
| herhaaldagen | `async_track_time_change` | `triggers/time.py:284-292` |
| eenmalig | `async_track_point_in_time` | `triggers/time.py:176-200` |

**De dagfiltering gebeurt in de callback, niet in de planner** (SPEC 13.1).
`async_track_time_change` kent geen dagpatroon; we plannen op `hour` en `minute` en
controleren in de callback of vandaag een aangevinkte dag is. Dat is eenvoudiger dan
zeven listeners en het houdt de dagvergelijking op één plek.

## De rem die niet te omzeilen is

Een `async_track_point_in_time` op een moment in het verleden vuurt
**onmiddellijk** — gemeten +0,0002 s. Zonder rem gaat een 06:45-wekker om 14:00 af
zodra HA herstart.

Die rem zit op **twee** plekken, en dat is met opzet:

1. **Bij het plannen.** Een eenmalige wekker wordt alleen gepland als
   `one_shot_at` in de toekomst ligt. Ligt hij in het verleden, dan is hij een geval
   voor de inhaalslag en niet voor de planner.
2. **In het afvuurpad.** `_async_vuur` weigert een moment dat verder dan het
   respijtvenster in het verleden ligt, en weigert een moment dat `last_fired` al
   heeft gehad. Ook een listener die er langs een weg komt die ik niet heb voorzien,
   kan dus geen wekker van vanmorgen om 14:00 laten afgaan.

Eén rem zou genoeg lijken. Twee is er omdat de eerste een *aanname* over de
planner is en de tweede een *eigenschap* van het afvuren — en de kosten van die
dubbele controle zijn nul terwijl de kosten van het faalgeval een verslapen klant
zijn.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from typing import Any

from homeassistant.const import EVENT_CORE_CONFIG_UPDATE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_time_change,
)
from homeassistant.util import dt as dt_util

from . import afvuren, meldingen
from .const import DATA_PLANNER, DATA_STORE, DOMAIN, RESPIJT_MINUTEN
from .volgende import laatste_verstreken_moment, parse_tijd

_LOGGER = logging.getLogger(__name__)


class Planner:
    """Houdt de listeners bij en bouwt ze volledig opnieuw op bij elke wijziging.

    **Volledig opnieuw** en niet incrementeel (SPEC 13.5). Een wekkerlijst is klein
    en de kosten zijn verwaarloosbaar; incrementeel bijwerken is de plek waar een
    verdwaalde listener ontstaat die op een verwijderde wekker vuurt.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        # Per (registry_id, alarm_id) de opzegfunctie van de listener.
        self._listeners: dict[tuple[str, str], CALLBACK_TYPE] = {}
        self._unsub_config: CALLBACK_TYPE | None = None

    # --- levenscyclus ---------------------------------------------------

    async def async_start(self) -> None:
        """Inhaalslag doen en daarna vooruit plannen (SPEC 13.4 stap 7)."""
        self._unsub_config = self.hass.bus.async_listen(
            EVENT_CORE_CONFIG_UPDATE, self._op_config_wijziging
        )
        await self.async_herplan(met_inhaalslag=True)

    @callback
    def async_stop(self) -> None:
        """Alle listeners opzeggen (SPEC 13.5, unload)."""
        self._zeg_listeners_op()
        if self._unsub_config is not None:
            self._unsub_config()
            self._unsub_config = None

    @callback
    def _zeg_listeners_op(self) -> None:
        for opzeggen in self._listeners.values():
            opzeggen()
        self._listeners.clear()

    @property
    def geplande_wekkers(self) -> set[tuple[str, str]]:
        """Welke wekkers nu een listener hebben. Alleen voor tests en diagnose."""
        return set(self._listeners)

    # --- herplannen -----------------------------------------------------

    async def async_herplan(self, *, met_inhaalslag: bool = False) -> None:
        """Bouw de hele planning opnieuw op.

        Wordt aangeroepen bij setup, na elke wijziging via een WebSocket-commando en
        bij een tijdzonewijziging (SPEC 13.5).
        """
        self._zeg_listeners_op()

        store = self.hass.data[DOMAIN][DATA_STORE]
        # Kapotte personen en een onbruikbare opslag leveren hier niets op: voor hen
        # wordt niets gepland (SPEC 19.2 geval B regel 6 en geval C regel 6).
        alles = store.alle_wekkers()

        nu = dt_util.now()
        for registry_id, wekkers in alles.items():
            person_entity_id = self._person_entity_id(registry_id)
            for wekker in wekkers:
                if not wekker.get("enabled"):
                    # Een uitgezette wekker wordt niet gepland en niet ingehaald.
                    continue
                if met_inhaalslag:
                    await self._async_inhaalslag(registry_id, person_entity_id, wekker)
                    # De wekker kan door de inhaalslag zijn gewijzigd (skip_next
                    # gewist, last_fired gezet); opnieuw lezen zodat we vooruit
                    # plannen op de actuele stand.
                    vers = store.wekker(registry_id, wekker["id"])
                    if vers is None or not vers.get("enabled"):
                        continue
                    wekker = vers
                self._plan(registry_id, person_entity_id, wekker, nu)

        _LOGGER.debug(
            "Planning opgebouwd: %d wekker(s) gepland%s",
            len(self._listeners),
            " (met inhaalslag)" if met_inhaalslag else "",
        )

    def _person_entity_id(self, registry_id: str) -> str:
        """Het entity-ID bij een registry-entry-ID, voor de events (SPEC 15.9).

        De opslag werkt op registry-entry-ID; de kaart en de events op entity-ID.
        Bestaat de entiteit niet meer, dan is er niets om te plannen — maar dat
        besluit hoort niet hier: `_plan` slaat hem dan over.
        """
        registry = er.async_get(self.hass)
        for item in registry.entities.values():
            if item.id == registry_id:
                return item.entity_id
        return ""

    # --- plannen --------------------------------------------------------

    @callback
    def _plan(
        self,
        registry_id: str,
        person_entity_id: str,
        wekker: dict[str, Any],
        nu: dt.datetime,
    ) -> None:
        """Zet één listener voor één wekker."""
        if not person_entity_id:
            # De person is verwijderd. Een wekker voor een niet-bestaande persoon
            # gaat niet af (SPEC 18.1 punt 2).
            _LOGGER.debug(
                "Wekker %s hoort bij een verwijderde person; niet gepland", wekker["id"]
            )
            return

        sleutel = (registry_id, wekker["id"])
        dagen = wekker.get("days") or []

        if dagen:
            uur, minuut = parse_tijd(wekker["time"])
            self._listeners[sleutel] = async_track_time_change(
                self.hass,
                self._maak_callback(registry_id, person_entity_id, wekker["id"]),
                hour=uur,
                minute=minuut,
                second=0,
            )
            return

        # Eenmalige wekker: één absoluut moment.
        rauw = wekker.get("one_shot_at")
        if not rauw:
            _LOGGER.warning(
                "Eenmalige wekker %s heeft geen one_shot_at en wordt niet gepland",
                wekker["id"],
            )
            return
        moment = dt.datetime.fromisoformat(rauw)
        if moment <= nu:
            # Rem 1: een point_in_time in het verleden vuurt onmiddellijk. Dit is een
            # geval voor de inhaalslag, niet voor de planner.
            _LOGGER.debug(
                "Eenmalige wekker %s ligt in het verleden (%s); niet gepland",
                wekker["id"],
                rauw,
            )
            return
        self._listeners[sleutel] = async_track_point_in_time(
            self.hass,
            self._maak_callback(registry_id, person_entity_id, wekker["id"]),
            moment,
        )

    def _maak_callback(
        self, registry_id: str, person_entity_id: str, alarm_id: str
    ) -> Callable[[dt.datetime], Any]:
        """De callback die op de wektijd draait.

        Sluit alleen de **ID's** in, niet de wekker zelf: die wordt op het moment van
        afgaan opnieuw uit de opslag gelezen. Zou de callback een kopie vasthouden,
        dan zou een wekker die inmiddels is gewijzigd met oude waarden afgaan.
        """

        async def _op_tijd(nu: dt.datetime) -> None:
            store = self.hass.data[DOMAIN].get(DATA_STORE)
            if store is None:
                return
            try:
                wekker = store.wekker(registry_id, alarm_id)
            except Exception:  # noqa: BLE001 - onleesbare opslag mag niet vuren
                _LOGGER.exception("Kon wekker %s niet lezen; niet afgegaan", alarm_id)
                return
            if wekker is None:
                # De wekker is verwijderd terwijl de listener nog liep. Kan alleen bij
                # een race; herplannen zegt listeners normaal op.
                _LOGGER.debug("Wekker %s bestaat niet meer; niet afgegaan", alarm_id)
                return
            if not wekker.get("enabled"):
                return

            # De dagfiltering, hier en niet in de planner (SPEC 13.1).
            dagen = wekker.get("days") or []
            if dagen and nu.isoweekday() not in dagen:
                _LOGGER.debug(
                    "Wekker %s: vandaag (%d) is geen aangevinkte dag %s",
                    alarm_id,
                    nu.isoweekday(),
                    dagen,
                )
                return

            # Het bedoelde moment is de wandkloktijd van vandaag, niet `nu`: `nu`
            # draagt de jitter van 50–500 ms (SPEC 13.1) en die hoort niet in
            # `last_fired`, want daar wordt op vergeleken.
            uur, minuut = parse_tijd(wekker["time"])
            moment = nu.replace(hour=uur, minute=minuut, second=0, microsecond=0)

            if wekker.get("skip_next"):
                # Dit ene moment overslaan, en skip_next daarna wissen (SPEC 13.4
                # stap 4 en SPEC 15.5).
                await self._async_sla_over(
                    registry_id, person_entity_id, wekker, moment,
                    meldingen.KIND_SKIPPED_BY_USER,
                )
                return

            await self._async_vuur(registry_id, person_entity_id, wekker, moment)

        return _op_tijd

    # --- afvuren, met de rem --------------------------------------------

    async def _async_vuur(
        self,
        registry_id: str,
        person_entity_id: str,
        wekker: dict[str, Any],
        moment: dt.datetime,
    ) -> bool:
        """Laat een wekker afgaan, maar alleen als dat mag. Geeft terug of het gebeurde.

        **Rem 2** (zie de moduledocstring). Twee weigeringen, en beide zijn nodig:

        - `last_fired` is al gelijk aan of later dan dit moment → al afgegaan.
          Dit is de bewaker uit SPEC 13.4 stap 3, en hij staat hier zodat ook een
          listener die ik niet heb voorzien er niet langs komt.
        - het moment ligt verder dan het respijtvenster in het verleden → te laat.
          Zonder deze weigering zou een `point_in_time` in het verleden een wekker
          van vanmorgen om 14:00 laten afgaan.
        """
        nu = dt_util.now()

        laatste = wekker.get("last_fired")
        if laatste is not None:
            eerder = dt.datetime.fromisoformat(laatste)
            # Vergelijking op het absolute moment, niet op de wandklok. Bij de
            # najaarsovergang komt 02:30 twee keer voorbij op twee verschillende
            # UTC-momenten; SPEC 13.1 schrijft voor dat hij dan twee keer afgaat, en
            # deze vergelijking staat dat toe.
            if eerder >= moment:
                _LOGGER.debug(
                    "Wekker %s is al afgegaan voor moment %s (last_fired %s); overgeslagen",
                    wekker["id"],
                    moment.isoformat(),
                    laatste,
                )
                return False

        te_laat = nu - moment
        if te_laat > dt.timedelta(minutes=RESPIJT_MINUTEN):
            _LOGGER.debug(
                "Wekker %s is %s te laat en valt buiten het respijtvenster van %d minuten",
                wekker["id"],
                te_laat,
                RESPIJT_MINUTEN,
            )
            return False

        await afvuren.async_laat_afgaan(
            self.hass, registry_id, person_entity_id, wekker, moment
        )
        return True

    async def _async_sla_over(
        self,
        registry_id: str,
        person_entity_id: str,
        wekker: dict[str, Any],
        moment: dt.datetime,
        kind: str,
    ) -> None:
        """Sla dit moment over, meld het, en wis `skip_next`.

        `last_fired` wordt **wel** op dit moment gezet. Anders zou de inhaalslag na
        een herstart hetzelfde overgeslagen moment opnieuw als "gemist" zien en er een
        tweede mededeling voor achterlaten.
        """
        store = self.hass.data[DOMAIN][DATA_STORE]
        await meldingen.async_meld(self.hass, store, registry_id, wekker, kind)
        await store.async_werk_velden_bij(
            registry_id,
            wekker["id"],
            {"skip_next": False, "last_fired": moment.isoformat()},
        )

    # --- de inhaalslag (SPEC 13.4) --------------------------------------

    async def _async_inhaalslag(
        self, registry_id: str, person_entity_id: str, wekker: dict[str, Any]
    ) -> None:
        """De zeven stappen uit SPEC 13.4, voor één wekker."""
        nu = dt_util.now()
        dagen = wekker.get("days") or []

        # Stap 1: het laatst verstreken passende moment.
        if dagen:
            moment = laatste_verstreken_moment(nu, wekker["time"], dagen)
        else:
            rauw = wekker.get("one_shot_at")
            moment = dt.datetime.fromisoformat(rauw) if rauw else None
            if moment is not None and moment > nu:
                moment = None  # ligt in de toekomst; de planner pakt hem op

        # Stap 2: niets langsgekomen, niets in te halen.
        if moment is None:
            return

        # Stap 3: al afgegaan?
        laatste = wekker.get("last_fired")
        if laatste is not None and dt.datetime.fromisoformat(laatste) >= moment:
            return

        # Stap 4: door de gebruiker overgeslagen.
        if wekker.get("skip_next"):
            await self._async_sla_over(
                registry_id, person_entity_id, wekker, moment,
                meldingen.KIND_SKIPPED_BY_USER,
            )
            return

        # Stap 5 en 6: binnen het respijtvenster alsnog afgaan, daarbuiten overslaan.
        if nu - moment <= dt.timedelta(minutes=RESPIJT_MINUTEN):
            _LOGGER.debug(
                "Wekker %s wordt ingehaald: moment %s ligt %s in het verleden",
                wekker["id"],
                moment.isoformat(),
                nu - moment,
            )
            await self._async_vuur(registry_id, person_entity_id, wekker, moment)
        else:
            await self._async_sla_over(
                registry_id, person_entity_id, wekker, moment,
                meldingen.KIND_SKIPPED_GRACE_WINDOW,
            )

    # --- tijdzone -------------------------------------------------------

    @callback
    def _op_config_wijziging(self, _event: Any) -> None:
        """Herplan bij een tijdzonewijziging (SPEC 13.2).

        **GEMETEN** in fase 0 (E1.4): alleen `SunListener` luistert op
        `EVENT_CORE_CONFIG_UPDATE` (`helpers/event.py:1672`); `_TrackUTCTimeChange`
        (regel 1750) doet dat **niet**. Een lopende listener blijft dus op het al
        berekende moment staan, en de integratie moet zelf herplannen.

        Zonder inhaalslag: een tijdzonewijziging is geen gemiste wekker.
        """
        _LOGGER.debug("Kernconfiguratie gewijzigd; planning wordt opnieuw opgebouwd")
        self.hass.async_create_task(self.async_herplan())


# --- toegang van buiten -------------------------------------------------


@callback
def planner_van(hass: HomeAssistant) -> Planner | None:
    """De planner van deze integratie, of `None` als er geen is."""
    return hass.data.get(DOMAIN, {}).get(DATA_PLANNER)


async def async_herplan(hass: HomeAssistant) -> None:
    """Herplan na een wijziging via een WebSocket-commando (SPEC 13.5).

    Als functie en niet als methode, zodat `websocket.py` niets over de planner hoeft
    te weten behalve dat hij bestaat. Gooit nooit: een mislukte herplanning mag een
    geslaagde opslagwijziging niet in een fout veranderen — de klant heeft dan zijn
    wekker wél opgeslagen.
    """
    planner = planner_van(hass)
    if planner is None:
        return
    try:
        await planner.async_herplan()
    except Exception:  # noqa: BLE001 - zie docstring
        _LOGGER.exception("Herplannen na een wijziging is mislukt")
