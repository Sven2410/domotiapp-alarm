"""De opslaglaag en het foutgedrag uit SPEC 19.2.

Alles hier is **NIEUW GEDRAG**: er was geen opslaglaag. Elke test legt een regel
uit SPEC 19.2 vast die ook later kan sneuvelen — en de belangrijkste is
`test_kapotte_persoon_blokkeert_gezonde_niet`: dat is de hele reden dat deze laag
gevalideerde en onbewerkte data naast elkaar bewaart.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.domotiapp_alarm.const import DOMAIN
from custom_components.domotiapp_alarm.store import (
    AlarmStore,
    OpslagOnbruikbaar,
    PersonNietGevonden,
    PersoonOnleesbaar,
    registry_id_van_person,
)

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


def volledige_wekker(alarm_id: str = "a" * 32, **overschrijf: Any) -> dict[str, Any]:
    """Een wekker zoals hij in de **opslag** staat, dus met de boekhoudvelden."""
    wekker: dict[str, Any] = {
        **geldige_wekker(),
        "id": alarm_id,
        "skip_next": False,
        "one_shot_at": None,
        "last_fired": None,
        "last_message": None,
    }
    wekker.update(overschrijf)
    return wekker


# --- geval B: één kapotte persoon (SPEC 19.2) --------------------------


async def test_kapotte_persoon_blokkeert_gezonde_niet(
    hass: HomeAssistant, hass_ws_client, schrijf_opslag, lees_opslag
) -> None:
    """Het belangrijkste geval van deze fase (SPEC 19.2 geval B, regel 1 en 5).

    NIEUW GEDRAG. Drie dingen tegelijk:

    1. een kapotte persoon maakt de wekkers van een huisgenoot niet onbruikbaar;
    2. de gezonde persoon kan gewoon opslaan;
    3. **de kapotte data staat na die schrijfronde nog letterlijk in het bestand.**

    Punt 3 is waar de hele constructie om bestaat. Een implementatie die de
    kapotte waarde opnieuw opbouwt, normaliseert of weglaat, faalt hier — en zou
    in productie de data van een klant weggooien op het moment dat een huisgenoot
    op Opslaan drukt.
    """
    kapot = {
        "alarms": [
            # `time` is onzin en `days` bevat een 9: dit valideert niet.
            {"id": "kapot1", "name": "Stuk", "time": "kwart voor zeven", "days": [9]}
        ],
        "ietsWatWijNietKennen": {"diep": [1, 2, 3]},
    }
    kapot_origineel = copy.deepcopy(kapot)

    gezond_id = registreer_person(hass)
    kapot_id = registreer_person(hass, "person.huisgenoot", "huisgenoot")
    schrijf_opslag({kapot_id: kapot})

    maak_speaker(hass, features=GOEDE_FEATURES)
    await zet_integratie_op(hass)
    client = await hass_ws_client(hass)

    # 1. De kapotte persoon geeft home_assistant_error, niet een lege lijst.
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/alarms/get", "person": "person.huisgenoot"}
    )
    antwoord = await client.receive_json()
    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "home_assistant_error", antwoord

    # en opslaan wordt voor hem geweigerd (regel 3).
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/alarms/save",
            "person": "person.huisgenoot",
            "alarm": geldige_wekker(),
        }
    )
    antwoord = await client.receive_json()
    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "home_assistant_error"

    # 2. De gezonde persoon kan wél opslaan.
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()}
    )
    antwoord = await client.receive_json()
    assert antwoord["success"], antwoord
    assert len(antwoord["result"]["alarms"]) == 1

    # 3. De kapotte data staat er nog, letterlijk.
    op_schijf = lees_opslag()
    assert op_schijf is not None, "er hoort geschreven te zijn"
    personen = op_schijf["data"]["persons"]
    assert kapot_id in personen, "de kapotte persoon mag niet verdwenen zijn"
    assert personen[kapot_id] == kapot_origineel, (
        "de kapotte data moet byte-voor-byte teruggeschreven zijn, "
        f"maar werd {personen[kapot_id]!r}"
    )
    assert gezond_id in personen
    assert len(personen[gezond_id]["alarms"]) == 1


async def test_kapotte_persoon_wordt_niet_gepland(
    hass: HomeAssistant, schrijf_opslag
) -> None:
    """Voor een kapotte persoon wordt niets gepland (SPEC 19.2 geval B, regel 6).

    NIEUW GEDRAG. `alle_wekkers()` is wat fase 3b gaat gebruiken om te plannen; een
    wekker die je niet kunt lezen kun je niet betrouwbaar plannen.
    """
    kapot_id = registreer_person(hass, "person.huisgenoot", "huisgenoot")
    gezond_id = registreer_person(hass)
    schrijf_opslag(
        {
            kapot_id: {"alarms": "geen lijst"},
            gezond_id: {"alarms": [volledige_wekker()]},
        }
    )
    store = AlarmStore(hass)
    await store.async_load()

    assert store.is_corrupt(kapot_id) is True
    assert store.is_corrupt(gezond_id) is False
    planbaar = store.alle_wekkers()
    assert set(planbaar) == {gezond_id}, "de kapotte persoon mag er niet in staan"
    assert len(planbaar[gezond_id]) == 1


async def test_corrupte_personen_worden_gemeld(hass: HomeAssistant, schrijf_opslag) -> None:
    """De reden staat erbij, zodat een melding kan zeggen wát er mis is.

    NIEUW GEDRAG.
    """
    kapot_id = registreer_person(hass, "person.huisgenoot", "huisgenoot")
    schrijf_opslag({kapot_id: {"alarms": [{"id": "x"}]}})
    store = AlarmStore(hass)
    await store.async_load()
    redenen = store.corrupte_personen()
    assert set(redenen) == {kapot_id}
    assert redenen[kapot_id], "er hoort een reden te staan"


# --- geval C: data.persons is geen object (SPEC 19.2) ------------------


@pytest.mark.parametrize("persons", [[], "leeg", 42, None])
async def test_geval_c_schrijft_niets(
    hass: HomeAssistant, hass_ws_client, schrijf_opslag, lees_opslag, persons
) -> None:
    """`data.persons` is geen object: niets schrijven, alles home_assistant_error.

    NIEUW GEDRAG. Verplicht geval 4. Er is geen enkele sleutel om per persoon te
    markeren, dus elke schrijfactie zou de hele inhoud weggooien. Dan wint SPEC
    19.1: niet overschrijven.
    """
    registreer_person(hass)
    schrijf_opslag(persons)
    voor = copy.deepcopy(lees_opslag())

    maak_speaker(hass, features=GOEDE_FEATURES)
    await zet_integratie_op(hass)
    client = await hass_ws_client(hass)

    for payload in (
        {"type": f"{DOMAIN}/alarms/get", "person": PERSON_ENTITY_ID},
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()},
    ):
        await client.send_json_auto_id(payload)
        antwoord = await client.receive_json()
        assert not antwoord["success"], (payload["type"], antwoord)
        assert antwoord["error"]["code"] == "home_assistant_error"

    assert lees_opslag() == voor, "er mag niets gewijzigd zijn op schijf"


async def test_geval_c_schrijft_ook_niet_langs_de_interne_route(
    hass: HomeAssistant, schrijf_opslag, lees_opslag
) -> None:
    """In geval C wordt er onder **geen enkele** omstandigheid geschreven.

    NIEUW GEDRAG, en deze test bestaat door een mutatietest. De guard in
    `_async_schrijf` bleek via de WebSocket-API onbereikbaar: elk pad daarheen gaat
    eerst langs `_eis_bruikbaar`, dus het weghalen van de guard veranderde niets en
    werd door geen enkele test gevangen.

    Dat maakt de guard geen dode code maar **een vangnet voor fase 3b**: de planner
    gaat `last_fired` en `last_message` wegschrijven, en die route hoeft niet langs
    een leesactie. Daarom wordt hier de schrijflaag rechtstreeks getoetst, met een
    private methode — de invariant is belangrijker dan de zichtbaarheid.
    """
    schrijf_opslag("onzin")
    voor = copy.deepcopy(lees_opslag())
    store = AlarmStore(hass)
    await store.async_load()
    assert store.onbruikbaar is not None

    with pytest.raises(OpslagOnbruikbaar):
        await store._async_schrijf()  # noqa: SLF001 - opzettelijk, zie docstring

    assert lees_opslag() == voor, "er mag niets gewijzigd zijn op schijf"


async def test_geval_c_plant_niets(hass: HomeAssistant, schrijf_opslag) -> None:
    """NIEUW GEDRAG. Geen enkele wekker gaat af (SPEC 19.2 geval C, regel 6)."""
    schrijf_opslag("onzin")
    store = AlarmStore(hass)
    await store.async_load()
    assert store.onbruikbaar is not None
    assert store.alle_wekkers() == {}
    with pytest.raises(OpslagOnbruikbaar):
        store.wekkers("maakt-niet-uit")


# --- de opslagsleutel (SPEC 6.2) ---------------------------------------


async def test_hernoemen_van_de_person_behoudt_de_wekkers(
    hass: HomeAssistant, hass_ws_client
) -> None:
    """De wekkers blijven vindbaar na hernoemen (SPEC 6.2).

    NIEUW GEDRAG. Verplicht geval 5. De sleutel is het registry-entry-ID en niet
    het entity-ID; zonder die keuze verdwijnen de wekkers van iemand die zijn naam
    wijzigt.

    De test hernoemt het **entity-ID**, wat de zwaarste variant is: bij een gewone
    naamswijziging verandert het entity-ID vaak niet eens.
    """
    registry_id = registreer_person(hass)
    maak_speaker(hass, features=GOEDE_FEATURES)
    await zet_integratie_op(hass)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/alarms/save", "person": PERSON_ENTITY_ID, "alarm": geldige_wekker()}
    )
    antwoord = await client.receive_json()
    assert antwoord["success"], antwoord
    alarm_id = antwoord["result"]["alarms"][0]["id"]

    registry = er.async_get(hass)
    nieuw = registry.async_update_entity(
        PERSON_ENTITY_ID, new_entity_id="person.sven_kool", name="Sven Kool"
    )
    assert nieuw.entity_id == "person.sven_kool"
    assert nieuw.id == registry_id, "het registry-entry-ID verandert niet bij hernoemen"
    hass.states.async_set("person.sven_kool", "home", {"friendly_name": "Sven Kool"})

    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/alarms/get", "person": "person.sven_kool"}
    )
    antwoord = await client.receive_json()
    assert antwoord["success"], antwoord
    assert [w["id"] for w in antwoord["result"]["alarms"]] == [alarm_id]

    # En het oude entity-ID bestaat niet meer.
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/alarms/get", "person": PERSON_ENTITY_ID}
    )
    antwoord = await client.receive_json()
    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "not_found"


async def test_registry_id_valt_nooit_terug_op_entity_id(hass: HomeAssistant) -> None:
    """Een person zonder registry-entry geeft een fout (SPEC 18.2).

    NIEUW GEDRAG. Terugvallen op het entity-ID zou betekenen dat de wekkers van
    iemand stil verdwijnen zodra het registry-entry er wél is.
    """
    hass.states.async_set("person.alleen_state", "home", {})
    with pytest.raises(PersonNietGevonden):
        registry_id_van_person(hass, "person.alleen_state")
    with pytest.raises(PersonNietGevonden):
        registry_id_van_person(hass, "light.bedlamp")
    with pytest.raises(PersonNietGevonden):
        registry_id_van_person(hass, "geen-punt")


# --- migratie (SPEC 14.6) ----------------------------------------------


async def test_onbekende_versie_gooit(hass: HomeAssistant, hass_storage) -> None:
    """Een oudere versie waarvoor geen migratie bestaat, faalt (SPEC 14.6).

    NIEUW GEDRAG. Liever falen dan een formaat half interpreteren. Zonder deze
    regel zou een toekomstige versiebump stilzwijgend data kunnen verliezen.
    """
    from custom_components.domotiapp_alarm.const import STORAGE_KEY

    hass_storage[STORAGE_KEY] = {
        "version": 0,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": {"persons": {}},
    }
    store = AlarmStore(hass)
    with pytest.raises(NotImplementedError):
        await store.async_load()


# --- de Store-laag zelf -------------------------------------------------


async def test_wekkers_geeft_een_kopie(hass: HomeAssistant, schrijf_opslag) -> None:
    """De aanroeper mag de opslag niet van binnenuit wijzigen.

    NIEUW GEDRAG. Zonder deze kopie zou een handler die het antwoord aanpast de
    opslag in het geheugen wijzigen zonder schrijfronde — en dan wijkt schijf af
    van geheugen tot de volgende herstart.
    """
    registry_id = registreer_person(hass)
    schrijf_opslag({registry_id: {"alarms": [volledige_wekker()]}})
    store = AlarmStore(hass)
    await store.async_load()

    eerste = store.wekkers(registry_id)
    eerste[0]["name"] = "aangepast van buiten"
    assert store.wekkers(registry_id)[0]["name"] == "Werk"


async def test_lege_opslag_is_geen_fout(hass: HomeAssistant) -> None:
    """Nog nooit opgeslagen: lege lijst, geen markering (SPEC 19.2 geval A).

    NIEUW GEDRAG. Dit is ook het pad na geval A: HA heeft het bestand weggezet en
    `async_load` geeft `None`. Wij mogen daar niets aan toevoegen en niets aan
    afdoen.
    """
    registry_id = registreer_person(hass)
    store = AlarmStore(hass)
    await store.async_load()
    assert store.onbruikbaar is None
    assert store.is_corrupt(registry_id) is False
    assert store.wekkers(registry_id) == []
    assert store.heeft_opslag(registry_id) is False


async def test_onleesbare_persoon_gooit_bij_lezen(
    hass: HomeAssistant, schrijf_opslag
) -> None:
    """NIEUW GEDRAG. `PersoonOnleesbaar` wordt `home_assistant_error` in de API."""
    registry_id = registreer_person(hass)
    schrijf_opslag({registry_id: {"alarms": [{"id": "x", "time": "fout"}]}})
    store = AlarmStore(hass)
    await store.async_load()
    with pytest.raises(PersoonOnleesbaar):
        store.wekkers(registry_id)
