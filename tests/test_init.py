"""De laadketen: statisch pad, index-import, en één URL voor beide routes.

Alles hier is **NIEUW GEDRAG**. Vóór deze fase bestond de integratie niet, dus
elke test faalt op de code van ervoor met een importfout. Dat is een triviale
mislukking, en daarom is elke test zo opgezet dat hij een *eigenschap* van de
laadketen vastlegt die ook bij toekomstige wijzigingen kan sneuvelen:

- `test_statisch_pad_geregistreerd` legt vast dat de bundel op het verwachte
  URL-pad staat en dat het pad naar een bestaand bestand wijst.
- `test_index_import_heeft_bundelhash` legt vast dat de `?v=` de **hash van het
  bestand** is en niet het versienummer. Dat is de fout die je pas merkt als een
  klant een oude bundel uit zijn cache blijft halen; hij is hier mechanisch
  aangetoond door de hash zelf opnieuw te berekenen.
- `test_beide_routes_dezelfde_url` is de kern van de ronde: één URL, twee
  routes. Lopen ze uit elkaar, dan evalueert de browser de bundel twee keer.
"""

from __future__ import annotations

import hashlib

import pytest

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.components.lovelace.resources import RESOURCE_STORAGE_KEY
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.domotiapp_alarm.const import (
    CARD_URL_PATH,
    DATA_JS_URL,
    DATA_RESOURCE_ID,
    DOMAIN,
    HASH_LENGTE,
)

from .conftest import (
    BUNDEL,
    lees_resources,
    onze_resources,
    verwachte_url,
    zet_integratie_op,
)


async def test_de_bundel_is_meegecommit() -> None:
    """De bundel hoort in de repo te staan; HACS levert wat er in de repo staat.

    NIEUW GEDRAG. Dit is geen test op gedrag maar op de oplevering, en hij staat
    hier omdat alle andere tests er stilzwijgend van uitgaan.
    """
    assert BUNDEL.is_file(), f"{BUNDEL} ontbreekt; draai npm run build"
    assert BUNDEL.stat().st_size > 0


async def test_statisch_pad_geregistreerd(hass: HomeAssistant, opgezet) -> None:
    """Setup zet de bundel op CARD_URL_PATH. NIEUW GEDRAG."""
    # De route staat in aiohttp; we controleren hem via de HTTP-app in plaats van
    # via onze eigen vlag, zodat de test niet meemeet wat hij moet bewijzen.
    paden = [
        resource.canonical
        for resource in hass.http.app.router.resources()
        if getattr(resource, "canonical", "").startswith(f"/{DOMAIN}")
    ]
    assert CARD_URL_PATH in paden, f"{CARD_URL_PATH} niet gevonden in {paden}"


async def test_index_import_heeft_bundelhash(hass: HomeAssistant, opgezet) -> None:
    """De ?v= is de hash van het bundelbestand, niet het versienummer.

    NIEUW GEDRAG, mechanisch onderbouwd: de verwachte hash wordt hier opnieuw
    uit het bestand berekend. Een implementatie die het versienummer in de ?v=
    zet, faalt hier — en dat is precies de vergissing die een verouderde bundel
    in de browsercache laat staan.
    """
    urls = hass.data[DATA_EXTRA_MODULE_URL]
    verwacht = verwachte_url()

    assert verwacht in urls.urls, f"{verwacht} niet in {urls.urls}"

    # En de hash is echt die van de bytes op schijf.
    hash_ = hashlib.sha256(BUNDEL.read_bytes()).hexdigest()[:HASH_LENGTE]
    assert verwacht.endswith(f"?v={hash_}")

    # Het versienummer mag er niet in staan; dat zou de oude fout zijn.
    manifest_versie = "0.1.0"
    assert f"?v={manifest_versie}" not in verwacht


async def test_beide_routes_dezelfde_url(hass: HomeAssistant, opgezet) -> None:
    """De index-import en de Lovelace-resource dragen exact dezelfde URL.

    NIEUW GEDRAG en de kern van deze ronde. Zou een van de twee de URL
    zelfstandig opbouwen, dan lopen ze uit elkaar zodra de bundel wijzigt en
    haalt de browser de bundel twee keer op.
    """
    index_urls = hass.data[DATA_EXTRA_MODULE_URL].urls
    resources = await onze_resources(hass)

    assert len(resources) == 1, f"verwacht precies één resource, kreeg {resources}"
    resource_url = resources[0]["url"]

    assert resource_url in index_urls
    assert resource_url == verwachte_url()
    assert resources[0]["type"] == "module"


async def test_resource_wordt_bijgewerkt_bij_hashwissel(hass: HomeAssistant) -> None:
    """Een bestaande resource met een oude hash wordt bijgewerkt, niet gedupliceerd.

    NIEUW GEDRAG. Met een positieve controle vooraf: eerst wordt aangetoond dát
    er één resource met de oude URL staat, zodat "er is er één" na de setup niet
    triviaal waar is. Zonder die controle zou een implementatie die de resource
    negeert en er zelf een aanmaakt óók op één uitkomen.
    """
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "frontend", {})
    assert await async_setup_component(hass, "lovelace", {})
    await hass.async_block_till_done()

    # Zet een resource neer met een verouderde hash, zoals na een rebuild.
    oude_url = f"{CARD_URL_PATH}?v=000000000000"
    collectie = hass.data["lovelace"].resources
    await collectie.async_get_info()
    await collectie.async_create_item({"res_type": "module", "url": oude_url})

    # Positieve controle: precies één, en met de oude URL.
    voor = await onze_resources(hass)
    assert len(voor) == 1
    assert voor[0]["url"] == oude_url

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(domain=DOMAIN, title="DomotiApp Alarm", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    na = await onze_resources(hass)
    assert len(na) == 1, "geen tweede resource ernaast"
    assert na[0]["url"] == verwachte_url(), "de hash moet bijgewerkt zijn"
    assert na[0]["id"] == voor[0]["id"], "hetzelfde item, niet een nieuw"


async def test_geen_tweede_resource_bij_ongeladen_collectie(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """Een resource die al in de opslag staat wordt gezien, niet gedupliceerd.

    NIEUW GEDRAG, en de enige test die de valkuil uit `resource.py` echt raakt:
    de resourcecollectie leest zijn opslag pas bij het eerste gebruik, dus
    `async_items()` geeft zonder `async_get_info()` een **lege lijst** terug — en
    dan zou de integratie een tweede resource naast de bestaande zetten.

    Waarom dit niet met `async_create_item` te toetsen is: die aanroep laadt de
    collectie zelf, en daarna is de valkuil weg. Daarom wordt hier
    **rechtstreeks in de opslag** geschreven, vóórdat de collectie ooit is
    aangeraakt. Dat is precies de situatie bij een herstart van Home Assistant.
    """
    oude_url = f"{CARD_URL_PATH}?v=111111111111"
    # De versie van **Lovelace's** resourceopslag, niet die van ons: die staat op 1
    # en heeft met onze schemaversie niets te maken.
    hass_storage[RESOURCE_STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": RESOURCE_STORAGE_KEY,
        "data": {
            "items": [
                {"id": "bestaand-item", "type": "module", "url": oude_url},
            ]
        },
    }

    entry = await zet_integratie_op(hass)
    assert entry.state is ConfigEntryState.LOADED

    na = await onze_resources(hass)
    assert len(na) == 1, (
        "de bestaande resource uit de opslag moet hergebruikt zijn; "
        f"gevonden: {na}"
    )
    assert na[0]["id"] == "bestaand-item", "hetzelfde item, niet een nieuw ernaast"
    assert na[0]["url"] == verwachte_url(), "en bijgewerkt naar de verse hash"


async def test_resource_blijft_staan_bij_unload(hass: HomeAssistant) -> None:
    """Een unload laat de resource staan; alleen remove_entry haalt hem weg.

    NIEUW GEDRAG. Unload draait óók bij elke reload — de handeling die na iedere
    rebuild nodig is — en de resource zou dan verdwijnen en terugkomen.
    """
    entry = await zet_integratie_op(hass)
    assert len(await onze_resources(hass)) == 1

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert len(await onze_resources(hass)) == 1, "resource moet blijven staan"

    # De index-import verdwijnt wél.
    assert verwachte_url() not in hass.data[DATA_EXTRA_MODULE_URL].urls
    assert DATA_JS_URL not in hass.data[DOMAIN]


async def test_resource_verdwijnt_bij_remove(hass: HomeAssistant) -> None:
    """remove_entry haalt de resource weg. NIEUW GEDRAG.

    Positieve controle vooraf: er staat er één vóór het verwijderen, dus "er
    staat er geen" is daarna geen triviale waarheid.
    """
    entry = await zet_integratie_op(hass)
    assert len(await onze_resources(hass)) == 1

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert await onze_resources(hass) == []


async def test_resource_van_iemand_anders_blijft(hass: HomeAssistant) -> None:
    """Resources die niet naar ons pad wijzen blijven onaangeroerd.

    NIEUW GEDRAG. Ongevraagd andermans resources weggooien is erger dan een
    dubbele import.
    """
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "frontend", {})
    assert await async_setup_component(hass, "lovelace", {})
    await hass.async_block_till_done()

    collectie = hass.data["lovelace"].resources
    await collectie.async_get_info()
    vreemd = await collectie.async_create_item(
        {"res_type": "module", "url": "/local/iemand-anders.js"}
    )

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(domain=DOMAIN, title="DomotiApp Alarm", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    alle = await lees_resources(hass)
    assert "/local/iemand-anders.js" in [item["url"] for item in alle]
    assert vreemd["id"] in [item["id"] for item in alle]
    # En onze eigen resource is wél weg.
    assert await onze_resources(hass) == []


async def test_setup_gaat_niet_stuk_zonder_lovelace_opslag(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Faalt de resourceregistratie, dan draait de integratie tóch.

    NIEUW GEDRAG, met een positieve controle: eerst wordt aangetoond dat de
    index-import er staat, zodat "setup faalt niet" niet triviaal waar is in
    code die de resource helemaal niet aanraakt.
    """
    from custom_components.domotiapp_alarm import resource as resource_module

    async def stuk(*args, **kwargs):
        raise RuntimeError("opslag onbruikbaar")

    monkeypatch.setattr(
        resource_module, "_async_lees_collectie", stuk, raising=True
    )

    entry = await zet_integratie_op(hass)

    # Positieve controle: de eerste route staat er wél.
    assert verwachte_url() in hass.data[DATA_EXTRA_MODULE_URL].urls
    # De entry is echt geladen, niet in een foutstand terechtgekomen.
    assert entry.state is ConfigEntryState.LOADED
    # En de tweede route is netjes op None uitgekomen in plaats van te gooien.
    assert hass.data[DOMAIN][DATA_RESOURCE_ID] is None
    # Ter controle dat de nabootsing echt raakte: er staat geen resource.
    assert await onze_resources(hass) == []
