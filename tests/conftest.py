"""Pytest-opzet voor de custom integration."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.domotiapp_alarm.const import (
    CARD_FILENAME,
    CARD_URL_PATH,
    DOMAIN,
    HASH_LENGTE,
)

pytest_plugins = "pytest_homeassistant_custom_component"

BUNDEL = (
    Path(__file__).parent.parent
    / "custom_components"
    / DOMAIN
    / "frontend"
    / CARD_FILENAME
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Laat Home Assistant custom_components/ zien in elke test."""
    return


def verwachte_url() -> str:
    """De URL die de integratie hoort te gebruiken: pad plus bundelhash.

    Bewust opnieuw berekend uit het bestand op schijf en niet overgenomen uit de
    integratie: anders zou de test de aanname meemeten in plaats van te
    controleren.
    """
    hash_ = hashlib.sha256(BUNDEL.read_bytes()).hexdigest()[:HASH_LENGTE]
    return f"{CARD_URL_PATH}?v={hash_}"


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


async def lees_resources(hass: HomeAssistant) -> list[dict[str, Any]]:
    """De resourcelijst, met de collectie gegarandeerd ingelezen.

    Zonder `async_get_info()` geeft `async_items()` een lege lijst — dezelfde
    valkuil die `resource.py` zelf moet omzeilen.
    """
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
