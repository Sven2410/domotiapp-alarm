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
    LOADER_URL_PATH,
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


async def test_index_importeert_de_lader_en_niet_de_bundel(
    hass: HomeAssistant, opgezet
) -> None:
    """In index.html staat de stabiele lader, niet de gehashte bundel-URL.

    NIEUW GEDRAG (fase 11) en de kern van die ronde. HA zet de import letterlijk
    in het HTML-document, en dat document wordt door de service worker gecachet;
    staat de hash erin, dan levert een gecacht document na een update de oude
    bundel op. Dat is op een verse instance gereproduceerd, zie
    docs/fase-11/RAPPORT.md.

    Faalt op de code van vóór fase 11: daar stond de gehashte URL hier.
    """
    urls = hass.data[DATA_EXTRA_MODULE_URL].urls

    assert LOADER_URL_PATH in urls, f"{LOADER_URL_PATH} niet in {urls}"

    # En de gehashte URL staat er juist NIET meer in.
    assert verwachte_url() not in urls

    # Geen enkele URL van ons in index.html mag nog een ?v= dragen: dat is
    # precies wat een verouderd document zou bevriezen.
    onze = [u for u in urls if DOMAIN in u]
    assert onze == [LOADER_URL_PATH]
    assert "?v=" not in LOADER_URL_PATH


async def test_de_lader_staat_onder_api(hass: HomeAssistant, opgezet) -> None:
    """Het /api/-voorvoegsel is dragend en geen smaak.

    REGRESSIEWACHT, en bewust zo gelabeld: deze test kijkt alleen naar de
    constante, dus hij slaagt ook op de code van vóór fase 11 zodra die constante
    bestaat. Hij bewijst geen nieuw gedrag — hij houdt een eigenschap vast die
    nergens anders afdwingbaar is. HA's service worker heeft precies één route
    die nooit cachet:
    de /api/- en /auth/-route met NetworkOnly. Verhuist de lader naar een ander
    pad, dan valt hij onder StaleWhileRevalidate en is de hele constructie
    zinloos — zonder dat er iets zichtbaar stukgaat. Vandaar deze regel.
    """
    assert LOADER_URL_PATH.startswith("/api/")


async def test_de_lader_geeft_de_hash_van_de_bundel_op_schijf(
    hass: HomeAssistant, hass_client_no_auth
) -> None:
    """De lader importeert de gehashte bundel-URL met de hash van dit moment.

    NIEUW GEDRAG. De hash wordt hier opnieuw uit het bestand berekend, zodat een
    implementatie die een vaste string of het versienummer teruggeeft faalt.
    """
    await zet_integratie_op(hass)
    client = await hass_client_no_auth()

    antwoord = await client.get(LOADER_URL_PATH)
    assert antwoord.status == 200

    tekst = await antwoord.text()
    hash_ = hashlib.sha256(BUNDEL.read_bytes()).hexdigest()[:HASH_LENGTE]
    assert f'import("{CARD_URL_PATH}?v={hash_}");' in tekst

    # Het versienummer mag er niet in staan; dat zou de oude fout zijn.
    assert "?v=1.0" not in tekst


async def test_de_lader_mag_niet_gecachet_worden(
    hass: HomeAssistant, hass_client_no_auth
) -> None:
    """Cache-Control: no-store, naast de NetworkOnly-route van de service worker.

    NIEUW GEDRAG. Twee lagen met twee redenen: de service worker dekt een
    geinstalleerde PWA, de header dekt een gewone browser. Valt de header weg,
    dan houdt de HTTP-cache de lader vast en is het probleem terug.
    """
    await zet_integratie_op(hass)
    client = await hass_client_no_auth()

    antwoord = await client.get(LOADER_URL_PATH)
    cache_control = antwoord.headers.get("Cache-Control", "")

    assert "no-store" in cache_control, f"kreeg {cache_control!r}"

    # En het content-type, want een module met een verkeerd type wordt door de
    # browser geweigerd (strikte MIME-controle op ES-modules) terwijl de server
    # gewoon 200 zegt. De mutatieproef van fase 11 vond dit als gat.
    assert "javascript" in antwoord.headers.get("Content-Type", ""), (
        antwoord.headers.get("Content-Type")
    )


async def test_de_lader_vereist_geen_token(
    hass: HomeAssistant, hass_client_no_auth
) -> None:
    """Een <script>-tag stuurt geen bearer-token mee.

    NIEUW GEDRAG, met een positieve controle op de inhoud: een 200 met een leeg
    antwoord zou ook slagen als we alleen de status controleerden, en dat is
    precies wat een verkeerd opgezette view oplevert.
    """
    await zet_integratie_op(hass)
    client = await hass_client_no_auth()

    antwoord = await client.get(LOADER_URL_PATH)

    assert antwoord.status == 200
    assert CARD_URL_PATH in await antwoord.text()


async def test_de_lader_url_verandert_niet_als_de_bundel_verandert(
    hass: HomeAssistant, hass_client_no_auth, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dit is de eigenschap waar de hele constructie op berust.

    NIEUW GEDRAG. Verandert de bundel, dan verandert wat de lader TERUGGEEFT maar
    niet WAAR hij staat. Alleen daardoor kan een verouderd document — dat de
    lader-URL bevat en niet de hash — de klant niet meer op oude code zetten.

    Met een positieve controle: eerst wordt aangetoond dat het antwoord werkelijk
    verandert, zodat "de URL bleef gelijk" niet triviaal waar is.
    """
    await zet_integratie_op(hass)
    client = await hass_client_no_auth()

    url_voor = sorted(hass.data[DATA_EXTRA_MODULE_URL].urls)
    body_voor = await (await client.get(LOADER_URL_PATH)).text()

    # Doe alsof de bundel is bijgewerkt: dezelfde setup, andere hash.
    import custom_components.domotiapp_alarm as integratie

    monkeypatch.setattr(integratie, "_bereken_hash", lambda pad: "beefbeefbeef")

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    url_na = sorted(hass.data[DATA_EXTRA_MODULE_URL].urls)
    body_na = await (await client.get(LOADER_URL_PATH)).text()

    # Positieve controle: er is werkelijk iets veranderd.
    assert body_voor != body_na, "de hash in het antwoord moet meeveranderen"
    assert "beefbeefbeef" in body_na

    # En de eigenschap zelf: het adres bleef hetzelfde.
    assert url_voor == url_na == [LOADER_URL_PATH]


async def test_lader_en_resource_wijzen_naar_dezelfde_bundel(
    hass: HomeAssistant, hass_client_no_auth
) -> None:
    """Beide routes komen op een modulespecifier uit.

    REGRESSIEWACHT. Deze eis stond er vóór fase 11 al, met dezelfde bedoeling in
    een andere vorm: toen droegen index en resource letterlijk dezelfde string,
    nu moet de lader dezelfde URL IMPORTEREN die de resource draagt. Lopen ze
    uit elkaar, dan evalueert de browser twee modules en kan de oude de
    registratierace winnen (valkuil 1).
    """
    await zet_integratie_op(hass)
    client = await hass_client_no_auth()

    resources = await onze_resources(hass)
    assert len(resources) == 1, f"verwacht precies een resource, kreeg {resources}"
    resource_url = resources[0]["url"]
    assert resources[0]["type"] == "module"

    body = await (await client.get(LOADER_URL_PATH)).text()
    assert f'import("{resource_url}");' in body
    assert resource_url == verwachte_url()


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

    # Positieve controle: de eerste route staat er wél. Sinds fase 11 is dat de
    # lader en niet meer de gehashte URL.
    assert LOADER_URL_PATH in hass.data[DATA_EXTRA_MODULE_URL].urls
    # De entry is echt geladen, niet in een foutstand terechtgekomen.
    assert entry.state is ConfigEntryState.LOADED
    # En de tweede route is netjes op None uitgekomen in plaats van te gooien.
    assert hass.data[DOMAIN][DATA_RESOURCE_ID] is None
    # Ter controle dat de nabootsing echt raakte: er staat geen resource.
    assert await onze_resources(hass) == []
