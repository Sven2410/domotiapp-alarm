"""Het abonnement: alles wat een open kaart moet weten om actueel te blijven.

Twee dingen wonen hier, en ze horen bij elkaar omdat ze dezelfde abonnees
bedienen:

1. **Het register van afgaande wekkers** — welke wekkers nu afgaan, met per
   wekker de context die `afvuren.py` nodig heeft om te stoppen.
2. **De doorgeefluik naar de abonnees** — vier soorten gebeurtenissen
   (SPEC 15.9).

## Waarom dit bestand niet meer `ringing.py` heet

Tot fase 4a ging het abonnement alleen over afgaan. Fase 4a mat dat dat niet
genoeg is: een wekker die op de telefoon wordt gewijzigd, verscheen op het
wandtablet pas na een herlaadbeurt, want er was **geen abonnement op
opslagwijzigingen**. Met de editor van fase 4b wordt dat zichtbaar gedrag.

De eigenaar heeft gekozen voor **één breder abonnement** in plaats van een
tweede: één commando, één codepad in de kaart. Daarmee gaat dit bestand niet
langer over "ringing" maar over "waar de kaart op geabonneerd is", en de naam
volgt die betekenis. Zie SPEC 15.9.

## Waarom `changed` een SEIN is en geen toestand

Het `changed`-bericht draagt alleen `person`. De ontvanger haalt daarna zelf
`alarms/get` op. Dat is met opzet:

- een abonnee **zonder** `person`-filter zou anders de wekkerlijst van élke
  persoon in huis toegestuurd krijgen bij elke wijziging, en dat is precies de
  scheiding die SPEC 6 aanbrengt (geen beveiliging, maar wel een weergavekeuze
  die je niet gratis moet weggooien);
- `alarms/get` blijft de **enige** plek die de toestand samenstelt. Twee plekken
  die hetzelfde antwoord opbouwen, lopen uiteen — dezelfde reden dat de kaart
  `next_fire` niet zelf berekent (SPEC 3.3).

De prijs is één extra aanroep per wijziging, en die is bewust betaald.

## Waar `changed` vandaan komt

**Uit de opslaglaag, niet uit de commando's.** `store.py` stuurt het na elke
geslaagde schrijfronde. Dat is het enige echte knooppunt: behalve de vijf
muterende commando's schrijven ook de planner (`last_fired`, de inhaalslag) en
`meldingen.py` (`last_message`) in de opslag, en die zijn geen commando. Zou het
bericht in `websocket.py` staan, dan mist de kaart precies de wijzigingen die
niemand heeft aangevraagd — en dat zijn juist de interessante.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant, callback

from .const import DATA_RINGING, DOMAIN

_LOGGER = logging.getLogger(__name__)

EVENT_STARTED = "started"
EVENT_STOPPED = "stopped"
EVENT_FAILED = "failed"
# Nieuw in fase 4b: de wekkers van deze persoon zijn gewijzigd (SPEC 15.9).
EVENT_CHANGED = "changed"

# Redenen bij `stopped` (SPEC 15.9).
REASON_USER = "user"
REASON_TIMEOUT = "timeout"
REASON_DELETED = "deleted"


@dataclass(slots=True)
class Register:
    """Welke wekkers nu afgaan, en wie er bericht van wil."""

    # (registry_id, alarm_id) -> context van `afvuren.py`: de stoptimer, de
    # oploop en het oorspronkelijke volume.
    actief: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    _abonnees: list[Callable[[dict[str, Any]], None]] = field(default_factory=list)

    def abonneer(self, terugroep: Callable[[dict[str, Any]], None]) -> Callable[[], None]:
        """Meld je aan. Geeft de functie terug waarmee je je afmeldt."""
        self._abonnees.append(terugroep)

        def afmelden() -> None:
            if terugroep in self._abonnees:
                self._abonnees.remove(terugroep)

        return afmelden

    def stuur(self, bericht: dict[str, Any]) -> None:
        """Stuur een gebeurtenis naar alle abonnees. Gooit nooit.

        Een abonnee die stukloopt mag de andere abonnees niet meesleuren, en al
        helemaal niet de wekker die op dat moment afgaat.
        """
        for terugroep in list(self._abonnees):
            try:
                terugroep(bericht)
            except Exception:  # noqa: BLE001 - een abonnee mag de wekker niet slopen
                _LOGGER.exception("Een abonnee liep stuk op %s", bericht.get("event"))

    def afgaand_voor(self, registry_id: str) -> list[str]:
        """De alarm-ID's van deze persoon die nu afgaan (SPEC 15.1 `ringing`)."""
        return [alarm_id for (rid, alarm_id) in self.actief if rid == registry_id]

    def is_afgaand(self, registry_id: str, alarm_id: str) -> bool:
        return (registry_id, alarm_id) in self.actief


@callback
def register_van(hass: HomeAssistant) -> Register:
    """Het register van deze integratie, aangemaakt bij het eerste gebruik."""
    data = hass.data.setdefault(DOMAIN, {})
    register = data.get(DATA_RINGING)
    if register is None:
        register = Register()
        data[DATA_RINGING] = register
    return register


@callback
def stuur_gewijzigd(hass: HomeAssistant, person_entity_id: str | None) -> None:
    """Meld dat de wekkers van deze persoon zijn gewijzigd (SPEC 15.9).

    `person_entity_id` is `None` wanneer het registry-entry-ID niet meer aan een
    bestaande `person.`-entiteit te koppelen is — de persoon is verwijderd terwijl
    zijn wekkers in de opslag blijven staan (SPEC 18.1). Er gaat dan **geen**
    bericht uit: er is geen kaart die zich op die persoon kan abonneren, en een
    bericht zonder `person` zou de filter van elke abonnee moeten passeren om
    daarna nergens over te gaan.
    """
    if not person_entity_id:
        _LOGGER.debug("Wijziging zonder bruikbare person-entiteit; geen bericht verstuurd")
        return
    register_van(hass).stuur({"event": EVENT_CHANGED, "person": person_entity_id})
