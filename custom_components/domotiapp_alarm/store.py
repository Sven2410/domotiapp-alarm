"""De opslaglaag (SPEC 14) met het foutgedrag uit SPEC 19.2.

## De constructie die deze laag bijzonder maakt

**Valideren is niet hetzelfde als parsen, en de laag bewaart het onbewerkte
materiaal naast het bewerkte** (SPEC 19.2 geval B).

Per persoon wordt de data gevalideerd. Slaagt dat, dan komt er een genormaliseerd
object in `_persons`. Faalt het, dan gaat de **onbewerkte waarde precies zoals hij
uit de JSON kwam** naar `_corrupt`, samen met de reden.

Bij het wegschrijven worden beide samengevoegd. De kapotte waarde gaat er
**letterlijk** weer in: niet genormaliseerd, niet gesorteerd, niet door een
validatieronde heen. Alleen dan kan een admin het `.storage`-bestand openen en
zien wat er stond.

Waarom niet gewoon "niets schrijven zolang er iets kapot is": er is **één Store
voor alle personen samen**. Een schrijfverbod op bestandsniveau zou het hele
huishouden blokkeren om één kapotte persoon, en dan drukt een klant op Opslaan en
gebeurt er niets, om een reden die alleen in een repair issue staat waar hij niet
bij kan (SPEC 19.2, na regel 5).

## Geval C is wél een schrijfverbod

Is `data.persons` geen object, dan is er **geen enkele sleutel** om per persoon te
markeren en dus ook geen manier om de inhoud bij een schrijfronde terug te zetten.
Elke schrijfactie zou de hele inhoud weggooien. Dan geldt SPEC 19.1 — niet
overschrijven — en wordt er helemaal niet geschreven.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.util import uuid as uuid_util

from . import abonnement
from .const import (
    STORAGE_KEY,
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
)
from .validatie import ValidatieFout, valideer_persoon

_LOGGER = logging.getLogger(__name__)

PERSON_DOMAIN = "person"


class OpslagOnbruikbaar(Exception):
    """Geval C: `data.persons` is geen object (SPEC 19.2 geval C).

    De hele opslag geldt als onbruikbaar. Er wordt niet geschreven en elk
    commando dat de opslag raakt geeft `home_assistant_error`.
    """


class PersoonOnleesbaar(Exception):
    """Geval B: de data van deze ene persoon valideert niet (SPEC 19.2 geval B)."""

    def __init__(self, registry_id: str, reden: str) -> None:
        self.registry_id = registry_id
        self.reden = reden
        super().__init__(f"opslag van {registry_id} is onleesbaar: {reden}")


class AlarmStore:
    """Eén Store voor alle personen samen (SPEC 14.1)."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = _AlarmStoreFile(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
            minor_version=STORAGE_MINOR_VERSION,
            atomic_writes=True,
        )
        # Gevalideerd, per registry-entry-ID van de person.
        self._persons: dict[str, dict[str, Any]] = {}
        # Onbewerkt plus reden. Geen sleutel komt in beide dicts voor; dat is de
        # enige invariant die de samenvoeging bij het schrijven nodig heeft.
        self._corrupt: dict[str, tuple[Any, str]] = {}
        # Geval C: dan is er niets bruikbaar en mag er niet geschreven worden.
        self._onbruikbaar: str | None = None

    # --- laden ----------------------------------------------------------

    async def async_load(self) -> None:
        """Lees de opslag. Gooit nooit; markeert wat er mis is."""
        rauw = await self._store.async_load()
        if rauw is None:
            # Nog nooit opgeslagen, of geval A (HA heeft het bestand al
            # weggezet als .corrupt en een CRITICAL repair issue aangemaakt).
            _LOGGER.debug("Geen opslag gevonden; begin met een lege lijst")
            return

        personen = rauw.get("persons")
        if not isinstance(personen, dict):
            self._onbruikbaar = (
                f"data.persons moet een object zijn, maar is {type(personen).__name__}"
            )
            _LOGGER.error(
                "De opslag %s is onbruikbaar: %s. Er wordt niets geschreven en geen "
                "enkele wekker gepland. Zet het bestand terug uit een backup of "
                "verwijder het en herstart Home Assistant.",
                STORAGE_KEY,
                self._onbruikbaar,
            )
            return

        for registry_id, data in personen.items():
            if not isinstance(registry_id, str) or not registry_id:
                # Een sleutel die geen ID is kunnen we niet aan een persoon
                # koppelen. Bewaren onder zijn eigen naam zou een tweede soort
                # sleutel introduceren; hij gaat naar _corrupt zodat hij bij het
                # schrijven letterlijk terugkomt.
                self._corrupt[str(registry_id)] = (data, "sleutel is geen registry-entry-ID")
                continue
            try:
                self._persons[registry_id] = valideer_persoon(data, veld=registry_id)
            except ValidatieFout as fout:
                self._corrupt[registry_id] = (data, fout.bericht)
                _LOGGER.error(
                    "De opgeslagen wekkers van %s zijn onleesbaar (%s: %s). De data blijft "
                    "ongewijzigd bewaard; er wordt voor deze persoon niets gepland en "
                    "opslaan wordt geweigerd.",
                    registry_id,
                    fout.veld,
                    fout.bericht,
                )

        _LOGGER.debug(
            "Opslag gelezen: %d gezonde personen, %d onleesbaar",
            len(self._persons),
            len(self._corrupt),
        )

    # --- toestand -------------------------------------------------------

    @property
    def onbruikbaar(self) -> str | None:
        """De reden dat de hele opslag onbruikbaar is, of `None` (geval C)."""
        return self._onbruikbaar

    def is_corrupt(self, registry_id: str) -> bool:
        return registry_id in self._corrupt

    def corrupte_personen(self) -> dict[str, str]:
        """Registry-ID naar reden, voor de reparatiemeldingen."""
        return {rid: reden for rid, (_rauw, reden) in self._corrupt.items()}

    def heeft_opslag(self, registry_id: str) -> bool:
        """Heeft deze persoon ooit opgeslagen (SPEC 15.1 `stored`)."""
        return registry_id in self._persons or registry_id in self._corrupt

    # --- lezen ----------------------------------------------------------

    def _eis_bruikbaar(self, registry_id: str) -> None:
        if self._onbruikbaar is not None:
            raise OpslagOnbruikbaar(self._onbruikbaar)
        if registry_id in self._corrupt:
            raise PersoonOnleesbaar(registry_id, self._corrupt[registry_id][1])

    def wekkers(self, registry_id: str) -> list[dict[str, Any]]:
        """De wekkers van één persoon.

        Gooit `OpslagOnbruikbaar` of `PersoonOnleesbaar`; die worden in
        `websocket.py` naar `home_assistant_error` omgezet.
        """
        self._eis_bruikbaar(registry_id)
        persoon = self._persons.get(registry_id)
        if persoon is None:
            return []
        # Kopie: de aanroeper mag de opslag niet van binnenuit wijzigen.
        return [dict(wekker) for wekker in persoon["alarms"]]

    def wekker(self, registry_id: str, alarm_id: str) -> dict[str, Any] | None:
        for wekker in self.wekkers(registry_id):
            if wekker["id"] == alarm_id:
                return wekker
        return None

    def alle_wekkers(self) -> dict[str, list[dict[str, Any]]]:
        """Alle gezonde personen met hun wekkers.

        Fase 3b heeft dit nodig om te plannen. Kapotte personen komen er
        **niet** in voor: voor hen wordt niets gepland (SPEC 19.2 geval B,
        regel 6).
        """
        if self._onbruikbaar is not None:
            return {}
        return {rid: [dict(w) for w in data["alarms"]] for rid, data in self._persons.items()}

    # --- schrijven ------------------------------------------------------

    def _as_stored(self) -> dict[str, Any]:
        """Wat er naar schijf gaat: gevalideerd plus onbewerkt (SPEC 19.2)."""
        personen: dict[str, Any] = {
            rid: {"alarms": data["alarms"]} for rid, data in self._persons.items()
        }
        for rid, (rauw, _reden) in self._corrupt.items():
            # Letterlijk terug, niet opnieuw opgebouwd. Dit is de regel waar de
            # hele constructie om bestaat.
            personen[rid] = rauw
        return {"persons": personen}

    async def _async_schrijf(self, gewijzigd_voor: str | None = None) -> None:
        """Schrijf weg, en meld de wijziging aan de abonnees (SPEC 15.9).

        **Dit is het enige knooppunt waar élke opslagwijziging langskomt**, en
        daarom staat het bericht hier en niet in `websocket.py`. Behalve de vijf
        muterende commando's schrijven ook de planner (`last_fired`, de
        inhaalslag) en `meldingen.py` (`last_message`) hierlangs, en dat zijn
        precies de wijzigingen die de klant niet zelf heeft aangevraagd — dus de
        wijzigingen waarvan hij het meest heeft dat zijn kaart ze uit zichzelf
        laat zien.

        Het bericht gaat er **ná** het wegschrijven uit. Faalt het schrijven, dan
        gooit `async_save` en is er niets gemeld — een kaart die dan `alarms/get`
        zou doen, zou een toestand ophalen die niet op schijf staat.
        """
        if self._onbruikbaar is not None:
            # Geval C: niet schrijven. Zou de hele inhoud weggooien.
            raise OpslagOnbruikbaar(self._onbruikbaar)
        await self._store.async_save(self._as_stored())
        if gewijzigd_voor is not None:
            abonnement.stuur_gewijzigd(
                self.hass, person_entity_id_van_registry_id(self.hass, gewijzigd_voor)
            )

    async def async_zet_wekker(
        self, registry_id: str, wekker: dict[str, Any]
    ) -> dict[str, Any]:
        """Voeg toe of werk bij. `wekker` moet al gevalideerd zijn.

        Geeft de opgeslagen wekker terug.
        """
        self._eis_bruikbaar(registry_id)
        persoon = self._persons.setdefault(registry_id, {"alarms": []})
        wekkers: list[dict[str, Any]] = persoon["alarms"]
        for index, bestaand in enumerate(wekkers):
            if bestaand["id"] == wekker["id"]:
                wekkers[index] = wekker
                break
        else:
            wekkers.append(wekker)
        await self._async_schrijf(gewijzigd_voor=registry_id)
        return wekker

    async def async_verwijder_wekker(self, registry_id: str, alarm_id: str) -> bool:
        """Verwijder een wekker. Geeft terug of er iets verwijderd is."""
        self._eis_bruikbaar(registry_id)
        persoon = self._persons.get(registry_id)
        if persoon is None:
            return False
        voor = len(persoon["alarms"])
        persoon["alarms"] = [w for w in persoon["alarms"] if w["id"] != alarm_id]
        if len(persoon["alarms"]) == voor:
            return False
        await self._async_schrijf(gewijzigd_voor=registry_id)
        return True

    async def async_werk_velden_bij(
        self, registry_id: str, alarm_id: str, velden: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Werk losse velden van één wekker bij en schrijf weg.

        Gebruikt door `set_enabled` en `skip_next`, en straks door de planner voor
        `last_fired` en `last_message`. De samengestelde wekker wordt opnieuw
        gevalideerd, zodat er langs deze route niets ongeldigs in de opslag komt.
        """
        self._eis_bruikbaar(registry_id)
        persoon = self._persons.get(registry_id)
        if persoon is None:
            return None
        for index, bestaand in enumerate(persoon["alarms"]):
            if bestaand["id"] != alarm_id:
                continue
            samengevoegd = {**bestaand, **velden}
            persoon["alarms"][index] = valideer_persoon({"alarms": [samengevoegd]})["alarms"][0]
            await self._async_schrijf(gewijzigd_voor=registry_id)
            return persoon["alarms"][index]
        return None

    def nieuw_alarm_id(self) -> str:
        """Een uniek ID binnen de persoon (SPEC 14.2)."""
        return uuid_util.random_uuid_hex()


class _AlarmStoreFile(Store[dict[str, Any]]):
    """`Store` met migratie (SPEC 14.6)."""

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Migreer oude data.

        Er bestaat nog geen oudere versie, dus er valt niets te migreren. Een
        onbekende versie is een fout en geen aanleiding om te gokken: liever
        falen dan een formaat half interpreteren (SPEC 14.6).

        Een hógere `version` dan de code aankan wordt al door HA zelf afgevangen
        met `UnsupportedStorageVersionError` (`helpers/storage.py:437-440`); deze
        functie ziet alleen oudere versies.
        """
        raise NotImplementedError(
            f"Geen migratie beschikbaar van versie {old_major_version}.{old_minor_version} "
            f"naar {STORAGE_VERSION}.{STORAGE_MINOR_VERSION}"
        )


# --- de vertaling entity-ID naar registry-entry-ID (SPEC 6.2) -----------


class PersonNietGevonden(Exception):
    """De person-entiteit bestaat niet, of heeft geen entity registry entry."""


def registry_id_van_person(hass: HomeAssistant, entity_id: str) -> str:
    """Het registry-entry-ID van een `person.`-entiteit (SPEC 6.2).

    Dit is de opslagsleutel. Het is **niet** het entity-ID: dat kan bij hernoemen
    veranderen, het registry-entry-ID niet (`helpers/entity_registry.py:234-235`,
    een `random_uuid_hex`).

    De vertaling gebeurt hier, server-side. De kaart kent alleen entity-ID's.

    Gooit `PersonNietGevonden` als de entiteit niet bestaat, niet in het
    `person`-domein zit, of geen registry-entry heeft. **Nooit terugvallen op het
    entity-ID als sleutel** (SPEC 18.2): dan zouden de wekkers van iemand stil
    verdwijnen zodra het registry-entry er wel is.
    """
    if not isinstance(entity_id, str) or "." not in entity_id:
        raise PersonNietGevonden(f"{entity_id!r} is geen entity-ID")
    if entity_id.split(".", 1)[0] != PERSON_DOMAIN:
        raise PersonNietGevonden(f"{entity_id} zit niet in het person-domein")

    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is None:
        raise PersonNietGevonden(f"{entity_id} heeft geen entity registry entry")
    return entry.id


def person_entity_id_van_registry_id(hass: HomeAssistant, registry_id: str) -> str | None:
    """De omgekeerde vertaling, voor het `changed`-bericht (SPEC 15.9).

    De opslag is per registry-entry-ID; de kaart praat in entity-ID's. Het bericht
    moet dus terugvertaald worden.

    `None` betekent: er is geen `person.`-entiteit meer met dit registry-entry.
    Dat is een bestaande toestand en geen fout — de wekkers van een verwijderde
    persoon blijven in de opslag staan (SPEC 18.1).

    Er is geen index op registry-entry-ID, dus dit is een lus. Dat is hier
    aanvaardbaar: het aantal `person.`-entiteiten in een huishouden is klein en
    de lus draait alleen bij een schrijfronde, niet bij het lezen.
    """
    for entry in er.async_get(hass).entities.values():
        if entry.id == registry_id and entry.domain == PERSON_DOMAIN:
            return entry.entity_id
    return None
