"""De rekenkunde van de volume-oploop (SPEC 9.3). Alles NIEUW GEDRAG.

Geen `hass`, geen klok, geen fixtures — `oploop.py` is puur en dat is precies waarom
deze getallen te toetsen zijn. Fase 0b kon de cadans van een oploop **niet** meten
vanuit de browser (Chrome knijpt `setTimeout` af in een achtergrondtabblad,
valkuil 31); hier is elke stap een gewone gelijkheid.
"""

from __future__ import annotations

import pytest

from custom_components.domotiapp_alarm import oploop
from custom_components.domotiapp_alarm.const import OPLOOP_STAPPEN


# --- clamp --------------------------------------------------------------


@pytest.mark.parametrize(
    ("ingang", "waarde", "geclampt"),
    [
        (-5, 0, True),
        (150, 100, True),
        (0, 0, False),
        (100, 100, False),
        (40, 40, False),
        # Afkappen, niet afronden — zoals MA het zelf doet (gemeten in fase 0b).
        (33.7, 33, False),
        (12.5, 12, False),
    ],
)
def test_clamp_kapt_af_en_meldt_dat(ingang, waarde, geclampt) -> None:
    """NIEUW GEDRAG. De getallen komen letterlijk uit de meting van fase 0b.

    Het tweede element van het antwoord is het hele punt: MA kapt buiten bereik
    **stil** af met HTTP 200, dus zonder een expliciet "ik heb geclampt" is een
    rekenfout in de oploop onzichtbaar.
    """
    assert oploop.clamp(ingang) == (waarde, geclampt)


# --- stappen ------------------------------------------------------------


def test_twintig_stappen_eindigen_exact_op_het_doel() -> None:
    """NIEUW GEDRAG. Verplicht geval 6, het rekendeel.

    De laatste stap is exact het ingestelde niveau. De klant heeft 40 ingesteld en
    dan hoort de wekker op 40 te eindigen, niet op 39 omdat de deling niet uitkwam.
    """
    waarden = oploop.stappen(40)
    assert len(waarden) == OPLOOP_STAPPEN == 20
    assert waarden[-1] == 40
    assert waarden == [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40]


def test_een_oneven_doel_eindigt_ook_exact() -> None:
    """NIEUW GEDRAG. 33 is niet deelbaar door 20; het einde moet tóch 33 zijn.

    Zonder de laatste stap hard op het doel te zetten zou de formule hier ook 33
    geven, maar bij een ánder aantal stappen niet — en het aantal stappen is met
    opzet één constante die verhoogd mag worden (SPEC 9.3).
    """
    waarden = oploop.stappen(33)
    assert waarden[-1] == 33
    assert len(waarden) == 20


def test_de_oploop_daalt_nooit() -> None:
    """NIEUW GEDRAG. Een oploop die halverwege zachter wordt is geen oploop.

    Voor elk doel van 1 tot 100, want een dalende stap door afronding zou alleen bij
    bepaalde delers opduiken.
    """
    for doel in range(1, 101):
        waarden = oploop.stappen(doel)
        assert waarden == sorted(waarden), f"doel {doel} daalt: {waarden}"
        assert waarden[-1] == doel
        assert all(0 <= w <= 100 for w in waarden)


def test_een_laag_doel_herhaalt_waarden_in_plaats_van_te_verzinnen() -> None:
    """NIEUW GEDRAG. Doel 1 kan niet in 20 hoorbare stappen.

    De resolutie van MA is 1 % (gemeten in fase 0b), dus fijner dan een heel procent
    bestaat niet. Herhaalde nullen zijn dan het juiste antwoord; een tussenwaarde
    verzinnen zou liegen over wat de speaker kan.
    """
    waarden = oploop.stappen(1)
    assert waarden[-1] == 1
    assert waarden.count(0) > 0
    assert set(waarden) <= {0, 1}


def test_een_doel_buiten_bereik_wordt_geclampt() -> None:
    """NIEUW GEDRAG. Anders zou een heel oploopverloop buiten bereik liggen."""
    assert oploop.stappen(150)[-1] == 100
    assert oploop.stappen(-5)[-1] == 0


def test_een_ander_aantal_stappen_blijft_kloppen() -> None:
    """NIEUW GEDRAG. SPEC 9.3 zegt dat dit één constante is die verhoogd mag worden.

    Deze test is de reden dat dat waar blijft: bij 100 stappen — wat de techniek
    toelaat — eindigt de oploop nog steeds exact op het doel en daalt hij niet.
    """
    waarden = oploop.stappen(40, aantal=100)
    assert len(waarden) == 100
    assert waarden[-1] == 40
    assert waarden == sorted(waarden)


def test_nul_stappen_is_een_fout_en_geen_lege_oploop() -> None:
    """NIEUW GEDRAG. Een lege lijst zou een stille "geen oploop" opleveren."""
    with pytest.raises(ValueError):
        oploop.stappen(40, aantal=0)


# --- wijkt_af -----------------------------------------------------------


@pytest.mark.parametrize(
    ("gelezen", "gezet", "verwacht"),
    [
        (10, 10, False),
        (15, 10, False),  # exact de marge van 5: nog niet afbreken
        (16, 10, True),  # één procentpunt erover
        (5, 10, False),
        (4, 10, True),  # ook naar beneden draaien breekt af
        (None, 10, False),  # niet te lezen is geen afwijking
    ],
)
def test_afwijking_boven_vijf_procentpunt_breekt_af(gelezen, gezet, verwacht) -> None:
    """NIEUW GEDRAG. Verplicht geval 7, het rekendeel.

    De grens ligt op *meer dan* 5, niet op 5 of meer: SPEC 9.3 zegt "meer dan 5
    procentpunt". Een speaker die precies 5 % afwijkt door afronding hoort de oploop
    niet af te breken.

    `None` is expliciet géén afwijking. Is het volume niet te lezen omdat de speaker
    `unavailable` is — en dan zijn de state attributes weg (valkuil 18) — dan is dat
    geen bewijs dat de gebruiker iets deed. Dat geval hoort bij `available`.
    """
    assert oploop.wijkt_af(gelezen, gezet) is verwacht


# --- index_bij: de oploop haalt in (SPEC 9.3, fase 11) ------------------


@pytest.mark.parametrize(
    ("verstreken", "verwacht"),
    [
        # Vóór de eerste stap: het begin, niet een fout en niet -1.
        (0.0, 0),
        (0.9, 0),
        # Stap i is verschuldigd op (i+1) seconden.
        (1.0, 0),
        (1.9, 0),
        (2.0, 1),
        (3.0, 2),
        # play_media blokkeerde 2,5 s; de eerste tik valt op 3,5 s en dan is stap
        # 2 verschuldigd. Dit is precies het geval waarvoor deze functie bestaat.
        (3.5, 2),
        # De laatste stap valt op aantal * stap_s = 20 s.
        (20.0, OPLOOP_STAPPEN - 1),
        # En daarna blijft het de laatste stap; nooit buiten de lijst.
        (25.0, OPLOOP_STAPPEN - 1),
        (10_000.0, OPLOOP_STAPPEN - 1),
    ],
)
def test_index_bij_geeft_de_verschuldigde_stap(verstreken, verwacht) -> None:
    """NIEUW GEDRAG. Faalt op de code van vóór fase 11: de functie bestond niet."""
    assert oploop.index_bij(verstreken) == verwacht


def test_de_oploop_is_op_twintig_seconden_klaar_hoe_laat_hij_ook_begint() -> None:
    """De eigenschap waar de hele wijziging om draait. NIEUW GEDRAG.

    Voor elke vertraging die `play_media` kan opleveren geldt: op 20 seconden na
    het bedoelde begin is de laatste stap verschuldigd. Vóór fase 11 begon de
    oploop pas ná die vertraging en was hij dus op 20 + vertraging klaar —
    gemeten +22,3 s in fase 3c.
    """
    for vertraging in (0.0, 0.5, 2.1, 2.6, 5.0):
        # De eerste tik valt één stap na het starten, dus vertraging + 1 s.
        eerste = oploop.index_bij(vertraging + 1.0)
        assert eerste == int(vertraging), f"vertraging {vertraging}"
        # En op 20 s is de laatste stap aan de beurt, ongeacht de vertraging.
        assert oploop.index_bij(20.0) == OPLOOP_STAPPEN - 1


def test_index_bij_weigert_een_onzinnige_oploop() -> None:
    """NIEUW GEDRAG. Zelfde afspraak als `stappen`: liever een fout dan stil raar."""
    with pytest.raises(ValueError):
        oploop.index_bij(1.0, aantal=0)
    with pytest.raises(ValueError):
        oploop.index_bij(1.0, stap_s=0)
