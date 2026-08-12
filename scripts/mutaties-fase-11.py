"""Mutatieproef fase 11 — de lader en de inhaalslag van de oploop.

Elke mutatie is een tekstvervanging in een bronbestand. Het script zet hem, draait
de tests in de Docker-container, en zet hem terug. Een mutatie die **niet** gevangen
wordt is een gat of een regel die niets doet; welke van de twee moet je narekenen
(CLAUDE.md valkuil 34).

Gebruik:
    python scripts/mutaties-fase-11.py            # alle mutaties
    python scripts/mutaties-fase-11.py M3 M7      # alleen deze
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

WORTEL = Path(__file__).resolve().parent.parent
CC = WORTEL / "custom_components" / "domotiapp_alarm"

TEST = (
    'docker run --rm -v "C:/dev/domotiapp-alarm:/app" -w /app python:3.14-slim '
    'sh -c "pip install -q -r requirements-test.txt && python -m pytest -q -x"'
)

# (naam, bestand, oud, nieuw, wat de mutatie voorstelt)
MUTATIES: list[tuple[str, str, str, str, str]] = [
    # --- ronde 1: doet de lader wat hij belooft? ---
    (
        "M1",
        "const.py",
        'LOADER_URL_PATH: Final = f"/api/{DOMAIN}/loader.js"',
        'LOADER_URL_PATH: Final = f"/{DOMAIN}/loader.js"',
        "de lader staat NIET meer onder /api/ — de service worker gaat hem cachen",
    ),
    (
        "M2",
        "__init__.py",
        "        add_extra_js_url(hass, LOADER_URL_PATH)",
        "        add_extra_js_url(hass, js_url)",
        "de gehashte URL gaat weer in index.html, zoals vóór fase 11",
    ),
    (
        "M3",
        "loader.py",
        '"Cache-Control": "no-store, must-revalidate",',
        '"Cache-Control": "public, max-age=3600",',
        "de lader mag gecachet worden",
    ),
    (
        "M4",
        "loader.py",
        "    requires_auth = False",
        "    requires_auth = True",
        "de lader vraagt een token, dat een <script>-tag niet meestuurt",
    ),
    (
        "M5",
        "loader.py",
        'text=f\'import("{CARD_URL_PATH}?v={hash_nu}");\\n\',',
        'text=f\'import("{CARD_URL_PATH}");\\n\',',
        "de lader laat de hash weg — geen cachebusting meer op de bundel",
    ),
    # --- ronde 1: de inhaalslag ---
    (
        "M6",
        "oploop.py",
        "    verschuldigd = int(verstreken_s // stap_s) - 1",
        "    verschuldigd = int(verstreken_s // stap_s)",
        "de stap is één te hoog: de oploop loopt vóór in plaats van gelijk",
    ),
    (
        "M7",
        "afvuren.py",
        "        index = max(verschuldigd, self._index)",
        "        index = self._index",
        "geen inhaalslag: de oude teller, precies de code van vóór fase 11",
    ),
    # --- ronde 2: de randen waarvan ik zou moeten toegeven dat ik ze niet toets ---
    (
        "M8",
        "afvuren.py",
        "        index = max(verschuldigd, self._index)",
        "        index = verschuldigd",
        "zonder de max: de oploop mag terugvallen naar een lagere stap",
    ),
    (
        "M9",
        "afvuren.py",
        "    oploop_t0 = _klok()",
        "    oploop_t0 = _klok() - 2.5",
        "het nulpunt ligt verkeerd: de oploop denkt dat hij al bezig was",
    ),
    (
        "M10",
        "oploop.py",
        "    if verschuldigd > aantal - 1:\n        return aantal - 1",
        "    if verschuldigd > aantal:\n        return aantal - 1",
        "de bovengrens is één te ruim — index buiten de lijst",
    ),
    (
        "M11",
        "oploop.py",
        "    if verschuldigd < 0:\n        return 0",
        "    if verschuldigd < -1:\n        return 0",
        "de ondergrens laat -1 door: de laatste stap als eerste",
    ),
    (
        "M12",
        "loader.py",
        "    al_geregistreerd = DATA_LOADER_REGISTERED in data",
        "    al_geregistreerd = False",
        "de view wordt bij elke setup opnieuw geregistreerd",
    ),
    # M13 is VERVALLEN: de tak die hij muteerde bleek onbereikbaar en is
    # geschrapt (valkuil 34, derde rij). Zie de comment in loader.py.
    (
        "M14",
        "loader.py",
        'content_type="text/javascript",',
        'content_type="text/plain",',
        "het content-type is geen javascript — de browser weigert de module",
    ),
    (
        "M15",
        "__init__.py",
        "if vorige_url is not None and vorige_url != LOADER_URL_PATH:",
        "if False and vorige_url != LOADER_URL_PATH:",
        "de oude gehashte URL wordt niet meer afgemeld bij een upgrade",
    ),
    (
        "M16",
        "__init__.py",
        "    data[DATA_RESOURCE_ID] = await resource.async_zorg_voor_resource(hass, js_url)",
        "    data[DATA_RESOURCE_ID] = await resource.async_zorg_voor_resource(hass, LOADER_URL_PATH)",
        "de resource wijst naar de lader in plaats van naar de bundel",
    ),
]


def draai(namen: list[str]) -> int:
    gekozen = [m for m in MUTATIES if not namen or m[0] in namen]
    ongevangen: list[str] = []

    for naam, bestand, oud, nieuw, wat in gekozen:
        pad = CC / bestand
        origineel = io.open(pad, encoding="utf-8").read()
        if oud not in origineel:
            print(f"{naam}: OVERSLAAN — patroon niet gevonden in {bestand}")
            continue
        try:
            io.open(pad, "w", encoding="utf-8", newline="\n").write(
                origineel.replace(oud, nieuw, 1)
            )
            uit = subprocess.run(TEST, shell=True, capture_output=True, text=True)
            gevangen = uit.returncode != 0
            print(f"{naam}: {'GEVANGEN' if gevangen else 'NIET GEVANGEN'}  — {wat}")
            if not gevangen:
                ongevangen.append(f"{naam} ({wat})")
        finally:
            io.open(pad, "w", encoding="utf-8", newline="\n").write(origineel)

    print()
    if ongevangen:
        print("NIET GEVANGEN:")
        for r in ongevangen:
            print("  -", r)
        print("\nReken per geval na (valkuil 34): testgat, redundante verdediging,")
        print("onbereikbare code, of equivalente mutant?")
    else:
        print("Alles gevangen. Let op valkuil 46: dat is geen goed teken maar een")
        print("aanwijzing dat de mutaties dekking bevestigen in plaats van gaten zoeken.")
    return len(ongevangen)


if __name__ == "__main__":
    sys.exit(0 if draai(sys.argv[1:]) == 0 else 1)
