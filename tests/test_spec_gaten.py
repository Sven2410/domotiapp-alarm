"""De twee SPEC-gaten die fase 4c dicht (SPEC 8.3.1/15.6 en 7.4/15.7).

Beide gaten hadden dezelfde vorm: **de server wist iets wat de kaart nodig had en
gaf het niet door**, waarna de kaart een keuze maakte die soms onwaar was. Deze
tests leggen vast dat het antwoord voortaan van de server komt.

Alles hier is **NIEUW GEDRAG**. Op de code van fase 4b faalt het met een
`KeyError` op het ontbrekende veld, en dat is geen triviale mislukking: het veld
is precies het onderwerp.

Het onderscheid dat deze tests bewaken is niet "er staat een veld in" maar **dat
de drie respectievelijk twee situaties uit elkaar te houden zijn**. Een
implementatie die overal hetzelfde teruggeeft, komt door een bestaanstest heen en
niet door deze.
"""

from __future__ import annotations

from typing import Any

import pytest

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import HomeAssistant

from custom_components.domotiapp_alarm import radiomodus
from custom_components.domotiapp_alarm.const import DOMAIN

from .conftest import (
    Speelhuis,
    maak_lamp,
    maak_speaker,
    registreer_person,
    zet_integratie_op,
)

GOEDE_FEATURES = int(
    MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.VOLUME_SET
)

# Een provider mét SIMILAR_TRACKS en een zonder, uit `SIMILAR_TRACKS_PROVIDERS`.
MET = "spotify--ZvzrFmgX"
ZONDER = "somafm"


@pytest.fixture(autouse=True)
def _laad_de_ma_entry_uit(hass: HomeAssistant):
    """Zelfde reden als in `test_afvuren.py` en `test_voorbeeld.py`: zonder dit
    laadt HA's teardown de nagebootste MA-entry uit en importeert het daarvoor de
    échte integratie, die `music_assistant_client` nodig heeft."""
    from homeassistant.config_entries import ConfigEntryState

    yield
    for entry in hass.config_entries.async_entries("music_assistant"):
        entry.mock_state(hass, ConfigEntryState.NOT_LOADED)


async def _stuur(client, payload: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(payload)
    return await client.receive_json()


# =======================================================================
# Gat 1 — `endless` in sound/search (SPEC 8.3.1 en 15.6)
# =======================================================================


@pytest.mark.parametrize(
    ("uri", "media_type", "verwacht"),
    [
        # Verplicht geval 1: dezelfde soort, twee providers, twee uitkomsten.
        (f"{MET}://track/1", "track", True),
        (f"{ZONDER}://track/1", "track", False),
        # Verplicht geval 3: radio en afspeellijst houden uit zichzelf niet op,
        # ongeacht de provider.
        (f"{ZONDER}://radio/beatblender", "radio", True),
        (f"{MET}://radio/x", "radio", True),
        (f"{ZONDER}://playlist/1", "playlist", True),
        (f"{MET}://playlist/1", "playlist", True),
        # De overige eindige soorten volgen de provider.
        (f"{MET}://podcast/1", "podcast", True),
        (f"{ZONDER}://podcast/1", "podcast", False),
        (f"{MET}://album/1", "album", True),
        (f"{ZONDER}://album/1", "album", False),
    ],
)
def test_blijft_doorspelen_per_soort_en_provider(uri, media_type, verwacht) -> None:
    """De twee redenen om eindeloos te zijn, elk afzonderlijk (SPEC 8.3.1).

    NIEUW GEDRAG. De tabel bevat van elke soort een paar met en zonder
    `SIMILAR_TRACKS`; alleen zo valt te zien of de soort of de provider de
    doorslag geeft. Een implementatie die alleen naar de soort kijkt faalt op rij
    1 en 2, een die alleen naar de provider kijkt op rij 3 en 5.
    """
    assert radiomodus.blijft_doorspelen(uri, media_type) is verwacht


@pytest.mark.parametrize(
    "media_type", ["RADIO", "Radio", " radio ", "playlist", "PLAYLIST"]
)
def test_de_soort_wordt_genormaliseerd(media_type) -> None:
    """NIEUW GEDRAG. MA levert de soort als tekst aan; hoofdletters mogen niet
    het verschil maken tussen wel en geen waarschuwing."""
    assert radiomodus.blijft_doorspelen(f"{ZONDER}://x/1", media_type) is True


@pytest.mark.parametrize(
    ("uri", "media_type"),
    [(None, None), ("", "track"), ("geen-uri", "track"), (f"{ZONDER}://x/1", None)],
)
def test_bij_twijfel_geen_belofte(uri, media_type) -> None:
    """Bij twijfel `False`: liever een waarschuwing te veel (SPEC 8.3.1).

    NIEUW GEDRAG. `False` betekent hier "de editor waarschuwt", en dat is de
    goede kant om fout te zitten: hinderlijk in plaats van een belofte dat het
    geluid doorspeelt terwijl het na drie minuten stopt.
    """
    assert radiomodus.blijft_doorspelen(uri, media_type) is False


def test_endless_gebruikt_dezelfde_bron_als_radio_mode() -> None:
    """Eén lijst, en dat is de hele reden dat dit server-side gebeurt (SPEC 15.6).

    NIEUW GEDRAG. Zou de editor het zelf uitrekenen, dan bestaat
    `SIMILAR_TRACKS_PROVIDERS` twee keer en kan de editor "dit speelt door"
    beloven terwijl `afvuren.py` `radio_mode` weglaat. Deze test legt vast dat de
    twee antwoorden op elkaar aansluiten voor een **eindige** soort — daar is
    `radio_mode` immers precies wat het eindeloos maakt.
    """
    for provider in (MET, ZONDER):
        uri = f"{provider}://track/1"
        assert radiomodus.blijft_doorspelen(uri, "track") is radiomodus.stuur_radio_mode_mee(uri)


async def test_sound_search_geeft_endless_per_treffer(
    hass: HomeAssistant, hass_ws_client, hass_storage: dict[str, Any]
) -> None:
    """`sound/search` levert het veld, en het verschilt per treffer (SPEC 15.6).

    NIEUW GEDRAG, en dit is de test die het gat dicht: op de code van fase 4b
    staat `endless` niet in het antwoord en moest de kaart het zelf verzinnen.

    Er zitten drie treffers in één antwoord, met opzet: een radiostation van een
    provider zonder `SIMILAR_TRACKS`, een los nummer van diezelfde provider, en
    een los nummer van een provider mét. Zou de server één waarde voor het hele
    antwoord bepalen, dan faalt dit.
    """
    registreer_person(hass)
    maak_speaker(hass, features=GOEDE_FEATURES)
    huis = Speelhuis(hass)
    huis.register()
    huis.zoekresultaat = {
        "radio": [{"name": "Beat Blender", "uri": f"{ZONDER}://radio/beatblender",
                   "media_type": "radio"}],
        "tracks": [
            {"name": "Gratis nummer", "uri": f"{ZONDER}://track/1", "media_type": "track"},
            {"name": "Betaald nummer", "uri": f"{MET}://track/2", "media_type": "track"},
        ],
    }
    await zet_integratie_op(hass)

    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, {"type": f"{DOMAIN}/sound/search", "query": "iets"})
    assert antwoord["success"], antwoord

    per_naam = {t["name"]: t["endless"] for t in antwoord["result"]["results"]}
    assert per_naam == {
        "Beat Blender": True,      # radio houdt uit zichzelf niet op
        "Gratis nummer": False,    # eindige soort, provider zonder SIMILAR_TRACKS
        "Betaald nummer": True,    # eindige soort, provider mét
    }


# =======================================================================
# Gat 2 — `filtered_out` in entities/list (SPEC 7.4 en 15.7)
# =======================================================================


async def _lijst(hass, hass_ws_client) -> dict[str, Any]:
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, {"type": f"{DOMAIN}/entities/list"})
    assert antwoord["success"], antwoord
    return antwoord["result"]


async def test_situatie_1_het_label_bestaat_niet(
    hass: HomeAssistant, hass_ws_client
) -> None:
    """Situatie 1 van SPEC 7.4: `label_exists` is `False`.

    NIEUW GEDRAG voor het derde veld. De teller staat op 0 en niet op iets
    verzonnens: zonder label is er niets om af te laten vallen.
    """
    registreer_person(hass)
    maak_speaker(hass, features=GOEDE_FEATURES)
    await zet_integratie_op(hass)

    uit = await _lijst(hass, hass_ws_client)
    assert uit["speakers"] == {"label_exists": False, "entities": [], "filtered_out": 0}


async def test_situatie_2_het_label_bestaat_maar_is_leeg(
    hass: HomeAssistant, hass_ws_client
) -> None:
    """Situatie 2: het label bestaat, er hangt niets aan (SPEC 7.4).

    NIEUW GEDRAG. `filtered_out` is **0** — en dat is precies het verschil met
    situatie 3, die er verder identiek uitziet.
    """
    from homeassistant.helpers import label_registry as lr

    registreer_person(hass)
    maak_speaker(hass, features=GOEDE_FEATURES)
    await zet_integratie_op(hass)
    lr.async_get(hass).async_create("Music Assistant Wekker")

    uit = await _lijst(hass, hass_ws_client)
    assert uit["speakers"] == {"label_exists": True, "entities": [], "filtered_out": 0}


async def test_situatie_3_alles_valt_af_op_de_eisen(
    hass: HomeAssistant, hass_ws_client
) -> None:
    """Situatie 3: er hing wél iets aan het label, maar het viel af (SPEC 7.2).

    NIEUW GEDRAG, en dit is de situatie die vóór fase 4c niet te onderscheiden
    was van situatie 2. Voor de eigenaar zijn het twee heel verschillende
    boodschappen: "zet het label op je speakers" tegenover "die speakers zijn
    geen Music Assistant-speakers".

    Er hangen er twee aan het label — een Sonos-entiteit en een groep — en beide
    vallen af op een **andere** eis van SPEC 7.2, zodat de teller ook echt telt
    en niet toevallig op 1 blijft staan.
    """
    from homeassistant.helpers import entity_registry as er, label_registry as lr

    registreer_person(hass)
    sonos = maak_speaker(hass, "media_player.sonos", platform="sonos", features=GOEDE_FEATURES)
    groep = maak_speaker(
        hass, "media_player.groep", features=GOEDE_FEATURES, player_type="group"
    )
    await zet_integratie_op(hass)

    label = lr.async_get(hass).async_create("Music Assistant Wekker")
    registry = er.async_get(hass)
    registry.async_update_entity(sonos, labels={label.label_id})
    registry.async_update_entity(groep, labels={label.label_id})

    uit = await _lijst(hass, hass_ws_client)
    assert uit["speakers"] == {"label_exists": True, "entities": [], "filtered_out": 2}


async def test_de_drie_situaties_zijn_onderscheidbaar(
    hass: HomeAssistant, hass_ws_client
) -> None:
    """Verplicht geval 2: drie situaties, drie uitkomsten (SPEC 7.4).

    NIEUW GEDRAG. De drie tests hierboven toetsen elk één situatie; deze toetst
    de **eigenschap** die de editor nodig heeft, namelijk dat de drie antwoorden
    verschillen. Een implementatie die `filtered_out` altijd op 0 zet, komt door
    de eerste twee heen en faalt hier.

    Er zit een positieve controle bij: zodra er één geschikte speaker is, is er
    geen melding meer nodig en is `entities` gevuld.
    """
    from homeassistant.helpers import entity_registry as er, label_registry as lr

    registreer_person(hass)
    goed = maak_speaker(hass, "media_player.goed", features=GOEDE_FEATURES, naam="Goed")
    groep = maak_speaker(
        hass, "media_player.groep", features=GOEDE_FEATURES, player_type="group"
    )
    await zet_integratie_op(hass)
    registry = er.async_get(hass)
    labels = lr.async_get(hass)

    # 1. geen label
    situatie_1 = (await _lijst(hass, hass_ws_client))["speakers"]

    # 2. label zonder entiteiten
    label = labels.async_create("Music Assistant Wekker")
    situatie_2 = (await _lijst(hass, hass_ws_client))["speakers"]

    # 3. label met alleen entiteiten die afvallen
    registry.async_update_entity(groep, labels={label.label_id})
    situatie_3 = (await _lijst(hass, hass_ws_client))["speakers"]

    kenmerk = lambda s: (s["label_exists"], len(s["entities"]), s["filtered_out"] > 0)
    assert kenmerk(situatie_1) == (False, 0, False)
    assert kenmerk(situatie_2) == (True, 0, False)
    assert kenmerk(situatie_3) == (True, 0, True)
    assert len({kenmerk(situatie_1), kenmerk(situatie_2), kenmerk(situatie_3)}) == 3

    # Positieve controle: mét een geschikte speaker is er niets te melden.
    registry.async_update_entity(goed, labels={label.label_id})
    normaal = (await _lijst(hass, hass_ws_client))["speakers"]
    assert normaal["entities"] == [{"entity_id": goed, "name": "Goed"}]
    assert normaal["filtered_out"] == 1


async def test_de_lampenlijst_telt_ook(hass: HomeAssistant, hass_ws_client) -> None:
    """Ook bij de lampen zijn de twee lege gevallen te onderscheiden (SPEC 7.4).

    NIEUW GEDRAG. De wake-up light is optioneel en blokkeert niets, maar de
    eigenaar die zijn label op de verkeerde entiteit plakt verdient dezelfde
    uitleg als bij de speakers.
    """
    from homeassistant.helpers import entity_registry as er, label_registry as lr

    registreer_person(hass)
    speaker = maak_speaker(hass, features=GOEDE_FEATURES)
    maak_lamp(hass)
    await zet_integratie_op(hass)

    label = lr.async_get(hass).async_create("Verlichting Wekker")
    # Het lamplabel op een media_player: geen lamp, dus hij valt af.
    er.async_get(hass).async_update_entity(speaker, labels={label.label_id})

    uit = await _lijst(hass, hass_ws_client)
    assert uit["lights"] == {"label_exists": True, "entities": [], "filtered_out": 1}
