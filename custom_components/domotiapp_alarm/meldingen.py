"""Meldingen aan de klant en aan de beheerder (SPEC 11.7 en 19.2).

Drie kanalen, met opzet gescheiden omdat ze verschillende mensen bereiken:

| Kanaal | Voor wie | Wanneer |
|---|---|---|
| `last_message` in de opslag | de **klant**, op de kaart | elke fout én elke mededeling |
| `persistent_notification` | de **klant**, in HA's meldingenlijst | alleen bij `severity: "error"` |
| repair issue | de **beheerder** | alleen bij onleesbare opslag (SPEC 19.2) |

Waarom geen repair issue voor de klant: die zijn admin-only
(`components/repairs`), en de klant is geen admin (SPEC 17). Een melding die
alleen de eigenaar ziet, bereikt de persoon die zich verslaapt niet.

Waarom geen `persistent_notification` bij een mededeling: die zou de meldingenlijst
vullen met dingen waar niets aan te doen is, en dan leest niemand hem meer
(SPEC 11.7).
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    ISSUE_CORRUPT_PERSON_PREFIX,
    ISSUE_STORE_UNUSABLE,
    SEVERITY_ERROR,
    SEVERITY_NOTICE,
    STORAGE_KEY,
)

_LOGGER = logging.getLogger(__name__)

# --- de soorten meldingen (SPEC 11.7) -----------------------------------

KIND_SPEAKER_UNAVAILABLE = "speaker_unavailable"
KIND_MA_UNAVAILABLE = "ma_unavailable"
# De naam blijft `sound_gone` — hij staat in de opslag van elke klant die 1.0.0
# draaide en de kaart vergelijkt erop (SPEC 14.2.1). De **tekst** is in fase 6
# gewijzigd omdat hij loog: hij beweerde dat het geluid niet meer bestond, terwijl
# de code alleen weet dat het starten mislukte. Zie `tekst_voor`.
KIND_SOUND_GONE = "sound_gone"
KIND_SPEAKER_LOST_DURING_PLAY = "speaker_lost_during_play"
KIND_LIGHT_FAILED = "light_failed"
KIND_VOLUME_RAMP_UNAVAILABLE = "volume_ramp_unavailable"
KIND_SKIPPED_GRACE_WINDOW = "skipped_grace_window"
KIND_SKIPPED_BY_USER = "skipped_by_user"

# Welke soort een fout is en welke een mededeling. Eén tabel, zodat een nieuwe soort
# niet per ongeluk als het verkeerde soort door het leven gaat.
_SEVERITY: dict[str, str] = {
    KIND_SPEAKER_UNAVAILABLE: SEVERITY_ERROR,
    KIND_MA_UNAVAILABLE: SEVERITY_ERROR,
    KIND_SOUND_GONE: SEVERITY_ERROR,
    KIND_SPEAKER_LOST_DURING_PLAY: SEVERITY_ERROR,
    KIND_LIGHT_FAILED: SEVERITY_ERROR,
    KIND_VOLUME_RAMP_UNAVAILABLE: SEVERITY_ERROR,
    KIND_SKIPPED_GRACE_WINDOW: SEVERITY_NOTICE,
    KIND_SKIPPED_BY_USER: SEVERITY_NOTICE,
}


def severity_van(kind: str) -> str:
    """De ernst van een soort melding. Gooit bij een onbekende soort.

    Bewust geen default: een nieuwe soort die stil als mededeling doorgaat, zou een
    fout kunnen verbergen (SPEC 19.1).
    """
    if kind not in _SEVERITY:
        raise ValueError(f"onbekende meldingssoort {kind!r}")
    return _SEVERITY[kind]


def tekst_voor(kind: str, wekker: dict[str, Any], **extra: str) -> str:
    """De Nederlandse tekst uit SPEC 11.7, letterlijk.

    De tekst wordt **in de opslag** gezet en niet in de kaart samengesteld, zodat een
    melding die een herstart moet overleven niet afhangt van de versie van de kaart
    die hem leest (SPEC 14.2.1).
    """
    tijd = wekker.get("time", "??:??")
    speaker = extra.get("speaker_naam") or wekker.get("speaker", "de speaker")
    geluid = extra.get("geluid_naam") or (wekker.get("sound") or {}).get("name", "het geluid")
    lamp = extra.get("lamp_naam") or ((wekker.get("light") or {}).get("entity_id") or "de lamp")

    if kind == KIND_SPEAKER_UNAVAILABLE:
        return (
            f"De wekker van {tijd} is niet afgegaan: de speaker '{speaker}' was niet "
            "bereikbaar."
        )
    if kind == KIND_MA_UNAVAILABLE:
        return f"De wekker van {tijd} is niet afgegaan: Music Assistant was niet bereikbaar."
    if kind == KIND_SOUND_GONE:
        # De reden die MA meegaf, tussen haakjes achter de vaststelling. Ontbreekt
        # hij, dan staat er niets — geen leeg haakje en geen verzonnen oorzaak.
        reden = (extra.get("ma_reden") or "").strip()
        erbij = f' Music Assistant meldde: "{reden}".' if reden else ""
        return (
            f"De wekker van {tijd} is niet afgegaan: het geluid '{geluid}' kon niet "
            f"gestart worden.{erbij} Controleer het geluid in Music Assistant, of "
            "kies een ander."
        )
    if kind == KIND_SPEAKER_LOST_DURING_PLAY:
        return (
            f"De wekker van {tijd} is mogelijk niet hoorbaar geweest: de speaker "
            f"'{speaker}' viel weg tijdens het spelen."
        )
    if kind == KIND_LIGHT_FAILED:
        return f"De wekker is afgegaan, maar de lamp '{lamp}' kon niet aangezet worden."
    if kind == KIND_VOLUME_RAMP_UNAVAILABLE:
        return (
            "De wekker is afgegaan op het ingestelde volume; het oplopende volume was "
            "op deze speaker niet mogelijk."
        )
    if kind == KIND_SKIPPED_GRACE_WINDOW:
        return f"Je wekker van {tijd} is niet afgegaan omdat Home Assistant uit stond."
    if kind == KIND_SKIPPED_BY_USER:
        return f"De wekker van {tijd} is overgeslagen, zoals je had ingesteld."
    raise ValueError(f"onbekende meldingssoort {kind!r}")


def bouw_message(kind: str, wekker: dict[str, Any], **extra: str) -> dict[str, Any]:
    """Het `last_message`-object uit SPEC 14.2."""
    return {
        "at": dt_util.now().isoformat(),
        "kind": kind,
        "severity": severity_van(kind),
        "text": tekst_voor(kind, wekker, **extra),
    }


async def async_meld(
    hass: HomeAssistant,
    store: Any,
    registry_id: str,
    wekker: dict[str, Any],
    kind: str,
    **extra: str,
) -> dict[str, Any]:
    """Leg een melding vast en stuur hem waar hij heen moet.

    Geeft het `last_message`-object terug. Gooit nooit: een melding die niet
    weggeschreven kan worden mag de wekker niet meesleuren.
    """
    message = bouw_message(kind, wekker, **extra)

    try:
        await store.async_werk_velden_bij(registry_id, wekker["id"], {"last_message": message})
    except Exception:  # noqa: BLE001 - melden mag de wekker nooit slopen
        _LOGGER.exception("Kon de melding niet in de opslag zetten: %s", message["text"])

    if message["severity"] == SEVERITY_ERROR:
        # Alleen bij een fout (SPEC 11.7b). Eén melding per wekker, zodat een wekker
        # die drie ochtenden faalt niet drie meldingen achterlaat.
        persistent_notification.async_create(
            hass,
            message["text"],
            title="DomotiApp Alarm",
            notification_id=f"{DOMAIN}_{wekker['id']}",
        )
        _LOGGER.error("%s", message["text"])
    else:
        # Een overgeslagen wekker wegens het respijtvenster is INFO: de klant kon er
        # niets aan doen. Een door de klant zelf ingesteld overslaan is DEBUG, want
        # dat is precies wat hij vroeg (SPEC 19.5).
        if kind == KIND_SKIPPED_GRACE_WINDOW:
            _LOGGER.info("%s", message["text"])
        else:
            _LOGGER.debug("%s", message["text"])

    return message


@callback
def async_wis_notificatie(hass: HomeAssistant, alarm_id: str) -> None:
    """Haal de `persistent_notification` van deze wekker weg.

    Gebeurt zodra de wekker weer normaal afgaat: de melding van gisteren hoort dan
    niet te blijven staan.
    """
    persistent_notification.async_dismiss(hass, f"{DOMAIN}_{alarm_id}")


# --- repair issues voor de beheerder (SPEC 19.2) ------------------------


@callback
def async_werk_reparatiemeldingen_bij(hass: HomeAssistant, store: Any) -> None:
    """Maak of ruim de repair issues op voor onleesbare opslag.

    SPEC 19.2 geval B regel 4 (een kapotte persoon) en geval C regel 3 (de hele
    opslag onbruikbaar). Fase 3a bouwde dit niet; het staat hier omdat het dezelfde
    machinerie gebruikt als de `persistent_notification` hierboven.

    Deze functie is **idempotent** en wordt bij elke setup aangeroepen: issues die er
    niet meer horen te zijn worden opgeruimd, zodat een gerepareerde opslag geen
    melding achterlaat.
    """
    # Geval C — de hele opslag.
    if store.onbruikbaar is not None:
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_STORE_UNUSABLE,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key="opslag_onbruikbaar",
            translation_placeholders={
                "opslagsleutel": STORAGE_KEY,
                "reden": store.onbruikbaar,
            },
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_STORE_UNUSABLE)

    # Geval B — per persoon. De naam van de persoon erin, zodat een admin het ziet
    # zonder in logs te kijken.
    corrupt = store.corrupte_personen()
    for registry_id, reden in corrupt.items():
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"{ISSUE_CORRUPT_PERSON_PREFIX}{registry_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="corrupte_opslag",
            translation_placeholders={
                "persoon": _persoon_naam(hass, registry_id),
                "reden": reden,
            },
        )

    # Ruim issues op van personen die niet meer kapot zijn.
    for issue in list(ir.async_get(hass).issues.values()):
        if issue.domain != DOMAIN:
            continue
        if not issue.issue_id.startswith(ISSUE_CORRUPT_PERSON_PREFIX):
            continue
        registry_id = issue.issue_id[len(ISSUE_CORRUPT_PERSON_PREFIX) :]
        if registry_id not in corrupt:
            ir.async_delete_issue(hass, DOMAIN, issue.issue_id)


def _persoon_naam(hass: HomeAssistant, registry_id: str) -> str:
    """De weergavenaam van een person bij zijn registry-entry-ID.

    Valt terug op het ID zelf: dat is geen stille default maar het enige wat er is
    als de entiteit inmiddels verwijderd is — en dan is het ID juist de informatie
    die een admin nodig heeft om de regel in `.storage` terug te vinden.
    """
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    for item in registry.entities.values():
        if item.id == registry_id:
            state = hass.states.get(item.entity_id)
            if state is not None:
                naam = state.attributes.get("friendly_name")
                if naam:
                    return str(naam)
            return item.name or item.original_name or item.entity_id
    return registry_id
