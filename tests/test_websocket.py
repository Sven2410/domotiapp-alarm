"""De negen WebSocket-commando's (SPEC 15), via een echte WebSocket-verbinding.

Alles hier is **NIEUW GEDRAG**: vóór deze fase bestond er geen enkel commando, dus
elke test faalt op de code van ervoor met `unknown_command`. Dat is een triviale
mislukking, en daarom is elke test zo opgezet dat hij een **eigenschap uit SPEC**
vastlegt die ook bij een latere wijziging kan sneuvelen — niet alleen dat het
commando bestaat.

De verbinding is de echte: `hass_ws_client` praat over de WebSocket-API heen, dus
de schema's, de foutcodes en de rechten zijn die van HA zelf en niet die van een
directe functieaanroep.
"""

from __future__ import annotations

from typing import Any

import pytest

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import HomeAssistant

from custom_components.domotiapp_alarm.const import DOMAIN

from .conftest import (
    PERSON_ENTITY_ID,
    geldige_wekker,
    maak_lamp,
    maak_speaker,
    registreer_person,
    zet_integratie_op,
)

GOEDE_FEATURES = int(
    MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.VOLUME_SET
)


@pytest.fixture
async def omgeving(hass: HomeAssistant):
    """Integratie op, één person, één geschikte speaker, één gelabelde lamp."""
    registry_id = registreer_person(hass)
    maak_speaker(hass, features=GOEDE_FEATURES)
    await zet_integratie_op(hass)
    return registry_id


async def _stuur(client, payload: dict[str, Any]) -> dict[str, Any]:
    """Stuur een commando en geef het hele antwoord terug, ook bij een fout."""
    await client.send_json_auto_id(payload)
    return await client.receive_json()


# --- 15.1 en 15.2: opslaan en teruglezen -------------------------------


async def test_save_dan_get_levert_dezelfde_data(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Een geldige save gevolgd door een get levert exact dezelfde data.

    NIEUW GEDRAG. Verplicht geval 1. Dit legt vast dat de opslagronde niets
    verandert aan wat er is opgeslagen — geen herordening van velden, geen
    normalisatie die de kaart niet verwacht.
    """
    client = await hass_ws_client(hass)

    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    assert antwoord["success"], antwoord
    na_save = antwoord["result"]["alarms"]
    assert len(na_save) == 1

    antwoord = await _stuur(
        client, {"type": f"{DOMAIN}/alarms/get", "person": PERSON_ENTITY_ID}
    )
    assert antwoord["success"], antwoord
    assert antwoord["result"]["alarms"] == na_save
    assert antwoord["result"]["stored"] is True

    wekker = na_save[0]
    # De server heeft de boekhouding zelf gezet.
    assert wekker["skip_next"] is False
    assert wekker["last_fired"] is None
    assert wekker["last_message"] is None
    # Herhalende wekker: geen one_shot_at.
    assert wekker["one_shot_at"] is None
    assert len(wekker["id"]) == 32


async def test_get_zonder_opslag_is_leeg(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Een persoon die nooit heeft opgeslagen: lege lijst, `stored: false`.

    NIEUW GEDRAG. Dit is de positieve controle onder alle andere tests: zonder
    deze zou "er staat één wekker" ook waar kunnen zijn omdat er iets bleef hangen.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client, {"type": f"{DOMAIN}/alarms/get", "person": PERSON_ENTITY_ID}
    )
    assert antwoord["success"], antwoord
    assert antwoord["result"] == {
        "alarms": [],
        "next_fire": None,
        "ringing": [],
        "stored": False,
    }


async def test_onbekende_person_geeft_not_found(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """NIEUW GEDRAG. Nooit terugvallen op het entity-ID als sleutel (SPEC 18.2)."""
    client = await hass_ws_client(hass)
    for person in ("person.bestaat_niet", "light.bedlamp", "geen-entity-id"):
        antwoord = await _stuur(
            client, {"type": f"{DOMAIN}/alarms/get", "person": person}
        )
        assert not antwoord["success"]
        assert antwoord["error"]["code"] == "not_found", (person, antwoord)


# --- 15.2: validatie, per regel afzonderlijk ---------------------------


@pytest.mark.parametrize(
    ("veld", "waarde"),
    [
        ("time", "6:45"),
        ("time", "06:45:00"),
        ("time", "24:00"),
        ("time", "06:60"),
        ("time", 645),
        ("days", [0]),
        ("days", [8]),
        ("days", [1, 1]),
        ("days", "ma"),
        ("days", [True]),
        ("volume_pct", 0),
        ("volume_pct", 101),
        ("volume_pct", 40.5),
        ("volume_pct", True),
        ("name", "   "),
        ("name", ""),
        ("name", 42),
        ("enabled", "ja"),
        ("sound", {"uri": "x://y", "name": "n"}),
        ("sound", {"uri": "", "name": "n", "media_type": "radio"}),
        ("sound", "somafm://radio/x"),
        ("light", {"entity_id": "light.bedlamp", "brightness_pct": 0}),
        ("light", {"entity_id": "light.bedlamp", "brightness_pct": 101}),
        ("light", {"entity_id": "media_player.x", "brightness_pct": 50}),
        ("light", {"brightness_pct": 50}),
    ],
)
async def test_validatieregel_geeft_invalid_format_en_schrijft_niets(
    hass: HomeAssistant, hass_ws_client, omgeving, lees_opslag, veld, waarde
) -> None:
    """Elke validatieregel uit SPEC 14.2 afzonderlijk.

    NIEUW GEDRAG. Verplicht geval 2, en met de tweede helft die het geval
    interessant maakt: **er is niets weggeschreven.** Een implementatie die eerst
    opslaat en daarna valideert, faalt hier.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/save",
            "person": PERSON_ENTITY_ID,
            "alarm": geldige_wekker(**{veld: waarde}),
        },
    )
    assert not antwoord["success"], (veld, waarde, antwoord)
    assert antwoord["error"]["code"] == "invalid_format", antwoord
    assert lees_opslag() is None, "er mag niets zijn weggeschreven"


async def test_servervelden_worden_geweigerd(
    hass: HomeAssistant, hass_ws_client, omgeving, lees_opslag
) -> None:
    """De kaart mag de boekhoudvelden niet zetten (SPEC 15.2).

    NIEUW GEDRAG. Ze stil negeren zou de kaart laten denken dat ze zijn
    overgenomen; daarom is het een fout. En het is de reden dat de inhaalslag uit
    SPEC 13.4 te vertrouwen is: `last_fired` komt nooit van buiten.
    """
    client = await hass_ws_client(hass)
    for veld, waarde in (
        ("skip_next", True),
        ("last_fired", "2026-08-10T06:45:00+02:00"),
        ("last_message", None),
        ("one_shot_at", "2026-08-11T06:45:00+02:00"),
    ):
        antwoord = await _stuur(
            client,
            {
                "type": f"{DOMAIN}/alarms/save",
                "person": PERSON_ENTITY_ID,
                "alarm": {**geldige_wekker(), veld: waarde},
            },
        )
        assert not antwoord["success"], (veld, antwoord)
        assert antwoord["error"]["code"] == "invalid_format"
        assert veld in antwoord["error"]["message"]
    assert lees_opslag() is None


async def test_save_neemt_last_fired_nooit_van_de_kaart_over(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Een save mag `last_fired` niet zetten én niet wissen (SPEC 15.2).

    NIEUW GEDRAG, en deze test bestaat door een mutatietest: de weigering van
    servervelden bleek **dubbel** gedekt (de onbekende-veldcontrole vangt hem ook),
    waardoor het weghalen van de expliciete weigering geen enkele test liet falen.
    Dat verhulde dat de échte eigenschap nergens werd getoetst: **wat er in de
    opslag komt te staan.**

    Dit is de eigenschap waar de inhaalslag uit SPEC 13.4 op rust. Zou de kaart
    `last_fired` kunnen zetten, dan kan ze de integratie laten denken dat een
    wekker al is afgegaan — en dan gaat hij niet meer af.
    """
    from custom_components.domotiapp_alarm.const import DATA_STORE

    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    alarm_id = antwoord["result"]["alarms"][0]["id"]

    # De planner (fase 3b) schrijft last_fired weg. Hier via de store, want er is
    # nog geen planner.
    store = hass.data[DOMAIN][DATA_STORE]
    gezet = "2026-08-10T06:45:00.312000+02:00"
    await store.async_werk_velden_bij(omgeving, alarm_id, {"last_fired": gezet})

    # 1. Een gewone update laat last_fired staan.
    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/save",
            "person": PERSON_ENTITY_ID,
            "alarm": geldige_wekker(id=alarm_id, name="Andere naam"),
        },
    )
    assert antwoord["success"], antwoord
    wekker = antwoord["result"]["alarms"][0]
    assert wekker["name"] == "Andere naam"
    assert wekker["last_fired"] == gezet, "een save mag last_fired niet wissen"

    # 2. Een save die last_fired zélf meestuurt wordt geweigerd, en de opgeslagen
    #    waarde blijft die van de server.
    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/save",
            "person": PERSON_ENTITY_ID,
            "alarm": {
                **geldige_wekker(id=alarm_id),
                "last_fired": "1999-01-01T00:00:00+01:00",
            },
        },
    )
    assert not antwoord["success"], antwoord
    assert antwoord["error"]["code"] == "invalid_format"

    antwoord = await _stuur(client, {"type": f"{DOMAIN}/alarms/get", "person": PERSON_ENTITY_ID})
    assert antwoord["result"]["alarms"][0]["last_fired"] == gezet


async def test_onbekend_veld_wordt_geweigerd(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """NIEUW GEDRAG. Een veld dat wij niet kennen kan de planner ook niet lezen."""
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/save",
            "person": PERSON_ENTITY_ID,
            "alarm": {**geldige_wekker(), "snooze_minuten": 9},
        },
    )
    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "invalid_format"


async def test_eenmalige_wekker_krijgt_one_shot_at(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """`days` leeg: de server berekent `one_shot_at` (SPEC 15.2).

    NIEUW GEDRAG. De kaart mag dat veld niet aanleveren, dus als de server het niet
    berekent, staat er niets en is de wekker niet te plannen.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/save",
            "person": PERSON_ENTITY_ID,
            "alarm": geldige_wekker(days=[]),
        },
    )
    assert antwoord["success"], antwoord
    wekker = antwoord["result"]["alarms"][0]
    assert wekker["days"] == []
    assert wekker["one_shot_at"] is not None
    # Met tijdzone, want zonder is het moment niet eenduidig (SPEC 14.2). Niet op
    # "+" testen: de testinstance draait niet op Europe/Amsterdam en een negatieve
    # offset is even geldig.
    import datetime as _dt

    assert _dt.datetime.fromisoformat(wekker["one_shot_at"]).tzinfo is not None


# --- 15.2: de speaker moet aan de eisen voldoen (SPEC 7.2, 7.3) --------


async def test_groep_wordt_geweigerd(hass: HomeAssistant, hass_ws_client) -> None:
    """Een groepsplayer mag geen wekkerspeaker zijn (SPEC 7.3).

    NIEUW GEDRAG. Verplicht geval 8. Groepsvolume is relatief en levert een
    onvoorspelbaar eindvolume — gemeten in fase 0b: 60 zetten gaf 60 en 50.
    """
    registreer_person(hass)
    maak_speaker(
        hass,
        "media_player.wekkergroep",
        features=GOEDE_FEATURES,
        player_type="group",
        naam="Wekkergroep",
    )
    await zet_integratie_op(hass)

    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/save",
            "person": PERSON_ENTITY_ID,
            "alarm": geldige_wekker(speaker="media_player.wekkergroep"),
        },
    )
    assert not antwoord["success"], antwoord
    assert antwoord["error"]["code"] == "not_allowed"
    assert "groep" in antwoord["error"]["message"]


@pytest.mark.parametrize(
    ("beschrijving", "kwargs", "fragment"),
    [
        ("verkeerd platform", {"platform": "sonos"}, "sonos"),
        ("geen PLAY_MEDIA", {"features": int(MediaPlayerEntityFeature.VOLUME_SET)}, "afspelen"),
        ("geen VOLUME_SET", {"features": int(MediaPlayerEntityFeature.PLAY_MEDIA)}, "volume"),
    ],
)
async def test_speaker_die_niet_aan_de_eisen_voldoet(
    hass: HomeAssistant, hass_ws_client, beschrijving, kwargs, fragment
) -> None:
    """De eisen uit SPEC 7.2, elk afzonderlijk gebroken.

    NIEUW GEDRAG. De platformcheck is het vangnet onder het label: bij een Sonos
    maken zowel Sonos als MA een entiteit voor dezelfde speaker.
    """
    registreer_person(hass)
    maak_speaker(hass, "media_player.twijfel", **kwargs)
    await zet_integratie_op(hass)

    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/save",
            "person": PERSON_ENTITY_ID,
            "alarm": geldige_wekker(speaker="media_player.twijfel"),
        },
    )
    assert not antwoord["success"], (beschrijving, antwoord)
    assert antwoord["error"]["code"] == "not_allowed"
    assert fragment in antwoord["error"]["message"].lower()


async def test_speaker_in_verkeerd_domein_geeft_not_allowed(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Een speaker buiten het media_player-domein: `not_allowed` (SPEC 7.2 eis 2).

    NIEUW GEDRAG. Bewust `not_allowed` en niet `invalid_format`: de zes eisen van
    SPEC 7.2 staan op één plek, en het domein is de tweede daarvan. Zou de
    schemavalidatie er óók een domeincontrole hebben, dan zou dezelfde afkeuring
    onder twee foutcodes uitkomen, afhankelijk van welke controle eerst draait.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/save",
            "person": PERSON_ENTITY_ID,
            "alarm": geldige_wekker(speaker="light.bedlamp"),
        },
    )
    assert not antwoord["success"], antwoord
    assert antwoord["error"]["code"] == "not_allowed"


async def test_lamp_zonder_label_wordt_geweigerd(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """NIEUW GEDRAG. De wake-up light moet het label hebben (SPEC 15.2)."""
    maak_lamp(hass)
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/save",
            "person": PERSON_ENTITY_ID,
            "alarm": geldige_wekker(light={"entity_id": "light.bedlamp", "brightness_pct": 60}),
        },
    )
    assert not antwoord["success"], antwoord
    assert antwoord["error"]["code"] == "not_allowed"


# --- 15.3, 15.4, 15.5 --------------------------------------------------


async def test_set_enabled_en_skip_next(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """NIEUW GEDRAG. Uitzetten wist `skip_next` (SPEC 15.3)."""
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    alarm_id = antwoord["result"]["alarms"][0]["id"]

    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/skip_next",
            "person": PERSON_ENTITY_ID,
            "alarm_id": alarm_id,
            "skip": True,
        },
    )
    assert antwoord["success"], antwoord
    assert antwoord["result"]["alarms"][0]["skip_next"] is True

    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/set_enabled",
            "person": PERSON_ENTITY_ID,
            "alarm_id": alarm_id,
            "enabled": False,
        },
    )
    assert antwoord["success"], antwoord
    wekker = antwoord["result"]["alarms"][0]
    assert wekker["enabled"] is False
    assert wekker["skip_next"] is False, "uitzetten hoort skip_next te wissen"
    assert antwoord["result"]["next_fire"] is None


async def test_delete_verwijdert_en_onbekende_id_geeft_not_found(
    hass: HomeAssistant, hass_ws_client, omgeving, lees_opslag
) -> None:
    """NIEUW GEDRAG."""
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    alarm_id = antwoord["result"]["alarms"][0]["id"]

    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/delete", "person": PERSON_ENTITY_ID, "alarm_id": "bestaat-niet"},
    )
    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "not_found"

    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/delete", "person": PERSON_ENTITY_ID, "alarm_id": alarm_id},
    )
    assert antwoord["success"], antwoord
    assert antwoord["result"]["alarms"] == []
    # `stored` blijft true: deze persoon heeft wél ooit opgeslagen.
    assert antwoord["result"]["stored"] is True


async def test_save_met_onbekende_id_geeft_not_found(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """NIEUW GEDRAG. Een `id` dat niet bestaat is geen nieuwe wekker (SPEC 15.2)."""
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/save",
            "person": PERSON_ENTITY_ID,
            "alarm": geldige_wekker(id="a" * 32),
        },
    )
    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "not_found"


async def test_save_werkt_bestaande_wekker_bij_en_bewaart_boekhouding(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Een update behoudt `skip_next` (SPEC 15.2).

    NIEUW GEDRAG. Een implementatie die de boekhouding op de beginwaarde zet bij
    elke save, zou een overgeslagen wekker stil weer laten afgaan.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    alarm_id = antwoord["result"]["alarms"][0]["id"]
    await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/skip_next",
            "person": PERSON_ENTITY_ID,
            "alarm_id": alarm_id,
            "skip": True,
        },
    )

    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/save",
            "person": PERSON_ENTITY_ID,
            "alarm": geldige_wekker(id=alarm_id, name="Werk (aangepast)"),
        },
    )
    assert antwoord["success"], antwoord
    wekker = antwoord["result"]["alarms"][0]
    assert wekker["name"] == "Werk (aangepast)"
    assert wekker["skip_next"] is True, "skip_next moet bewaard blijven"
    assert len(antwoord["result"]["alarms"]) == 1, "geen tweede wekker ernaast"


# --- 15.7 entities/list ------------------------------------------------


async def test_entities_list_zonder_labels(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Bestaat het label niet, dan `label_exists: false` (SPEC 7.4).

    NIEUW GEDRAG. Dit onderscheid is wat de editor nodig heeft om "vraag de
    beheerder een label aan te maken" te tonen in plaats van "er zijn geen
    speakers" — twee verschillende meldingen bij een nieuwe klant.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, {"type": f"{DOMAIN}/entities/list"})
    assert antwoord["success"], antwoord
    assert antwoord["result"]["speakers"] == {"label_exists": False, "entities": []}
    assert antwoord["result"]["lights"] == {"label_exists": False, "entities": []}


async def test_entities_list_met_labels(hass: HomeAssistant, hass_ws_client) -> None:
    """Met labels: de gelabelde speakers en lampen, server-side gefilterd.

    NIEUW GEDRAG. Met een positieve controle: er staat óók een gelabelde speaker
    die op de eisen van SPEC 7.2 afvalt, en die mag er niet in staan.
    """
    from homeassistant.helpers import entity_registry as er, label_registry as lr

    registreer_person(hass)
    goed = maak_speaker(hass, "media_player.goed", features=GOEDE_FEATURES, naam="Goed")
    groep = maak_speaker(
        hass, "media_player.groep", features=GOEDE_FEATURES, player_type="group", naam="Groep"
    )
    lamp = maak_lamp(hass)
    await zet_integratie_op(hass)

    labels = lr.async_get(hass)
    speaker_label = labels.async_create("Music Assistant Wekker")
    lamp_label = labels.async_create("Verlichting Wekker")
    registry = er.async_get(hass)
    registry.async_update_entity(goed, labels={speaker_label.label_id})
    registry.async_update_entity(groep, labels={speaker_label.label_id})
    registry.async_update_entity(lamp, labels={lamp_label.label_id})

    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, {"type": f"{DOMAIN}/entities/list"})
    assert antwoord["success"], antwoord
    speakers = antwoord["result"]["speakers"]
    assert speakers["label_exists"] is True
    assert speakers["entities"] == [{"entity_id": goed, "name": "Goed"}]
    lights = antwoord["result"]["lights"]
    assert lights["label_exists"] is True
    assert lights["entities"] == [{"entity_id": lamp, "name": "Bedlamp"}]


# --- 15.8 en 15.9 ------------------------------------------------------


async def test_stop_is_idempotent(hass: HomeAssistant, hass_ws_client, omgeving) -> None:
    """Een wekker stoppen die niet loopt is geen fout (SPEC 15.8).

    NIEUW GEDRAG. Een wandtablet en een telefoon kunnen tegelijk drukken; een
    implementatie die de tweede aanroep afkeurt, laat de kaart een fout tonen voor
    een handeling die precies goed ging.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    alarm_id = antwoord["result"]["alarms"][0]["id"]

    for _ in range(2):
        antwoord = await _stuur(
            client,
            {"type": f"{DOMAIN}/alarms/stop", "person": PERSON_ENTITY_ID, "alarm_id": alarm_id},
        )
        assert antwoord["success"], antwoord
        assert antwoord["result"]["ringing"] == []


async def test_updates_subscribe_ontvangt_gebeurtenissen(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Het abonnement levert de berichten uit SPEC 15.9.

    NIEUW GEDRAG. Er is in fase 3a nog niets dat een wekker laat afgaan, dus de
    gebeurtenis wordt hier via het register gestuurd — hetzelfde register dat fase
    3b vult. Zo is het doorgeefluik nu al vastgelegd.
    """
    from custom_components.domotiapp_alarm import abonnement

    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client, {"type": f"{DOMAIN}/updates/subscribe", "person": PERSON_ENTITY_ID}
    )
    assert antwoord["success"], antwoord
    abonnement_id = antwoord["id"]

    abonnement.register_van(hass).stuur(
        {
            "event": "started",
            "person": PERSON_ENTITY_ID,
            "alarm_id": "abc",
            "name": "Werk",
            "time": "06:45",
        }
    )
    bericht = await client.receive_json()
    assert bericht["id"] == abonnement_id
    assert bericht["type"] == "event"
    assert bericht["event"]["event"] == "started"
    assert bericht["event"]["alarm_id"] == "abc"


async def test_subscribe_filtert_op_person(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """NIEUW GEDRAG. Een kaart hoort alleen de wekkers van zijn eigen persoon."""
    from custom_components.domotiapp_alarm import abonnement

    client = await hass_ws_client(hass)
    await _stuur(client, {"type": f"{DOMAIN}/updates/subscribe", "person": PERSON_ENTITY_ID})

    register = abonnement.register_van(hass)
    register.stuur({"event": "started", "person": "person.iemand_anders", "alarm_id": "x"})
    register.stuur({"event": "started", "person": PERSON_ENTITY_ID, "alarm_id": "eigen"})

    bericht = await client.receive_json()
    assert bericht["event"]["alarm_id"] == "eigen", "het bericht van de ander mag niet doorkomen"


async def test_ringing_wordt_getoond_in_get_en_gestopt(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """`alarms/get` meldt wat nu afgaat, en `stop` haalt het eruit (SPEC 15.1, 15.8).

    NIEUW GEDRAG, met een positieve controle: eerst staat de wekker in `ringing`,
    daarna niet meer. Zonder die eerste helft zou "ringing is leeg" triviaal waar
    zijn.
    """
    from custom_components.domotiapp_alarm import abonnement

    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    alarm_id = antwoord["result"]["alarms"][0]["id"]

    register = abonnement.register_van(hass)
    register.actief[(omgeving, alarm_id)] = {}

    antwoord = await _stuur(client, {"type": f"{DOMAIN}/alarms/get", "person": PERSON_ENTITY_ID})
    assert antwoord["result"]["ringing"] == [alarm_id]

    antwoord = await _stuur(
        client, {"type": f"{DOMAIN}/alarms/stop", "person": PERSON_ENTITY_ID, "alarm_id": alarm_id}
    )
    assert antwoord["success"], antwoord
    assert antwoord["result"]["ringing"] == []


# --- 15.6 sound/search -------------------------------------------------


async def test_search_zonder_music_assistant(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Geen geladen MA-config-entry: `not_found` met uitleg (SPEC 18.5).

    NIEUW GEDRAG.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, {"type": f"{DOMAIN}/sound/search", "query": "jazz"})
    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "not_found"
    assert "Music Assistant" in antwoord["error"]["message"]


# --- 15.10 alarms/clear_message ----------------------------------------


async def _wekker_met_melding(client, store, registry_id) -> tuple[str, dict[str, Any]]:
    """Sla één wekker op en laat de server er een melding op zetten.

    De melding komt via de store, want dat is ook de enige route in productie:
    `meldingen.py` schrijft hem, de kaart niet.
    """
    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    assert antwoord["success"], antwoord
    alarm_id = antwoord["result"]["alarms"][0]["id"]
    melding = {
        "at": "2026-08-10T06:45:00.312000+02:00",
        "kind": "speaker_unavailable",
        "severity": "error",
        "text": "De wekker van 06:45 is niet afgegaan: de speaker was niet bereikbaar.",
    }
    await store.async_werk_velden_bij(registry_id, alarm_id, {"last_message": melding})
    return alarm_id, melding


async def test_clear_message_wist_de_melding_uit_de_opslag(
    hass: HomeAssistant, hass_ws_client, omgeving, lees_opslag
) -> None:
    """"Begrepen" wist `last_message` in de **opslag** (SPEC 11.7, 15.10).

    NIEUW GEDRAG, met een positieve controle vooraf: eerst staat de melding er, en
    pas daarna is "hij is weg" iets waard. Zonder die eerste helft slaagt deze test
    ook op een implementatie die nooit een melding te zien krijgt.

    Dat er in de **opslag** gekeken wordt en niet alleen in het antwoord is de kern:
    de melding staat daar zodat hij een herstart overleeft en op elk scherm
    zichtbaar is (SPEC 11.7). Een kaart die hem alleen lokaal verbergt, laat hem
    staan op het wandtablet.
    """
    from custom_components.domotiapp_alarm.const import DATA_STORE

    client = await hass_ws_client(hass)
    store = hass.data[DOMAIN][DATA_STORE]
    alarm_id, melding = await _wekker_met_melding(client, store, omgeving)

    # Positieve controle: de melding is er, in het antwoord én op schijf.
    antwoord = await _stuur(client, {"type": f"{DOMAIN}/alarms/get", "person": PERSON_ENTITY_ID})
    assert antwoord["result"]["alarms"][0]["last_message"] == melding
    op_schijf = lees_opslag()["data"]["persons"][omgeving]["alarms"][0]
    assert op_schijf["last_message"] == melding

    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/clear_message",
            "person": PERSON_ENTITY_ID,
            "alarm_id": alarm_id,
        },
    )
    assert antwoord["success"], antwoord
    wekker = antwoord["result"]["alarms"][0]
    assert wekker["last_message"] is None
    assert lees_opslag()["data"]["persons"][omgeving]["alarms"][0]["last_message"] is None

    # En er is niets anders gesneuveld.
    assert wekker["name"] == geldige_wekker()["name"]
    assert wekker["enabled"] is True
    assert wekker["time"] == geldige_wekker()["time"]


async def test_clear_message_laat_de_andere_servervelden_staan(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Wissen raakt alleen `last_message` (SPEC 15.10).

    NIEUW GEDRAG. `skip_next` en `last_fired` dragen respectievelijk de overslag en
    de inhaalslag (SPEC 13.4). Een commando dat ze en passant meewist, zou een
    wekker die vanochtend al is afgegaan vanavond opnieuw laten afgaan.
    """
    from custom_components.domotiapp_alarm.const import DATA_STORE

    client = await hass_ws_client(hass)
    store = hass.data[DOMAIN][DATA_STORE]
    alarm_id, _ = await _wekker_met_melding(client, store, omgeving)
    gezet = "2026-08-10T06:45:00.312000+02:00"
    await store.async_werk_velden_bij(
        omgeving, alarm_id, {"last_fired": gezet, "skip_next": True}
    )

    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/clear_message",
            "person": PERSON_ENTITY_ID,
            "alarm_id": alarm_id,
        },
    )
    assert antwoord["success"], antwoord
    wekker = antwoord["result"]["alarms"][0]
    assert wekker["last_message"] is None
    assert wekker["last_fired"] == gezet, "last_fired draagt de inhaalslag"
    assert wekker["skip_next"] is True, "de overslag is een aparte keuze"


async def test_clear_message_kan_geen_melding_zetten(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Het commando neemt geen waarde aan (SPEC 15.10, 15.11).

    NIEUW GEDRAG, en dit is de test die het commando afbakent. Zou het een veld
    accepteren, dan had de kaart via deze weg alsnog een serverveld in handen —
    precies wat SPEC 15.2 verbiedt — en kon een aanroeper de klant vertellen dat
    zijn wekker niet is afgegaan terwijl hij wel afging.

    Er is een positieve controle bij: dezelfde aanroep **zonder** het extra veld
    slaagt. Zonder die helft zou deze test ook slagen op een commando dat helemaal
    niet bestaat.
    """
    from custom_components.domotiapp_alarm.const import DATA_STORE

    client = await hass_ws_client(hass)
    store = hass.data[DOMAIN][DATA_STORE]
    alarm_id, melding = await _wekker_met_melding(client, store, omgeving)

    for extra in (
        {"last_message": {**melding, "text": "verzonnen"}},
        {"message": {**melding, "text": "verzonnen"}},
        {"severity": "notice"},
    ):
        antwoord = await _stuur(
            client,
            {
                "type": f"{DOMAIN}/alarms/clear_message",
                "person": PERSON_ENTITY_ID,
                "alarm_id": alarm_id,
                **extra,
            },
        )
        assert not antwoord["success"], (extra, antwoord)
        assert antwoord["error"]["code"] == "invalid_format", (extra, antwoord)

    # De melding staat er dus nog steeds — en is niet vervangen door "verzonnen".
    antwoord = await _stuur(client, {"type": f"{DOMAIN}/alarms/get", "person": PERSON_ENTITY_ID})
    assert antwoord["result"]["alarms"][0]["last_message"] == melding

    # Positieve controle: zonder extra veld lukt het wel.
    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/clear_message",
            "person": PERSON_ENTITY_ID,
            "alarm_id": alarm_id,
        },
    )
    assert antwoord["success"], antwoord
    assert antwoord["result"]["alarms"][0]["last_message"] is None


async def test_clear_message_is_idempotent_en_kent_zijn_wekker(
    hass: HomeAssistant, hass_ws_client, omgeving
) -> None:
    """Twee keer wissen is geen fout; een onbekende wekker wel (SPEC 15.10).

    NIEUW GEDRAG. Twee schermen kunnen tegelijk op "Begrepen" drukken, net als bij
    `alarms/stop`. Maar een `alarm_id` die niet bestaat is wél `not_found`: stil
    slagen op een wekker die er niet is, verbergt een kaart die met verouderde
    ID's werkt.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    alarm_id = antwoord["result"]["alarms"][0]["id"]

    for _ in range(2):
        antwoord = await _stuur(
            client,
            {
                "type": f"{DOMAIN}/alarms/clear_message",
                "person": PERSON_ENTITY_ID,
                "alarm_id": alarm_id,
            },
        )
        assert antwoord["success"], antwoord
        assert antwoord["result"]["alarms"][0]["last_message"] is None

    antwoord = await _stuur(
        client,
        {
            "type": f"{DOMAIN}/alarms/clear_message",
            "person": PERSON_ENTITY_ID,
            "alarm_id": "bestaat-niet",
        },
    )
    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "not_found"


# --- SPEC 17: rechten --------------------------------------------------


async def test_niet_admin_mag_alle_tien_commandos(
    hass: HomeAssistant, hass_ws_client, hass_read_only_access_token, omgeving
) -> None:
    """Een niet-admin mag alle tien commando's aanroepen (SPEC 17).

    NIEUW GEDRAG. Verplicht geval 6, en de belangrijkste rechtentest van dit
    product: klanten draaien Fully Kiosk met een niet-admin account. Zou er ergens
    een `@require_admin` staan, dan kan de klant zijn wekker niet uitzetten.

    De test faalt met `unauthorized` op elk commando dat admin-only is gemaakt.
    """
    client = await hass_ws_client(hass, hass_read_only_access_token)

    antwoord = await _stuur(
        client,
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    )
    assert antwoord["success"], antwoord
    alarm_id = antwoord["result"]["alarms"][0]["id"]

    aanroepen: list[dict[str, Any]] = [
        {"type": f"{DOMAIN}/alarms/get", "person": PERSON_ENTITY_ID},
        {
            "type": f"{DOMAIN}/alarms/set_enabled",
            "person": PERSON_ENTITY_ID,
            "alarm_id": alarm_id,
            "enabled": True,
        },
        {
            "type": f"{DOMAIN}/alarms/skip_next",
            "person": PERSON_ENTITY_ID,
            "alarm_id": alarm_id,
            "skip": False,
        },
        {"type": f"{DOMAIN}/entities/list"},
        {"type": f"{DOMAIN}/alarms/stop", "person": PERSON_ENTITY_ID, "alarm_id": alarm_id},
        {"type": f"{DOMAIN}/updates/subscribe"},
        {"type": f"{DOMAIN}/sound/search", "query": "jazz"},
        {
            "type": f"{DOMAIN}/alarms/clear_message",
            "person": PERSON_ENTITY_ID,
            "alarm_id": alarm_id,
        },
        {"type": f"{DOMAIN}/alarms/delete", "person": PERSON_ENTITY_ID, "alarm_id": alarm_id},
    ]
    for payload in aanroepen:
        antwoord = await _stuur(client, payload)
        # sound/search mag not_found geven (geen MA), maar nooit unauthorized.
        code = antwoord.get("error", {}).get("code")
        assert code != "unauthorized", (payload["type"], antwoord)
