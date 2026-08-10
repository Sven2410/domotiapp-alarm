"""Wanneer gaat een wekker de eerstvolgende keer af.

Deze module is **puur**: geen `hass`, geen imports uit Home Assistant, geen
netwerk, geen klok anders dan wat je meegeeft. Daardoor is hij in een gewone
unittest te toetsen met een vaste `nu`, en dat is precies wat de
zomertijdgevallen nodig hebben.

**Fase 3b hergebruikt deze module.** De planner uit SPEC 13 heeft dezelfde
rekenkunde nodig: bij setup om vast te stellen welk moment gemist is
(respijtvenster, SPEC 13.4), en daarna om vooruit te plannen. Er mag geen tweede
implementatie van deze berekening komen — dat is de fout die DomotiApp Scene met
de helderheidsschaal maakte, waar kaart en server het over verschillende getallen
hadden.

## Zomertijd

Het gedrag volgt `async_track_time_change`, want dat is wat er in fase 3b
daadwerkelijk plant (SPEC 13.1). Dat betekent, gemeten in fase 0
(`docs/fase-0/ONDERZOEK.md` E1.3):

- **Voorjaar.** Een wandkloktijd die niet bestaat wordt **overgeslagen**: 02:30 op
  29 maart 2026 bestaat niet in Europe/Amsterdam, dus die dag gaat de wekker niet
  af en schuift hij naar de volgende passende dag.
- **Najaar.** Een wandkloktijd die twee keer voorkomt levert hier het **eerste**
  van de twee momenten op, want dat is het eerstvolgende moment. Dat de planner
  hem die nacht twee keer laat afgaan is gedrag van de planner, geen eigenschap
  van "wanneer is de eerstvolgende keer".
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

# Nederlandse namen, want alle zichtbare teksten zijn Nederlands (SPEC 1).
_DAGEN_VOLUIT = (
    "Maandag",
    "Dinsdag",
    "Woensdag",
    "Donderdag",
    "Vrijdag",
    "Zaterdag",
    "Zondag",
)
_DAGEN_KORT = ("ma", "di", "wo", "do", "vr", "za", "zo")
_MAANDEN_KORT = (
    "jan",
    "feb",
    "mrt",
    "apr",
    "mei",
    "jun",
    "jul",
    "aug",
    "sep",
    "okt",
    "nov",
    "dec",
)

GEEN_WEKKER_TEKST = "Geen wekker actief"

# Hoe ver we vooruit zoeken. Een wekker met herhaaldagen komt binnen 7 dagen
# langs; 8 dagen geeft ruimte voor een dag die door zomertijd wordt overgeslagen.
_MAX_DAGEN_VOORUIT = 8


@dataclass(frozen=True, slots=True)
class VolgendMoment:
    """Het eerstvolgende moment plus de kant-en-klare tekst voor de kaart."""

    at: dt.datetime
    text: str
    alarm_id: str


def bestaat(moment: dt.datetime) -> bool:
    """Bestaat deze wandkloktijd in zijn tijdzone?

    Bij de overgang naar zomertijd wordt een uur overgeslagen; een tijd in dat
    uur bestaat niet. De controle is een rondje langs UTC — dezelfde methode die
    Home Assistant zelf gebruikt (`util/dt.py:_datetime_exists`).
    """
    if moment.tzinfo is None:
        raise ValueError("moment moet een tijdzone hebben")
    return moment == moment.astimezone(dt.UTC).astimezone(moment.tzinfo)


def _kandidaat(datum: dt.date, uur: int, minuut: int, tz: dt.tzinfo) -> dt.datetime:
    """De wandkloktijd op deze datum, met fold=0.

    `fold=0` betekent: bij een dubbel voorkomend uur het **eerste** van de twee.
    """
    return dt.datetime(datum.year, datum.month, datum.day, uur, minuut, 0, 0, tzinfo=tz).replace(
        fold=0
    )


def parse_tijd(tijd: str) -> tuple[int, int]:
    """`"06:45"` naar `(6, 45)`. Gooit `ValueError` bij een ongeldige vorm.

    Bewust streng: geen `6:45`, geen `06:45:00`, geen witruimte. De opslag bevat
    één vorm, en die vorm is wat de planner straks leest.
    """
    if not isinstance(tijd, str) or len(tijd) != 5 or tijd[2] != ":":
        raise ValueError(f"tijd moet de vorm HH:MM hebben, kreeg {tijd!r}")
    uur_s, minuut_s = tijd[:2], tijd[3:]
    if not (uur_s.isdigit() and minuut_s.isdigit()):
        raise ValueError(f"tijd moet de vorm HH:MM hebben, kreeg {tijd!r}")
    uur, minuut = int(uur_s), int(minuut_s)
    if not (0 <= uur <= 23 and 0 <= minuut <= 59):
        raise ValueError(f"tijd buiten bereik: {tijd!r}")
    return uur, minuut


def volgende_momenten(
    nu: dt.datetime,
    tijd: str,
    dagen: list[int] | tuple[int, ...],
    *,
    aantal: int = 1,
) -> list[dt.datetime]:
    """De eerstvolgende `aantal` momenten ná `nu` voor een herhalende wekker.

    :param nu: tijdzone-bewust; de tijdzone bepaalt de wandklok.
    :param tijd: `"HH:MM"`.
    :param dagen: ISO-weekdagen 1–7. **Leeg betekent: elke dag** — een eenmalige
        wekker gebruikt deze functie niet, die heeft `one_shot_at`.
    """
    if nu.tzinfo is None:
        raise ValueError("nu moet een tijdzone hebben")
    uur, minuut = parse_tijd(tijd)
    tz = nu.tzinfo
    toegestaan = set(dagen) if dagen else set(range(1, 8))

    gevonden: list[dt.datetime] = []
    for verschuiving in range(_MAX_DAGEN_VOORUIT + 1):
        datum = (nu + dt.timedelta(days=verschuiving)).date()
        if datum.isoweekday() not in toegestaan:
            continue
        moment = _kandidaat(datum, uur, minuut, tz)
        # Voorjaar: deze wandkloktijd bestaat vandaag niet. Overslaan, net als
        # find_next_time_expression_time doet.
        if not bestaat(moment):
            continue
        if moment <= nu:
            continue
        gevonden.append(moment)
        if len(gevonden) >= aantal:
            break
    return gevonden


def laatste_verstreken_moment(
    nu: dt.datetime, tijd: str, dagen: list[int] | tuple[int, ...]
) -> dt.datetime | None:
    """Het meest recente moment **in het verleden** dat aan tijd én dagen voldoet.

    Dit is stap 1 van het respijtvenster (SPEC 13.4). `None` betekent: deze wekker is
    nog nooit langsgekomen binnen het zoekvenster, dus er valt niets in te halen.

    Zelfde regels als vooruit kijken: een wandkloktijd die niet bestaat wordt
    **overgeslagen**, want de planner heeft hem die dag ook niet laten afgaan.

    Bij een dubbel voorkomend uur (najaar) geeft deze functie het **tweede** van de
    twee — het meest recente. Dat is bedoeld: staat `last_fired` op het eerste, dan
    is het tweede nog niet gehad en hoort het te worden ingehaald, precies zoals
    SPEC 13.1 twee keer vuren voorschrijft.
    """
    if nu.tzinfo is None:
        raise ValueError("nu moet een tijdzone hebben")
    uur, minuut = parse_tijd(tijd)
    tz = nu.tzinfo
    toegestaan = set(dagen) if dagen else set(range(1, 8))

    for verschuiving in range(_MAX_DAGEN_VOORUIT + 1):
        datum = (nu - dt.timedelta(days=verschuiving)).date()
        if datum.isoweekday() not in toegestaan:
            continue
        # Beide folds langslopen, laatste eerst: bij een dubbel uur is het tweede
        # moment het meest recente.
        for fold in (1, 0):
            moment = dt.datetime(
                datum.year, datum.month, datum.day, uur, minuut, 0, 0, tzinfo=tz
            ).replace(fold=fold)
            if not bestaat(moment):
                continue
            if moment >= nu:
                continue
            return moment
    return None


def tekst_voor(moment: dt.datetime, nu: dt.datetime) -> str:
    """De regel onderaan de kaart (SPEC 3.3)."""
    klok = f"{moment.hour:02d}:{moment.minute:02d}"
    dagen_verschil = (moment.date() - nu.date()).days
    if dagen_verschil == 0:
        return f"Vandaag {klok}"
    if dagen_verschil == 1:
        return f"Morgen {klok}"
    if 2 <= dagen_verschil <= 6:
        return f"{_DAGEN_VOLUIT[moment.isoweekday() - 1]} {klok}"
    return (
        f"{_DAGEN_KORT[moment.isoweekday() - 1]} {moment.day} "
        f"{_MAANDEN_KORT[moment.month - 1]} {klok}"
    )


def dagen_tekst(dagen: list[int] | tuple[int, ...]) -> str:
    """`[1,2,3,4,5]` naar `"ma di wo do vr"`; leeg naar `"Eenmalig"` (SPEC 3.2)."""
    if not dagen:
        return "Eenmalig"
    return " ".join(_DAGEN_KORT[d - 1] for d in sorted(set(dagen)))


def volgend_moment_van_wekker(wekker: dict, nu: dt.datetime) -> dt.datetime | None:
    """Het eerstvolgende moment van één wekker, of `None`.

    `None` betekent: deze wekker gaat niet meer af. Dat geldt voor een
    uitgezette wekker en voor een eenmalige wekker waarvan het moment voorbij is.

    `skip_next` slaat het **eerstvolgende** moment over: de teruggegeven waarde is
    dan het moment daarna. Dat is wat de kaart moet tonen, want de gebruiker heeft
    gezegd "deze ene niet".
    """
    if not wekker.get("enabled"):
        return None

    dagen = wekker.get("days") or []
    overslaan = bool(wekker.get("skip_next"))

    if not dagen:
        # Eenmalige wekker: het moment staat in de opslag.
        rauw = wekker.get("one_shot_at")
        if not rauw:
            return None
        moment = dt.datetime.fromisoformat(rauw)
        if moment.tzinfo is None:
            raise ValueError("one_shot_at moet een tijdzone hebben")
        if moment <= nu:
            return None
        # Een overgeslagen eenmalige wekker gaat helemaal niet meer af.
        return None if overslaan else moment

    aantal = 2 if overslaan else 1
    momenten = volgende_momenten(nu, wekker["time"], dagen, aantal=aantal)
    if len(momenten) < aantal:
        return None
    return momenten[aantal - 1]


def volgende_wekker(wekkers: list[dict], nu: dt.datetime) -> VolgendMoment | None:
    """Welke wekker gaat als eerste af, en wanneer (SPEC 15.1 `next_fire`).

    Geeft `None` als er geen enkele wekker aan staat. De kaart toont dan
    `GEEN_WEKKER_TEKST`.
    """
    beste: tuple[dt.datetime, str] | None = None
    for wekker in wekkers:
        moment = volgend_moment_van_wekker(wekker, nu)
        if moment is None:
            continue
        if beste is None or moment < beste[0]:
            beste = (moment, wekker["id"])
    if beste is None:
        return None
    return VolgendMoment(at=beste[0], text=tekst_voor(beste[0], nu), alarm_id=beste[1])


def eerstvolgende_keer_dat_tijd_voorbijkomt(nu: dt.datetime, tijd: str) -> dt.datetime:
    """Voor `one_shot_at` (SPEC 15.2): de eerstvolgende keer dat `tijd` langskomt.

    Wordt server-side gebruikt wanneer `days` leeg is. Slaat een niet-bestaande
    wandkloktijd over, net als de herhalende variant.
    """
    momenten = volgende_momenten(nu, tijd, [], aantal=1)
    if not momenten:
        # Kan alleen als de tijd acht dagen op rij niet bestaat, wat niet kan.
        raise ValueError(f"geen moment gevonden voor {tijd!r} na {nu.isoformat()}")
    return momenten[0]


def sorteer(wekkers: list[dict]) -> list[dict]:
    """Op tijd oplopend, bij gelijke tijd op naam (SPEC 3.4).

    Niet op "eerstvolgende": dan verspringt de lijst gedurende de dag en verliest
    de gebruiker zijn plek.
    """
    return sorted(wekkers, key=lambda w: (w.get("time", ""), (w.get("name") or "").lower()))
