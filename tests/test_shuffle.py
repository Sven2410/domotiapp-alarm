"""Wel of niet shuffelen (SPEC 9.6). Puur, dus gewone Node-achtige tests zonder hass.

**Alles NIEUW GEDRAG.** `shuffle.py` bestaat pas sinds deze ronde; er is geen oude
code waarop een van deze tests kan slagen — de import zelf faalt daar al.

Waarom deze module apart getest wordt en niet alleen via `afvuren.py`: de vraag "heeft
dit geluid meerdere nummers" is beslislogica en die hoort in een gewone test
(CLAUDE.md, werkafspraken). Via het afvuren zou elk geval een hele wekker en een
nagebootste speaker kosten voor één booleaanse uitkomst.
"""

from __future__ import annotations

import pytest

from custom_components.domotiapp_alarm import shuffle
from custom_components.domotiapp_alarm.const import MEERSTUKS_SOORTEN, ONEINDIGE_SOORTEN


@pytest.mark.parametrize("soort", ["playlist", "album", "artist"])
def test_meerstuks_soorten_worden_geschud(soort: str) -> None:
    """NIEUW GEDRAG. De drie soorten uit de bevinding van de eigenaar."""
    assert shuffle.moet_shuffelen(soort) is True


@pytest.mark.parametrize("soort", ["radio", "track", "podcast", "audiobook"])
def test_soorten_met_een_enkel_stuk_worden_niet_geschud(soort: str) -> None:
    """NIEUW GEDRAG, en dit is de **positieve controle op de andere kant**.

    Zonder deze test komt een implementatie die altijd `True` teruggeeft er ongehinderd
    doorheen — precies de mutatie die valkuil 36 beschrijft. Bij radio is er één
    doorlopende stream en geen volgorde om te schudden.
    """
    assert shuffle.moet_shuffelen(soort) is False


def test_de_twee_lijsten_zijn_niet_dezelfde_vraag() -> None:
    """NIEUW GEDRAG. `ONEINDIGE_SOORTEN` gaat over duur, `MEERSTUKS_SOORTEN` over aantal.

    Ze overlappen in `playlist` en verschillen verder volledig. Deze test staat er
    omdat de verleiding om de bestaande lijst te hergebruiken groot is: hij bestond
    al en hij bevat `playlist`. Dat zou `radio` laten schudden (zinloos) en `album`
    en `artist` niet (de bevinding zelf).
    """
    assert "radio" in ONEINDIGE_SOORTEN
    assert "radio" not in MEERSTUKS_SOORTEN
    assert "album" in MEERSTUKS_SOORTEN
    assert "album" not in ONEINDIGE_SOORTEN
    assert MEERSTUKS_SOORTEN & ONEINDIGE_SOORTEN == {"playlist"}


@pytest.mark.parametrize("soort", ["PLAYLIST", " Playlist ", "Album"])
def test_hoofdletters_en_witruimte_doen_er_niet_toe(soort: str) -> None:
    """NIEUW GEDRAG. MA levert `media_type` als kleine letters, maar de waarde komt
    via de opslag binnen en die is door een klant te vullen. Een afspeellijst die niet
    schudt omdat er een spatie in het veld staat, is niet uit te leggen."""
    assert shuffle.moet_shuffelen(soort) is True


@pytest.mark.parametrize("waarde", [None, "", "   ", 5, ["playlist"], {"playlist": 1}])
def test_bij_twijfel_niet_shuffelen(waarde: object) -> None:
    """NIEUW GEDRAG. Een ontbrekende of onbegrijpelijke soort levert `False`.

    Dit is de goedkope kant van de twijfel: een niet-geschudde afspeellijst is
    hinderlijk, een aanroep op iets waarvan we de vorm niet kennen levert niets op en
    kost een service-aanroep vlak vóór het geluid.
    """
    assert shuffle.moet_shuffelen(waarde) is False  # type: ignore[arg-type]
