"""De mutatieproef van fase 6, ronde 1 en 2.

Draaien (in de Linux-container, want HA importeert `fcntl`)::

    MSYS_NO_PATHCONV=1 docker run --rm -v "C:/dev/domotiapp-alarm:/app" -w /app \
      python:3.14-slim sh -c "pip install -q -r requirements-test.txt && \
      python scripts/mutaties-fase-6.py"

Elke mutatie is een letterlijke tekstvervanging in een bronbestand. Het script zet
hem, draait de tests, en zet hem terug — ook als pytest ontploft. Een mutatie die
**slaagt** is een gat: de tests merken de wijziging niet.

De uitvoer is bedoeld om letterlijk in `docs/fase-6/RAPPORT.md` te plakken.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

WORTEL = Path(__file__).resolve().parent.parent


@dataclass
class Mutatie:
    code: str
    bestand: str
    oud: str
    nieuw: str
    waarom: str
    tests: list[str] = field(default_factory=list)


# Welke tests er per mutatie gedraaid worden. Alles draaien kost 40 s per mutatie;
# deze selectie houdt het onder de tien minuten zonder een gat te verbergen — de
# bestanden zijn ruim gekozen, niet op één test toegespitst.
AFVUREN = ["tests/test_afvuren.py", "tests/test_shuffle.py"]
PLANNER = ["tests/test_planner.py", "tests/test_afvuren.py"]
WS = ["tests/test_websocket.py", "tests/test_volgende.py"]

MUTATIES: list[Mutatie] = [
    # --- shuffle.py, de pure beslissing --------------------------------
    Mutatie(
        "M1",
        "custom_components/domotiapp_alarm/shuffle.py",
        "    return media_type.strip().lower() in MEERSTUKS_SOORTEN",
        "    return True",
        "altijd shuffelen — ook radio",
        AFVUREN,
    ),
    Mutatie(
        "M2",
        "custom_components/domotiapp_alarm/shuffle.py",
        "    return media_type.strip().lower() in MEERSTUKS_SOORTEN",
        "    return False",
        "nooit shuffelen — de functie volledig uitgeschakeld",
        AFVUREN,
    ),
    Mutatie(
        "M3",
        "custom_components/domotiapp_alarm/shuffle.py",
        "    return media_type.strip().lower() in MEERSTUKS_SOORTEN",
        "    return media_type in MEERSTUKS_SOORTEN",
        "geen normalisatie: 'Playlist' en ' playlist ' vallen buiten de boot",
        AFVUREN,
    ),
    Mutatie(
        "M4",
        "custom_components/domotiapp_alarm/shuffle.py",
        "    if not isinstance(media_type, str):\n        return False",
        "    if not isinstance(media_type, str):\n        return True",
        "bij twijfel wél shuffelen",
        AFVUREN,
    ),
    # --- afvuren.py, de volgorde en de melding --------------------------
    Mutatie(
        "M5",
        "custom_components/domotiapp_alarm/afvuren.py",
        '    await async_zet_shuffle(hass, speaker, (wekker.get("sound") or {}).get("media_type"))\n'
        "\n"
        "    # --- stap 6: geluid starten ----------------------------------------\n"
        '    gelukt, ma_reden = await _async_start_geluid(hass, speaker, wekker.get("sound") or {})',
        "    # --- stap 6: geluid starten ----------------------------------------\n"
        '    gelukt, ma_reden = await _async_start_geluid(hass, speaker, wekker.get("sound") or {})\n'
        '    await async_zet_shuffle(hass, speaker, (wekker.get("sound") or {}).get("media_type"))',
        "shuffle NA het afspelen — de aanroep bestaat, maar te laat. Dit is de "
        "bevinding zelf, in de vorm waarin een reparatie er per ongeluk uit kan zien.",
        AFVUREN,
    ),
    Mutatie(
        "M6",
        "custom_components/domotiapp_alarm/afvuren.py",
        '            {ATTR_ENTITY_ID: speaker, "shuffle": True},',
        '            {ATTR_ENTITY_ID: speaker, "shuffle": False},',
        "shuffle op False zetten",
        AFVUREN,
    ),
    Mutatie(
        "M7",
        "custom_components/domotiapp_alarm/afvuren.py",
        '    velden: dict[str, Any] = {"last_fired": moment.isoformat()}\n'
        "    if volgende.is_eenmalig(wekker):\n"
        '        velden["enabled"] = False',
        '    velden: dict[str, Any] = {"last_fired": moment.isoformat()}',
        "de eenmalige wekker gaat NIET uit — de bevinding uit productie",
        PLANNER,
    ),
    Mutatie(
        "M8",
        "custom_components/domotiapp_alarm/afvuren.py",
        "    if volgende.is_eenmalig(wekker):\n        velden[\"enabled\"] = False",
        "    if True:\n        velden[\"enabled\"] = False",
        "ELKE wekker gaat uit na één keer afgaan",
        PLANNER,
    ),
    Mutatie(
        "M9",
        "custom_components/domotiapp_alarm/afvuren.py",
        "        return False, _reden_van(fout)",
        "        return False, None",
        "de reden van MA wordt weggegooid",
        AFVUREN,
    ),
    Mutatie(
        "M10",
        "custom_components/domotiapp_alarm/afvuren.py",
        "    tekst = str(fout).strip()\n    if not tekst:\n        return None",
        "    tekst = str(fout).strip()\n    if False:\n        return None",
        "een lege reden wordt tóch doorgegeven",
        AFVUREN,
    ),
    Mutatie(
        "M11",
        "custom_components/domotiapp_alarm/afvuren.py",
        "            ma_reden=ma_reden or \"\",",
        "            ma_reden=\"\",",
        "de reden komt niet bij de melding aan",
        AFVUREN,
    ),
    # --- meldingen.py, de tekst ----------------------------------------
    Mutatie(
        "M12",
        "custom_components/domotiapp_alarm/meldingen.py",
        '        erbij = f\' Music Assistant meldde: "{reden}".\' if reden else ""',
        '        erbij = f\' Music Assistant meldde: "{reden}".\'',
        "de reden altijd invoegen, ook als hij leeg is",
        AFVUREN,
    ),
    Mutatie(
        "M13",
        "custom_components/domotiapp_alarm/meldingen.py",
        '            f"De wekker van {tijd} is niet afgegaan: het geluid \'{geluid}\' kon niet "\n'
        '            f"gestart worden.{erbij} Controleer het geluid in Music Assistant, of "\n'
        '            "kies een ander."',
        '            f"De wekker van {tijd} is niet afgegaan: het gekozen geluid \'{geluid}\' "\n'
        '            "bestaat niet meer. Kies een nieuw geluid."',
        "de oude, liegende tekst terug",
        AFVUREN,
    ),
    # --- volgende.py ----------------------------------------------------
    Mutatie(
        "M14",
        "custom_components/domotiapp_alarm/volgende.py",
        '    return not (wekker.get("days") or [])',
        '    return bool(wekker.get("days") or [])',
        "is_eenmalig omgedraaid",
        PLANNER,
    ),
    # --- planner.py, het overslaan --------------------------------------
    Mutatie(
        "M15",
        "custom_components/domotiapp_alarm/planner.py",
        '            {"skip_next": False, **afvuren.velden_bij_verbruikt_moment(wekker, moment)},',
        '            {"skip_next": False, "last_fired": moment.isoformat()},',
        "overslaan zet de eenmalige wekker niet uit (het tweede pad)",
        PLANNER,
    ),
    # --- websocket.py, het opnieuw aanzetten ----------------------------
    Mutatie(
        "M16",
        "custom_components/domotiapp_alarm/websocket.py",
        "        velden.update(_one_shot_bij_aanzetten(hass, store, registry_id, msg[\"alarm_id\"]))",
        "        pass",
        "aanzetten berekent geen nieuw moment",
        WS,
    ),
    Mutatie(
        "M17",
        "custom_components/domotiapp_alarm/websocket.py",
        "            if dt.datetime.fromisoformat(rauw) > nu:\n                return {}",
        "            if False:\n                return {}",
        "ook een toekomstig moment wordt opnieuw berekend — de wekker kan naar vroeger",
        WS,
    ),
    Mutatie(
        "M18",
        "custom_components/domotiapp_alarm/websocket.py",
        "    if wekker is None or not volgende.is_eenmalig(wekker):\n        return {}",
        "    if wekker is None:\n        return {}",
        "een herhalende wekker krijgt ook een one_shot_at",
        WS,
    ),
    # --- ronde 2: de randen die ronde 1 niet raakte ---------------------
    Mutatie(
        "M19",
        "custom_components/domotiapp_alarm/afvuren.py",
        "            blocking=True,\n        )\n    except Exception as fout:  # noqa: BLE001 - zie docstring\n"
        "        _LOGGER.warning(\n            \"Shuffle aanzetten op %s is mislukt",
        "            blocking=False,\n        )\n    except Exception as fout:  # noqa: BLE001 - zie docstring\n"
        "        _LOGGER.warning(\n            \"Shuffle aanzetten op %s is mislukt",
        "de shuffle-aanroep niet-blokkerend maken (valkuil 42)",
        AFVUREN,
    ),
    Mutatie(
        "M20",
        "custom_components/domotiapp_alarm/afvuren.py",
        "    return tekst.splitlines()[0].strip() or None",
        "    return tekst",
        "de hele foutmelding in de kaart, inclusief eventuele stacktrace",
        AFVUREN,
    ),
    Mutatie(
        "M21",
        "custom_components/domotiapp_alarm/websocket.py",
        '    return {"one_shot_at": eerstvolgende_keer_dat_tijd_voorbijkomt(nu, wekker["time"]).isoformat()}',
        '    return {"one_shot_at": nu.isoformat()}',
        "het nieuwe moment is NU in plaats van de eerstvolgende wektijd",
        WS,
    ),
    Mutatie(
        "M22",
        "custom_components/domotiapp_alarm/const.py",
        'MEERSTUKS_SOORTEN: Final[frozenset[str]] = frozenset({"playlist", "album", "artist"})',
        'MEERSTUKS_SOORTEN: Final[frozenset[str]] = frozenset({"playlist"})',
        "album en artiest vallen uit de lijst",
        AFVUREN,
    ),
]


def draai(tests: list[str]) -> tuple[bool, str]:
    uitkomst = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "--no-header", *tests],
        cwd=WORTEL,
        capture_output=True,
        text=True,
    )
    laatste = [r for r in uitkomst.stdout.strip().splitlines() if r.strip()]
    return uitkomst.returncode == 0, (laatste[-1] if laatste else "geen uitvoer")


def main() -> int:
    ongevangen: list[Mutatie] = []
    print(f"{'code':<5} {'gevangen':<9} bestand / wat er verandert")
    print("-" * 78)
    for mutatie in MUTATIES:
        pad = WORTEL / mutatie.bestand
        origineel = pad.read_text(encoding="utf-8")
        if mutatie.oud not in origineel:
            print(f"{mutatie.code:<5} {'PATCH MIST':<9} {mutatie.bestand} — {mutatie.waarom}")
            ongevangen.append(mutatie)
            continue
        if origineel.count(mutatie.oud) != 1:
            print(
                f"{mutatie.code:<5} {'NIET UNIEK':<9} {mutatie.bestand} "
                f"({origineel.count(mutatie.oud)}x) — {mutatie.waarom}"
            )
            ongevangen.append(mutatie)
            continue
        try:
            pad.write_text(origineel.replace(mutatie.oud, mutatie.nieuw), encoding="utf-8")
            groen, regel = draai(mutatie.tests)
        finally:
            pad.write_text(origineel, encoding="utf-8")
        merk = "NEE  <<<" if groen else "ja"
        print(f"{mutatie.code:<5} {merk:<9} {mutatie.waarom}")
        print(f"{'':<15} {regel}")
        if groen:
            ongevangen.append(mutatie)

    print("-" * 78)
    print(f"{len(MUTATIES) - len(ongevangen)} van {len(MUTATIES)} gevangen")
    for mutatie in ongevangen:
        print(f"  ONGEVANGEN {mutatie.code}: {mutatie.bestand} — {mutatie.waarom}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
