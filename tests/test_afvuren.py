"""Het afvuren (SPEC 9, 11 en 12). Alles NIEUW GEDRAG.

Er was in fase 3b **niets** dat afspeelde: `afvuren.py` deed alleen de boekhouding.
Elke test hier legt dus nieuw gedrag vast; er valt niets te bewaken wat er al was.

**Wat er gemockt wordt en wat niet.** Alleen de vier HA-services van andere
integraties (`music_assistant.play_media`, `media_player.volume_set`,
`media_player.media_stop`, `light.turn_on`) — de grens van dit product.
`music_assistant.search` staat er nog steeds tussen, maar hoort in het **afvuurpad**
niet meer aangeroepen te worden: dat is sinds fase 3c-bis een assertie in plaats van een
verwachting. Van onze eigen code wordt niets vervangen: de volgorde, de clamping, de
`radio_mode`-terugval en het terugzetten van het volume worden allemaal afgelezen uit
één lijst met werkelijke aanroepen in werkelijke volgorde (`Speelhuis.aanroepen`).

**Waarom `async_call_later` en niet `asyncio.sleep` in de implementatie**: alleen dan
is de oploop met `async_fire_time_changed` vooruit te zetten en kost een test van 20
stappen geen 20 seconden. Fase 0b heeft laten zien wat er gebeurt als je een oploop
alleen op totaalduur meet: je meldt een vloeiende oploop die in werkelijkheid uit tien
sprongen bestond (valkuil 31).
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.domotiapp_alarm import afvuren, meldingen, abonnement
from custom_components.domotiapp_alarm.const import (
    DATA_STORE,
    DOMAIN,
    NOODREM_NA_SECONDEN,
    OPLOOP_STAP_SECONDEN,
    STOP_NA_MINUTEN,
    STORAGE_KEY,
)

from .conftest import (
    PERSON_ENTITY_ID,
    Speelhuis,
    geldige_wekker,
    maak_lamp,
    maak_speaker,
    registreer_person,
)

AMS = ZoneInfo("Europe/Amsterdam")
ALARM_ID = "a" * 32
URI = "somafm://radio/beatblender"
GOEDE_FEATURES = int(
    MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.VOLUME_SET
)
MOMENT = dt.datetime(2026, 8, 10, 6, 45, tzinfo=AMS)


@pytest.fixture(autouse=True)
def _laad_de_ma_entry_uit(hass: HomeAssistant):
    """Zet de nagebootste MA-config-entry aan het eind terug op NOT_LOADED.

    Zonder dit laadt HA's eigen teardown elke `LOADED` entry uit, en dáárvoor
    importeert het de **echte** `music_assistant`-integratie — die
    `music_assistant_client` nodig heeft, en dat pakket staat niet in
    `requirements-test.txt` (en hoort daar ook niet: dan zouden onze tests de
    binnenkant van een andere integratie meeslepen, precies wat SPEC 11.2 afwijst).

    De entry moet tijdens de test wél `LOADED` zijn: `noodrem.controleer_speaker`
    onderscheidt "speaker weg" van "MA weg" op `async_loaded_entries`.
    """
    yield
    for entry in hass.config_entries.async_entries("music_assistant"):
        entry.mock_state(hass, ConfigEntryState.NOT_LOADED)


def volledige_wekker(**overschrijf: Any) -> dict[str, Any]:
    wekker: dict[str, Any] = {
        **geldige_wekker(),
        "id": ALARM_ID,
        "skip_next": False,
        "one_shot_at": None,
        "last_fired": None,
        "last_message": None,
    }
    wekker.update(overschrijf)
    return wekker


async def zet_op(
    hass: HomeAssistant,
    hass_storage: dict,
    wekker: dict[str, Any] | None = None,
    *,
    beschikbaar: bool = True,
) -> tuple[str, Speelhuis]:
    """De integratie plus een nagebootste speaker en de vier services."""
    await hass.config.async_update(time_zone="Europe/Amsterdam")
    registry_id = registreer_person(hass)
    maak_speaker(hass, features=GOEDE_FEATURES, beschikbaar=beschikbaar)
    maak_lamp(hass)

    huis = Speelhuis(hass)
    huis.register()
    huis.vind(URI)
    if beschikbaar:
        # Een echte speaker meldt zijn volume; 50 % is de stand "van gisteravond".
        huis.zet_volume_op(50)
    else:
        huis.volume_niveau = None

    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": {"persons": {registry_id: {"alarms": [wekker or volledige_wekker()]}}},
    }
    assert await async_setup_component(hass, "frontend", {})
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="DomotiApp Alarm", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # De inhaalslag bij setup mag deze tests niet in de weg zitten. De klok staat hier
    # op de echte tijd, dus de 06:45 van vandaag is doorgaans al lang verstreken en de
    # inhaalslag slaat hem over met een mededeling `skipped_grace_window`. Dat is
    # correct gedrag van fase 3b, maar het zou hier elke `last_message`-assertie
    # vervuilen. De beginstand wordt daarom expliciet teruggezet naar "er is nog niets
    # gebeurd" — niet door de inhaalslag uit te zetten, maar door zijn spoor te wissen.
    store = hass.data[DOMAIN][DATA_STORE]
    await store.async_werk_velden_bij(
        registry_id, ALARM_ID, {"last_fired": None, "last_message": None}
    )
    huis.aanroepen.clear()
    abonnement.register_van(hass).actief.clear()
    return registry_id, huis


async def vuur(
    hass: HomeAssistant,
    registry_id: str,
    wekker: dict[str, Any] | None = None,
    moment: dt.datetime = MOMENT,
) -> None:
    """Laat de wekker afgaan, rechtstreeks — de planner is fase 3b en is af."""
    store = hass.data[DOMAIN][DATA_STORE]
    echte = wekker or store.wekker(registry_id, ALARM_ID)
    await afvuren.async_laat_afgaan(hass, registry_id, PERSON_ENTITY_ID, echte, moment)
    await hass.async_block_till_done()


async def tik(hass: HomeAssistant, seconden: float) -> None:
    """Zet HA's klok `seconden` vooruit en laat de `async_call_later`s afgaan."""
    async_fire_time_changed(hass, dt.datetime.now(dt.UTC) + dt.timedelta(seconds=seconden))
    await hass.async_block_till_done()


async def draai_oploop_af(hass: HomeAssistant, stappen: int = 21) -> None:
    """Laat de oploop tikken. Eén tik per stap; `async_call_later` herplant zichzelf."""
    for i in range(1, stappen + 1):
        await tik(hass, OPLOOP_STAP_SECONDEN * i + 0.1)


def bericht(hass: HomeAssistant, registry_id: str) -> dict[str, Any] | None:
    return hass.data[DOMAIN][DATA_STORE].wekker(registry_id, ALARM_ID)["last_message"]


# =======================================================================
# 1. De volgorde (SPEC 9.1)
# =======================================================================



def _ringing(gebeurtenissen: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Alleen de afgaan-gebeurtenissen, zonder `changed`.

    Sinds fase 4b stuurt de **opslaglaag** een `changed`-bericht na elke
    geslaagde schrijfronde (SPEC 15.9), en het afvuren schrijft twee keer:
    `last_fired` vooraf en bij een mislukking `last_message`. Die berichten
    horen daar te zijn — dat is precies het gat dat fase 4a vond — maar deze
    tests gaan over het afgaan zelf. Dat `changed` er óók uitgaat, is het
    onderwerp van `test_abonnement.py`.
    """
    return [g for g in gebeurtenissen if g["event"] != abonnement.EVENT_CHANGED]



async def test_de_acht_stappen_gebeuren_in_de_voorgeschreven_volgorde(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Verplicht geval 1, en de belangrijkste test van deze fase.

    De volgorde is niet cosmetisch. **Volume op 0 vóór het geluid** is het verschil
    tussen wakker worden en wakker schrikken: andersom knalt de wekker één keer hard
    op de stand van gisteravond voordat de oploop begint.

    De assertie is daarom niet "0 komt voor in de lijst" maar de **index**: de
    volume_set(0) staat vóór de play_media.
    """
    registry_id, huis = await zet_op(
        hass, hass_storage, volledige_wekker(light={"entity_id": "light.bedlamp", "brightness_pct": 60})
    )

    await vuur(hass, registry_id)

    namen = huis.namen()
    # stap 3 (volume 0), 4 (lamp), 5 (geluid) — in deze orde. Stap 1 (de noodrem) is
    # sinds fase 3c-bis alleen nog een `hass.states.get` en levert dus geen aanroep op;
    # dat er géén `music_assistant.search` meer tussen staat is precies de wijziging, en
    # heeft zijn eigen test (`test_er_wordt_geen_uri_controle_meer_gedaan`).
    assert namen[:3] == [
        "media_player.volume_set",
        "light.turn_on",
        "music_assistant.play_media",
    ], namen

    # Het volume dat als eerste gezet werd, was 0.
    assert huis.volumes()[0] == 0

    # En dat is aantoonbaar vóór het geluid gebeurd, niet erna.
    assert namen.index("media_player.volume_set") < namen.index("music_assistant.play_media")


async def test_het_volume_wordt_gelezen_voordat_het_op_nul_gaat(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. SPEC 9.5: het volume wordt vóór stap 3 gelezen.

    Erna lezen zou altijd 0 opleveren, en dan zou het terugzetten bij het stoppen de
    speaker op stil achterlaten — een bijwerking die de klant nooit heeft gevraagd en
    die niemand zou opmerken tot hij 's avonds muziek wil.
    """
    registry_id, huis = await zet_op(hass, hass_storage)

    await vuur(hass, registry_id)

    context = abonnement.register_van(hass).actief[(registry_id, ALARM_ID)]
    assert context[afvuren.CTX_VOLUME_VOOR] == 50


async def test_de_stoptimer_en_de_tweede_noodrem_worden_gezet(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Stap 7 en 8 bestaan als afzegbare timer, niet als losse taak.

    Zonder de unsub in de context zou stoppen ze niet kunnen afbreken en zou de
    stoptimer 30 minuten later een wekker "stoppen" die al uit stond.
    """
    registry_id, _ = await zet_op(hass, hass_storage)

    await vuur(hass, registry_id)

    context = abonnement.register_van(hass).actief[(registry_id, ALARM_ID)]
    assert context[afvuren.CTX_UNSUB_NOODREM] is not None
    assert context[afvuren.CTX_UNSUB_STOP] is not None
    assert context[afvuren.CTX_OPLOOP] is not None


# =======================================================================
# 2. De noodrem vooraf (SPEC 11.1), en dat er GEEN URI-controle meer is
# =======================================================================


async def test_een_onbereikbare_speaker_laat_de_wekker_niet_afgaan(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Verplicht geval 2.

    Drie eisen in één test, en de derde is de scherpste: **geen enkele
    service-aanroep** naar die speaker. Vertrouwen op HA's service-dispatch zou hier
    stil falen — HA filtert onbeschikbare entiteiten weg zonder exceptie, en bij
    targeting op een label komt er zelfs geen logregel (gemeten in fase 0: nul
    waarschuwingen). Dit is de stilste faalmodus in het product.
    """
    registry_id, huis = await zet_op(hass, hass_storage, beschikbaar=False)

    await vuur(hass, registry_id)

    assert huis.aanroepen == []
    assert not abonnement.register_van(hass).is_afgaand(registry_id, ALARM_ID)

    melding = bericht(hass, registry_id)
    assert melding["kind"] == meldingen.KIND_SPEAKER_UNAVAILABLE
    assert melding["severity"] == "error"
    assert "niet bereikbaar" in melding["text"]


async def test_een_mislukte_wekker_stuurt_het_failed_event(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG (SPEC 15.9), en deze test bestaat door een mutatietest (A37).

    Het `failed`-event uit `_async_faal` was niet gedekt: de tests op de noodrem keken
    naar `last_message`, en de enige test die wél een `failed`-event verwachtte was die
    over de weggevallen speaker — en die gaat door een **ander** stuk code
    (`_maak_noodrem_achteraf` stuurt zijn eigen event). Het gat zat dus in de tests, en
    het zou betekenen dat een open kaart een mislukte wekker pas na een herlaadactie
    ziet.

    De `reason` is de machineleesbare `kind` en de `text` is de Nederlandse tekst die
    ook in de opslag staat, zodat de kaart hem kan tonen zonder hem zelf samen te
    stellen (SPEC 14.2.1).
    """
    registry_id, _ = await zet_op(hass, hass_storage, beschikbaar=False)
    gebeurtenissen: list[dict[str, Any]] = []
    abonnement.register_van(hass).abonneer(gebeurtenissen.append)

    await vuur(hass, registry_id)

    assert len(_ringing(gebeurtenissen)) == 1
    gebeurtenis = _ringing(gebeurtenissen)[0]
    assert gebeurtenis["event"] == abonnement.EVENT_FAILED
    assert gebeurtenis["person"] == PERSON_ENTITY_ID
    assert gebeurtenis["alarm_id"] == ALARM_ID
    assert gebeurtenis["reason"] == meldingen.KIND_SPEAKER_UNAVAILABLE
    assert gebeurtenis["text"] == bericht(hass, registry_id)["text"]


async def test_een_geslaagde_wekker_stuurt_geen_failed_event(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG, en de positieve controle bij de test hierboven.

    Zonder deze zou "er komt een `failed`-event" ook waar kunnen zijn omdat er altijd
    één komt, en dan zou de kaart bij elke gewone wekker een storing tonen.
    """
    registry_id, _ = await zet_op(hass, hass_storage)
    gebeurtenissen: list[dict[str, Any]] = []
    abonnement.register_van(hass).abonneer(gebeurtenissen.append)

    await vuur(hass, registry_id)

    assert [g["event"] for g in _ringing(gebeurtenissen)] == [abonnement.EVENT_STARTED]


async def test_zonder_music_assistant_meldt_de_wekker_dat_en_niet_de_speaker(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. `available` kan de twee storingen niet scheiden, de entry wel.

    SPEC 11.1: MA's `available` is `player.available and connection.connected`, dus
    een dode speaker én een dode server komen op dezelfde plek uit. Voor de klant is
    dat verschil juist het enige dat telt: "zet je speaker aan" tegen "je server ligt
    eruit". Het onderscheid gaat op de geladen config-entry.
    """
    registry_id, huis = await zet_op(hass, hass_storage, beschikbaar=False)
    # Op NOT_LOADED en niet verwijderd: `async_loaded_entries` geeft alleen geladen
    # entries terug, dus dit is precies "MA ligt eruit". Verwijderen zou HA de echte
    # integratie laten importeren, en die is er in een test niet.
    for entry in hass.config_entries.async_entries("music_assistant"):
        entry.mock_state(hass, ConfigEntryState.NOT_LOADED)

    await vuur(hass, registry_id)

    assert bericht(hass, registry_id)["kind"] == meldingen.KIND_MA_UNAVAILABLE
    assert "Music Assistant" in bericht(hass, registry_id)["text"]


async def test_er_wordt_geen_uri_controle_meer_gedaan(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG (SPEC 11.2, fase 3c-bis). Verplicht geval van taak B.

    Hier stonden drie tests die de URI-controle toetsten. Die controle is vervallen omdat
    ze vals alarm sloeg voor een hele provider, dus ze zijn **vervangen** in plaats van
    weggehaald: wat nu vastligt is dat er **géén** `music_assistant.search` in het
    afvuurpad zit.

    Waarom dat een test verdient en geen simpele verwijdering: de aanroep terugzetten is
    één regel, en het zou opnieuw dezelfde stille storing opleveren. Deze test faalt op de
    code van vóór 3c-bis — daar stond `search` op de eerste plaats in `namen[:4]`.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    # Laat de nagebootste zoekopdracht bewust NIETS vinden. Vóór 3c-bis was dat genoeg
    # om de wekker tegen te houden; nu mag het niets uitmaken, want er wordt niet gezocht.
    huis.zoekresultaat = {}

    await vuur(hass, registry_id)

    assert "music_assistant.search" not in huis.namen()
    assert "music_assistant.play_media" in huis.namen()
    assert abonnement.register_van(hass).is_afgaand(registry_id, ALARM_ID)
    assert bericht(hass, registry_id) is None


async def test_een_somafm_wekker_gaat_af(hass: HomeAssistant, hass_storage: dict) -> None:
    """NIEUW GEDRAG. Dit is precies het geval dat taak I van fase 3c liet mislukken.

    De opgeslagen naam is `"SomaFM: Beat Blender"` — de naam die MA zelf teruggaf — en
    die is in MA's zoekindex **niet** te vinden. Vóór 3c-bis concludeerde de URI-controle
    daaruit dat het geluid niet meer bestond en ging de wekker niet af:

        23:23:00.245 WARNING [afvuren] gaat NIET af:
                     het geluid 'somafm://radio/beatblender' bestaat niet meer

    De opzet van deze test bootst dat na: de zoekopdracht vindt het geluid **niet**, maar
    de wekker gaat wél af. Dat is de hele wijziging van deze ronde, in één test.
    """
    wekker = volledige_wekker(
        sound={
            "uri": "somafm://radio/beatblender",
            "name": "SomaFM: Beat Blender",
            "media_type": "radio",
            "image": None,
        }
    )
    registry_id, huis = await zet_op(hass, hass_storage, wekker)
    # Zoals MA het werkelijk doet: zoeken op "SomaFM: Beat Blender" geeft nul treffers.
    huis.zoekresultaat = {}

    await vuur(hass, registry_id)

    data = dict(huis.aanroepen)["music_assistant.play_media"]
    assert data["media_id"] == "somafm://radio/beatblender"
    assert abonnement.register_van(hass).is_afgaand(registry_id, ALARM_ID)
    assert bericht(hass, registry_id) is None


async def test_een_traag_antwoord_van_ma_houdt_de_wekker_niet_meer_op(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG, en dit was de reden dat SPEC 11.2.1 bestond.

    Vóór 3c-bis moest de code onderscheiden tussen "de URI bestaat niet" (niet afgaan) en
    "de controle kon niet worden uitgevoerd" (wél afgaan). Dat was het subtielste
    onderscheid in het product, met een `Uitkomst`-enum van drie waarden om het te dragen.

    Nu is er geen controle die kan mislukken, dus kan een falende of trage zoekopdracht de
    wekker per constructie niet meer ophouden. Deze test legt dat vast door de zoekopdracht
    te laten ontploffen: dat mag geen enkel effect hebben.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    huis.zoekfout = TimeoutError()

    await vuur(hass, registry_id)

    assert "music_assistant.search" not in huis.namen()
    assert abonnement.register_van(hass).is_afgaand(registry_id, ALARM_ID)
    assert bericht(hass, registry_id) is None


async def test_een_mislukt_afspelen_meldt_het_geluid_en_niet_de_speaker(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. De melding `sound_gone` wordt nu door `play_media` gestuurd.

    Vóór 3c-bis stuurde de URI-controle deze soort, en een mislukt `play_media` meldde
    `speaker_unavailable`. Dat laatste was al twijfelachtig en is nu onwaar: de speaker is
    een paar milliseconden eerder nog beschikbaar bevonden (stap 1). Wat er dan overblijft
    is het geluid.

    Het is bovendien een **sterker** signaal dan de zoekopdracht ooit was: de aanroep die
    het geluid werkelijk zou starten heeft geweigerd.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    huis.faal.add("music_assistant.play_media")

    await vuur(hass, registry_id)

    melding = bericht(hass, registry_id)
    assert melding["kind"] == meldingen.KIND_SOUND_GONE
    assert melding["severity"] == "error"
    assert "SomaFM: Beat Blender" in melding["text"]
    assert not abonnement.register_van(hass).is_afgaand(registry_id, ALARM_ID)


# =======================================================================
# 5. De noodrem achteraf (SPEC 11.3)
# =======================================================================


async def test_een_speaker_die_wegvalt_na_het_starten_wordt_gemeld(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Verplicht geval 5.

    Dit is het geval waarin de aanroep sláágde en er tóch geen geluid is. De tekst is
    met opzet anders: "mogelijk niet hoorbaar geweest" en niet "is niet afgegaan",
    want de wekker is wél gestart en misschien heeft de klant de eerste seconden nog
    gehoord.

    Het is ook het net onder SPEC 11.2.1: is de URI werkelijk dood, dan komt dat hier
    alsnog boven.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    await vuur(hass, registry_id)
    assert bericht(hass, registry_id) is None

    gebeurtenissen: list[dict[str, Any]] = []
    abonnement.register_van(hass).abonneer(gebeurtenissen.append)

    huis.laat_speaker_wegvallen()
    await tik(hass, NOODREM_NA_SECONDEN + 0.5)

    melding = bericht(hass, registry_id)
    assert melding["kind"] == meldingen.KIND_SPEAKER_LOST_DURING_PLAY
    assert "mogelijk niet hoorbaar geweest" in melding["text"]
    assert [g["event"] for g in _ringing(gebeurtenissen)] == [abonnement.EVENT_FAILED]

    # En de wekker blijft afgaan: SPEC 11.3 vraagt om controleren, niet om afbreken.
    # De kaart hoort een stopknop te blijven, want het volume moet nog terug.
    assert abonnement.register_van(hass).is_afgaand(registry_id, ALARM_ID)


async def test_een_speaker_die_blijft_staan_levert_geen_melding_op(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG, en de positieve controle bij de test hierboven.

    Zonder deze zou "er staat een melding" ook waar kunnen zijn omdat er altijd één
    komt. Dit is de valkuil uit CLAUDE.md: een test die niet faalt op de oude code
    omdat hij triviaal waar is.
    """
    registry_id, _ = await zet_op(hass, hass_storage)
    await vuur(hass, registry_id)

    await tik(hass, NOODREM_NA_SECONDEN + 0.5)

    assert bericht(hass, registry_id) is None


# =======================================================================
# 6 en 7. De volume-oploop (SPEC 9.3)
# =======================================================================


async def test_de_oploop_bereikt_het_ingestelde_niveau_in_twintig_stappen(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Verplicht geval 6.

    Niet alleen "eindigt op 40", maar **elke stap afzonderlijk**, in volgorde. Fase 0b
    is precies hierop misgegaan: een oploop van 20 stappen liep in paren van 2 per 2
    seconden, en wie alleen de totaalduur rapporteert meldt een vloeiende oploop die
    in werkelijkheid tien sprongen was (valkuil 31).

    De eerste 0 is stap 3 van de afvuurvolgorde, daarna 20 stappen naar 40.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    await vuur(hass, registry_id)

    await draai_oploop_af(hass)

    assert huis.volumes() == [
        0,
        *[2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40],
    ]


async def test_de_oploop_breekt_af_als_de_gebruiker_aan_het_volume_draait(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Verplicht geval 7.

    Zonder deze regel vecht de integratie met de gebruiker: hij draait zachter en de
    volgende stap zet het weer harder. SPEC 9.3 legt de grens op **meer dan** 5
    procentpunt afwijking van wat de oploop zelf net zette.

    Hier draait de gebruiker na een paar stappen naar 80 — ruim buiten de marge — en
    daarna hoort de oploop niets meer te zetten.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    await vuur(hass, registry_id)

    await tik(hass, OPLOOP_STAP_SECONDEN + 0.1)
    await tik(hass, OPLOOP_STAP_SECONDEN * 2 + 0.1)
    tot_nu = list(huis.volumes())
    assert tot_nu == [0, 2, 4]

    huis.zet_volume_op(80)
    await draai_oploop_af(hass)

    # Niets meer gezet ná het draaien: de laatste volume_set is nog steeds de 4.
    assert huis.volumes() == tot_nu


async def test_een_kleine_afwijking_breekt_de_oploop_niet_af(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG, en de positieve controle bij de test hierboven.

    Een speaker die door afronding 3 % afwijkt van wat wij zetten, mag de oploop niet
    afbreken. Zonder deze test zou een implementatie die *altijd* afbreekt ook door
    de test hierboven komen — en dan zou de oploop nooit verder komen dan stap 1.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    await vuur(hass, registry_id)

    await tik(hass, OPLOOP_STAP_SECONDEN + 0.1)
    assert huis.volumes() == [0, 2]

    huis.zet_volume_op(5)  # 3 procentpunt van de gezette 2: binnen de marge
    await draai_oploop_af(hass)

    assert huis.volumes()[-1] == 40


async def test_een_weggevallen_speaker_breekt_de_oploop_af(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Volume blijven zetten op een dode speaker heeft geen zin.

    En het gebeurt **zonder** eigen melding: die hoort bij de tweede noodremcontrole
    (SPEC 11.3), anders staan er twee meldingen over hetzelfde en overschrijft de
    laatste de eerste in het ene veld `last_message` (SPEC 14.2.1).
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    await vuur(hass, registry_id)
    await tik(hass, OPLOOP_STAP_SECONDEN + 0.1)

    huis.laat_speaker_wegvallen()
    n_voor = len(huis.volumes())
    await draai_oploop_af(hass)

    assert len(huis.volumes()) == n_voor


async def test_de_oploop_stopt_als_de_wekker_gestopt_wordt(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. SPEC 9.3: de oploop stopt zodra de wekker gestopt wordt.

    Twee remmen tegelijk, en dat is opzet: de unsub wordt afgezegd **en** de tik
    controleert het register. Eén afzegging die net te laat komt zou anders nog één
    keer het volume omhoog zetten nadat de klant op stop heeft gedrukt.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    await vuur(hass, registry_id)
    await tik(hass, OPLOOP_STAP_SECONDEN + 0.1)

    await afvuren.async_stop_afgaan(
        hass, registry_id, PERSON_ENTITY_ID, ALARM_ID, abonnement.REASON_USER
    )
    na_stop = list(huis.volumes())
    await draai_oploop_af(hass)

    assert huis.volumes() == na_stop


async def test_een_tik_op_een_wekker_die_niet_meer_afgaat_zet_geen_volume(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG, en deze test bestaat door een mutatietest (A19).

    Het weghalen van de `is_afgaand`-controle in `_Oploop._async_tik` veranderde eerst
    niets: `async_stop_afgaan` zegt de `async_call_later` toch al af, dus via die weg is
    de controle overbodig. Dat is dezelfde vorm als mutatie P3 van fase 3b, en dezelfde
    conclusie: **het is dubbele verdediging op de ene weg en enige verdediging op de
    andere.**

    De weg waarop hij de enige is: `_async_tik` zet `self._unsub = None` en gaat dan
    `await`en. Komt de stop precies daartussen, dan is er geen unsub meer om af te
    zeggen en is deze controle het enige dat voorkomt dat er ná de stop nog één keer
    het volume omhoog gaat — op een speaker waarvan het volume net is teruggezet.

    Deze test zet dat neer door de tik rechtstreeks aan te roepen op een register dat
    de wekker niet meer kent.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    await vuur(hass, registry_id)
    register = abonnement.register_van(hass)
    loop = register.actief[(registry_id, ALARM_ID)][afvuren.CTX_OPLOOP]

    # Eén stap laten lopen, zodat het volume van de speaker gelijk is aan wat de oploop
    # zelf zette. Dat is nodig om déze controle te isoleren: staat het volume ergens
    # anders, dan breekt `wijkt_af` de oploop al af en zegt de test niets over het
    # register.
    await tik(hass, OPLOOP_STAP_SECONDEN + 0.1)
    assert huis.volumes() == [0, 2]

    # Precies zo ver als `async_stop_afgaan` komt: timer afgezegd en uit het register.
    # Het volume wordt hier niet teruggezet, want in het geval dat deze test nabootst
    # was de tik al voorbij dat punt.
    context = register.actief.pop((registry_id, ALARM_ID))
    loop.stop()
    for sleutel in (afvuren.CTX_UNSUB_NOODREM, afvuren.CTX_UNSUB_STOP):
        context[sleutel]()
    huis.aanroepen.clear()

    await loop._async_tik(dt.datetime.now(dt.UTC))

    assert huis.aanroepen == []


async def test_een_speaker_die_geen_volume_aanneemt_gaat_af_zonder_oploop(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. SPEC 11.7 `volume_ramp_unavailable`.

    Het geluid is de wekker: kan de speaker geen volume aannemen, dan gaat hij af op
    het **ingestelde** niveau in plaats van niet af te gaan. De melding zegt precies
    dat, en het is een `error` en geen mededeling — de klant is te hard gewekt en dat
    is iets waar hij iets aan kan doen.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    huis.faal.add("media_player.volume_set")

    await vuur(hass, registry_id)

    assert "music_assistant.play_media" in huis.namen()
    assert abonnement.register_van(hass).is_afgaand(registry_id, ALARM_ID)
    melding = bericht(hass, registry_id)
    assert melding["kind"] == meldingen.KIND_VOLUME_RAMP_UNAVAILABLE
    # Er is geprobeerd op 0 én op het ingestelde niveau te zetten; beide geweigerd.
    assert huis.namen().count("media_player.volume_set") == 2
    assert abonnement.register_van(hass).actief[(registry_id, ALARM_ID)][
        afvuren.CTX_OPLOOP
    ] is None


# =======================================================================
# 8 en 9. radio_mode (SPEC 8.3.1)
# =======================================================================


async def test_radio_mode_gaat_niet_mee_bij_een_gratis_radioprovider(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Verplicht geval 8, en let op het verschil met `radio_mode: False`.

    Het veld wordt **weggelaten** en niet op `False` gezet, zodat Music Assistant zijn
    eigen standaard houdt (SPEC 8.3.1). `assert "radio_mode" not in data` is dus de
    juiste assertie en `assert data["radio_mode"] is False` zou verkeerd zijn.
    """
    registry_id, huis = await zet_op(hass, hass_storage)

    await vuur(hass, registry_id)

    data = dict(huis.aanroepen)["music_assistant.play_media"]
    assert data["media_id"] == URI
    assert "radio_mode" not in data


async def test_radio_mode_gaat_mee_bij_een_ondersteunende_provider(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Verplicht geval 8, tweede helft.

    Spotify ondersteunt `SIMILAR_TRACKS`, dus MA speelt na het nummer eindeloos door
    in dezelfde stijl — en dan is een los nummer wél een bruikbare wekker in plaats
    van drie minuten geluid en daarna stilte.
    """
    uri = "spotify--ZvzrFmgX://track/4uLU"
    wekker = volledige_wekker(
        sound={"uri": uri, "name": "Iets", "media_type": "track", "image": None}
    )
    registry_id, huis = await zet_op(hass, hass_storage, wekker)
    huis.vind(uri, media_type="track")

    await vuur(hass, registry_id)

    assert dict(huis.aanroepen)["music_assistant.play_media"]["radio_mode"] is True


async def test_een_mislukte_radio_mode_wordt_opnieuw_geprobeerd_zonder(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Verplicht geval 9, en dit is de eis die fase 3a-bis stelde.

    De providerlijst kan **stil** verouderen. Blijft een provider erin staan die de
    feature verliest, dan geeft MA HTTP 500 en speelt er *niets* — gemeten in fase 3a:
    `met radio_mode: HTTP 500, queue items=0, state=idle`. Een wekker die na drie
    minuten stopt is hinderlijk; een wekker die helemaal niet afgaat is stuk.

    **De terugval is de garantie, niet de lijst.** Deze test is de reden dat je op de
    lijst niet hoeft te vertrouwen: er wordt twee keer aangeroepen, de tweede zonder
    het veld, en de wekker gaat alsnog af.
    """
    uri = "spotify://track/4uLU"
    wekker = volledige_wekker(
        sound={"uri": uri, "name": "Iets", "media_type": "track", "image": None}
    )
    registry_id, huis = await zet_op(hass, hass_storage, wekker)
    huis.vind(uri, media_type="track")

    # De eerste play_media faalt, de tweede lukt — precies het gedrag van MA's server
    # als er geen provider met SIMILAR_TRACKS is.
    pogingen: list[dict[str, Any]] = []

    async def _play(call) -> None:
        pogingen.append(dict(call.data))
        if len(pogingen) == 1:
            raise HomeAssistantError("UnsupportedFeaturedException")

    hass.services.async_register("music_assistant", "play_media", _play)

    await vuur(hass, registry_id)

    assert len(pogingen) == 2
    assert pogingen[0]["radio_mode"] is True
    assert "radio_mode" not in pogingen[1]
    assert abonnement.register_van(hass).is_afgaand(registry_id, ALARM_ID)
    assert bericht(hass, registry_id) is None


async def test_als_het_afspelen_ook_zonder_radio_mode_faalt_gaat_de_wekker_niet_af(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG, en de positieve controle bij de terugval hierboven.

    Zonder deze test zou een implementatie die elke fout wegslikt ook door geval 9
    komen — en dan zou een wekker die niets speelt zich als een geslaagde wekker
    voordoen. Dat is de stilte die SPEC 11 juist verbiedt.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    huis.faal.add("music_assistant.play_media")

    await vuur(hass, registry_id)

    assert not abonnement.register_van(hass).is_afgaand(registry_id, ALARM_ID)
    melding = bericht(hass, registry_id)
    assert melding["severity"] == "error"
    # `sound_gone` en niet `speaker_unavailable`: de speaker is bij stap 1 nog
    # beschikbaar bevonden, dus die melding zou onwaar zijn.
    assert melding["kind"] == meldingen.KIND_SOUND_GONE


# =======================================================================
# 10 en 11. Stoppen (SPEC 9.4, 9.5, 10)
# =======================================================================


async def test_stoppen_zet_het_volume_terug(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Verplicht geval 10, eerste helft.

    Zonder dit staat de speaker de rest van de dag op het wekvolume — een bijwerking
    die de klant niet heeft gevraagd en die hij pas 's avonds merkt.

    Let op de **volgorde**: eerst het geluid stoppen, dan het volume terug. Andersom
    klinkt de laatste seconde op het oude volume, en als dat 80 was is dat precies de
    uitbarsting die stap 3 van de afvuurvolgorde had voorkomen.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    await vuur(hass, registry_id)
    await draai_oploop_af(hass)
    huis.aanroepen.clear()

    assert await afvuren.async_stop_afgaan(
        hass, registry_id, PERSON_ENTITY_ID, ALARM_ID, abonnement.REASON_USER
    )

    assert huis.namen() == ["media_player.media_stop", "media_player.volume_set"]
    assert huis.volumes() == [50]


async def test_een_onleesbaar_oud_volume_zet_niets_terug(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Verplicht geval 10, tweede helft, en dit is een regel uit SPEC 9.5.

    Was het volume bij het afgaan niet te lezen, dan wordt er **niets** teruggezet.
    Nooit een verzonnen waarde: 50 % op een speaker die op 10 % stond is een wekker
    die 's avonds iemand laat schrikken, en het zou een waarde zijn die dit product
    zelf bedacht heeft.

    Dit is dezelfde regel als "toon nooit een terugvalwaarde die je niet zou opslaan"
    uit CLAUDE.md, één laag dieper.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    huis.zet_volume_op(None)  # geen volume_level in de attributen
    await vuur(hass, registry_id)
    huis.aanroepen.clear()

    await afvuren.async_stop_afgaan(
        hass, registry_id, PERSON_ENTITY_ID, ALARM_ID, abonnement.REASON_USER
    )

    assert huis.namen() == ["media_player.media_stop"]
    assert huis.volumes() == []


async def test_de_stoptimer_stopt_de_wekker_na_dertig_minuten(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Verplicht geval 11.

    Dat voorkomt dat de muziek dagenlang doorspeelt in een lege woning. De reden in
    het `stopped`-event is `timeout` en niet `user`: de kaart hoort te kunnen zien dat
    niemand op stop heeft gedrukt.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    await vuur(hass, registry_id)
    gebeurtenissen: list[dict[str, Any]] = []
    abonnement.register_van(hass).abonneer(gebeurtenissen.append)

    await tik(hass, STOP_NA_MINUTEN * 60 + 1)

    assert not abonnement.register_van(hass).is_afgaand(registry_id, ALARM_ID)
    assert [g["reason"] for g in gebeurtenissen if g["event"] == abonnement.EVENT_STOPPED] == [
        abonnement.REASON_TIMEOUT
    ]
    assert "media_player.media_stop" in huis.namen()


async def test_een_gestopte_wekker_wordt_niet_nog_eens_gestopt_door_de_timer(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. De stoptimer moet afgezegd worden, niet alleen genegeerd.

    Zou hij blijven staan, dan komt er 30 minuten na een wekker die om 06:47 is
    gestopt nog een `stopped`-event langs — en dan zet de integratie het volume terug
    dat de klant inmiddels zelf heeft gekozen.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    await vuur(hass, registry_id)
    await afvuren.async_stop_afgaan(
        hass, registry_id, PERSON_ENTITY_ID, ALARM_ID, abonnement.REASON_USER
    )
    huis.aanroepen.clear()
    gebeurtenissen: list[dict[str, Any]] = []
    abonnement.register_van(hass).abonneer(gebeurtenissen.append)

    await tik(hass, STOP_NA_MINUTEN * 60 + 1)

    assert _ringing(gebeurtenissen) == []
    assert huis.aanroepen == []


async def test_stoppen_is_idempotent(hass: HomeAssistant, hass_storage: dict) -> None:
    """NIEUW GEDRAG voor het afvuurpad (SPEC 15.8).

    Fase 3b toonde dit al voor het commando, toen er nog niets afspeelde. Nu er wél
    services aangeroepen worden is de eis scherper: de **tweede** stop mag geen
    `media_stop` en geen `volume_set` sturen. Een wandtablet en een telefoon kunnen
    tegelijk drukken.

    Daarom haalt `async_stop_afgaan` de wekker als **eerste** uit het register, vóór
    de eerste `await`: dan vindt een tweede stop niets meer, ook als de eerste nog
    aan het afronden is.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    await vuur(hass, registry_id)
    huis.aanroepen.clear()

    eerste = await afvuren.async_stop_afgaan(
        hass, registry_id, PERSON_ENTITY_ID, ALARM_ID, abonnement.REASON_USER
    )
    n_na_eerste = len(huis.aanroepen)
    tweede = await afvuren.async_stop_afgaan(
        hass, registry_id, PERSON_ENTITY_ID, ALARM_ID, abonnement.REASON_USER
    )

    assert eerste is True
    assert tweede is False
    assert len(huis.aanroepen) == n_na_eerste


async def test_de_started_en_stopped_events_gaan_naar_de_abonnees(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG (SPEC 15.9). In fase 3b stond deze test in `test_planner.py`.

    Hij is hierheen verhuisd omdat hij over het afvuren gaat en niet over de planning,
    en omdat hij nu de echte weg aflegt: van `async_laat_afgaan` via het register naar
    de abonnee, met een speaker die werkelijk wordt aangeroepen.
    """
    registry_id, _ = await zet_op(hass, hass_storage)
    gebeurtenissen: list[dict[str, Any]] = []
    abonnement.register_van(hass).abonneer(gebeurtenissen.append)

    await vuur(hass, registry_id)
    await afvuren.async_stop_afgaan(
        hass, registry_id, PERSON_ENTITY_ID, ALARM_ID, abonnement.REASON_USER
    )

    assert [g["event"] for g in _ringing(gebeurtenissen)] == [
        abonnement.EVENT_STARTED,
        abonnement.EVENT_STOPPED,
    ]
    assert _ringing(gebeurtenissen)[0] == {
        "event": "started",
        "person": PERSON_ENTITY_ID,
        "alarm_id": ALARM_ID,
        "name": "Werk",
        "time": "06:45",
    }
    assert _ringing(gebeurtenissen)[1]["reason"] == abonnement.REASON_USER


# =======================================================================
# 12. De wake-up light (SPEC 12)
# =======================================================================


async def test_de_lamp_gaat_aan_met_helderheid_en_zonder_transition(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. SPEC 12: geen opbouw, dus **geen** `transition` meesturen.

    Niet `transition: 0`: dat is niet hetzelfde als hem weglaten bij lampen die de
    parameter niet kennen. "Geen opbouw" is de eis en weglaten is de enige manier die
    op elke lamp hetzelfde doet.
    """
    wekker = volledige_wekker(light={"entity_id": "light.bedlamp", "brightness_pct": 60})
    registry_id, huis = await zet_op(hass, hass_storage, wekker)

    await vuur(hass, registry_id)

    data = dict(huis.aanroepen)["light.turn_on"]
    assert data["entity_id"] == "light.bedlamp"
    assert data["brightness_pct"] == 60
    assert "transition" not in data


async def test_een_falende_lamp_laat_de_wekker_gewoon_afgaan(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Verplicht geval 12.

    Het geluid is de wekker en het licht is een toevoeging. Een lamp die niet aangaat
    mag de wekker niet meeslepen — maar hij wordt wél gemeld, want de klant heeft hem
    ingesteld en zou anders denken dat het werkt.
    """
    wekker = volledige_wekker(light={"entity_id": "light.bedlamp", "brightness_pct": 60})
    registry_id, huis = await zet_op(hass, hass_storage, wekker)
    huis.faal.add("light.turn_on")

    await vuur(hass, registry_id)

    assert "music_assistant.play_media" in huis.namen()
    assert abonnement.register_van(hass).is_afgaand(registry_id, ALARM_ID)
    melding = bericht(hass, registry_id)
    assert melding["kind"] == meldingen.KIND_LIGHT_FAILED
    assert "lamp" in melding["text"]


async def test_zonder_lamp_wordt_light_turn_on_niet_aangeroepen(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Een wekker zonder wake-up light is geldig (SPEC 12).

    En het product verzint geen lamp die de klant niet heeft gekozen — dat is dezelfde
    regel als SPEC 11.6 punt 2, hier in het geslaagde geval.
    """
    registry_id, huis = await zet_op(hass, hass_storage)

    await vuur(hass, registry_id)

    assert "light.turn_on" not in huis.namen()


async def test_bij_een_noodremfout_gaat_een_ingestelde_lamp_wel_aan(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. SPEC 11.6 punt 2, en dit is een regel die makkelijk omvalt.

    De lamp had ook aan moeten gaan als het geluid het had gedaan, dus hij gaat aan.
    Wat het product **niet** doet, is een lamp verzinnen die de klant niet heeft
    gekozen — dat zou een alternatief zijn dat niemand heeft gevraagd.

    En de melding blijft die over de speaker: waaróm de wekker stil was, is het
    belangrijkste dat de klant 's ochtends kan lezen. Er is één veld `last_message`
    (SPEC 14.2.1), dus die volgorde is niet vrij.
    """
    wekker = volledige_wekker(light={"entity_id": "light.bedlamp", "brightness_pct": 60})
    registry_id, huis = await zet_op(hass, hass_storage, wekker, beschikbaar=False)

    await vuur(hass, registry_id)

    assert huis.namen() == ["light.turn_on"]
    assert bericht(hass, registry_id)["kind"] == meldingen.KIND_SPEAKER_UNAVAILABLE


async def test_een_falende_lamp_overschrijft_de_noodremmelding_niet(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG, en de scherpe kant van de test hierboven.

    Faalt de lamp *tijdens* een noodremfout, dan zou een verkeerde volgorde
    `last_message` op "de lamp kon niet aangezet worden" laten eindigen — terwijl de
    klant zich net heeft verslapen omdat de speaker weg was. Er is één veld, dus de
    laatste schrijver wint, en de belangrijkste moet als laatste schrijven.
    """
    wekker = volledige_wekker(light={"entity_id": "light.bedlamp", "brightness_pct": 60})
    registry_id, huis = await zet_op(hass, hass_storage, wekker, beschikbaar=False)
    huis.faal.add("light.turn_on")

    await vuur(hass, registry_id)

    assert bericht(hass, registry_id)["kind"] == meldingen.KIND_SPEAKER_UNAVAILABLE


# =======================================================================
# De naad met de planner, en met de opslag
# =======================================================================


async def test_de_planner_laat_een_wekker_echt_afspelen(
    hass: HomeAssistant, hass_storage: dict, freezer
) -> None:
    """NIEUW GEDRAG, en de enige test die de héle keten aflegt.

    `test_planner.py` vervangt `async_laat_afgaan` door een boekhouder, zodat die
    tests over *wanneer* gaan. Deze test bestaat om wat die vervanging verbergt:
    dat de planner werkelijk dít pad aanroept en dat er aan het eind een speaker wordt
    aangesproken. Zonder deze test zou een verkeerd argument in de planner nergens
    opvallen.

    De inhaalslag bij setup doet het werk: een wekker van 06:45 met `last_fired` leeg,
    op een klok die 06:50 staat, valt binnen het respijtvenster van 30 minuten.
    """
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 50, tzinfo=AMS))
    wekker = volledige_wekker(days=[1, 2, 3, 4, 5, 6, 7])

    # Niet via `zet_op`: die gooit de aanroepen van de inhaalslag juist weg, en hier
    # zijn dat precies de aanroepen waar het om gaat.
    await hass.config.async_update(time_zone="Europe/Amsterdam")
    registry_id = registreer_person(hass)
    maak_speaker(hass, features=GOEDE_FEATURES)
    huis = Speelhuis(hass)
    huis.register()
    huis.vind(URI)
    huis.zet_volume_op(50)
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": {"persons": {registry_id: {"alarms": [wekker]}}},
    }
    assert await async_setup_component(hass, "frontend", {})
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="DomotiApp Alarm", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert "music_assistant.play_media" in huis.namen()
    assert abonnement.register_van(hass).is_afgaand(registry_id, ALARM_ID)
    # Het bedoelde moment, niet "nu": 06:45 en niet 06:50 (fase 3b, regel 2).
    opgeslagen = hass.data[DOMAIN][DATA_STORE].wekker(registry_id, ALARM_ID)
    assert opgeslagen["last_fired"] == "2026-08-10T06:45:00+02:00"

    await afvuren.async_stop_afgaan(
        hass, registry_id, PERSON_ENTITY_ID, ALARM_ID, abonnement.REASON_USER
    )


async def test_last_fired_wordt_ook_bij_een_noodremfout_gezet(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG, en een keuze met een prijs die uitgelegd hoort te worden.

    Een noodremfout **verbruikt** het moment. Anders zou elke herstart binnen het
    respijtvenster van 30 minuten de mislukking herhalen — een nieuwe melding, een
    nieuwe `persistent_notification` — en als de speaker inmiddels terug is, zou de
    wekker alsnog afgaan op een moment dat de klant niet verwacht.

    Dat mag omdat een mislukte noodrem **geen geluid** maakt: opnieuw proberen kan
    nooit "twee keer afgaan" opleveren, en dat is de enige uitkomst die echt erg is.
    Het sluit aan bij hoe fase 3b het overslaan behandelt; dat zet `last_fired` ook.
    """
    registry_id, _ = await zet_op(hass, hass_storage, beschikbaar=False)

    await vuur(hass, registry_id)

    opgeslagen = hass.data[DOMAIN][DATA_STORE].wekker(registry_id, ALARM_ID)
    assert opgeslagen["last_fired"] == MOMENT.isoformat()


async def test_unload_stopt_een_afgaande_wekker(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. Twee redenen, en elk is genoeg.

    De oploop, de tweede noodremcontrole en de stoptimer zijn `async_call_later`s.
    Blijven die staan, dan tikt de eerste over een `hass.data[DOMAIN]` die net is
    losgelaten. En zonder stoptimer speelt de muziek **door** zonder dat er nog iemand
    is die hem afzet — precies de lege woning waar SPEC 9.4 voor bestaat.
    """
    registry_id, huis = await zet_op(hass, hass_storage)
    await vuur(hass, registry_id)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    huis.aanroepen.clear()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert not abonnement.register_van(hass).is_afgaand(registry_id, ALARM_ID)
    assert "media_player.media_stop" in huis.namen()
    # En daarna tikt er niets meer over een losgelaten opslag.
    await tik(hass, STOP_NA_MINUTEN * 60 + 1)


async def test_een_oude_melding_wordt_gewist_als_de_wekker_weer_gewoon_afgaat(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """NIEUW GEDRAG. De `persistent_notification` van gisteren hoort niet te blijven.

    En het wissen gebeurt zodra de noodrem gehaald is, **niet** aan het eind: aan het
    eind zou het de melding wegwissen die de lamp of de tweede noodremcontrole net had
    gemaakt.
    """
    wekker = volledige_wekker(
        last_message={
            "at": "2026-08-09T06:45:00+02:00",
            "kind": meldingen.KIND_SPEAKER_UNAVAILABLE,
            "severity": "error",
            "text": "gisteren ging het mis",
        }
    )
    registry_id, huis = await zet_op(hass, hass_storage, wekker)
    meldingen.async_meld  # noqa: B018 - alleen om de import te verantwoorden
    from homeassistant.components import persistent_notification

    persistent_notification.async_create(
        hass, "gisteren ging het mis", title="DomotiApp Alarm",
        notification_id=f"{DOMAIN}_{ALARM_ID}",
    )
    assert f"{DOMAIN}_{ALARM_ID}" in persistent_notification._async_get_or_create_notifications(
        hass
    )

    await vuur(hass, registry_id)

    assert f"{DOMAIN}_{ALARM_ID}" not in (
        persistent_notification._async_get_or_create_notifications(hass)
    )
