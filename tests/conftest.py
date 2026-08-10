"""Pytest-opzet voor de custom integration."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.domotiapp_alarm.const import (
    CARD_FILENAME,
    CARD_URL_PATH,
    DOMAIN,
    HASH_LENGTE,
    STORAGE_KEY,
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
        version: int = 1,
        minor_version: int = 1,
    ) -> None:
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
