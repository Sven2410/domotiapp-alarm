"""De rekenkunde van de volume-oploop (SPEC 9.3). Puur.

Geen HA-imports, geen `hass`, geen tijd. Dat is een eis en geen stijlkeuze: fase 0b
mat dat een oploop **niet** vanuit de browser te meten is (Chrome knijpt `setTimeout`
af in een achtergrondtabblad, valkuil 31), dus de enige plek waar de getallen
controleerbaar zijn, is een gewone Node- of pytest-test zonder klok.

Wat hier NIET staat: het wachten en het aanroepen van de speaker. Dat is
`afvuren.py`, want dat heeft een `hass` nodig.

**Waarom clampen hier gebeurt en niet bij Music Assistant.** Fase 0b mat dat MA
buiten bereik **stil afkapt** en HTTP 200 teruggeeft: `-5` → 0, `150` → 100,
`33.7` → 33 (afkappen, niet afronden). Een rekenfout in de oploop levert dus geen
exceptie op, alleen een verkeerd volume — en dat is precies het soort fout dat
maanden blijft zitten. Daarom clampt deze module zelf en meldt ze dát ze clampte.
"""

from __future__ import annotations

from .const import (
    OPLOOP_AFBREEK_MARGE_PCT,
    OPLOOP_STAPPEN,
    VOLUME_PCT_MAX,
)


def clamp(pct: float) -> tuple[int, bool]:
    """Kap een volumepercentage af op 0–100. Geeft `(waarde, is_geclampt)` terug.

    De tweede waarde bestaat zodat de aanroeper kan **loggen** dat er geclampt moest
    worden. Zonder dat verschil is clampen zelf ook stil, en dan is er niets
    gewonnen ten opzichte van MA's eigen stille afkapping.

    Ondergrens is 0 en niet `VOLUME_PCT_MIN` (1): 0 is een geldig **oploopvolume**
    — de oploop begint er zelfs op. De ondergrens van 1 uit SPEC 14.2 geldt voor het
    *eindniveau* dat de klant instelt, en die wordt in `validatie.py` bewaakt.
    """
    afgekapt = int(pct)
    if afgekapt < 0:
        return 0, True
    if afgekapt > VOLUME_PCT_MAX:
        return VOLUME_PCT_MAX, True
    return afgekapt, False


def stappen(doel_pct: int, aantal: int = OPLOOP_STAPPEN) -> list[int]:
    """De volumes van de oploop: `aantal` stappen van 0 naar `doel_pct`.

    De **laatste stap is exact `doel_pct`**. Dat is geen bijkomstigheid van de
    rekenkunde maar een eis: de klant heeft een niveau ingesteld en daar hoort de
    wekker op te eindigen, niet op 39 omdat 40 niet precies deelbaar was.

    De lijst is niet-dalend. Bij een laag doel levert dat herhaalde waarden op —
    doel 1 geeft achttien nullen en dan een 1 — en dat is goed: de resolutie van MA
    is 1 % (gemeten in fase 0b), dus fijner kan niet en een tussenwaarde verzinnen
    zou liegen.

    `doel_pct` wordt geclampt, want een doel buiten bereik zou anders een hele
    oploop buiten bereik opleveren.
    """
    if aantal < 1:
        raise ValueError(f"een oploop heeft minstens één stap, niet {aantal}")

    doel, _ = clamp(doel_pct)

    # De laatste term is `doel * aantal / aantal`, en dat is voor elk geheel doel en
    # elk aantal stappen **exact** het doel. Hier stond eerst een regel die de laatste
    # stap er voor de zekerheid nog eens hard op zette; een mutatietest liet zien dat
    # die regel onbereikbaar was — nagerekend voor aantal ∈ {1, 2, 3, 7, 20, 100, 999}
    # en doel 0–100: nul afwijkingen. Weggehaald in plaats van er een test bij te
    # verzinnen, want een test op onbereikbare code bewijst niets.
    #
    # Dat de laatste stap exact het doel is blijft wél een **eis**, en die wordt
    # bewaakt door `test_de_oploop_daalt_nooit` voor elk doel van 1 tot 100.
    return [round(doel * (i + 1) / aantal) for i in range(aantal)]


def wijkt_af(
    gelezen_pct: int | None,
    gezet_pct: int,
    marge: int = OPLOOP_AFBREEK_MARGE_PCT,
) -> bool:
    """Heeft iemand anders aan het volume gedraaid? (SPEC 9.3)

    De oploop breekt af zodra het gelezen volume meer dan `marge` procentpunt afwijkt
    van wat de oploop zelf net heeft gezet. Zonder die regel vecht de integratie met
    de gebruiker: hij draait zachter, de volgende stap zet het weer harder.

    **`None` is géén afwijking.** Is het volume niet te lezen — de speaker is
    `unavailable` en dan zijn de state attributes weg (SPEC 7.2, valkuil 18) — dan is
    dat geen bewijs dat de gebruiker iets deed. Het afbreken bij een weggevallen
    speaker gebeurt op `available`, en die controle staat in `afvuren.py`; deze
    functie gaat alleen over de knop.
    """
    if gelezen_pct is None:
        return False
    return abs(gelezen_pct - gezet_pct) > marge
