"""Het abonnement en het `changed`-bericht (SPEC 15.9).

**NIEUW GEDRAG in fase 4b.** Het abonnement bestond al — het heette
`ringing/subscribe` en meldde alleen afgaan — maar het `changed`-bericht is
nieuw, en dat maakt de tests hier niet-triviaal: ze falen op de code van fase 4a
omdat er dan **geen** bericht komt, niet omdat het commando ontbreekt.

Waar deze tests op letten is niet dát er een bericht komt maar **waar het
vandaan komt**. Fase 4a's bevinding was dat de kaart wijzigingen van buiten niet
zag; de val bij het repareren is dat je het bericht in de vijf muterende
commando's zet en dan precies de wijzigingen mist die niemand heeft aangevraagd —
de planner die `last_fired` schrijft, en een melding die op de kaart hoort te
verschijnen. Daarom zit het bericht in de **opslaglaag**, en daarom staat hier
een test per route.
"""

from __future__ import annotations

from typing import Any

import pytest

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import HomeAssistant

from custom_components.domotiapp_alarm import abonnement
from custom_components.domotiapp_alarm.const import DATA_STORE, DOMAIN

from .conftest import (
    PERSON_ENTITY_ID,
    geldige_wekker,
    maak_speaker,
    registreer_person,
    zet_integratie_op,
)

GOEDE_FEATURES = int(
    MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.VOLUME_SET
)


@pytest.fixture
async def omgeving(hass: HomeAssistant):
    registry_id = registreer_person(hass)
    maak_speaker(hass, features=GOEDE_FEATURES)
    await zet_integratie_op(hass)
    return registry_id


async def _stuur(client, payload: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(payload)
    return await client.receive_json()


def _changed(gebeurtenissen: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [g for g in gebeurtenissen if g["event"] == abonnement.EVENT_CHANGED]


# --- het bericht zelf ---------------------------------------------------


async def test_changed_draagt_alleen_de_persoon(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Het bericht is een sein, geen toestand (SPEC 15.9).

    NIEUW GEDRAG. Dat er alléén `person` in staat is vastgelegd gedrag en geen
    zuinigheid: een abonnee zonder `person`-filter zou anders bij elke wijziging
    de wekkerlijst van élke persoon in huis krijgen, en `alarms/get` zou niet
    langer de enige plek zijn die de toestand samenstelt.
    """
    gebeurtenissen: list[dict[str, Any]] = []
    abonnement.register_van(hass).abonneer(gebeurtenissen.append)

    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    assert antwoord["success"], antwoord

    berichten = _changed(gebeurtenissen)
    assert berichten, "een save hoort een changed-bericht op te leveren"
    assert berichten[0] == {"event": "changed", "person": PERSON_ENTITY_ID}


@pytest.mark.parametrize("commando", ["save", "set_enabled", "skip_next", "clear_message", "delete"])
async def test_elk_muterend_commando_meldt_de_wijziging(
    hass: HomeAssistant, hass_ws_client, omgeving, commando: str
) -> None:
    """Alle vijf de muterende commando's sturen `changed` (SPEC 15.9).

    NIEUW GEDRAG. Dit is de test die een vergeten commando vangt — en die
    vergeetachtigheid is de reden dat het bericht in de opslaglaag zit en niet
    per commando wordt verstuurd.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    alarm_id = antwoord["result"]["alarms"][0]["id"]

    # Pas ná de voorbereiding abonneren, zodat alleen het commando onder toets telt.
    gebeurtenissen: list[dict[str, Any]] = []
    abonnement.register_van(hass).abonneer(gebeurtenissen.append)

    payloads = {
        "save": {
            "type": f"{DOMAIN}/alarms/save",
            "person": PERSON_ENTITY_ID,
            "alarm": geldige_wekker(id=alarm_id, name="Anders"),
        },
        "set_enabled": {
            "type": f"{DOMAIN}/alarms/set_enabled",
            "person": PERSON_ENTITY_ID,
            "alarm_id": alarm_id,
            "enabled": False,
        },
        "skip_next": {
            "type": f"{DOMAIN}/alarms/skip_next",
            "person": PERSON_ENTITY_ID,
            "alarm_id": alarm_id,
            "skip": True,
        },
        "clear_message": {
            "type": f"{DOMAIN}/alarms/clear_message",
            "person": PERSON_ENTITY_ID,
            "alarm_id": alarm_id,
        },
        "delete": {
            "type": f"{DOMAIN}/alarms/delete",
            "person": PERSON_ENTITY_ID,
            "alarm_id": alarm_id,
        },
    }
    antwoord = await _stuur(client, payloads[commando])
    assert antwoord["success"], antwoord
    assert _changed(gebeurtenissen), f"{commando} heeft geen changed-bericht gestuurd"


async def test_lezen_meldt_niets(hass: HomeAssistant, hass_ws_client, omgeving) -> None:
    """De positieve controle: een commando dat niets wijzigt, meldt niets.

    NIEUW GEDRAG. Zonder deze test slaagt de vorige ook op een implementatie die
    bij **elke** aanroep een bericht stuurt — en dan haalt elke open kaart bij
    elke `alarms/get` van elke andere kaart opnieuw de toestand op.
    """
    client = await hass_ws_client(hass)
    await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )

    gebeurtenissen: list[dict[str, Any]] = []
    abonnement.register_van(hass).abonneer(gebeurtenissen.append)

    for payload in (
        {"type": f"{DOMAIN}/alarms/get", "person": PERSON_ENTITY_ID},
        {"type": f"{DOMAIN}/entities/list"},
    ):
        antwoord = await _stuur(client, payload)
        assert antwoord["success"], antwoord
    assert _changed(gebeurtenissen) == []


async def test_een_schrijfronde_buiten_de_commando_om_meldt_ook(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """De planner en de meldingen sturen het bericht óók (SPEC 15.9).

    NIEUW GEDRAG, en dit is de reden dat het bericht in de opslaglaag zit. Zou het
    in `websocket.py` staan, dan mist de kaart precies de wijzigingen die de klant
    **niet** zelf heeft aangevraagd: `last_fired` na een wekker, en `last_message`
    als er iets misging. Dat zijn de twee dingen waarvoor je 's ochtends op de
    kaart kijkt.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    alarm_id = antwoord["result"]["alarms"][0]["id"]

    gebeurtenissen: list[dict[str, Any]] = []
    abonnement.register_van(hass).abonneer(gebeurtenissen.append)

    # Precies wat de planner doet, langs dezelfde route.
    store = hass.data[DOMAIN][DATA_STORE]
    await store.async_werk_velden_bij(
        omgeving, alarm_id, {"last_fired": "2026-08-10T06:45:00+02:00"}
    )
    assert _changed(gebeurtenissen), "een schrijfronde van de planner hoort te melden"


async def test_geen_bericht_voor_een_verwijderde_persoon(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Zonder `person.`-entiteit gaat er geen bericht uit (SPEC 15.9, 18.1).

    NIEUW GEDRAG. De wekkers van een verwijderde persoon blijven in de opslag
    staan, maar er is dan geen entity-ID om in het bericht te zetten en geen kaart
    die zich erop kan abonneren. Een bericht zonder `person` zou de filter van
    elke abonnee moeten passeren om daarna nergens over te gaan.

    Er zit een positieve controle in: dezelfde schrijfactie op een **bestaande**
    persoon levert wél een bericht op.
    """
    from homeassistant.helpers import entity_registry as er

    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    alarm_id = antwoord["result"]["alarms"][0]["id"]
    store = hass.data[DOMAIN][DATA_STORE]

    gebeurtenissen: list[dict[str, Any]] = []
    abonnement.register_van(hass).abonneer(gebeurtenissen.append)

    # Positieve controle: mét persoon komt er een bericht.
    await store.async_werk_velden_bij(omgeving, alarm_id, {"skip_next": True})
    assert len(_changed(gebeurtenissen)) == 1

    # De persoon verdwijnt; zijn wekkers blijven staan (SPEC 18.1).
    er.async_get(hass).async_remove(PERSON_ENTITY_ID)
    await store.async_werk_velden_bij(omgeving, alarm_id, {"skip_next": False})
    assert len(_changed(gebeurtenissen)) == 1, "geen tweede bericht zonder person-entiteit"


async def test_abonnee_krijgt_changed_over_de_websocket(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Het bericht komt echt bij een geabonneerde client aan (SPEC 15.9).

    NIEUW GEDRAG. De tests hierboven kijken in het register; deze kijkt aan de
    andere kant van de WebSocket, want daar zit de kaart. Twee clients: de een
    wijzigt, de ander is geabonneerd — precies het geval uit fase 4a dat niet
    werkte (telefoon wijzigt, wandtablet blijft achter).
    """
    kijker = await hass_ws_client(hass)
    antwoord = await _stuur(
        kijker, {"type": f"{DOMAIN}/updates/subscribe", "person": PERSON_ENTITY_ID}
    )
    assert antwoord["success"], antwoord
    abonnement_id = antwoord["id"]

    schrijver = await hass_ws_client(hass)
    await _stuur(
        schrijver,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )

    bericht = await kijker.receive_json()
    assert bericht["id"] == abonnement_id
    assert bericht["type"] == "event"
    assert bericht["event"] == {"event": "changed", "person": PERSON_ENTITY_ID}
