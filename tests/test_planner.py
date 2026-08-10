"""De planner (SPEC 13): plannen, herplannen, inhalen.

Alles **NIEUW GEDRAG**: er was geen planner. Elke test legt een regel uit SPEC 13
vast. De kern van deze fase is het respijtvenster, en daar zitten de tests die het
verschil maken tussen "gaat af" en "gaat stil niet af".

De tijd wordt gemanipuleerd met `freezer` plus `async_fire_time_changed`; er wordt
nergens gewacht. De tijdzone staat op **Europe/Amsterdam**, want de
zomertijdgevallen zijn anders niet te toetsen.

**Waarom bijna geen WebSocket in dit bestand.** Het toegangstoken van
`hass_ws_client` is een JWT met `iat`/`exp`, en dat verdraagt een teruggezette klok
niet: verbinden op een frozen 06:00 terwijl de echte klok verder staat, geeft
`auth_invalid`. De mutaties gaan daarom via de Store plus `async_herplan` — precies
wat de commando's doen. Dát de commando's dat aanroepen, staat in
`test_websocket_save_herplant`, en die beweegt de klok niet.
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.const import EVENT_CORE_CONFIG_UPDATE
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.domotiapp_alarm import afvuren, meldingen
from custom_components.domotiapp_alarm import planner as planner_mod
from custom_components.domotiapp_alarm import ringing
from custom_components.domotiapp_alarm.const import (
    DATA_PLANNER,
    DATA_STORE,
    DOMAIN,
    STORAGE_KEY,
)

from .conftest import PERSON_ENTITY_ID, geldige_wekker, maak_speaker, registreer_person

AMS = ZoneInfo("Europe/Amsterdam")
GOEDE_FEATURES = int(
    MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.VOLUME_SET
)
ALARM_ID = "a" * 32


def volledige_wekker(**overschrijf: Any) -> dict[str, Any]:
    """Een wekker zoals hij in de opslag staat, dus met de boekhoudvelden."""
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


async def _setup(hass: HomeAssistant, hass_storage: dict, persons: Any) -> str:
    """Ruwe opslag klaarzetten en de integratie opzetten. Geeft het registry-ID."""
    await hass.config.async_update(time_zone="Europe/Amsterdam")
    registry_id = registreer_person(hass)
    maak_speaker(hass, features=GOEDE_FEATURES)
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": {"persons": persons},
    }
    assert await async_setup_component(hass, "frontend", {})
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="DomotiApp Alarm", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hass.data.setdefault("_test_entry", entry)
    return registry_id


async def zet_op(
    hass: HomeAssistant, wekkers: list[dict[str, Any]], hass_storage: dict
) -> str:
    """Zoals `_setup`, maar met de wekkers van één gezonde persoon.

    De opslag wordt **vóór** de setup geschreven, want de inhaalslag draait bij setup
    en moet die data zien.
    """
    await hass.config.async_update(time_zone="Europe/Amsterdam")
    registry_id = registreer_person(hass)
    maak_speaker(hass, features=GOEDE_FEATURES)
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": {"persons": {registry_id: {"alarms": wekkers}}},
    }
    assert await async_setup_component(hass, "frontend", {})
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="DomotiApp Alarm", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hass.data["_test_entry"] = entry
    return registry_id


def afgegaan(hass: HomeAssistant, registry_id: str, alarm_id: str = ALARM_ID) -> bool:
    return ringing.register_van(hass).is_afgaand(registry_id, alarm_id)


def uit_opslag(hass: HomeAssistant, registry_id: str, alarm_id: str = ALARM_ID) -> dict:
    return hass.data[DOMAIN][DATA_STORE].wekker(registry_id, alarm_id)


async def tik(hass: HomeAssistant, freezer, doel: dt.datetime) -> None:
    """Zet de klok op `doel` en laat HA's timers afgaan."""
    freezer.move_to(doel)
    async_fire_time_changed(hass, doel)
    await hass.async_block_till_done()


async def stop(hass: HomeAssistant, registry_id: str) -> None:
    await afvuren.async_stop_afgaan(
        hass, registry_id, PERSON_ENTITY_ID, ALARM_ID, ringing.REASON_USER
    )


# --- 1. herhaaldagen ----------------------------------------------------


async def test_herhalende_wekker_vuurt_op_de_juiste_dagen(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """Vuurt op de aangevinkte dagen en niet op de andere.

    NIEUW GEDRAG. Verplicht geval 1. De dagfiltering gebeurt in de callback en niet in
    de planner (SPEC 13.1), dus een implementatie die de dag vergeet vuurt hier op
    zaterdag.
    """
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 0, tzinfo=AMS))  # maandag
    registry_id = await zet_op(
        hass, [volledige_wekker(time="06:45", days=[1, 2, 3, 4, 5])], hass_storage
    )
    assert not afgegaan(hass, registry_id)

    await tik(hass, freezer, dt.datetime(2026, 8, 10, 6, 45, 1, tzinfo=AMS))
    assert afgegaan(hass, registry_id), "maandag hoort af te gaan"
    await stop(hass, registry_id)

    await tik(hass, freezer, dt.datetime(2026, 8, 15, 6, 45, 1, tzinfo=AMS))
    assert not afgegaan(hass, registry_id), "zaterdag staat niet aangevinkt"

    await tik(hass, freezer, dt.datetime(2026, 8, 17, 6, 45, 1, tzinfo=AMS))
    assert afgegaan(hass, registry_id), "de volgende maandag hoort weer af te gaan"


# --- 2. eenmalige wekker -----------------------------------------------


async def test_eenmalige_wekker_vuurt_een_keer(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """Vuurt één keer en daarna nooit meer. NIEUW GEDRAG. Verplicht geval 2."""
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 0, tzinfo=AMS))
    moment = dt.datetime(2026, 8, 10, 6, 45, tzinfo=AMS)
    registry_id = await zet_op(
        hass,
        [volledige_wekker(time="06:45", days=[], one_shot_at=moment.isoformat())],
        hass_storage,
    )
    planner = hass.data[DOMAIN][DATA_PLANNER]
    assert planner.geplande_wekkers == {(registry_id, ALARM_ID)}

    await tik(hass, freezer, dt.datetime(2026, 8, 10, 6, 45, 1, tzinfo=AMS))
    assert afgegaan(hass, registry_id)
    assert uit_opslag(hass, registry_id)["last_fired"] == moment.isoformat()

    await stop(hass, registry_id)
    await tik(hass, freezer, dt.datetime(2026, 8, 11, 6, 45, 1, tzinfo=AMS))
    assert not afgegaan(hass, registry_id), "een eenmalige wekker vuurt niet opnieuw"


# --- 3, 4, 5. het respijtvenster --------------------------------------


async def test_herstart_5_minuten_te_laat_haalt_in(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """5 minuten te laat: gaat alsnog af (SPEC 13.4 stap 5).

    NIEUW GEDRAG. Verplicht geval 3.
    """
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 50, tzinfo=AMS))
    registry_id = await zet_op(
        hass, [volledige_wekker(time="06:45", days=[1, 2, 3, 4, 5])], hass_storage
    )
    assert afgegaan(hass, registry_id), "binnen het respijtvenster hoort hij af te gaan"

    wekker = uit_opslag(hass, registry_id)
    # last_fired staat op het BEDOELDE moment, niet op "nu": anders schuift de
    # vergelijking uit stap 3 elke herstart mee op.
    assert wekker["last_fired"] == dt.datetime(2026, 8, 10, 6, 45, tzinfo=AMS).isoformat()
    assert wekker["last_message"] is None, "een ingehaalde wekker is geen mededeling"


async def test_herstart_45_minuten_te_laat_slaat_over_met_mededeling(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """45 minuten te laat: overgeslagen, met een mededeling (SPEC 13.4 stap 6).

    NIEUW GEDRAG. Verplicht geval 4. De tekst is die uit SPEC 13.4, letterlijk, en de
    severity is `notice` en niet `error`.
    """
    freezer.move_to(dt.datetime(2026, 8, 10, 7, 30, tzinfo=AMS))
    registry_id = await zet_op(
        hass, [volledige_wekker(time="06:45", days=[1, 2, 3, 4, 5])], hass_storage
    )
    assert not afgegaan(hass, registry_id), "buiten het respijtvenster: niet afgaan"

    message = uit_opslag(hass, registry_id)["last_message"]
    assert message is not None, "er hoort een mededeling te staan"
    assert message["kind"] == meldingen.KIND_SKIPPED_GRACE_WINDOW
    assert message["severity"] == "notice"
    assert message["text"] == (
        "Je wekker van 06:45 is niet afgegaan omdat Home Assistant uit stond."
    )


async def test_herstart_te_laat_met_last_fired_vuurt_niet_opnieuw(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """Het geval waar het stil mis kan gaan (SPEC 13.4 stap 3).

    NIEUW GEDRAG. Verplicht geval 5, en de belangrijkste test van deze fase.

    Herstart 5 minuten ná de wektijd, maar `last_fired` staat al op dat moment: de
    wekker is al afgegaan en mag **niet** opnieuw. Een implementatie die stap 3
    overslaat, laat de wekker bij elke herstart binnen het respijtvenster opnieuw
    afgaan — en jaagt een klant om 06:50 uit bed terwijl hij al op was.
    """
    moment = dt.datetime(2026, 8, 10, 6, 45, tzinfo=AMS)
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 50, tzinfo=AMS))
    registry_id = await zet_op(
        hass,
        [
            volledige_wekker(
                time="06:45", days=[1, 2, 3, 4, 5], last_fired=moment.isoformat()
            )
        ],
        hass_storage,
    )
    assert not afgegaan(hass, registry_id), "al afgegaan; mag niet opnieuw"
    assert uit_opslag(hass, registry_id)["last_message"] is None


async def test_last_fired_met_jitter_blokkeert_ook(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """`last_fired` met de jitter erin blokkeert nog steeds (SPEC 13.4 stap 3).

    NIEUW GEDRAG. `async_track_time_change` vuurt 50–500 ms ná de seconde, dus in de
    praktijk staat `last_fired` net ná het moment. De vergelijking is `>=`; een
    implementatie die op gelijkheid vergelijkt, faalt hier.
    """
    net_na = dt.datetime(2026, 8, 10, 6, 45, 0, 312000, tzinfo=AMS)
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 50, tzinfo=AMS))
    registry_id = await zet_op(
        hass,
        [volledige_wekker(time="06:45", days=[1], last_fired=net_na.isoformat())],
        hass_storage,
    )
    assert not afgegaan(hass, registry_id)


async def test_inhaalslag_kijkt_alleen_naar_het_laatste_moment(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """Alleen het **laatst** verstreken moment telt (SPEC 13.4 stap 1).

    NIEUW GEDRAG. HA staat drie dagen uit; dan is er niet drie keer iets in te halen
    maar één keer. Een implementatie die alle gemiste momenten afloopt, zou hier drie
    keer melden of drie keer vuren.
    """
    freezer.move_to(dt.datetime(2026, 8, 13, 12, 0, tzinfo=AMS))  # donderdagmiddag
    registry_id = await zet_op(
        hass, [volledige_wekker(time="06:45", days=[1, 2, 3, 4, 5])], hass_storage
    )
    assert not afgegaan(hass, registry_id)
    wekker = uit_opslag(hass, registry_id)
    assert wekker["last_message"]["kind"] == meldingen.KIND_SKIPPED_GRACE_WINDOW
    # Donderdag 06:45, niet maandag.
    assert wekker["last_fired"] == dt.datetime(2026, 8, 13, 6, 45, tzinfo=AMS).isoformat()


# --- 6. skip_next -----------------------------------------------------


async def test_skip_next_slaat_een_moment_over_en_wordt_gewist(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """`skip_next` slaat precies één moment over en wordt daarna gewist.

    NIEUW GEDRAG. Verplicht geval 6. Een implementatie die `skip_next` laat staan,
    slaat élke volgende dag over — de wekker is dan stil uitgezet.

    `last_fired` staat op het vorige moment (vrijdag), zodat de inhaalslag bij setup
    niets vindt. Zonder dat wordt de skip al op dát gemiste moment opgebruikt; zie het
    rapport onder "wat niet lukte" — SPEC 13.4 stap 4 laat dat open.
    """
    vrijdag = dt.datetime(2026, 8, 7, 6, 45, tzinfo=AMS)
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 0, tzinfo=AMS))  # maandag
    registry_id = await zet_op(
        hass,
        [
            volledige_wekker(
                time="06:45",
                days=[1, 2, 3, 4, 5],
                skip_next=True,
                last_fired=vrijdag.isoformat(),
            )
        ],
        hass_storage,
    )
    assert uit_opslag(hass, registry_id)["skip_next"] is True, "nog niet opgebruikt"

    await tik(hass, freezer, dt.datetime(2026, 8, 10, 6, 45, 1, tzinfo=AMS))
    assert not afgegaan(hass, registry_id)
    wekker = uit_opslag(hass, registry_id)
    assert wekker["skip_next"] is False, "skip_next hoort gewist te zijn"
    assert wekker["last_message"]["kind"] == meldingen.KIND_SKIPPED_BY_USER
    assert wekker["last_message"]["severity"] == "notice"

    await tik(hass, freezer, dt.datetime(2026, 8, 11, 6, 45, 1, tzinfo=AMS))
    assert afgegaan(hass, registry_id), "de dag erna hoort hij weer af te gaan"


# --- 7, 8, 11. herplannen ---------------------------------------------


async def test_wijzigen_zegt_de_oude_planning_op(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """Een wekker wijzigen: de oude planning is weg (SPEC 13.5).

    NIEUW GEDRAG. Verplicht geval 7, en dit is de test op de **verdwaalde listener**:
    na het verzetten van 06:45 naar 08:00 mag er om 06:45 niets meer gebeuren. Een
    implementatie die incrementeel bijwerkt en de oude listener laat staan, faalt hier.
    """
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 0, tzinfo=AMS))
    registry_id = await zet_op(
        hass, [volledige_wekker(time="06:45", days=[1, 2, 3, 4, 5])], hass_storage
    )
    planner = hass.data[DOMAIN][DATA_PLANNER]
    assert planner.geplande_wekkers == {(registry_id, ALARM_ID)}
    voor = planner._listeners[(registry_id, ALARM_ID)]  # noqa: SLF001

    store = hass.data[DOMAIN][DATA_STORE]
    await store.async_werk_velden_bij(registry_id, ALARM_ID, {"time": "08:00"})
    await planner_mod.async_herplan(hass)

    assert planner.geplande_wekkers == {(registry_id, ALARM_ID)}, "precies één listener"
    assert planner._listeners[(registry_id, ALARM_ID)] is not voor  # noqa: SLF001

    await tik(hass, freezer, dt.datetime(2026, 8, 10, 6, 45, 1, tzinfo=AMS))
    assert not afgegaan(hass, registry_id), "de oude tijd mag niet meer vuren"

    await tik(hass, freezer, dt.datetime(2026, 8, 10, 8, 0, 1, tzinfo=AMS))
    assert afgegaan(hass, registry_id), "de nieuwe tijd hoort te vuren"


async def test_verwijderen_laat_niets_meer_vuren(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """Verwijderen terwijl hij gepland staat (SPEC 13.5, 15.4).

    NIEUW GEDRAG. Verplicht geval 8.
    """
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 0, tzinfo=AMS))
    registry_id = await zet_op(
        hass, [volledige_wekker(time="06:45", days=[1, 2, 3, 4, 5])], hass_storage
    )
    planner = hass.data[DOMAIN][DATA_PLANNER]
    assert planner.geplande_wekkers

    store = hass.data[DOMAIN][DATA_STORE]
    assert await store.async_verwijder_wekker(registry_id, ALARM_ID)
    await planner_mod.async_herplan(hass)
    assert planner.geplande_wekkers == set(), "geen listener meer"

    await tik(hass, freezer, dt.datetime(2026, 8, 10, 6, 45, 1, tzinfo=AMS))
    assert not afgegaan(hass, registry_id)


async def test_uitzetten_zegt_de_planning_op(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """NIEUW GEDRAG. Verplicht geval 11, tweede helft."""
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 0, tzinfo=AMS))
    registry_id = await zet_op(
        hass, [volledige_wekker(time="06:45", days=[1, 2, 3, 4, 5])], hass_storage
    )
    planner = hass.data[DOMAIN][DATA_PLANNER]

    store = hass.data[DOMAIN][DATA_STORE]
    await store.async_werk_velden_bij(registry_id, ALARM_ID, {"enabled": False})
    await planner_mod.async_herplan(hass)
    assert planner.geplande_wekkers == set()

    await tik(hass, freezer, dt.datetime(2026, 8, 10, 6, 45, 1, tzinfo=AMS))
    assert not afgegaan(hass, registry_id)


async def test_uitgezette_wekker_wordt_niet_ingehaald(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """Niet gepland en niet ingehaald.

    NIEUW GEDRAG. Verplicht geval 11, eerste helft. Herstart binnen het
    respijtvenster, maar de wekker staat uit: niets, en géén mededeling.
    """
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 50, tzinfo=AMS))
    registry_id = await zet_op(
        hass,
        [volledige_wekker(time="06:45", days=[1, 2, 3, 4, 5], enabled=False)],
        hass_storage,
    )
    assert hass.data[DOMAIN][DATA_PLANNER].geplande_wekkers == set()
    assert not afgegaan(hass, registry_id)
    assert uit_opslag(hass, registry_id)["last_message"] is None


# --- 9. tijdzone ------------------------------------------------------


async def test_tijdzonewijziging_herplant(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """Een tijdzonewijziging bouwt de planning opnieuw op (SPEC 13.2).

    NIEUW GEDRAG. Verplicht geval 9. `_TrackUTCTimeChange` luistert zélf niet op
    `EVENT_CORE_CONFIG_UPDATE` (gemeten in fase 0, `helpers/event.py:1750`), dus de
    integratie moet het doen. Bewijs: de opzegfunctie is een andere dan ervoor.
    """
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 0, tzinfo=AMS))
    registry_id = await zet_op(
        hass, [volledige_wekker(time="06:45", days=[1, 2, 3, 4, 5])], hass_storage
    )
    planner = hass.data[DOMAIN][DATA_PLANNER]
    voor = planner._listeners[(registry_id, ALARM_ID)]  # noqa: SLF001

    hass.bus.async_fire(EVENT_CORE_CONFIG_UPDATE, {"time_zone": "Europe/Lisbon"})
    await hass.async_block_till_done()

    na = planner._listeners[(registry_id, ALARM_ID)]  # noqa: SLF001
    assert na is not voor, "de listener hoort vervangen te zijn"
    assert planner.geplande_wekkers == {(registry_id, ALARM_ID)}, "en er is er precies één"


# --- 10. zomertijd ----------------------------------------------------


async def test_voorjaar_0230_wordt_overgeslagen(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """02:30 bestaat niet op 29 maart 2026: die nacht gaat de wekker niet af.

    NIEUW GEDRAG. Verplicht geval 10, eerste helft. Fase 3a toetste dit in
    `volgende.py`; deze test controleert dat de **planner** hetzelfde doet, want die
    gebruikt `async_track_time_change` en niet onze eigen rekenkunde.

    `last_fired` staat op 02:30 van de vorige dag, zodat de inhaalslag bij setup niets
    doet en de test alleen over vooruit plannen gaat.
    """
    vorige = dt.datetime(2026, 3, 28, 2, 30, tzinfo=AMS)
    freezer.move_to(dt.datetime(2026, 3, 28, 23, 0, tzinfo=AMS))
    registry_id = await zet_op(
        hass,
        [
            volledige_wekker(
                time="02:30", days=[1, 2, 3, 4, 5, 6, 7], last_fired=vorige.isoformat()
            )
        ],
        hass_storage,
    )
    assert not afgegaan(hass, registry_id)

    await tik(hass, freezer, dt.datetime(2026, 3, 29, 4, 0, tzinfo=AMS))
    assert not afgegaan(hass, registry_id), "02:30 bestaat die nacht niet"

    await tik(hass, freezer, dt.datetime(2026, 3, 30, 2, 30, 1, tzinfo=AMS))
    assert afgegaan(hass, registry_id), "30 maart 02:30 bestaat wel"


async def test_najaar_0230_vuurt_twee_keer(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """02:30 komt op 25 oktober 2026 twee keer voorbij, en vuurt twee keer.

    NIEUW GEDRAG. Verplicht geval 10, tweede helft, en het geval waar de opdracht
    expliciet naar vroeg: **werkt `last_fired` daar zoals bedoeld, of blokkeert het de
    tweede?**

    Het werkt, omdat de vergelijking op het **absolute moment** gaat en niet op de
    wandklok: het eerste moment is 02:30+02:00 (UTC 00:30), het tweede 02:30+01:00
    (UTC 01:30). `last_fired` van het eerste is dus kleiner dan het tweede moment.

    Een implementatie die op de wandkloktijd vergelijkt — bijvoorbeeld alleen op datum
    plus `HH:MM` — blokkeert de tweede en faalt hier.
    """
    vorige = dt.datetime(2026, 10, 24, 2, 30, tzinfo=AMS)
    freezer.move_to(dt.datetime(2026, 10, 25, 1, 0, tzinfo=AMS))
    registry_id = await zet_op(
        hass,
        [
            volledige_wekker(
                time="02:30", days=[1, 2, 3, 4, 5, 6, 7], last_fired=vorige.isoformat()
            )
        ],
        hass_storage,
    )

    eerste_utc = dt.datetime(2026, 10, 25, 0, 30, tzinfo=dt.UTC)
    tweede_utc = dt.datetime(2026, 10, 25, 1, 30, tzinfo=dt.UTC)

    await tik(hass, freezer, eerste_utc + dt.timedelta(seconds=1))
    assert afgegaan(hass, registry_id), "eerste 02:30 (UTC 00:30)"
    eerste_last_fired = uit_opslag(hass, registry_id)["last_fired"]
    await stop(hass, registry_id)

    await tik(hass, freezer, tweede_utc + dt.timedelta(seconds=1))
    assert afgegaan(hass, registry_id), (
        "tweede 02:30 (UTC 01:30) hoort óók af te gaan; SPEC 13.1 schrijft twee keer voor"
    )
    tweede_last_fired = uit_opslag(hass, registry_id)["last_fired"]
    assert dt.datetime.fromisoformat(tweede_last_fired) > dt.datetime.fromisoformat(
        eerste_last_fired
    ), "het tweede moment is een later absoluut moment"


# --- ringing en de events ---------------------------------------------


async def test_started_event_gaat_naar_de_abonnees(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """Een afgaande wekker stuurt `started` naar de abonnees (SPEC 15.9).

    NIEUW GEDRAG. Fase 3a kon alleen aantonen dat het doorgeefluik werkte door het
    register zélf te vullen; hier vult de **planner** het, en dat is het stuk dat 3a
    nog niet kon bewijzen.
    """
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 0, tzinfo=AMS))
    registry_id = await zet_op(
        hass,
        [volledige_wekker(time="06:45", days=[1, 2, 3, 4, 5], name="Werk")],
        hass_storage,
    )

    ontvangen: list[dict] = []
    ringing.register_van(hass).abonneer(ontvangen.append)

    await tik(hass, freezer, dt.datetime(2026, 8, 10, 6, 45, 1, tzinfo=AMS))

    assert ontvangen == [
        {
            "event": "started",
            "person": PERSON_ENTITY_ID,
            "alarm_id": ALARM_ID,
            "name": "Werk",
            "time": "06:45",
        }
    ]
    assert ringing.register_van(hass).afgaand_voor(registry_id) == [ALARM_ID]


async def test_stop_stuurt_stopped_event_en_is_idempotent(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """NIEUW GEDRAG (SPEC 15.9), en stoppen is idempotent (SPEC 15.8)."""
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 50, tzinfo=AMS))
    registry_id = await zet_op(
        hass, [volledige_wekker(time="06:45", days=[1, 2, 3, 4, 5])], hass_storage
    )
    assert afgegaan(hass, registry_id), "ingehaald, dus hij loopt"

    ontvangen: list[dict] = []
    ringing.register_van(hass).abonneer(ontvangen.append)

    assert await afvuren.async_stop_afgaan(
        hass, registry_id, PERSON_ENTITY_ID, ALARM_ID, ringing.REASON_USER
    )
    assert ontvangen == [
        {
            "event": "stopped",
            "person": PERSON_ENTITY_ID,
            "alarm_id": ALARM_ID,
            "reason": "user",
        }
    ]
    assert not afgegaan(hass, registry_id)

    assert not await afvuren.async_stop_afgaan(
        hass, registry_id, PERSON_ENTITY_ID, ALARM_ID, ringing.REASON_USER
    ), "stoppen wat niet loopt is geen fout, maar levert ook geen tweede bericht op"
    assert len(ontvangen) == 1


async def test_websocket_save_herplant(
    hass: HomeAssistant, hass_ws_client, hass_storage
) -> None:
    """Een save via de WebSocket roept de herplanning aan (SPEC 13.5).

    NIEUW GEDRAG. Deze test beweegt de klok **niet**: hij bewijst alleen dat de
    WebSocket-laag en de planner aan elkaar geknoopt zijn, door te kijken of er na een
    save een listener bij is gekomen. Het gedrag van die listener staat in de tests
    hierboven.

    Zonder deze test zou die koppeling ongetoetst zijn: alle andere planner-tests
    roepen `async_herplan` zelf aan.
    """
    registry_id = await zet_op(hass, [], hass_storage)
    planner = hass.data[DOMAIN][DATA_PLANNER]
    assert planner.geplande_wekkers == set()

    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/alarms/save",
            "person": PERSON_ENTITY_ID,
            "alarm": geldige_wekker(days=[1, 2, 3, 4, 5]),
        }
    )
    antwoord = await client.receive_json()
    assert antwoord["success"], antwoord
    alarm_id = antwoord["result"]["alarms"][0]["id"]

    assert planner.geplande_wekkers == {(registry_id, alarm_id)}, (
        "na een save hoort de planner een listener te hebben; zonder de aanroep van "
        "async_herplan in websocket.py blijft dit leeg"
    )
    await client.close()


# --- repair issues (SPEC 19.2) ----------------------------------------


async def test_repair_issue_bij_kapotte_persoon(hass: HomeAssistant, hass_storage) -> None:
    """Een kapotte persoon levert een repair issue op (SPEC 19.2 geval B regel 4).

    NIEUW GEDRAG, en het gat dat fase 3a bewust open liet.
    """
    from homeassistant.helpers import issue_registry as ir

    from custom_components.domotiapp_alarm.const import ISSUE_CORRUPT_PERSON_PREFIX

    kapot_id = "x" * 32
    await _setup(hass, hass_storage, {kapot_id: {"alarms": "geen lijst"}})
    sleutels = [k for k in ir.async_get(hass).issues if k[0] == DOMAIN]
    assert sleutels, "er hoort een repair issue te zijn"
    assert any(k[1] == f"{ISSUE_CORRUPT_PERSON_PREFIX}{kapot_id}" for k in sleutels)


async def test_repair_issue_bij_onbruikbare_opslag(
    hass: HomeAssistant, hass_storage
) -> None:
    """Geval C levert één repair issue op (SPEC 19.2 geval C regel 3). NIEUW GEDRAG."""
    from homeassistant.helpers import issue_registry as ir

    from custom_components.domotiapp_alarm.const import ISSUE_STORE_UNUSABLE

    await _setup(hass, hass_storage, "onzin")
    assert (DOMAIN, ISSUE_STORE_UNUSABLE) in ir.async_get(hass).issues


async def test_geen_repair_issue_bij_gezonde_opslag(
    hass: HomeAssistant, hass_storage
) -> None:
    """De positieve controle onder de twee tests hierboven.

    NIEUW GEDRAG. Zonder deze zou "er is een issue" ook waar kunnen zijn omdat er
    altijd een issue wordt aangemaakt.
    """
    from homeassistant.helpers import issue_registry as ir

    await zet_op(hass, [volledige_wekker()], hass_storage)
    assert [k for k in ir.async_get(hass).issues if k[0] == DOMAIN] == []


# --- unload -----------------------------------------------------------


async def test_unload_zegt_de_listeners_op(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """Na unload vuurt er niets meer (SPEC 13.5).

    NIEUW GEDRAG. Een listener die na het loslaten van de opslag nog vuurt, zou op een
    Store lezen die er niet meer is.
    """
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 0, tzinfo=AMS))
    registry_id = await zet_op(
        hass, [volledige_wekker(time="06:45", days=[1, 2, 3, 4, 5])], hass_storage
    )
    planner = hass.data[DOMAIN][DATA_PLANNER]
    assert planner.geplande_wekkers
    entry = hass.data["_test_entry"]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert planner.geplande_wekkers == set()
    assert DATA_PLANNER not in hass.data[DOMAIN]

    await tik(hass, freezer, dt.datetime(2026, 8, 10, 6, 45, 1, tzinfo=AMS))
    assert not afgegaan(hass, registry_id)


# --- de rem, rechtstreeks getoetst ------------------------------------


async def test_de_rem_weigert_een_moment_ver_in_het_verleden(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """Rem 2 in het afvuurpad, rechtstreeks getoetst.

    NIEUW GEDRAG. Een `async_track_point_in_time` in het verleden vuurt onmiddellijk
    (+0,0002 s, gemeten in fase 0). De planner weigert zo'n moment al bij het plannen,
    maar de weigering staat óók in het afvuurpad — en die is via de normale route niet
    te bereiken. Daarom hier rechtstreeks, met dezelfde onderbouwing als in fase 3a
    voor de schrijfguard van geval C: de invariant is belangrijker dan de zichtbaarheid.
    """
    moment = dt.datetime(2026, 8, 10, 6, 45, tzinfo=AMS)
    freezer.move_to(dt.datetime(2026, 8, 10, 14, 0, tzinfo=AMS))
    registry_id = await zet_op(
        hass,
        [volledige_wekker(time="06:45", days=[1], last_fired=moment.isoformat())],
        hass_storage,
    )
    planner = hass.data[DOMAIN][DATA_PLANNER]
    # last_fired op None zetten in de kopie, zodat alleen het respijtvenster nog
    # tegenhoudt en de test precies die ene rem toetst.
    wekker = {**uit_opslag(hass, registry_id), "last_fired": None}

    gevuurd = await planner._async_vuur(  # noqa: SLF001 - zie docstring
        registry_id, PERSON_ENTITY_ID, wekker, moment
    )
    assert gevuurd is False, "een wekker van vanmorgen mag om 14:00 niet afgaan"
    assert not afgegaan(hass, registry_id)


async def test_de_rem_weigert_een_tweede_keer_op_hetzelfde_moment(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """Rem 2, andere helft: `last_fired` weigert hetzelfde moment een tweede keer.

    NIEUW GEDRAG, en deze test bestaat door een mutatietest. Het weghalen van de
    `last_fired`-vergelijking in `_async_vuur` liet **geen** test falen: de inhaalslag
    heeft dezelfde controle als stap 3, en die zit ervóór. Dat is redundante
    verdediging en geen dode code — de controle in `_async_vuur` beschermt het
    **callbackpad**, waar de inhaalslag niet langskomt.

    Dat pad is via de normale route niet dubbel te laten vuren, want de planner zet één
    listener per wekker. Daarom hier rechtstreeks: twee keer hetzelfde moment aanbieden,
    en de tweede hoort geweigerd te worden. Zonder deze controle zou een dubbel
    geleverde timer een wekker twee keer laten afgaan.

    Dit is dezelfde afweging als in fase 3a bij de schrijfguard van geval C, en dezelfde
    les: een overlevende mutatie kan redundante verdediging zijn — je scheidt dat van een
    testgat door de invariant apart te toetsen.
    """
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 44, tzinfo=AMS))
    registry_id = await zet_op(
        hass, [volledige_wekker(time="06:45", days=[1, 2, 3, 4, 5])], hass_storage
    )
    planner = hass.data[DOMAIN][DATA_PLANNER]
    moment = dt.datetime(2026, 8, 10, 6, 45, tzinfo=AMS)
    freezer.move_to(dt.datetime(2026, 8, 10, 6, 45, 1, tzinfo=AMS))

    eerste = await planner._async_vuur(  # noqa: SLF001 - zie docstring
        registry_id, PERSON_ENTITY_ID, uit_opslag(hass, registry_id), moment
    )
    assert eerste is True, "de eerste keer hoort te vuren"
    assert afgegaan(hass, registry_id)
    await stop(hass, registry_id)

    tweede = await planner._async_vuur(  # noqa: SLF001
        registry_id, PERSON_ENTITY_ID, uit_opslag(hass, registry_id), moment
    )
    assert tweede is False, "hetzelfde moment mag niet twee keer afgaan"
    assert not afgegaan(hass, registry_id)


async def test_eenmalige_wekker_in_het_verleden_wordt_niet_gepland(
    hass: HomeAssistant, hass_storage, freezer
) -> None:
    """Rem 1: een `one_shot_at` in het verleden levert geen listener op.

    NIEUW GEDRAG. Zonder deze rem zou `async_track_point_in_time` onmiddellijk vuren.
    """
    moment = dt.datetime(2026, 8, 10, 6, 45, tzinfo=AMS)
    freezer.move_to(dt.datetime(2026, 8, 10, 14, 0, tzinfo=AMS))
    registry_id = await zet_op(
        hass,
        [
            volledige_wekker(
                time="06:45",
                days=[],
                one_shot_at=moment.isoformat(),
                last_fired=moment.isoformat(),
            )
        ],
        hass_storage,
    )
    assert hass.data[DOMAIN][DATA_PLANNER].geplande_wekkers == set(), (
        "geen listener voor een moment in het verleden"
    )
    assert not afgegaan(hass, registry_id)
