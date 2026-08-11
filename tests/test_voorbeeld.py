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

from typing import Any

import pytest

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import HomeAssistant

from custom_components.domotiapp_alarm import abonnement, voorbeeld
from custom_components.domotiapp_alarm.const import DOMAIN, VOORBEELD_MAX_MINUTEN

from .conftest import (
    PERSON_ENTITY_ID,
    Speelhuis,
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
    speelhuis = Speelhuis(hass)
    speelhuis.register()
    speelhuis.zet_volume_op(55)
    await zet_integratie_op(hass)
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
