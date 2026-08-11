"""De mutatieproef van fase 8, ronde 1 en 2.

Draaien in de Linux-container (HA importeert `fcntl`)::

    MSYS_NO_PATHCONV=1 docker run --rm -v "C:/dev/domotiapp-alarm:/app" -w /app \
      python:3.14-slim sh -c "pip install -q -r requirements-test.txt && \
      python scripts/mutaties-fase-8.py"

Alles zit deze ronde in Python: de opmaakwijzigingen van bevinding 1 zijn CSS, en
CSS is met een tekstvervanging niet zinvol te muteren — die kant is met gemeten
posities in de browser vastgelegd en niet met unittests.

Elke mutatie is een letterlijke tekstvervanging, wordt gezet, getest en teruggezet
— ook als pytest ontploft. Een mutatie die **slaagt** is een gat.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

WORTEL = Path(__file__).resolve().parent.parent
VB = "custom_components/domotiapp_alarm/voorbeeld.py"
WS = "custom_components/domotiapp_alarm/websocket.py"


@dataclass
class Mutatie:
    code: str
    bestand: str
    oud: str
    nieuw: str
    waarom: str


MUTATIES: list[Mutatie] = [
    # === ronde 1: bevestigt de dekking ================================
    Mutatie(
        "M1",
        VB,
        "    lamp_entity, lamp_voor = await _async_lamp_aan(hass, lamp)",
        "    lamp_entity, lamp_voor = None, None",
        "het voorbeeld zet de lamp helemaal niet aan — de bevinding zelf",
    ),
    Mutatie(
        "M2",
        VB,
        '            {ATTR_ENTITY_ID: entity_id, "brightness_pct": lamp.get("brightness_pct")},',
        "            {ATTR_ENTITY_ID: entity_id},",
        "de lamp gaat aan zonder helderheid — je ziet niet wat je instelde",
    ),
    Mutatie(
        "M3",
        VB,
        "    await _async_lamp_terug(hass, context.get(CTX_LAMP), context.get(CTX_LAMP_VOOR))",
        "    pass",
        "de lamp blijft na het voorbeeld branden",
    ),
    Mutatie(
        "M4",
        VB,
        "    if not entity_id or stand is None:\n        return",
        "    if not entity_id:\n        return",
        "een onleesbare stand wordt tóch teruggezet (verzonnen waarde)",
    ),
    Mutatie(
        "M5",
        VB,
        '        if not stand["aan"]:',
        "        if False:",
        "een lamp die uit stond blijft aan na het voorbeeld",
    ),
    Mutatie(
        "M6",
        VB,
        '        if stand["brightness"] is not None:\n            data["brightness"] = stand["brightness"]',
        "        if False:\n            data[\"brightness\"] = stand[\"brightness\"]",
        "de oude helderheid gaat verloren; de lamp komt op volle sterkte terug",
    ),
    Mutatie(
        "M7",
        VB,
        "    stand_voor = lampstand_van(hass, entity_id)",
        "    stand_voor = None\n    lampstand_van(hass, entity_id)",
        "de oude stand wordt gelezen maar niet bewaard",
    ),
    Mutatie(
        "M8",
        VB,
        "    if state is None or state.state not in (STATE_ON, STATE_OFF):\n        return None",
        "    if state is None:\n        return None",
        "een `unavailable` lamp levert toch een stand op",
    ),
    Mutatie(
        "M9",
        WS,
        "            geschikt, reden = entiteiten.is_wekkerlamp(hass, lamp[\"entity_id\"])\n"
        "            if not geschikt:\n"
        "                raise voorbeeld.VoorbeeldGeweigerd(\"not_allowed\", str(reden))",
        "            pass",
        "elke lamp in huis is via het voorbeeld aan te zetten",
    ),
    Mutatie(
        "M10",
        WS,
        '        lamp = valideer_light(msg.get("light"), "light")',
        '        lamp = msg.get("light")',
        "de lamp gaat ongekeurd door naar light.turn_on",
    ),
    # === ronde 2: zoekt naar gaten ====================================
    # M11 is VERVALLEN. Hij haalde de controle op een lege `entity_id` weg en werd
    # niet gevangen — narekenen wees uit dat er geen invoer is waarbij die regel iets
    # verandert: `valideer_light` eist een `entity_id` in het light-domein en is de
    # enige weg hierheen. De regel is daarom uit de code gehaald in plaats van er een
    # test bij te verzinnen (valkuil 34, derde rij).
    Mutatie(
        "M12",
        VB,
        "    lamp_entity, lamp_voor = await _async_lamp_aan(hass, lamp)\n\n    context",
        "    lamp_entity, lamp_voor = await _async_lamp_aan(hass, lamp)\n"
        "    lamp_voor = {\"aan\": False, \"brightness\": None}\n\n    context",
        "de bewaarde stand wordt overschreven met een vaste 'uit'",
    ),
    Mutatie(
        "M13",
        VB,
        "    helderheid = state.attributes.get(\"brightness\")\n    return {\n        \"aan\": True,\n"
        "        \"brightness\": int(helderheid) if isinstance(helderheid, (int, float)) else None,\n    }",
        "    helderheid = state.attributes.get(\"brightness\")\n    return {\n        \"aan\": True,\n"
        "        \"brightness\": helderheid,\n    }",
        "een helderheid die geen getal is gaat zo naar light.turn_on",
    ),
    Mutatie(
        "M14",
        VB,
        "    except Exception as fout:  # noqa: BLE001 - het licht is het voorbeeld niet",
        "    except ValueError as fout:",
        "een falende lamp breekt het voorbeeld alsnog af",
    ),
    Mutatie(
        "M15",
        VB,
        "    lamp_entity, lamp_voor = await _async_lamp_aan(hass, lamp)\n\n    context",
        "    context",
        "de lamp-aanroep valt weg maar de context blijft (bewijst dat de test op de "
        "aanroep let en niet op de context)",
    ),
]


def draai() -> tuple[bool, str]:
    uit = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "--no-header", "tests/"],
        cwd=WORTEL,
        capture_output=True,
        text=True,
    )
    regels = [r for r in (uit.stdout or "").strip().splitlines() if r.strip()]
    samenvatting = next(
        (r for r in reversed(regels) if "pass" in r or "fail" in r or "error" in r),
        regels[-1] if regels else "?",
    )
    return uit.returncode == 0, samenvatting.strip()


def main() -> int:
    ongevangen: list[Mutatie] = []
    print(f"{'code':<5} {'gevangen':<9} wat er verandert")
    print("-" * 78)
    for mutatie in MUTATIES:
        pad = WORTEL / mutatie.bestand
        origineel = pad.read_text(encoding="utf-8")
        aantal = origineel.count(mutatie.oud)
        if aantal != 1:
            print(f"{mutatie.code:<5} {'PATCH ' + str(aantal):<9} {mutatie.waarom}")
            ongevangen.append(mutatie)
            continue
        try:
            pad.write_text(origineel.replace(mutatie.oud, mutatie.nieuw), encoding="utf-8")
            groen, regel = draai()
        finally:
            pad.write_text(origineel, encoding="utf-8")
        print(f"{mutatie.code:<5} {'NEE  <<<' if groen else 'ja':<9} {mutatie.waarom}")
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
