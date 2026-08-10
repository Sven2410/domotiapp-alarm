"""Welke wekkers nu afgaan, en wie daarvan op de hoogte wil (SPEC 15.9).

De kaart wordt een stopknop zodra een wekker afgaat (SPEC 4). Ze weet dat via een
**abonnement**, niet door te pollen — en niet via een entiteit. Dat is vastgelegd
in SPEC 15.9: een `binary_sensor` per persoon zou de entiteitenkiezer van de klant
vullen met dingen die hij niet nodig heeft, en dit product levert bewust geen
entiteiten (`integration_type: service`).

**Wat deze module in fase 3a wél is:** het register plus de doorgeefluik. Er is nog
niets dat een wekker laat afgaan — dat is fase 3b — dus in deze fase blijft het
register leeg en worden er geen gebeurtenissen verstuurd. Het register bestaat nu
al omdat `alarms/get` het veld `ringing` moet kunnen vullen en `alarms/stop` iets
moet kunnen stoppen; fase 3b vult het.
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

# Redenen bij `stopped` (SPEC 15.9).
REASON_USER = "user"
REASON_TIMEOUT = "timeout"
REASON_DELETED = "deleted"


@dataclass(slots=True)
class Register:
    """Welke wekkers nu afgaan, en wie er bericht van wil."""

    # (registry_id, alarm_id) -> vrije context die fase 3b mag vullen, zoals de
    # stoptimer en het oorspronkelijke volume.
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
                _LOGGER.exception("Een abonnee op ringing-gebeurtenissen liep stuk")

    def afgaand_voor(self, registry_id: str) -> list[str]:
        """De alarm-ID's van deze persoon die nu afgaan (SPEC 15.1 `ringing`)."""
        return [
            alarm_id for (rid, alarm_id) in self.actief if rid == registry_id
        ]

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
