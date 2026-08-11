"""De voorbeeldknop (SPEC 5.4 en 15.11).

Alles hier is **NIEUW GEDRAG**: `preview/start` bestaat pas in fase 4b, dus op de
code van ervoor faalt elke test met `unknown_command`. Dat is een triviale
mislukking, en daarom letten deze tests op de eigenschappen die ook bij een
latere wijziging kunnen sneuvelen:

- dat het volume **vóór** het geluid gezet wordt en er **geen oploop** achteraan
  komt (SPEC 5.4);
- dat **afmelden** het geluid stopt en het volume terugzet — dat is de reden dat
  dit een abonnement is en geen start/stop-paar;
- dat een **wekker** voorgaat op een voorbeeld.

De buitenwereld komt uit `Speelhuis`: alleen HA-services van andere integraties
worden nagebootst, niets van onze eigen code. De volgorde en de argumenten worden
uit `aanroepen` afgelezen.
"""

from __future__ import annotations

import logging

from typing import Any

import pytest

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr

from custom_components.domotiapp_alarm import abonnement, voorbeeld
from custom_components.domotiapp_alarm.const import DOMAIN, VOORBEELD_MAX_MINUTEN

from .conftest import (
    PERSON_ENTITY_ID,
    Speelhuis,
    maak_lamp,
    maak_speaker,
    registreer_person,
    zet_integratie_op,
)

GOEDE_FEATURES = int(
    MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.VOLUME_SET
)
GELUID = {
    "uri": "somafm://radio/beatblender",
    "name": "SomaFM: Beat Blender",
    "media_type": "radio",
    "image": None,
}


@pytest.fixture(autouse=True)
def _laad_de_ma_entry_uit(hass: HomeAssistant):
    """Zet de nagebootste MA-config-entry aan het eind terug op NOT_LOADED.

    Zelfde reden als in `test_afvuren.py`: zonder dit laadt HA's eigen teardown
    elke `LOADED` entry uit, en dáárvoor importeert het de **echte**
    `music_assistant`-integratie — die `music_assistant_client` nodig heeft, en
    dat pakket staat niet in `requirements-test.txt`.
    """
    from homeassistant.config_entries import ConfigEntryState

    yield
    for entry in hass.config_entries.async_entries("music_assistant"):
        entry.mock_state(hass, ConfigEntryState.NOT_LOADED)


@pytest.fixture
async def huis(hass: HomeAssistant, hass_storage: dict[str, Any]) -> Speelhuis:
    """Integratie op, één person, één geschikte speaker op volume 55 %.

    `hass_storage` staat er niet voor de inhoud maar voor de **opruiming**: zonder
    die fixture schrijft `MockConfigEntry.add_to_hass` van de nagebootste
    MA-entry met een echte vertraagde `Store`, en dan blijft er een timer hangen
    die pytest bij teardown als "Lingering timer" afkeurt.
    """
    registreer_person(hass)
    maak_speaker(hass, features=GOEDE_FEATURES)
    lamp = maak_lamp(hass)
    speelhuis = Speelhuis(hass)
    speelhuis.register()
    speelhuis.zet_volume_op(55)
    await zet_integratie_op(hass)
    # De lamp moet gelabeld zijn, anders weigert `preview/start` hem op SPEC 12 —
    # dezelfde controle als `alarms/save` doet.
    label = lr.async_get(hass).async_create("Verlichting Wekker")
    er.async_get(hass).async_update_entity(lamp, labels={label.label_id})
    return speelhuis


async def _stuur(client, payload: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(payload)
    return await client.receive_json()


def _start(volume_pct: int = 40, **overschrijf: Any) -> dict[str, Any]:
    payload = {
        "type": f"{DOMAIN}/preview/start",
        "speaker": "media_player.slaapkamer",
        "sound": GELUID,
        "volume_pct": volume_pct,
    }
    payload.update(overschrijf)
    return payload


# --- starten ------------------------------------------------------------


async def test_voorbeeld_speelt_op_het_ingestelde_volume_zonder_oploop(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """Volume eerst, dan geluid, en verder niets (SPEC 5.4).

    NIEUW GEDRAG. Twee dingen tegelijk, en het tweede is het interessante:

    1. het volume gaat **vóór** het afspelen naar het ingestelde niveau — niet
       naar 0, want dit is geen wekker en er komt geen oploop;
    2. er staat **precies één** `volume_set` in de lijst. Een implementatie die de
       oploop van het afvuren hergebruikt, zou er twintig zetten en hier falen.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(volume_pct=40))
    assert antwoord["success"], antwoord

    assert huis.namen() == ["media_player.volume_set", "music_assistant.play_media"]
    assert huis.volumes() == [40]

    _naam, data = huis.aanroepen[1]
    assert data["media_id"] == GELUID["uri"]
    # Geen radio_mode: bij een provider zonder SIMILAR_TRACKS geeft MA HTTP 500 en
    # speelt er niets, en dan lijkt de voorbeeldknop stuk terwijl het geluid deugt.
    assert "radio_mode" not in data


async def test_afmelden_stopt_het_geluid_en_zet_het_volume_terug(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """Afmelden **is** het stoppen (SPEC 15.11).

    NIEUW GEDRAG, en de kern van het ontwerp. Er is geen `preview/stop`; de
    stopknop in de editor meldt zich af, en een tabblad dat verdwijnt doet
    hetzelfde. Deze test loopt langs de echte WebSocket, dus het is HA's eigen
    opruimpad dat hier getoetst wordt en niet een functieaanroep.

    De volgorde is onderdeel van het gedrag: **eerst** `media_stop`, **dan** het
    volume terug. Andersom klinkt de laatste seconde op het oude niveau.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(volume_pct=40))
    abonnement_id = antwoord["id"]
    assert huis.volumes() == [40]

    await _stuur(client, {"type": "unsubscribe_events", "subscription": abonnement_id})
    await hass.async_block_till_done()

    assert huis.namen() == [
        "media_player.volume_set",
        "music_assistant.play_media",
        "media_player.media_stop",
        "media_player.volume_set",
    ]
    assert huis.volumes() == [40, 55], "het volume van vóór het voorbeeld hoort terug"
    assert not voorbeeld.loopt_op(hass, "media_player.slaapkamer")


async def test_het_voorbeeld_zet_shuffle_terug_bij_afmelden(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG. Bevinding 4 van fase 6b, ook voor het voorbeeld (SPEC 9.6).

    Het voorbeeld schudt sinds fase 6 mee — anders laat het iets anders horen dan
    wat er 's ochtends gebeurt. Precies daarom heeft het ook dezelfde bijwerking:
    zonder terugzetten blijft de shuffle van de klant aan staan omdat hij één keer
    op de voorbeeldknop drukte.

    Het geluid is hier een **afspeellijst** en geen radio; met de standaard
    `GELUID` zou er niets te schudden en dus niets terug te zetten zijn.
    """
    afspeellijst = {
        "uri": "library://playlist/12",
        "name": "Ochtend",
        "media_type": "playlist",
        "image": None,
    }
    huis.zet_shuffle_op(False)
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(volume_pct=40, sound=afspeellijst))
    assert antwoord["success"], antwoord
    assert huis.shuffles() == [True]

    await _stuur(
        client, {"type": "unsubscribe_events", "subscription": antwoord["id"]}
    )
    await hass.async_block_till_done()

    assert huis.shuffles() == [True, False], huis.namen()
    assert huis.shuffle_stand is False


async def test_het_voorbeeld_laat_shuffle_met_rust_bij_radio(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """REGRESSIEWACHT, en de positieve controle bij de test hierboven. Hij slaagt
    op de oude code omdat daar bij radio niets met shuffle gebeurt.

    Een implementatie die bij elk voorbeeld `shuffle_set` aanroept, komt door die
    test heen en zet hier de shuffle van de klant om terwijl er niets te schudden
    valt. Bij radio is er één stream en geen volgorde.
    """
    huis.zet_shuffle_op(True)
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(volume_pct=40))
    assert antwoord["success"], antwoord

    await _stuur(
        client, {"type": "unsubscribe_events", "subscription": antwoord["id"]}
    )
    await hass.async_block_till_done()

    assert huis.shuffles() == [], huis.namen()
    assert huis.shuffle_stand is True


async def test_een_weggevallen_verbinding_stopt_het_voorbeeld(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """Een verbinding die wegvalt stopt het geluid (SPEC 15.11).

    NIEUW GEDRAG, en dit is het geval waarvoor het abonnement bestaat: een
    tabblad dat wordt weggeklikt, een browser die crasht, een wandtablet dat zijn
    wifi verliest. Met een expliciet `preview/stop` speelt de muziek dan door op
    een speaker waarvan het volume ook nog verzet is.

    Er is geen afmelding — de verbinding gaat gewoon dicht.
    """
    client = await hass_ws_client(hass)
    await _stuur(client, _start(volume_pct=40))
    assert voorbeeld.loopt_op(hass, "media_player.slaapkamer")

    await client.close()
    await hass.async_block_till_done()

    assert not voorbeeld.loopt_op(hass, "media_player.slaapkamer")
    assert huis.namen()[-2:] == ["media_player.media_stop", "media_player.volume_set"]
    assert huis.volumes()[-1] == 55


async def test_het_maximum_stopt_het_voorbeeld(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """Na het maximum stopt het voorbeeld vanzelf (SPEC 15.11).

    NIEUW GEDRAG. De tweede rem: een abonnement leeft zolang de verbinding leeft,
    en een tabblad dat op een editor blijft staan kan dagen leven.

    Met een positieve controle ervoor: vlak vóór het maximum loopt hij nog.
    """
    import datetime as dt

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    client = await hass_ws_client(hass)
    await _stuur(client, _start())

    async_fire_time_changed(
        hass, dt_util.utcnow() + dt.timedelta(minutes=VOORBEELD_MAX_MINUTEN - 1)
    )
    await hass.async_block_till_done()
    assert voorbeeld.loopt_op(hass, "media_player.slaapkamer"), "nog niet"

    async_fire_time_changed(
        hass, dt_util.utcnow() + dt.timedelta(minutes=VOORBEELD_MAX_MINUTEN, seconds=5)
    )
    await hass.async_block_till_done()
    assert not voorbeeld.loopt_op(hass, "media_player.slaapkamer")
    assert huis.volumes()[-1] == 55


# --- weigeren -----------------------------------------------------------


async def test_onbereikbare_speaker_geeft_de_noodrem(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """De noodrem, en de editor hoort het te zeggen (SPEC 5.4, 11.1).

    NIEUW GEDRAG. Dit is precies het moment waarop de klant wil weten dat zijn
    speaker onbereikbaar is — vóór hij een wekker opslaat die er niet op afgaat.

    Er wordt **niets** aangeroepen: geen volume, geen afspelen.
    """
    huis.laat_speaker_wegvallen()

    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start())
    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "speaker_unavailable"
    assert "niet bereikbaar" in antwoord["error"]["message"]
    assert huis.namen() == []


async def test_een_afgaande_wekker_gaat_voor(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """Op een speaker waar een wekker afgaat komt geen voorbeeld (SPEC 15.11).

    NIEUW GEDRAG. Het voorbeeld zou de queue overnemen en bij het stoppen het
    volume terugzetten naar wat de oploop op dat moment toevallig had gezet —
    waarna de wekker zachtjes of helemaal niet verder speelt. De wekker is het
    product.

    Positieve controle: zodra de wekker uit het register is, lukt het wél.
    """
    from custom_components.domotiapp_alarm import afvuren

    registry_id = registreer_person(hass)
    register = abonnement.register_van(hass)
    register.actief[(registry_id, "abc")] = {
        afvuren.CTX_SPEAKER: "media_player.slaapkamer",
        afvuren.CTX_PERSON: PERSON_ENTITY_ID,
    }

    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start())
    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "not_allowed"
    assert "wekker" in antwoord["error"]["message"]
    assert huis.namen() == []

    register.actief.clear()
    antwoord = await _stuur(client, _start())
    assert antwoord["success"], antwoord


async def test_speaker_die_niet_aan_de_eisen_voldoet(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """Dezelfde controle als `alarms/save` (SPEC 7.2).

    NIEUW GEDRAG. De editor stuurt hier een keuze heen die nog niet is opgeslagen
    en dus nog niet is gekeurd; zonder deze controle kan een voorbeeld op een
    speaker die nooit een wekker zou mogen dragen.
    """
    maak_speaker(hass, "media_player.sonos", platform="sonos", features=GOEDE_FEATURES)

    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(speaker="media_player.sonos"))
    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "not_allowed"
    assert huis.namen() == []


async def test_mislukt_afspelen_zet_het_volume_terug(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """Faalt het afspelen, dan hoort het volume terug (SPEC 5.4).

    NIEUW GEDRAG. Het volume is op dat moment al verzet, dus zonder deze regel
    blijft de speaker op het voorbeeldniveau staan na een poging waarin niets
    heeft geklonken — een bijwerking van iets dat niet is gebeurd.
    """
    huis.faal.add("music_assistant.play_media")

    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(volume_pct=40))
    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "sound_gone"

    assert huis.volumes() == [40, 55], "het oude volume hoort terug"
    assert not voorbeeld.loopt_op(hass, "media_player.slaapkamer")


async def test_zonder_uri_wordt_geweigerd(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG. Zonder `uri` valt er niets af te spelen (SPEC 15.11)."""
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(sound={"name": "iets"}))
    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "invalid_format"
    assert huis.namen() == []


async def test_volume_buiten_bereik_wordt_geweigerd(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG. Zelfde grenzen als de opslag: 1 t/m 100 (SPEC 14.2)."""
    client = await hass_ws_client(hass)
    for pct in (0, 101):
        antwoord = await _stuur(client, _start(volume_pct=pct))
        assert not antwoord["success"], pct
        assert antwoord["error"]["code"] == "invalid_format"


async def test_tweede_voorbeeld_vervangt_het_eerste(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """MA heeft één queue per player, dus naast elkaar bestaan ze niet (SPEC 15.11).

    NIEUW GEDRAG. Het eerste voorbeeld wordt netjes gestopt — inclusief het
    terugzetten van het volume — vóór het tweede begint. Zonder dat zou het
    tweede voorbeeld het volume van het **eerste** onthouden als "het volume van
    vóór", en dan komt de speaker na afloop op 40 uit in plaats van op 55.
    """
    client = await hass_ws_client(hass)
    await _stuur(client, _start(volume_pct=40))
    antwoord = await _stuur(client, _start(volume_pct=30))
    assert antwoord["success"], antwoord

    assert huis.namen() == [
        "media_player.volume_set",
        "music_assistant.play_media",
        "media_player.media_stop",
        "media_player.volume_set",
        "media_player.volume_set",
        "music_assistant.play_media",
    ]
    assert huis.volumes() == [40, 55, 30]

    await _stuur(client, {"type": "unsubscribe_events", "subscription": antwoord["id"]})
    await hass.async_block_till_done()
    assert huis.volumes()[-1] == 55, "en na afloop staat hij weer op 55, niet op 40"


async def test_niet_admin_mag_een_voorbeeld_spelen(
    hass: HomeAssistant, hass_ws_client, hass_read_only_access_token, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG. Geen enkel commando is admin-only (SPEC 17)."""
    client = await hass_ws_client(hass, hass_read_only_access_token)
    antwoord = await _stuur(client, _start())
    assert antwoord["success"], antwoord


# --- de wake-up light in het voorbeeld (SPEC 5.4 en 12, fase 8) ---------

LAMP = {"entity_id": "light.bedlamp", "brightness_pct": 80}


def _lampstand(huis: Speelhuis) -> list[dict[str, Any]]:
    """Alle lamp-aanroepen, in volgorde, met alleen wat er toe doet."""
    return [
        {"dienst": naam.split(".")[1], **{s: w for s, w in data.items() if s != "entity_id"}}
        for naam, data in huis.aanroepen
        if naam.startswith("light.")
    ]


async def test_het_voorbeeld_zet_de_lamp_aan_op_de_ingestelde_helderheid(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG. Bevinding 2 van fase 8, verplicht geval 1.

    Wie 100 % helderheid instelt wil zien of dat niet te fel is, net zoals hij het
    volume wil horen. Een voorbeeld dat de helft van de wekker weglaat, is geen
    voorbeeld.

    De assertie staat op de **helderheid** en niet alleen op "er is een lamp
    aangeraakt": een implementatie die `light.turn_on` zonder `brightness_pct`
    stuurt, laat de lamp op zijn vorige stand staan en toont dus juist niet wat de
    klant wilde beoordelen.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(volume_pct=40, light=LAMP))
    assert antwoord["success"], antwoord

    assert _lampstand(huis) == [{"dienst": "turn_on", "brightness_pct": 80}]


async def test_de_lamp_gaat_na_het_geluid_aan(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG, en het is een keuze die uitgelegd hoort te worden.

    Bij een wekker gaat de lamp **vóór** het geluid (SPEC 9.1 stap 4), omdat
    `play_media` daar 2,1-2,6 s blokkeert en de lamp niet mag wachten op iets dat
    kan mislukken. Bij een voorbeeld ligt het andersom: mislukt het afspelen, dan
    wordt het voorbeeld geweigerd, en dan hoort er geen lamp te hebben geflitst die
    we meteen weer uitzetten.

    Zie `test_een_mislukt_voorbeeld_laat_de_lamp_met_rust` voor de andere helft.
    """
    client = await hass_ws_client(hass)
    await _stuur(client, _start(volume_pct=40, light=LAMP))

    namen = huis.namen()
    assert namen.index("music_assistant.play_media") < namen.index("light.turn_on"), namen


async def test_stoppen_zet_de_lamp_terug_zoals_hij_stond(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG. Verplicht geval 2.

    Dit is het verschil met een echte wekker, en het is bewust: SPEC 12 laat de
    lamp na een wekker **aan** staan, want dan word je wakker. Bij een voorbeeld
    wil je je kamer niet op vol licht achterlaten omdat je even iets uitprobeerde —
    dezelfde redenering als het volume in SPEC 9.5.

    De lamp stond **uit**, dus hij hoort uit te gaan. Niet "aan op 1 %", niet "aan
    op de vorige helderheid van een andere lamp": uit.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(volume_pct=40, light=LAMP))
    abonnement_id = antwoord["id"]

    await _stuur(client, {"type": "unsubscribe_events", "subscription": abonnement_id})
    await hass.async_block_till_done()

    assert _lampstand(huis) == [
        {"dienst": "turn_on", "brightness_pct": 80},
        {"dienst": "turn_off"},
    ]


async def test_een_lamp_die_aan_stond_gaat_terug_naar_zijn_helderheid(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG, en de positieve controle bij de test hierboven.

    Een implementatie die bij het stoppen altijd `turn_off` doet, komt door die
    test heen en zet hier het licht uit dat de klant zelf aan had staan. Dat is
    precies de bijwerking die we wilden wegnemen, alleen dan andersom.

    `brightness` is de 0-255-schaal van Home Assistant; die gaat er letterlijk weer
    in. Omrekenen naar procenten en terug zou afronden, en dan komt de lamp niet
    terug op de stand die hij had.
    """
    hass.states.async_set("light.bedlamp", "on", {"friendly_name": "Bedlamp", "brightness": 120})
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(volume_pct=40, light=LAMP))

    await _stuur(client, {"type": "unsubscribe_events", "subscription": antwoord["id"]})
    await hass.async_block_till_done()

    assert _lampstand(huis) == [
        {"dienst": "turn_on", "brightness_pct": 80},
        {"dienst": "turn_on", "brightness": 120},
    ]


async def test_een_onleesbare_lampstand_wordt_niet_teruggezet(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis, caplog
) -> None:
    """NIEUW GEDRAG. Verplicht geval 2, tweede helft: nooit een verzonnen waarde.

    Een lamp die `unavailable` is heeft geen leesbare stand — en valkuil 18 zegt
    waarom dat juist op dit moment gebeurt: extra state attributes verdwijnen zodra
    een entiteit wegvalt. `turn_off` sturen zou een keuze maken die we niet kennen.

    Het **aanzetten** gaat wel gewoon door: dat is wat de klant vroeg, en of het
    lukt merkt hij vanzelf.
    """
    hass.states.async_set("light.bedlamp", "unavailable", {"friendly_name": "Bedlamp"})
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(volume_pct=40, light=LAMP))

    with caplog.at_level(logging.WARNING, logger="custom_components.domotiapp_alarm.voorbeeld"):
        await _stuur(client, {"type": "unsubscribe_events", "subscription": antwoord["id"]})
        await hass.async_block_till_done()

    assert _lampstand(huis) == [{"dienst": "turn_on", "brightness_pct": 80}]
    # En er staat geen WAARSCHUWING over een mislukt terugzetten. "Ik weet zijn oude
    # stand niet" is geen fout maar de normale uitkomst bij een weggevallen lamp;
    # een waarschuwing zou beweren dat er iets misging (SPEC 11.7's regel, hier in
    # een logregel). Gevonden in de mutatieproef van fase 8 (M4): zonder deze
    # assertie loopt het terugzetten via een exceptie en merkt geen test dat.
    assert "terugzetten is mislukt" not in caplog.text, caplog.text


async def test_een_voorbeeld_zonder_lamp_raakt_geen_enkele_lamp_aan(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """REGRESSIEWACHT. Verplicht geval 3.

    Hij slaagt op de code van vóór fase 8, en dat is narekenbaar: daar deed het
    voorbeeld sowieso niets met een lamp. Zijn waarde ligt aan de andere kant —
    tegen een implementatie die een lamp verzint, of die de lamp van de vorige
    wekker uit de opslag pakt. De klant heeft er geen gekozen, dus er hoort er geen
    aan te gaan.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(volume_pct=40))
    assert antwoord["success"], antwoord

    await _stuur(client, {"type": "unsubscribe_events", "subscription": antwoord["id"]})
    await hass.async_block_till_done()

    assert _lampstand(huis) == []


async def test_een_falende_lamp_laat_het_geluid_gewoon_spelen(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG. Verplicht geval 4, en het is SPEC 12 in het klein.

    Het geluid is het voorbeeld, net zoals het geluid de wekker is. Een lamp die
    weigert mag het voorbeeld niet afbreken — dan zou een kapotte lamp de klant
    beletten zijn geluid te beoordelen.

    De eerste assertie vermijdt "de setup faalt niet": zonder die regel slaagt deze
    test ook op een implementatie die de lamp helemaal niet aanraakt.
    """
    huis.faal.add("light.turn_on")
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(volume_pct=40, light=LAMP))

    assert antwoord["success"], antwoord
    assert "light.turn_on" in huis.namen(), "er is niets misgegaan om op te toetsen"
    assert "music_assistant.play_media" in huis.namen()
    assert voorbeeld.loopt_op(hass, "media_player.slaapkamer")


async def test_een_mislukt_voorbeeld_laat_de_lamp_met_rust(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """REGRESSIEWACHT — hij slaagt op de code van vóór fase 8, en dat is
    narekenbaar: daar wordt sowieso geen lamp aangeraakt. Zijn waarde ligt aan de
    andere kant, tegen een implementatie die de lamp vóór het geluid zet en hem
    daarna vergeet terug te draaien.

    De keerzijde van "de lamp gaat ná het geluid aan".

    Faalt `play_media`, dan wordt het voorbeeld geweigerd en is er niets gebeurd
    dat teruggedraaid moet worden. Er hoort dan ook geen lamp te hebben geflitst.
    """
    huis.faal.add("music_assistant.play_media")
    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(volume_pct=40, light=LAMP))

    assert not antwoord["success"]
    assert _lampstand(huis) == []


async def test_een_weggevallen_verbinding_zet_de_lamp_ook_terug(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG. Verplicht geval 5, en het geval dat de kaart niet kan afvangen.

    Een tabblad dat wordt weggeklikt, een browser die crasht, een wandtablet dat
    zijn wifi verliest: SPEC 5.4 eist dat élke manier van sluiten het voorbeeld
    stopt, en fase 4b heeft dat opgelost door het voorbeeld een **abonnement** te
    maken. De lamp hangt aan diezelfde opruiming, en deze test bewijst dat door de
    verbinding echt te laten wegvallen in plaats van netjes af te melden.
    """
    client = await hass_ws_client(hass)
    await _stuur(client, _start(volume_pct=40, light=LAMP))
    assert voorbeeld.loopt_op(hass, "media_player.slaapkamer")

    await client.close()
    await hass.async_block_till_done()

    assert _lampstand(huis) == [
        {"dienst": "turn_on", "brightness_pct": 80},
        {"dienst": "turn_off"},
    ]
    assert not voorbeeld.loopt_op(hass, "media_player.slaapkamer")


async def test_het_maximum_zet_de_lamp_ook_terug(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG. Verplicht geval 5, langs de derde route.

    Er zijn drie manieren waarop een voorbeeld eindigt: afmelden, een tweede
    voorbeeld op dezelfde speaker, en de maximumtimer. Alle drie lopen door
    `async_stop`, en dat is precies waarom het terugzetten daar staat en niet in de
    afmeldcallback.
    """
    import datetime as dt

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    client = await hass_ws_client(hass)
    await _stuur(client, _start(volume_pct=40, light=LAMP))

    async_fire_time_changed(
        hass, dt_util.utcnow() + dt.timedelta(minutes=VOORBEELD_MAX_MINUTEN, seconds=5)
    )
    await hass.async_block_till_done()

    assert _lampstand(huis)[-1] == {"dienst": "turn_off"}
    assert not voorbeeld.loopt_op(hass, "media_player.slaapkamer")


async def test_een_lamp_zonder_label_wordt_geweigerd(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG. Dezelfde keuring als `alarms/save` (SPEC 12).

    De editor stuurt hier een keuze heen die nog niet is opgeslagen en dus nog niet
    gekeurd is. Zonder deze controle kan iemand langs de API elke lamp in huis laten
    aanfloepen — en dan is het voorbeeld een afstandsbediening voor het hele huis
    in plaats van voor de wekker.
    """
    maak_lamp(hass, "light.woonkamer", "Woonkamer")
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        _start(volume_pct=40, light={"entity_id": "light.woonkamer", "brightness_pct": 80}),
    )

    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "not_allowed"
    assert _lampstand(huis) == []


async def test_een_helderheid_buiten_bereik_wordt_geweigerd(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG. `invalid_format`, en niet stil doorgeven aan `light.turn_on`.

    Hetzelfde als bij `alarms/save` (SPEC 15.2): de vorm wordt server-side gekeurd,
    door **dezelfde** functie, zodat het voorbeeld en het opslaan niet uiteen kunnen
    lopen over wat een geldige lamp is.
    """
    client = await hass_ws_client(hass)
    antwoord = await _stuur(
        client,
        _start(volume_pct=40, light={"entity_id": "light.bedlamp", "brightness_pct": 250}),
    )

    assert not antwoord["success"]
    assert antwoord["error"]["code"] == "invalid_format"
    # En de fout gaat over de **helderheid**, niet over "onbekend veld". Zonder deze
    # regel slaagt de test ook op de code van vóór fase 8, waar `light` gewoon een
    # onbekende sleutel was — een andere fout om een andere reden.
    assert "brightness_pct" in antwoord["error"]["message"], antwoord["error"]
    assert _lampstand(huis) == []


async def test_een_helderheid_die_geen_getal_is_telt_als_onbekend(
    hass: HomeAssistant, hass_ws_client, huis: Speelhuis
) -> None:
    """NIEUW GEDRAG. Een verdediging tegen data van een ánder, niet tegen onszelf.

    `brightness` is een attribuut van een `light` die niet van ons is. HA typeert
    hem als `int | None`, maar de statemachine dwingt niets af en een integratie die
    er `"128"` in zet houdt niemand tegen. Zonder de `isinstance`-controle gaat die
    string zo door naar `light.turn_on`.

    Gevonden in de mutatieproef van fase 8 (M13), en het is dezelfde soort als
    valkuil 59: alle tests gebruiken ons eigen testdubbel, en dat gedraagt zich
    netjes.
    """
    hass.states.async_set(
        "light.bedlamp", "on", {"friendly_name": "Bedlamp", "brightness": "128"}
    )
    assert voorbeeld.lampstand_van(hass, "light.bedlamp") == {"aan": True, "brightness": None}

    client = await hass_ws_client(hass)
    antwoord = await _stuur(client, _start(volume_pct=40, light=LAMP))
    await _stuur(client, {"type": "unsubscribe_events", "subscription": antwoord["id"]})
    await hass.async_block_till_done()

    # Aan blijft aan, maar zonder een helderheid die we niet kunnen lezen.
    assert _lampstand(huis) == [
        {"dienst": "turn_on", "brightness_pct": 80},
        {"dienst": "turn_on"},
    ]
