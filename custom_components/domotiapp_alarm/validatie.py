"""Validatie van het opslagschema (SPEC 14.2).

Deze module is **puur**: geen `hass`, geen Home Assistant-imports. Hij beoordeelt
of een stuk data aan het schema voldoet en zegt bij een afkeuring **welk veld** en
**waarom**.

Twee aanroepers, met opzet dezelfde regels:

- `store.py` bij het **laden**, om te bepalen of een persoon gevalideerd of kapot
  is (SPEC 19.2 geval B);
- `websocket.py` bij het **opslaan**, om `invalid_format` terug te geven vóórdat er
  iets wordt weggeschreven (SPEC 15.2).

Zonder die gedeelde regels zou een wekker die via de API geweigerd wordt, na een
herstart alsnog als geldig uit de opslag kunnen komen.

**De regel achter alle regels** (SPEC 19.1): een waarde die niet valideert *is
geen waarde*. Er wordt nooit een default ingevuld en stil doorgegaan.
"""

from __future__ import annotations

from typing import Any

from .const import (
    BRIGHTNESS_PCT_MAX,
    BRIGHTNESS_PCT_MIN,
    SEVERITY_ERROR,
    SEVERITY_NOTICE,
    VOLUME_PCT_MAX,
    VOLUME_PCT_MIN,
    WEEKDAG_MAX,
    WEEKDAG_MIN,
)
from .volgende import parse_tijd

# Velden die de gebruiker beheert en die `alarms/save` accepteert (SPEC 15.2).
GEBRUIKERSVELDEN: frozenset[str] = frozenset(
    {"id", "name", "time", "days", "enabled", "sound", "speaker", "volume_pct", "light"}
)

# Velden die de server zelf beheert en die nooit van de kaart komen (SPEC 15.2).
SERVERVELDEN: frozenset[str] = frozenset(
    {"one_shot_at", "last_fired", "last_message"}
)

_SOUND_VELDEN: frozenset[str] = frozenset({"uri", "name", "media_type", "image"})
_LIGHT_VELDEN: frozenset[str] = frozenset({"entity_id", "brightness_pct"})
_MESSAGE_VELDEN: frozenset[str] = frozenset({"at", "kind", "severity", "text"})


class ValidatieFout(ValueError):
    """Een veld voldoet niet aan het schema.

    `veld` is het pad naar het veld, zodat de WebSocket-fout kan zeggen wát er
    mis is in plaats van alleen dát er iets mis is.
    """

    def __init__(self, veld: str, bericht: str) -> None:
        self.veld = veld
        self.bericht = bericht
        super().__init__(f"{veld}: {bericht}")


def _eis_bool(waarde: Any, veld: str) -> bool:
    # Bewust niet `bool(waarde)`: dan zou "nee" of 0 stil doorgaan als een
    # geldige boolean, en dat is precies het stille terugvallen uit SPEC 19.1.
    if not isinstance(waarde, bool):
        raise ValidatieFout(veld, f"moet true of false zijn, kreeg {waarde!r}")
    return waarde


def _eis_string(waarde: Any, veld: str, *, mag_leeg: bool = False) -> str:
    if not isinstance(waarde, str):
        raise ValidatieFout(veld, f"moet tekst zijn, kreeg {type(waarde).__name__}")
    if not mag_leeg and not waarde.strip():
        raise ValidatieFout(veld, "mag niet leeg zijn")
    return waarde


def _eis_int_bereik(waarde: Any, veld: str, minimum: int, maximum: int) -> int:
    # `isinstance(True, int)` is waar in Python; een boolean is hier geen getal.
    if isinstance(waarde, bool) or not isinstance(waarde, int):
        raise ValidatieFout(veld, f"moet een heel getal zijn, kreeg {waarde!r}")
    if not (minimum <= waarde <= maximum):
        raise ValidatieFout(veld, f"moet tussen {minimum} en {maximum} liggen, kreeg {waarde}")
    return waarde


def valideer_tijd(waarde: Any, veld: str = "time") -> str:
    try:
        parse_tijd(waarde)
    except ValueError as fout:
        raise ValidatieFout(veld, str(fout)) from fout
    return waarde


def valideer_dagen(waarde: Any, veld: str = "days") -> list[int]:
    """ISO-weekdagen 1–7. Een lege lijst is geldig: dat is een eenmalige wekker."""
    if not isinstance(waarde, list):
        raise ValidatieFout(veld, f"moet een lijst zijn, kreeg {type(waarde).__name__}")
    dagen: list[int] = []
    for index, dag in enumerate(waarde):
        if isinstance(dag, bool) or not isinstance(dag, int):
            raise ValidatieFout(f"{veld}[{index}]", f"moet een heel getal zijn, kreeg {dag!r}")
        if not (WEEKDAG_MIN <= dag <= WEEKDAG_MAX):
            raise ValidatieFout(
                f"{veld}[{index}]",
                f"moet tussen {WEEKDAG_MIN} (maandag) en {WEEKDAG_MAX} (zondag) liggen, kreeg {dag}",
            )
        dagen.append(dag)
    if len(set(dagen)) != len(dagen):
        raise ValidatieFout(veld, f"bevat dubbele dagen: {waarde!r}")
    return sorted(dagen)


def valideer_sound(waarde: Any, veld: str = "sound") -> dict[str, Any]:
    """Het gekozen geluid: `uri`, `name`, `media_type` en `image` (SPEC 8.2).

    `image` mag `null` zijn — niet elk item heeft een afbeelding; SomaFM gaf er in
    fase 0b geen. De andere drie zijn verplicht, want zonder `uri` valt er niets af
    te spelen en zonder `name` kan een foutmelding niet zeggen wélk geluid weg is.
    """
    if not isinstance(waarde, dict):
        raise ValidatieFout(veld, f"moet een object zijn, kreeg {type(waarde).__name__}")
    onbekend = set(waarde) - _SOUND_VELDEN
    if onbekend:
        raise ValidatieFout(veld, f"onbekende velden: {sorted(onbekend)}")
    for sleutel in ("uri", "name", "media_type"):
        if sleutel not in waarde:
            raise ValidatieFout(f"{veld}.{sleutel}", "is verplicht")
        _eis_string(waarde[sleutel], f"{veld}.{sleutel}")
    image = waarde.get("image")
    if image is not None:
        _eis_string(image, f"{veld}.image")
    return {
        "uri": waarde["uri"],
        "name": waarde["name"],
        "media_type": waarde["media_type"],
        "image": image,
    }


def valideer_light(waarde: Any, veld: str = "light") -> dict[str, Any] | None:
    """De wake-up light, of `None`. Optioneel (SPEC 12)."""
    if waarde is None:
        return None
    if not isinstance(waarde, dict):
        raise ValidatieFout(veld, f"moet een object of null zijn, kreeg {type(waarde).__name__}")
    onbekend = set(waarde) - _LIGHT_VELDEN
    if onbekend:
        raise ValidatieFout(veld, f"onbekende velden: {sorted(onbekend)}")
    if "entity_id" not in waarde:
        raise ValidatieFout(f"{veld}.entity_id", "is verplicht")
    entity_id = _eis_string(waarde["entity_id"], f"{veld}.entity_id")
    if not entity_id.startswith("light."):
        raise ValidatieFout(f"{veld}.entity_id", f"moet in het light-domein zitten, kreeg {entity_id}")
    if "brightness_pct" not in waarde:
        raise ValidatieFout(f"{veld}.brightness_pct", "is verplicht")
    helderheid = _eis_int_bereik(
        waarde["brightness_pct"], f"{veld}.brightness_pct", BRIGHTNESS_PCT_MIN, BRIGHTNESS_PCT_MAX
    )
    return {"entity_id": entity_id, "brightness_pct": helderheid}


def valideer_message(waarde: Any, veld: str = "last_message") -> dict[str, Any] | None:
    """De melding op de kaart, of `None` (SPEC 14.2.1)."""
    if waarde is None:
        return None
    if not isinstance(waarde, dict):
        raise ValidatieFout(veld, f"moet een object of null zijn, kreeg {type(waarde).__name__}")
    onbekend = set(waarde) - _MESSAGE_VELDEN
    if onbekend:
        raise ValidatieFout(veld, f"onbekende velden: {sorted(onbekend)}")
    for sleutel in _MESSAGE_VELDEN:
        if sleutel not in waarde:
            raise ValidatieFout(f"{veld}.{sleutel}", "is verplicht")
        _eis_string(waarde[sleutel], f"{veld}.{sleutel}")
    if waarde["severity"] not in (SEVERITY_ERROR, SEVERITY_NOTICE):
        raise ValidatieFout(
            f"{veld}.severity",
            f"moet {SEVERITY_ERROR!r} of {SEVERITY_NOTICE!r} zijn, kreeg {waarde['severity']!r}",
        )
    return dict(waarde)


def _valideer_iso(waarde: Any, veld: str) -> str | None:
    """ISO-8601 **met** tijdzone, of `None` (SPEC 14.2)."""
    if waarde is None:
        return None
    tekst = _eis_string(waarde, veld)
    import datetime as dt

    try:
        moment = dt.datetime.fromisoformat(tekst)
    except ValueError as fout:
        raise ValidatieFout(veld, f"moet ISO-8601 zijn, kreeg {tekst!r}") from fout
    if moment.tzinfo is None:
        raise ValidatieFout(veld, f"moet een tijdzone bevatten, kreeg {tekst!r}")
    return tekst


def valideer_wekker(waarde: Any, veld: str = "alarm") -> dict[str, Any]:
    """Eén volledige wekker zoals hij in de opslag staat (SPEC 14.2).

    Geeft een **genormaliseerde kopie** terug met precies de velden uit het
    schema, in vaste volgorde. Onbekende velden worden geweigerd en niet
    stilzwijgend meegenomen: een veld dat wij niet kennen kan de planner ook niet
    interpreteren.
    """
    if not isinstance(waarde, dict):
        raise ValidatieFout(veld, f"moet een object zijn, kreeg {type(waarde).__name__}")

    toegestaan = GEBRUIKERSVELDEN | SERVERVELDEN
    onbekend = set(waarde) - toegestaan
    if onbekend:
        raise ValidatieFout(veld, f"onbekende velden: {sorted(onbekend)}")

    for sleutel in ("id", "name", "time", "days", "enabled", "sound", "speaker", "volume_pct"):
        if sleutel not in waarde:
            raise ValidatieFout(f"{veld}.{sleutel}", "is verplicht")

    dagen = valideer_dagen(waarde["days"], f"{veld}.days")
    one_shot_at = _valideer_iso(waarde.get("one_shot_at"), f"{veld}.one_shot_at")

    # De samenhang tussen days en one_shot_at is een schemaregel, niet een
    # implementatiedetail: een eenmalige wekker zonder moment is niet te plannen,
    # en een herhalende wekker mét moment zou twee bronnen van waarheid hebben.
    if dagen and one_shot_at is not None:
        raise ValidatieFout(
            f"{veld}.one_shot_at", "mag alleen gevuld zijn als days leeg is (eenmalige wekker)"
        )

    # Alleen "is het een niet-lege tekst". Of deze speaker **mag**, wordt bepaald
    # door `entiteiten.is_ma_speaker` volgens de zes eisen van SPEC 7.2, en dat
    # levert `not_allowed` op en geen `invalid_format` (SPEC 15.2). Een tweede
    # domeincontrole hier zou dezelfde afkeuring onder twee verschillende
    # foutcodes laten uitkomen, afhankelijk van welke controle eerst draait.
    speaker = _eis_string(waarde["speaker"], f"{veld}.speaker")

    return {
        "id": _eis_string(waarde["id"], f"{veld}.id"),
        "name": _eis_string(waarde["name"], f"{veld}.name"),
        "time": valideer_tijd(waarde["time"], f"{veld}.time"),
        "days": dagen,
        "enabled": _eis_bool(waarde["enabled"], f"{veld}.enabled"),
        "one_shot_at": one_shot_at,
        "sound": valideer_sound(waarde["sound"], f"{veld}.sound"),
        "speaker": speaker,
        "volume_pct": _eis_int_bereik(
            waarde["volume_pct"], f"{veld}.volume_pct", VOLUME_PCT_MIN, VOLUME_PCT_MAX
        ),
        "light": valideer_light(waarde.get("light"), f"{veld}.light"),
        "last_fired": _valideer_iso(waarde.get("last_fired"), f"{veld}.last_fired"),
        "last_message": valideer_message(waarde.get("last_message"), f"{veld}.last_message"),
    }


def valideer_persoon(waarde: Any, veld: str = "person") -> dict[str, Any]:
    """De data van één persoon: `{"alarms": [...]}` (SPEC 14.2)."""
    if not isinstance(waarde, dict):
        raise ValidatieFout(veld, f"moet een object zijn, kreeg {type(waarde).__name__}")
    onbekend = set(waarde) - {"alarms"}
    if onbekend:
        raise ValidatieFout(veld, f"onbekende velden: {sorted(onbekend)}")
    if "alarms" not in waarde:
        raise ValidatieFout(f"{veld}.alarms", "is verplicht")
    if not isinstance(waarde["alarms"], list):
        raise ValidatieFout(
            f"{veld}.alarms", f"moet een lijst zijn, kreeg {type(waarde['alarms']).__name__}"
        )

    wekkers = [
        valideer_wekker(wekker, f"{veld}.alarms[{index}]")
        for index, wekker in enumerate(waarde["alarms"])
    ]

    ids = [wekker["id"] for wekker in wekkers]
    if len(set(ids)) != len(ids):
        raise ValidatieFout(f"{veld}.alarms", "bevat wekkers met hetzelfde id")

    return {"alarms": wekkers}
