"""De mutatieproef van fase 6b, ronde 1 en 2.

Zowel Python als JavaScript, want deze ronde raakt beide kanten. Draaien in de
Linux-container (HA importeert `fcntl`), met Node erbij::

    MSYS_NO_PATHCONV=1 docker run --rm -v "C:/dev/domotiapp-alarm:/app" -w /app \
      python:3.14-slim sh -c "apt-get -qq update && apt-get -qq install -y nodejs \
      && pip install -q -r requirements-test.txt && python scripts/mutaties-fase-6b.py"

Elke mutatie is een letterlijke tekstvervanging, wordt gezet, getest en teruggezet —
ook als de testrunner ontploft. Een mutatie die **slaagt** is een gat.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

WORTEL = Path(__file__).resolve().parent.parent


@dataclass
class Mutatie:
    code: str
    bestand: str
    oud: str
    nieuw: str
    waarom: str
    js: bool = False


PY_AFVUREN = "custom_components/domotiapp_alarm/afvuren.py"
PY_MELD = "custom_components/domotiapp_alarm/meldingen.py"
PY_VOORBEELD = "custom_components/domotiapp_alarm/voorbeeld.py"
JS_MENU = "src/menu.js"
JS_WEERGAVE = "src/weergave.js"

MUTATIES: list[Mutatie] = [
    # === ronde 1: bevestigt de dekking =================================
    # --- bevinding 4: shuffle terugzetten -------------------------------
    Mutatie(
        "M1",
        PY_AFVUREN,
        "        shuffle_voor = context.get(CTX_SHUFFLE_VOOR)\n"
        "        if shuffle_voor is None:",
        "        shuffle_voor = None\n" "        if shuffle_voor is None:",
        "shuffle wordt bij het stoppen NIET teruggezet — de bevinding zelf",
    ),
    Mutatie(
        "M2",
        PY_AFVUREN,
        "            await async_zet_shuffle(hass, speaker, shuffle_voor)\n\n    if reason is not None:",
        "            await async_zet_shuffle(hass, speaker, False)\n\n    if reason is not None:",
        "bij het stoppen wordt shuffle UIT gezet in plaats van teruggezet",
    ),
    Mutatie(
        "M3",
        PY_AFVUREN,
        "    stand_voor = shuffle_van(hass, speaker)\n    if stand_voor is None:",
        "    await async_zet_shuffle(hass, speaker, True)\n"
        "    stand_voor = shuffle_van(hass, speaker)\n"
        "    if stand_voor is None:",
        "de stand wordt NA het zetten gelezen — dan lees je je eigen True terug",
    ),
    Mutatie(
        "M4",
        PY_AFVUREN,
        "    if not shuffle.moet_shuffelen(media_type):\n        return None",
        "    if False:\n        return None",
        "ook radio krijgt een shuffle-aanroep en een terugzetting",
    ),
    Mutatie(
        "M5",
        PY_AFVUREN,
        "    stand = state.attributes.get(\"shuffle\")\n    if not isinstance(stand, bool):\n        return None",
        "    stand = state.attributes.get(\"shuffle\")\n    if False:\n        return None",
        "een ontbrekende shuffle wordt als False gelezen (verzonnen waarde)",
    ),
    Mutatie(
        "M6",
        PY_VOORBEELD,
        "    shuffle_voor = context.get(CTX_SHUFFLE_VOOR)\n    if shuffle_voor is not None:",
        "    shuffle_voor = context.get(CTX_SHUFFLE_VOOR)\n    if False:",
        "het voorbeeld zet shuffle niet terug",
    ),
    # --- bevinding 3: de twee teksten -----------------------------------
    Mutatie(
        "M7",
        PY_MELD,
        '            "De wekker is afgegaan, maar het volume was op deze speaker niet in te "\n'
        '            "stellen; het oplopende volume is overgeslagen."',
        '            "De wekker is afgegaan op het ingestelde volume; het oplopende volume was "\n'
        '            "op deze speaker niet mogelijk."',
        "de oude, te veel claimende volumetekst terug",
    ),
    Mutatie(
        "M8",
        PY_MELD,
        'return f"Je wekker van {tijd} is niet afgegaan; Home Assistant heeft dat moment gemist."',
        'return f"Je wekker van {tijd} is niet afgegaan omdat Home Assistant uit stond."',
        "de oude, te veel claimende overslaantekst terug",
    ),
    # --- bevinding 1: de plaatsing van het menu (JS) --------------------
    Mutatie(
        "M9",
        JS_MENU,
        "  const pastOnder = onder + menu.hoogte <= kaart.bottom;",
        "  const pastOnder = true;",
        "het menu hangt altijd onder de knop — het gedrag van vóór 6b",
        js=True,
    ),
    Mutatie(
        "M10",
        JS_MENU,
        "  const pastBoven = boven >= kaart.top;",
        "  const pastBoven = false;",
        "omhoog klappen bestaat niet meer",
        js=True,
    ),
    Mutatie(
        "M11",
        JS_MENU,
        "  const boven = anker.top - menu.hoogte - MENU_MARGE;",
        "  const boven = anker.top - MENU_MARGE;",
        "bij omhoog klappen telt de hoogte van het menu niet mee",
        js=True,
    ),
    Mutatie(
        "M12",
        JS_MENU,
        "  const left = klem(\n    anker.right - menu.breedte,",
        "  const left = klem(\n    anker.right,",
        "het menu wordt links uitgelijnd op de knop in plaats van rechts",
        js=True,
    ),
    Mutatie(
        "M13",
        JS_MENU,
        "  return Math.max(min, Math.min(waarde, max));",
        "  return Math.min(max, Math.max(waarde, min));",
        "de klemvolgorde omgedraaid: bij een krap venster begint het menu buiten beeld",
        js=True,
    ),
    # --- bevinding 2: de kopbalk (JS) ------------------------------------
    Mutatie(
        "M14",
        JS_WEERGAVE,
        "  if (!Array.isArray(wekkers) || wekkers.length === 0) {\n    return TEKST_GEEN_WEKKERS;\n  }",
        "  if (!Array.isArray(wekkers)) {\n    return TEKST_GEEN_WEKKERS;\n  }",
        "een lege lijst krijgt weer 'Geen wekker actief'",
        js=True,
    ),
    Mutatie(
        "M15",
        JS_WEERGAVE,
        '  return typeof tekst === "string" && tekst.trim() ? tekst : TEKST_GEEN_WEKKER_ACTIEF;',
        "  return TEKST_GEEN_WEKKER_ACTIEF;",
        "de tekst van de server wordt genegeerd",
        js=True,
    ),
    Mutatie(
        "M16",
        JS_WEERGAVE,
        '  return typeof tekst === "string" && tekst.trim() ? tekst : TEKST_GEEN_WEKKER_ACTIEF;',
        "  return tekst ?? TEKST_GEEN_WEKKER_ACTIEF;",
        "een lege tekst uit de server komt zo op de kaart",
        js=True,
    ),
    # === ronde 2: zoekt naar gaten in plaats van dekking te bevestigen ==
    Mutatie(
        "M17",
        PY_AFVUREN,
        "    if stand_voor is None:\n"
        "        _LOGGER.debug(\n"
        '            "Shuffle van %s is niet te lezen; er wordt bij het stoppen niets teruggezet",\n'
        "            speaker,\n"
        "        )\n"
        "    await async_zet_shuffle(hass, speaker, True)\n"
        "    return stand_voor",
        "    if stand_voor is None:\n"
        "        return None\n"
        "    await async_zet_shuffle(hass, speaker, True)\n"
        "    return stand_voor",
        "shuffle wordt NIET aangezet als de oude stand onleesbaar is — de wekker "
        "begint dan bij nummer 1 terwijl er niets aan de hand is",
    ),
    Mutatie(
        "M18",
        PY_AFVUREN,
        "    shuffle_voor = await async_shuffle_aan_voor(\n"
        '        hass, speaker, (wekker.get("sound") or {}).get("media_type")\n'
        "    )",
        "    shuffle_voor = None\n"
        "    await async_shuffle_aan_voor(\n"
        '        hass, speaker, (wekker.get("sound") or {}).get("media_type")\n'
        "    )",
        "de oude stand wordt gelezen maar niet bewaard",
    ),
    Mutatie(
        "M19",
        PY_AFVUREN,
        "        CTX_SHUFFLE_VOOR: shuffle_voor,\n        CTX_OPLOOP: None,",
        "        CTX_SHUFFLE_VOOR: True,\n        CTX_OPLOOP: None,",
        "de context krijgt een vaste True in plaats van de gelezen stand",
    ),
    Mutatie(
        "M20",
        JS_MENU,
        "  const binnenKaart = pastOnder || pastBoven;",
        "  const binnenKaart = true;",
        "de kaart meldt altijd dat het menu binnen de kaart past",
        js=True,
    ),
    Mutatie(
        "M21",
        JS_MENU,
        "export const MENU_MARGE = 4;",
        "export const MENU_MARGE = 0;",
        "geen ruimte tussen knop, menu en vensterrand",
        js=True,
    ),
    Mutatie(
        "M22",
        PY_MELD,
        '        erbij = f\' Music Assistant meldde: "{reden}".\' if reden else ""',
        '        erbij = ""',
        "de reden van MA valt weg (regressie op fase 6)",
    ),
    Mutatie(
        "M23",
        PY_AFVUREN,
        "    state = hass.states.get(speaker)\n"
        "    if state is None or state.state == STATE_UNAVAILABLE:\n"
        "        return None\n"
        '    stand = state.attributes.get("shuffle")',
        "    state = hass.states.get(speaker)\n"
        "    if state is None:\n"
        "        return None\n"
        '    stand = state.attributes.get("shuffle")',
        "een `unavailable` speaker levert toch een stand op",
    ),
]


def draai(mutatie: Mutatie) -> tuple[bool, str]:
    if mutatie.js:
        cmd = ["node", "--test", "tests/js/"]
    else:
        cmd = [sys.executable, "-m", "pytest", "-q", "-x", "--no-header", "tests/"]
    uit = subprocess.run(cmd, cwd=WORTEL, capture_output=True, text=True)
    regels = [r for r in (uit.stdout or "").strip().splitlines() if r.strip()]
    samenvatting = next(
        (r for r in reversed(regels) if "pass" in r or "fail" in r or "passed" in r),
        regels[-1] if regels else "geen uitvoer",
    )
    return uit.returncode == 0, samenvatting.strip()


def main() -> int:
    # De Python-tests draaien alleen in Linux (HA importeert `fcntl`), de JS-tests
    # draaien overal. Vandaar een filter in plaats van één run: `py` in de container,
    # `js` op de host.
    keuze = sys.argv[1] if len(sys.argv) > 1 else "alles"
    selectie = [
        m
        for m in MUTATIES
        if keuze == "alles" or (keuze == "js") == m.js
    ]

    ongevangen: list[Mutatie] = []
    print(f"{'code':<5} {'gevangen':<9} wat er verandert")
    print("-" * 78)
    for mutatie in selectie:
        pad = WORTEL / mutatie.bestand
        origineel = pad.read_text(encoding="utf-8")
        aantal = origineel.count(mutatie.oud)
        if aantal != 1:
            print(f"{mutatie.code:<5} {'PATCH ' + str(aantal):<9} {mutatie.waarom}")
            ongevangen.append(mutatie)
            continue
        try:
            pad.write_text(origineel.replace(mutatie.oud, mutatie.nieuw), encoding="utf-8")
            groen, regel = draai(mutatie)
        finally:
            pad.write_text(origineel, encoding="utf-8")
        print(f"{mutatie.code:<5} {'NEE  <<<' if groen else 'ja':<9} {mutatie.waarom}")
        print(f"{'':<15} {regel}")
        if groen:
            ongevangen.append(mutatie)

    print("-" * 78)
    print(f"{len(selectie) - len(ongevangen)} van {len(selectie)} gevangen")
    for mutatie in ongevangen:
        print(f"  ONGEVANGEN {mutatie.code}: {mutatie.bestand} — {mutatie.waarom}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
