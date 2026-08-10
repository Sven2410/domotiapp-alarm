"""Wat er gebeurt als een wekker afgaat.

## De naad tussen fase 3b en 3c

De planner (`planner.py`) bepaalt **wanneer**; deze module bepaalt **wat**. Dat is
met opzet gescheiden: de planner is af, en fase 3c hoeft hem niet aan te raken.

**In fase 3b doet deze module de boekhouding en niets meer:**

1. `last_fired` bijwerken — de enige bewaker tegen dubbel vuren (SPEC 13.4 stap 3);
2. de wekker in het ringing-register zetten (SPEC 15.1 `ringing`);
3. het `started`-event naar de abonnees sturen (SPEC 15.9);
4. een oude foutmelding opruimen: gaat de wekker nu gewoon af, dan hoort de melding
   van gisteren niet te blijven staan.

**Wat fase 3c hier invult**, in `async_laat_afgaan`, tussen stap 1 en stap 2 —
de volgorde uit SPEC 9.1:

- de noodrem vooraf: `available` op de speaker en de URI-controle (SPEC 11.1, 11.2);
- volume op 0, wake-up light aan, geluid starten via `music_assistant.play_media`;
- de volume-oploop van 20 stappen (SPEC 9.3);
- de tweede `available`-controle een paar seconden later (SPEC 11.3);
- de stoptimer van 30 minuten (SPEC 9.4).

En in `async_stop_afgaan`: geluid stoppen, oploop afbreken, volume terugzetten
(SPEC 9.5).

**De afspraak die dat mogelijk maakt:** `async_laat_afgaan` krijgt alles wat het
nodig heeft als argument en geeft niets terug wat de planner gebruikt. De planner
roept hem aan en is klaar; of het geluid het haalt, is de zorg van deze module.
Faalt er iets, dan legt deze module de melding vast (SPEC 11.7) — de planner hoort
daar niets van, want een mislukte wekker mag de plánning niet stukmaken.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from . import meldingen, ringing
from .const import DATA_STORE, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_laat_afgaan(
    hass: HomeAssistant,
    registry_id: str,
    person_entity_id: str,
    wekker: dict[str, Any],
    moment: dt.datetime,
) -> None:
    """Laat één wekker afgaan.

    :param moment: het **bedoelde** moment, niet "nu". Bij een inhaalslag liggen die
        tot 30 minuten uit elkaar, en `last_fired` moet het bedoelde moment vasthouden
        — anders schuift de vergelijking uit SPEC 13.4 stap 3 elke herstart mee op en
        kan dezelfde wekker alsnog twee keer afgaan.

    Gooit nooit. Een wekker die stukloopt mag de planner niet meeslepen.
    """
    store = hass.data[DOMAIN][DATA_STORE]

    # 1. last_fired eerst, en pas daarna geluid maken. Die volgorde is niet
    #    willekeurig: crasht of herstart HA tussen deze twee stappen, dan is de
    #    ergste uitkomst een wekker die niet klonk. Andersom zou de ergste uitkomst
    #    een wekker zijn die elke herstart opnieuw afgaat.
    try:
        await store.async_werk_velden_bij(
            registry_id, wekker["id"], {"last_fired": moment.isoformat()}
        )
    except Exception:  # noqa: BLE001 - zie docstring
        _LOGGER.exception(
            "Kon last_fired niet bijwerken voor wekker %s; de wekker gaat wél af",
            wekker["id"],
        )

    # --- FASE 3C VULT HIER: noodrem, geluid, volume-oploop, wake-up light ---

    # 2. In het register, zodat `alarms/get` hem meldt en `alarms/stop` hem kan
    #    stoppen. De context is vrij voor 3c: stoptimer, oorspronkelijk volume.
    register = ringing.register_van(hass)
    register.actief[(registry_id, wekker["id"])] = {
        "person": person_entity_id,
        "moment": moment.isoformat(),
    }

    # 3. Het started-event (SPEC 15.9), zodat een open kaart een stopknop wordt.
    register.stuur(
        {
            "event": ringing.EVENT_STARTED,
            "person": person_entity_id,
            "alarm_id": wekker["id"],
            "name": wekker.get("name"),
            "time": wekker.get("time"),
        }
    )

    # 4. Een foutmelding van een vorige keer hoort niet te blijven staan nu het wél
    #    lukt. De melding op de kaart wordt gewist door de kaart zelf ("Begrepen");
    #    de persistent_notification ruimen wij op.
    meldingen.async_wis_notificatie(hass, wekker["id"])

    _LOGGER.debug(
        "Wekker %s (%s) afgegaan voor moment %s",
        wekker["id"],
        wekker.get("name"),
        moment.isoformat(),
    )


async def async_stop_afgaan(
    hass: HomeAssistant,
    registry_id: str,
    person_entity_id: str,
    alarm_id: str,
    reason: str,
) -> bool:
    """Stop een lopende wekker. Geeft terug of er iets liep.

    **Idempotent** (SPEC 15.8): stoppen wat niet loopt is geen fout. Een wandtablet
    en een telefoon kunnen tegelijk drukken.

    Fase 3c vult hier het stoppen van geluid en oploop en het terugzetten van het
    volume in (SPEC 9.5).
    """
    register = ringing.register_van(hass)
    if not register.is_afgaand(registry_id, alarm_id):
        return False

    register.actief.pop((registry_id, alarm_id), None)

    # --- FASE 3C VULT HIER: geluid stoppen, oploop afbreken, volume terugzetten ---

    register.stuur(
        {
            "event": ringing.EVENT_STOPPED,
            "person": person_entity_id,
            "alarm_id": alarm_id,
            "reason": reason,
        }
    )
    _LOGGER.debug("Wekker %s gestopt (%s)", alarm_id, reason)
    return True
