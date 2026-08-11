"""De mutatieproef van fase 7, ronde 1 en 2.

Python en JavaScript, met een filter omdat de Python-tests alleen in Linux draaien
(HA importeert `fcntl`) en de JS-tests overal::

    python scripts/mutaties-fase-7.py js          # op de host
    ... python scripts/mutaties-fase-7.py py      # in de container

Elke mutatie is een letterlijke tekstvervanging, wordt gezet, getest en teruggezet
— ook als de testrunner ontploft. Een mutatie die **slaagt** is een gat.

Het zwaartepunt ligt op de **migratie**: dat is de plek waar deze ronde stil mis
kan gaan, want een klant merkt pas dat zijn wekkers weg zijn op de eerste ochtend
dat er niets afgaat.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

WORTEL = Path(__file__).resolve().parent.parent

PY_STORE = "custom_components/domotiapp_alarm/store.py"
PY_CONST = "custom_components/domotiapp_alarm/const.py"
PY_VALID = "custom_components/domotiapp_alarm/validatie.py"
PY_VOLG = "custom_components/domotiapp_alarm/volgende.py"
PY_WS = "custom_components/domotiapp_alarm/websocket.py"
JS_BEV = "src/bevestiging.js"
JS_WEER = "src/weergave.js"


@dataclass
class Mutatie:
    code: str
    bestand: str
    oud: str
    nieuw: str
    waarom: str
    js: bool = False


MUTATIES: list[Mutatie] = [
    # === ronde 1: bevestigt de dekking ================================
    # --- de migratie ---------------------------------------------------
    Mutatie(
        "M1",
        PY_STORE,
        "        if old_major_version == 1:\n            return _migreer_v1_naar_v2(old_data)",
        "        if old_major_version == 1:\n            return old_data",
        "de migratie doet niets — de bestaande klant raakt al zijn wekkers kwijt",
    ),
    Mutatie(
        "M2",
        PY_STORE,
        "                {s: w for s, w in wekker.items() if s not in VERVALLEN_VELDEN_V1}",
        "                {s: w for s, w in wekker.items() if s in VERVALLEN_VELDEN_V1}",
        "de migratie houdt ALLEEN het vervallen veld over in plaats van het weg te halen",
    ),
    Mutatie(
        "M3",
        PY_CONST,
        'VERVALLEN_VELDEN_V1: Final[frozenset[str]] = frozenset({"skip_next"})',
        "VERVALLEN_VELDEN_V1: Final[frozenset[str]] = frozenset()",
        "de lijst met vervallen velden is leeg",
    ),
    Mutatie(
        "M4",
        PY_CONST,
        "STORAGE_VERSION: Final = 2",
        "STORAGE_VERSION: Final = 1",
        "de schemaversie gaat niet omhoog, dus de migratie draait nooit",
    ),
    Mutatie(
        "M5",
        PY_STORE,
        "    personen = oud.get(\"persons\")\n    if not isinstance(personen, dict):\n        return oud",
        "    personen = oud.get(\"persons\")\n    if False:\n        return oud",
        "de migratie valt om op kapotte data in plaats van hem door te laten",
    ),
    Mutatie(
        "M6",
        PY_STORE,
        "        if not isinstance(wekkers, list):\n            nieuw_personen[registry_id] = blok\n            continue",
        "        if not isinstance(wekkers, list):\n            continue",
        "een persoon met een kapotte alarms-lijst verdwijnt uit de opslag",
    ),
    # --- het veld is echt weg -------------------------------------------
    Mutatie(
        "M7",
        PY_VALID,
        'SERVERVELDEN: frozenset[str] = frozenset(\n    {"one_shot_at", "last_fired", "last_message"}\n)',
        'SERVERVELDEN: frozenset[str] = frozenset(\n    {"skip_next", "one_shot_at", "last_fired", "last_message"}\n)',
        "skip_next staat weer als serverveld genoteerd",
    ),
    Mutatie(
        "M8",
        PY_WS,
        "    _handle_delete,\n    _handle_search,",
        "    _handle_delete,\n    _handle_get,\n    _handle_search,",
        "een commando dubbel registreren (positieve controle op de registratielijst)",
    ),
    # --- de kaart -------------------------------------------------------
    Mutatie(
        "M12",
        JS_BEV,
        '    return `Wil je de wekker "${naam}" van ${tijd} verwijderen?`;',
        '    return `Wil je de wekker "${naam}" verwijderen?`;',
        "de tijd valt uit de bevestiging — twee wekkers Werk zijn niet te onderscheiden",
        js=True,
    ),
    Mutatie(
        "M13",
        JS_WEER,
        "  if (isAfgelopen(wekker, nuMs)) {\n    return TEKST_AFGELOPEN;\n  }\n  return dagenTekst(wekker?.days);",
        "  return dagenTekst(wekker?.days);",
        "een afgelopen eenmalige wekker heet weer gewoon Eenmalig",
        js=True,
    ),
    # === ronde 2: zoekt naar gaten ====================================
    Mutatie(
        "M14",
        PY_STORE,
        "        raise NotImplementedError(\n            f\"Geen migratie beschikbaar van versie {old_major_version}.{old_minor_version} \"",
        "        return old_data\n        raise NotImplementedError(\n            f\"Geen migratie beschikbaar van versie {old_major_version}.{old_minor_version} \"",
        "een ONBEKENDE oudere versie wordt stil doorgelaten in plaats van te falen",
    ),
    Mutatie(
        "M15",
        PY_CONST,
        "STORAGE_MINOR_VERSION: Final = 1\n\n# Velden die in een oudere schemaversie bestonden",
        "STORAGE_MINOR_VERSION: Final = 2\n\n# Velden die in een oudere schemaversie bestonden",
        "minor_version blijft doortellen over de majorsprong heen",
    ),
    Mutatie(
        "M16",
        PY_STORE,
        "                if isinstance(wekker, dict)\n                else wekker",
        "                if isinstance(wekker, dict)\n                else {}",
        "een wekker die geen object is wordt stil vervangen door een leeg object",
    ),
    Mutatie(
        "M17",
        PY_VOLG,
        "    momenten = volgende_momenten(nu, wekker[\"time\"], dagen, aantal=1)\n    return momenten[0] if momenten else None",
        "    momenten = volgende_momenten(nu, wekker[\"time\"], dagen, aantal=2)\n    return momenten[1] if len(momenten) > 1 else None",
        "het volgende moment slaat er stiekem één over (de oude skip-tak)",
    ),
    Mutatie(
        "M18",
        JS_BEV,
        '  const naam = typeof wekker?.name === "string" ? wekker.name.trim() : "";',
        "  const naam = wekker?.name ?? \"\";",
        "een naam die geen tekst is komt zo in de bevestiging",
        js=True,
    ),
]


def draai(mutatie: Mutatie) -> tuple[bool, str]:
    cmd = (
        ["node", "--test", "tests/js/"]
        if mutatie.js
        else [sys.executable, "-m", "pytest", "-q", "-x", "--no-header", "tests/"]
    )
    uit = subprocess.run(cmd, cwd=WORTEL, capture_output=True, text=True)
    regels = [r for r in (uit.stdout or "").strip().splitlines() if r.strip()]
    samenvatting = next(
        (r for r in reversed(regels) if "pass" in r or "fail" in r), regels[-1] if regels else "?"
    )
    return uit.returncode == 0, samenvatting.strip()


def main() -> int:
    keuze = sys.argv[1] if len(sys.argv) > 1 else "alles"
    selectie = [m for m in MUTATIES if keuze == "alles" or (keuze == "js") == m.js]

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
