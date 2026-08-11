"""Pytest-opzet voor de custom integration."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.domotiapp_alarm.const import (
    CARD_FILENAME,
    CARD_URL_PATH,
    DOMAIN,
    HASH_LENGTE,
    STORAGE_KEY,
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
)

pytest_plugins = "pytest_homeassistant_custom_component"

BUNDEL = (
    Path(__file__).parent.parent
    / "custom_components"
    / DOMAIN
    / "frontend"
    / CARD_FILENAME
)

PERSON_ENTITY_ID = "person.sven"
PERSON_UNIQUE_ID = "sven"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Laat Home Assistant custom_components/ zien in elke test."""
    return


def verwachte_url() -> str:
    """De URL die de integratie hoort te gebruiken: pad plus bundelhash."""
    hash_ = hashlib.sha256(BUNDEL.read_bytes()).hexdigest()[:HASH_LENGTE]
    return f"{CARD_URL_PATH}?v={hash_}"


def registreer_person(
    hass: HomeAssistant,
    entity_id: str = PERSON_ENTITY_ID,
    unique_id: str = PERSON_UNIQUE_ID,
) -> str:
    """Maak een person in het entity registry én in de state machine.

    Geeft het **registry-entry-ID** terug — de opslagsleutel uit SPEC 6.2.

    Bewust via het registry en niet via de person-integratie: die vraagt een
    gebruiker en een opslagcollectie, en wat deze tests nodig hebben is precies
    wat SPEC 6.2 gebruikt — een entiteit met een `unique_id` en dus een
    registry-entry met een stabiel ID.
    """
    registry = er.async_get(hass)
    entry = registry.async_get_or_create(
        "person",
        "person",
        unique_id,
        suggested_object_id=entity_id.split(".", 1)[1],
    )
    hass.states.async_set(entry.entity_id, "home", {"friendly_name": "Sven"})
    return entry.id


async def zet_integratie_op(hass: HomeAssistant) -> MockConfigEntry:
    """Zet de integratie op, met frontend en lovelace erachter."""
    assert await async_setup_component(hass, "frontend", {})
    assert await async_setup_component(hass, "lovelace", {})
    await hass.async_block_till_done()

    entry = MockConfigEntry(domain=DOMAIN, title="DomotiApp Alarm", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def opgezet(hass: HomeAssistant) -> MockConfigEntry:
    """De integratie volledig opgezet."""
    return await zet_integratie_op(hass)


@pytest.fixture
def lees_opslag(hass_storage: dict[str, Any]):
    """Lees terug wat er weggeschreven is.

    `hass_storage` onderschept `Store`-schrijfacties en bewaart het resultaat ná
    een echte JSON-serialisatieronde, dus wat hier uitkomt is letterlijk wat er in
    het bestand had gestaan.
    """

    def _lees() -> dict[str, Any] | None:
        return hass_storage.get(STORAGE_KEY)

    return _lees


@pytest.fixture
def schrijf_opslag(hass_storage: dict[str, Any]):
    """Zet opslag klaar vóór de integratie geladen wordt."""

    def _schrijf(
        persons: Any,
        version: int = STORAGE_VERSION,
        minor_version: int = STORAGE_MINOR_VERSION,
    ) -> None:
        """`version` staat standaard op de **huidige** versie.

        Sinds fase 7 bestaat er een migratie, en een fixture die stilzwijgend op
        versie 1 zou blijven staan, zou elke test die hem gebruikt ongemerkt door
        die migratie sturen. Wie de migratie wíl toetsen, geeft `version=1` mee —
        expliciet, want dat is dan het onderwerp.
        """
        hass_storage[STORAGE_KEY] = {
            "version": version,
            "minor_version": minor_version,
            "key": STORAGE_KEY,
            "data": {"persons": persons},
        }

    return _schrijf


def maak_speaker(
    hass: HomeAssistant,
    entity_id: str = "media_player.slaapkamer",
    *,
    platform: str = "music_assistant",
    features: int = 0,
    player_type: str | None = "player",
    beschikbaar: bool = True,
    naam: str = "Slaapkamer",
) -> str:
    """Een media_player die aan de eisen van SPEC 7.2 kan voldoen.

    `features` moet PLAY_MEDIA en VOLUME_SET bevatten om te slagen; de tests zetten
    dat expliciet zodat elke eis afzonderlijk te breken is.
    """
    registry = er.async_get(hass)
    entry = registry.async_get_or_create(
        "media_player",
        platform,
        f"uid_{entity_id}",
        suggested_object_id=entity_id.split(".", 1)[1],
    )
    attributen: dict[str, Any] = {
        "friendly_name": naam,
        "supported_features": features,
    }
    if player_type is not None:
        attributen["mass_player_type"] = player_type
    hass.states.async_set(
        entry.entity_id, "unavailable" if not beschikbaar else "idle", attributen
    )
    return entry.entity_id


def maak_lamp(
    hass: HomeAssistant, entity_id: str = "light.bedlamp", naam: str = "Bedlamp"
) -> str:
    registry = er.async_get(hass)
    entry = registry.async_get_or_create(
        "light", "demo", f"uid_{entity_id}", suggested_object_id=entity_id.split(".", 1)[1]
    )
    hass.states.async_set(entry.entity_id, "off", {"friendly_name": naam})
    return entry.entity_id


def geldige_wekker(**overschrijf: Any) -> dict[str, Any]:
    """Een wekker zoals `alarms/save` hem accepteert (SPEC 15.2).

    Alleen gebruikersvelden; de server vult de boekhouding zelf.
    """
    wekker: dict[str, Any] = {
        "name": "Werk",
        "time": "06:45",
        "days": [1, 2, 3, 4, 5],
        "enabled": True,
        "sound": {
            "uri": "somafm://radio/beatblender",
            "name": "SomaFM: Beat Blender",
            "media_type": "radio",
            "image": None,
        },
        "speaker": "media_player.slaapkamer",
        "volume_pct": 40,
        "light": None,
    }
    wekker.update(overschrijf)
    return wekker


class Speelhuis:
    """De buitenwereld van het afvuren, nagebouwd en meetbaar (SPEC 9, 11, 12).

    Wat hier gemockt wordt zijn **HA-services van andere integraties**, en dat is de
    enige eerlijke manier: `music_assistant` is er niet in een test, en de vier
    aanroepen die dit product doet (`play_media`, `volume_set`, `media_stop`,
    `shuffle_set`, `light.turn_on`, `light.turn_off`) zijn precies zijn grens.

    **Er wordt niets van onze eigen code gemockt.** Dat is het verschil met een test
    die "de setup faalt niet" bewijst: de volgorde, de clamping, de terugval op
    `radio_mode` en het terugzetten van het volume worden allemaal uit `aanroepen`
    afgelezen — één lijst, in de werkelijke volgorde, met de werkelijke argumenten.

    `faal` bepaalt welke aanroepen een `HomeAssistantError` geven. `zoekresultaat`
    bepaalt wat de URI-controle terugvindt; `zoekfout` laat de zoekopdracht zelf
    stuklopen, wat een heel andere uitkomst hoort te hebben (SPEC 11.2.1).
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.aanroepen: list[tuple[str, dict[str, Any]]] = []
        self.faal: set[str] = set()
        # De tekst die de gefaalde aanroep meegeeft. Dat is niet altijd hetzelfde:
        # Music Assistant geeft er een ("No playable items found"), HA's eigen fouten
        # soms geen. Een lege string bootst dat tweede geval na.
        self.faalreden: dict[str, str] = {}
        self.zoekresultaat: dict[str, Any] | None = None
        self.zoekfout: Exception | None = None
        # Het volume dat de nagebootste speaker "heeft". `volume_set` werkt het bij,
        # zodat de oploop zijn eigen waarde terugleest zoals bij een echte speaker.
        self.volume_niveau: float | None = 0.5
        # De shuffle-stand die de nagebootste speaker "heeft". `shuffle_set` werkt
        # hem bij, zodat het terugzetten bij het stoppen zijn eigen waarde terugleest
        # zoals bij een echte speaker. `None` = het attribuut ontbreekt, wat gebeurt
        # zodra de entiteit `unavailable` is (valkuil 18).
        self.shuffle_stand: bool | None = False
        self.speaker = "media_player.slaapkamer"

    def _boek(self, naam: str, data: dict[str, Any]) -> None:
        self.aanroepen.append((naam, dict(data)))
        if naam in self.faal:
            raise HomeAssistantError(
                self.faalreden.get(naam, f"{naam} geweigerd door de test")
            )

    def namen(self) -> list[str]:
        """Alleen de namen, in volgorde. Hiermee wordt de volgorde uit SPEC 9.1 getoetst."""
        return [naam for naam, _ in self.aanroepen]

    def volumes(self) -> list[int]:
        """De volumepercentages die er gezet zijn, in volgorde."""
        return [
            round(data["volume_level"] * 100)
            for naam, data in self.aanroepen
            if naam == "media_player.volume_set"
        ]

    def register(self) -> None:
        """Registreer de vier services plus een geladen MA-config-entry."""

        async def _play(call) -> None:
            self._boek("music_assistant.play_media", call.data)

        async def _zoek(call) -> dict[str, Any]:
            self.aanroepen.append(("music_assistant.search", dict(call.data)))
            if self.zoekfout is not None:
                raise self.zoekfout
            return self.zoekresultaat or {}

        async def _volume(call) -> None:
            self._boek("media_player.volume_set", call.data)
            self.volume_niveau = call.data["volume_level"]
            self._werk_state_bij()

        async def _stop(call) -> None:
            self._boek("media_player.media_stop", call.data)

        async def _licht(call) -> None:
            self._boek("light.turn_on", call.data)

        async def _licht_uit(call) -> None:
            self._boek("light.turn_off", call.data)

        async def _shuffle(call) -> None:
            self._boek("media_player.shuffle_set", call.data)
            self.shuffle_stand = bool(call.data["shuffle"])
            self._werk_state_bij()

        self.hass.services.async_register("music_assistant", "play_media", _play)
        self.hass.services.async_register(
            "music_assistant",
            "search",
            _zoek,
            supports_response=SupportsResponse.ONLY,
        )
        self.hass.services.async_register("media_player", "volume_set", _volume)
        self.hass.services.async_register("media_player", "media_stop", _stop)
        self.hass.services.async_register("media_player", "shuffle_set", _shuffle)
        self.hass.services.async_register("light", "turn_on", _licht)
        self.hass.services.async_register("light", "turn_off", _licht_uit)

        # `noodrem.controleer_speaker` en `async_controleer_uri` vragen naar een geladen
        # MA-entry. Zonder deze zou elke test hier al afketsen op `ma_unavailable`, en
        # dan zou geen enkele test iets over het afvuren zeggen.
        ma_entry = MockConfigEntry(domain="music_assistant", title="Music Assistant")
        ma_entry.add_to_hass(self.hass)
        ma_entry.mock_state(self.hass, ConfigEntryState.LOADED)

    def _werk_state_bij(self) -> None:
        """Zet het gelezen volume in de state, zoals een echte speaker zou doen."""
        state = self.hass.states.get(self.speaker)
        if state is None:
            return
        attributen = dict(state.attributes)
        if self.volume_niveau is None:
            attributen.pop("volume_level", None)
        else:
            attributen["volume_level"] = self.volume_niveau
        if self.shuffle_stand is None:
            attributen.pop("shuffle", None)
        else:
            attributen["shuffle"] = self.shuffle_stand
        self.hass.states.async_set(self.speaker, state.state, attributen)

    def zet_volume_op(self, pct: int | None) -> None:
        """Draai zelf aan de knop, zoals een gebruiker (SPEC 9.3)."""
        self.volume_niveau = None if pct is None else pct / 100
        self._werk_state_bij()

    def zet_shuffle_op(self, stand: bool | None) -> None:
        """De shuffle-stand van de speaker vóór de wekker. `None` = niet leesbaar."""
        self.shuffle_stand = stand
        self._werk_state_bij()

    def shuffles(self) -> list[bool]:
        """De shuffle-waarden die er gezet zijn, in volgorde."""
        return [
            bool(data["shuffle"])
            for naam, data in self.aanroepen
            if naam == "media_player.shuffle_set"
        ]

    def laat_speaker_wegvallen(self) -> None:
        """Laat de speaker wegvallen zoals Home Assistant dat werkelijk doet.

        **Niet met een lege attributenlijst.** Valkuil 18 en de livemeting van
        fase 3c zeggen wat er overblijft zodra een entiteit `unavailable` is:
        `device_class`, `icon`, `friendly_name`, `supported_features` en
        `entity_picture`. Wat verdwijnt zijn de extra state attributes —
        `volume_level` en `mass_player_type`.

        Dat verschil is niet cosmetisch. Met een lege lijst zou `is_ma_speaker`
        (SPEC 7.2) een weggevallen speaker afkeuren op *ontbrekende features* in
        plaats van dat de noodrem hem afkeurt op *onbereikbaarheid*, en dan toetst
        een test een foutmelding die in productie nooit optreedt. Fase 4b liep
        hier tegenaan bij de voorbeeldknop.
        """
        state = self.hass.states.get(self.speaker)
        blijft = {}
        if state is not None:
            blijft = {
                sleutel: waarde
                for sleutel, waarde in state.attributes.items()
                if sleutel
                in ("device_class", "icon", "friendly_name", "supported_features", "entity_picture")
            }
        self.hass.states.async_set(self.speaker, "unavailable", blijft)

    def vind(self, uri: str, media_type: str = "radio") -> None:
        """Laat de URI-controle deze URI vinden (SPEC 11.2, vergelijking op de URI)."""
        self.zoekresultaat = {f"{media_type}s": [{"uri": uri, "name": "iets"}]}


async def lees_resources(hass: HomeAssistant) -> list[dict[str, Any]]:
    """De resourcelijst, met de collectie gegarandeerd ingelezen."""
    collectie = hass.data[LOVELACE_DATA].resources
    await collectie.async_get_info()
    return list(collectie.async_items())


async def onze_resources(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Alleen de resources die naar ons bundelpad wijzen, ongeacht de hash."""
    return [
        item
        for item in await lees_resources(hass)
        if item.get("url", "").partition("?")[0] == CARD_URL_PATH
    ]
