"""`volgende.py`: wanneer gaat een wekker de eerstvolgende keer af.

Alles **NIEUW GEDRAG**: de module bestond niet. Elk geval legt een eigenschap vast
die fase 3b hergebruikt, en de zomertijdgevallen zijn de reden dat deze module puur
is: ze zijn alleen te toetsen met een vaste `nu`.

Deze tests draaien **zonder** `hass`: geen Home Assistant, geen fixtures. Dat is
het bewijs dat de module puur is — zou hij iets uit HA importeren, dan zou hij op
Windows niet eens te importeren zijn (`fcntl`).
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from custom_components.domotiapp_alarm.volgende import (
    GEEN_WEKKER_TEKST,
    bestaat,
    dagen_tekst,
    eerstvolgende_keer_dat_tijd_voorbijkomt,
    parse_tijd,
    sorteer,
    tekst_voor,
    volgend_moment_van_wekker,
    volgende_momenten,
    volgende_wekker,
)

AMS = ZoneInfo("Europe/Amsterdam")


def wekker(**overschrijf) -> dict:
    basis = {
        "id": "a1",
        "name": "Werk",
        "time": "06:45",
        "days": [1, 2, 3, 4, 5],
        "enabled": True,
        "one_shot_at": None,
    }
    basis.update(overschrijf)
    return basis


# --- parse_tijd --------------------------------------------------------


@pytest.mark.parametrize("goed", ["00:00", "06:45", "23:59"])
def test_parse_tijd_accepteert(goed) -> None:
    """NIEUW GEDRAG."""
    assert parse_tijd(goed) == (int(goed[:2]), int(goed[3:]))


@pytest.mark.parametrize(
    "fout", ["6:45", "06:45:00", "24:00", "06:60", "0645", " 6:45", "", "aa:bb", 645, None]
)
def test_parse_tijd_weigert(fout) -> None:
    """NIEUW GEDRAG. Bewust streng: de opslag bevat één vorm."""
    with pytest.raises(ValueError):
        parse_tijd(fout)


# --- next_fire per soort wekker (verplicht geval 7) --------------------


def test_next_fire_herhalende_wekker() -> None:
    """Een wekker met herhaaldagen. NIEUW GEDRAG."""
    # Maandag 10 augustus 2026, 08:00. 06:45 is vandaag al voorbij.
    nu = dt.datetime(2026, 8, 10, 8, 0, tzinfo=AMS)
    assert nu.isoweekday() == 1
    volgend = volgend_moment_van_wekker(wekker(), nu)
    assert volgend == dt.datetime(2026, 8, 11, 6, 45, tzinfo=AMS)

    # Vóór 06:45 op een werkdag is het vandaag.
    nu = dt.datetime(2026, 8, 10, 6, 0, tzinfo=AMS)
    assert volgend_moment_van_wekker(wekker(), nu) == dt.datetime(2026, 8, 10, 6, 45, tzinfo=AMS)


def test_next_fire_slaat_niet_aangevinkte_dagen_over() -> None:
    """NIEUW GEDRAG. Alleen-weekend op een vrijdag springt naar zaterdag."""
    nu = dt.datetime(2026, 8, 14, 12, 0, tzinfo=AMS)  # vrijdag
    assert nu.isoweekday() == 5
    volgend = volgend_moment_van_wekker(wekker(days=[6, 7], time="09:00"), nu)
    assert volgend == dt.datetime(2026, 8, 15, 9, 0, tzinfo=AMS)


def test_next_fire_eenmalige_wekker() -> None:
    """Een eenmalige wekker gebruikt `one_shot_at`. NIEUW GEDRAG."""
    nu = dt.datetime(2026, 8, 10, 8, 0, tzinfo=AMS)
    moment = dt.datetime(2026, 8, 12, 5, 20, tzinfo=AMS)
    eenmalig = wekker(days=[], one_shot_at=moment.isoformat(), time="05:20")
    assert volgend_moment_van_wekker(eenmalig, nu) == moment

    # Voorbij: gaat niet meer af.
    nu_later = dt.datetime(2026, 8, 13, 8, 0, tzinfo=AMS)
    assert volgend_moment_van_wekker(eenmalig, nu_later) is None


def test_next_fire_uitgezette_wekker() -> None:
    """Een uitgezette wekker gaat niet af. NIEUW GEDRAG."""
    nu = dt.datetime(2026, 8, 10, 8, 0, tzinfo=AMS)
    assert volgend_moment_van_wekker(wekker(enabled=False), nu) is None


def test_een_vervallen_veld_verandert_niets_meer(  # noqa: D103
) -> None:
    """REGRESSIEWACHT. Een oud `skip_next` in de invoer wordt genegeerd.

    Tot fase 7 sloeg `skip_next: True` hier het eerstvolgende moment over. Het
    veld is vervallen, en na de migratie staat het nergens meer — maar een wekker
    die om wat voor reden dan ook nog zo'n sleutel draagt, mag het moment niet
    stil een dag verschuiven. Deze test is de bewaker dat er niets van de oude
    tak is blijven hangen.
    """
    nu = dt.datetime(2026, 8, 10, 8, 0, tzinfo=AMS)  # maandag
    zonder = volgend_moment_van_wekker(wekker(), nu)
    met = volgend_moment_van_wekker(wekker(skip_next=True), nu)
    assert zonder == dt.datetime(2026, 8, 11, 6, 45, tzinfo=AMS)
    assert met == zonder


def test_volgende_wekker_kiest_het_vroegste_moment_niet_de_vroegste_tijd() -> None:
    """Het **moment** beslist, niet de kloktijd. NIEUW GEDRAG.

    Om maandag 08:00 is de wekker van 09:00 vandaag eerder aan de beurt dan die van
    06:45, want die is vandaag al voorbij en komt morgen pas. Een implementatie die
    op de `time`-string sorteert kiest 06:45 en faalt hier.

    Dit is ook de reden dat `next_fire` server-side wordt berekend en niet in de
    kaart (SPEC 3.3): de kaart zou deze fout zomaar maken.
    """
    nu = dt.datetime(2026, 8, 10, 8, 0, tzinfo=AMS)  # maandag
    later_op_de_dag = wekker(id="negen_uur", time="09:00")
    morgen_vroeg = wekker(id="kwart_voor_zeven", time="06:45")
    uit = wekker(id="uit", time="05:00", enabled=False)

    gekozen = volgende_wekker([later_op_de_dag, morgen_vroeg, uit], nu)
    assert gekozen is not None
    assert gekozen.alarm_id == "negen_uur"
    assert gekozen.text == "Vandaag 09:00"
    assert gekozen.at == dt.datetime(2026, 8, 10, 9, 0, tzinfo=AMS)

    # En ná 09:00 wint de wekker van morgenvroeg wél.
    later = dt.datetime(2026, 8, 10, 10, 0, tzinfo=AMS)
    gekozen = volgende_wekker([later_op_de_dag, morgen_vroeg, uit], later)
    assert gekozen is not None
    assert gekozen.alarm_id == "kwart_voor_zeven"
    assert gekozen.text == "Morgen 06:45"


def test_volgende_wekker_zonder_actieve_wekker() -> None:
    """NIEUW GEDRAG. `None`, en de kaart toont `GEEN_WEKKER_TEKST`."""
    nu = dt.datetime(2026, 8, 10, 8, 0, tzinfo=AMS)
    assert volgende_wekker([wekker(enabled=False)], nu) is None
    assert volgende_wekker([], nu) is None
    assert GEEN_WEKKER_TEKST == "Geen wekker actief"


# --- zomertijd (SPEC 5.3 en 13.1) -------------------------------------


def test_bestaat_herkent_de_ontbrekende_uur() -> None:
    """NIEUW GEDRAG. 02:30 bestaat niet op 29 maart 2026 in Europe/Amsterdam."""
    assert bestaat(dt.datetime(2026, 3, 29, 2, 30, tzinfo=AMS)) is False
    assert bestaat(dt.datetime(2026, 3, 29, 3, 30, tzinfo=AMS)) is True
    assert bestaat(dt.datetime(2026, 10, 25, 2, 30, tzinfo=AMS)) is True


def test_voorjaar_slaat_de_dag_over() -> None:
    """Een wekker op 02:30 gaat de voorjaarsnacht niet af (gemeten in fase 0).

    NIEUW GEDRAG. Dit is het gedrag van `find_next_time_expression_time` en dus van
    `async_track_time_change`: die dag wordt overgeslagen en de wekker schuift naar
    de volgende passende dag. Een implementatie die de tijd stil naar 03:30
    verschuift, faalt hier — en dat is precies wat een naieve
    `async_track_point_in_time` zou doen.
    """
    nu = dt.datetime(2026, 3, 28, 23, 0, tzinfo=AMS)
    volgend = volgende_momenten(nu, "02:30", [], aantal=1)[0]
    assert volgend == dt.datetime(2026, 3, 30, 2, 30, tzinfo=AMS)
    assert volgend.utcoffset() == dt.timedelta(hours=2)


def test_najaar_geeft_het_eerste_van_de_twee() -> None:
    """Bij een dubbel uur is het eerstvolgende moment het eerste (fold=0).

    NIEUW GEDRAG. Dat de planner hem die nacht twee keer laat afgaan is gedrag van
    de planner; "wanneer is de eerstvolgende keer" heeft één antwoord.
    """
    nu = dt.datetime(2026, 10, 25, 1, 0, tzinfo=AMS)
    volgend = volgende_momenten(nu, "02:30", [], aantal=1)[0]
    assert volgend.hour == 2 and volgend.minute == 30
    # Het eerste van de twee heeft nog de zomertijdoffset (+02:00).
    assert volgend.utcoffset() == dt.timedelta(hours=2)
    assert volgend.astimezone(dt.UTC) == dt.datetime(2026, 10, 25, 0, 30, tzinfo=dt.UTC)


def test_normale_wektijd_heeft_geen_last_van_zomertijd() -> None:
    """06:45 gaat op beide overgangsdagen precies één keer af (fase 0, E1.3).

    NIEUW GEDRAG, en een REGRESSIEWACHT op de gevallen hierboven: die mogen 06:45
    niet raken.
    """
    for nu, verwacht in (
        (dt.datetime(2026, 3, 28, 23, 0, tzinfo=AMS), dt.datetime(2026, 3, 29, 6, 45, tzinfo=AMS)),
        (dt.datetime(2026, 10, 24, 23, 0, tzinfo=AMS), dt.datetime(2026, 10, 25, 6, 45, tzinfo=AMS)),
    ):
        assert volgende_momenten(nu, "06:45", [], aantal=1)[0] == verwacht


def test_one_shot_at_slaat_niet_bestaande_tijd_over() -> None:
    """NIEUW GEDRAG. Ook een eenmalige wekker schuift bij een ontbrekend uur."""
    nu = dt.datetime(2026, 3, 28, 23, 0, tzinfo=AMS)
    moment = eerstvolgende_keer_dat_tijd_voorbijkomt(nu, "02:30")
    assert moment == dt.datetime(2026, 3, 30, 2, 30, tzinfo=AMS)


def test_naieve_nu_wordt_geweigerd() -> None:
    """NIEUW GEDRAG. Zonder tijdzone is een wandkloktijd niet eenduidig."""
    with pytest.raises(ValueError):
        volgende_momenten(dt.datetime(2026, 8, 10, 8, 0), "06:45", [])


# --- teksten (SPEC 3.2 en 3.3) ----------------------------------------


@pytest.mark.parametrize(
    ("dagen_erbij", "verwacht"),
    [
        (0, "Vandaag 06:45"),
        (1, "Morgen 06:45"),
        (2, None),  # weekdagnaam, hieronder apart
        (7, None),  # datum, hieronder apart
    ],
)
def test_tekst_voor_vandaag_en_morgen(dagen_erbij, verwacht) -> None:
    """NIEUW GEDRAG."""
    nu = dt.datetime(2026, 8, 10, 5, 0, tzinfo=AMS)
    moment = dt.datetime(2026, 8, 10 + dagen_erbij, 6, 45, tzinfo=AMS)
    tekst = tekst_voor(moment, nu)
    if verwacht is not None:
        assert tekst == verwacht
    else:
        assert tekst != "Vandaag 06:45" and tekst != "Morgen 06:45"


def test_tekst_voor_binnen_een_week_en_verder() -> None:
    """NIEUW GEDRAG. Weekdagnaam binnen zes dagen, datum daarna (SPEC 3.3)."""
    nu = dt.datetime(2026, 8, 10, 5, 0, tzinfo=AMS)  # maandag
    assert tekst_voor(dt.datetime(2026, 8, 15, 8, 0, tzinfo=AMS), nu) == "Zaterdag 08:00"
    assert tekst_voor(dt.datetime(2026, 8, 17, 8, 0, tzinfo=AMS), nu) == "ma 17 aug 08:00"


@pytest.mark.parametrize(
    ("dagen", "verwacht"),
    [
        ([], "Eenmalig"),
        ([1, 2, 3, 4, 5], "ma di wo do vr"),
        ([6, 7], "za zo"),
        ([7, 1], "ma zo"),
    ],
)
def test_dagen_tekst(dagen, verwacht) -> None:
    """NIEUW GEDRAG (SPEC 3.2)."""
    assert dagen_tekst(dagen) == verwacht


# --- sorteren (SPEC 3.4) ----------------------------------------------


def test_sorteer_op_tijd_dan_naam() -> None:
    """NIEUW GEDRAG. Niet op "eerstvolgende": dan verspringt de lijst."""
    wekkers = [
        {"time": "09:00", "name": "Weekend"},
        {"time": "06:45", "name": "Werk"},
        {"time": "06:45", "name": "Ander"},
    ]
    assert [w["name"] for w in sorteer(wekkers)] == ["Ander", "Werk", "Weekend"]
