"""Welke speakers en lampen de kaart mag aanbieden (SPEC 7).

Alle filtering gebeurt **server-side**. De kaart filtert niet zelf: dan zou de
label-expansie in twee talen bestaan en zouden kaart en server het over
verschillende lijsten hebben.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    entity_registry as er,
    label_registry as lr,
)
from homeassistant.helpers.target import (
    TargetSelection,
    async_extract_referenced_entity_ids,
)

from .const import (
    ATTR_MASS_PLAYER_TYPE,
    LABEL_LAMP_NAAM,
    LABEL_SPEAKER_NAAM,
    MA_DOMAIN,
    MASS_PLAYER_TYPE_GROUP,
)

_LOGGER = logging.getLogger(__name__)

MEDIA_PLAYER_DOMAIN = "media_player"
LIGHT_DOMAIN = "light"


@dataclass(slots=True)
class Selectie:
    """Wat `entities/list` per soort teruggeeft (SPEC 15.7).

    **`filtered_out` is nieuw in fase 4c**, en het bestaat om precies één reden: de
    drie situaties uit SPEC 7.4 uit elkaar houden. Met alleen `label_exists` en
    `entities` zijn er drie situaties en twee signalen:

    | Situatie (SPEC 7.4) | `label_exists` | `entities` | `filtered_out` |
    |---|---|---|---|
    | het label bestaat niet | `False` | leeg | 0 |
    | het label bestaat, er hangt niets aan | `True` | leeg | **0** |
    | er hing wel iets aan, maar het viel af op 7.2 | `True` | leeg | **> 0** |

    De onderste twee zijn voor de eigenaar heel verschillende meldingen — *"zet het
    label op je speakers"* tegenover *"die speakers zijn geen Music
    Assistant-speakers"* — en zonder deze teller kiest de kaart er één en heeft hij
    het in de helft van de gevallen mis.

    Het is bewust een **getal** en geen lijst met redenen: de melding uit SPEC 7.4
    is één zin die alle afvalredenen samenvat, en de redenen zelf staan al per
    entiteit op `DEBUG` in het log. Een lijst zou de kaart uitnodigen er zelf
    zinnen van te maken.
    """

    label_exists: bool
    entities: list[dict[str, str]] = field(default_factory=list)
    filtered_out: int = 0

    def as_dict(self) -> dict:
        return {
            "label_exists": self.label_exists,
            "entities": self.entities,
            "filtered_out": self.filtered_out,
        }


def _label_id(hass: HomeAssistant, naam: str) -> str | None:
    """Het `label_id` bij een labelnaam, of `None` als het label niet bestaat.

    We werken met het `label_id` en niet met de naam: hernoemen laat het
    `label_id` ongemoeid (`helpers/label_registry.py:182-213`, gemeten in fase 0).
    """
    label = lr.async_get(hass).async_get_label_by_name(naam)
    return label.label_id if label else None


def _entiteiten_met_label(hass: HomeAssistant, label_id: str) -> set[str]:
    """Alle entiteiten die dit label bereikt: via entiteit, apparaat of gebied.

    Rechtstreeks `entity_entry.labels` lezen vindt alleen het eerste geval. De
    helper uit `helpers/target.py` rolt alle drie uit (gemeten in fase 0, E4.2).

    `TargetSelection` en niet `TargetSelectorData`: dat laatste verdwijnt in HA
    2026.12.

    `primary_entities_only=True` is de standaard en blijft staan: een gelabeld
    apparaat levert zijn lamp op en niet zijn signaalsterktesensor.
    """
    selectie = async_extract_referenced_entity_ids(
        hass, TargetSelection({"label_id": label_id})
    )
    return selectie.referenced | selectie.indirectly_referenced


def _naam(hass: HomeAssistant, entity_id: str, entry: er.RegistryEntry | None) -> str:
    """De weergavenaam, ook als de entiteit `unavailable` is.

    `friendly_name` overleeft onbeschikbaarheid (`helpers/entity.py:1166-1167`),
    anders zou een weggevallen speaker als kaal entity-ID in de lijst staan.
    """
    state = hass.states.get(entity_id)
    if state is not None:
        naam = state.attributes.get("friendly_name")
        if naam:
            return str(naam)
    if entry is not None:
        return entry.name or entry.original_name or entity_id
    return entity_id


def is_ma_speaker(hass: HomeAssistant, entity_id: str) -> tuple[bool, str | None]:
    """Voldoet deze entiteit aan de eisen voor een wekkerspeaker (SPEC 7.2)?

    Geeft `(True, None)` of `(False, reden)`. De reden is bedoeld voor het log en
    voor de foutmelding van `alarms/save`.

    De zes eisen, in de volgorde waarin ze het goedkoopst te controleren zijn.
    Eis 1 (het label) zit niet hier maar in `speakers()`: deze functie is ook de
    controle die `alarms/save` doet op een speaker die de kaart aanlevert.
    """
    if not entity_id.startswith(f"{MEDIA_PLAYER_DOMAIN}."):
        return False, f"{entity_id} zit niet in het {MEDIA_PLAYER_DOMAIN}-domein"

    entry = er.async_get(hass).async_get(entity_id)
    if entry is None:
        return False, f"{entity_id} heeft geen entity registry entry"

    # De platformcheck is het vangnet onder het label: bij een Sonos maken zowel
    # de Sonos-integratie als Music Assistant een entiteit aan voor dezelfde
    # fysieke speaker. Zonder deze check zou de wekker de Sonos-entiteit kunnen
    # kiezen, waarop music_assistant.play_media niet werkt (SPEC 7.2).
    if entry.platform != MA_DOMAIN:
        return False, f"{entity_id} komt van {entry.platform!r} en niet van {MA_DOMAIN!r}"

    state = hass.states.get(entity_id)
    if state is None:
        return False, f"{entity_id} heeft geen state"

    # supported_features overleeft `unavailable` (helpers/entity.py:1169-1170);
    # mass_player_type niet. Daarom staat de featurecheck vóór de groepcheck.
    kenmerken = state.attributes.get("supported_features") or 0
    try:
        kenmerken = MediaPlayerEntityFeature(int(kenmerken))
    except ValueError:
        return False, f"{entity_id} heeft onleesbare supported_features"

    if MediaPlayerEntityFeature.PLAY_MEDIA not in kenmerken:
        return False, f"{entity_id} kan geen media afspelen"
    if MediaPlayerEntityFeature.VOLUME_SET not in kenmerken:
        # Zonder VOLUME_SET is de volume-oploop niet uitvoerbaar en is de wekker
        # een belofte die niet nagekomen wordt (SPEC 7.2, eis 5).
        return False, f"{entity_id} kan het volume niet instellen"

    # Groepen worden uitgesloten: groepsvolume is relatief en levert een
    # onvoorspelbaar eindvolume (SPEC 7.3, gemeten in fase 0b).
    #
    # Dit attribuut verdwijnt zodra de entiteit `unavailable` is. Dat is hier
    # aanvaardbaar: het betekent dat een weggevallen speaker niet als groep te
    # herkennen is, en dan geldt hij als niet-groep. De alternatieve keuze —
    # weigeren bij twijfel — zou een onbereikbare speaker onbewerkbaar maken,
    # en dat is erger.
    if state.attributes.get(ATTR_MASS_PLAYER_TYPE) == MASS_PLAYER_TYPE_GROUP:
        return False, f"{entity_id} is een groep"

    return True, None


def speakers(hass: HomeAssistant) -> Selectie:
    """De gelabelde Music Assistant-speakers (SPEC 7.2)."""
    label_id = _label_id(hass, LABEL_SPEAKER_NAAM)
    if label_id is None:
        # Het label bestaat niet. Dat is de situatie bij een nieuwe klant en geen
        # fout (SPEC 7.4); `label_exists: false` maakt het onderscheid met "het
        # label bestaat maar is leeg".
        return Selectie(label_exists=False)

    registry = er.async_get(hass)
    gevonden: list[dict[str, str]] = []
    afgevallen = 0
    for entity_id in sorted(_entiteiten_met_label(hass, label_id)):
        geschikt, reden = is_ma_speaker(hass, entity_id)
        if not geschikt:
            # De reden blijft op DEBUG staan en gaat niet mee naar de kaart: de
            # melding van SPEC 7.4 vat ze samen in één zin, en wie de details wil
            # heeft er een logregel per entiteit voor.
            _LOGGER.debug("Speaker %s valt af: %s", entity_id, reden)
            afgevallen += 1
            continue
        gevonden.append(
            {"entity_id": entity_id, "name": _naam(hass, entity_id, registry.async_get(entity_id))}
        )
    return Selectie(label_exists=True, entities=gevonden, filtered_out=afgevallen)


def is_wekkerlamp(hass: HomeAssistant, entity_id: str) -> tuple[bool, str | None]:
    """Mag deze lamp als wake-up light gekozen worden (SPEC 12)?

    Alleen het domein en het label; er is geen eis aan `supported_color_modes`,
    want de wake-up light gebruikt uitsluitend `brightness_pct`.
    """
    if not entity_id.startswith(f"{LIGHT_DOMAIN}."):
        return False, f"{entity_id} zit niet in het {LIGHT_DOMAIN}-domein"
    label_id = _label_id(hass, LABEL_LAMP_NAAM)
    if label_id is None:
        return False, f"het label {LABEL_LAMP_NAAM!r} bestaat niet"
    if entity_id not in _entiteiten_met_label(hass, label_id):
        return False, f"{entity_id} heeft het label {LABEL_LAMP_NAAM!r} niet"
    return True, None


def lampen(hass: HomeAssistant) -> Selectie:
    """De gelabelde lampen voor de wake-up light (SPEC 7.1)."""
    label_id = _label_id(hass, LABEL_LAMP_NAAM)
    if label_id is None:
        return Selectie(label_exists=False)

    registry = er.async_get(hass)
    gevonden: list[dict[str, str]] = []
    afgevallen = 0
    for entity_id in sorted(_entiteiten_met_label(hass, label_id)):
        if not entity_id.startswith(f"{LIGHT_DOMAIN}."):
            # Voor de lamp is de enige eis het domein (SPEC 12): er is geen eis aan
            # `supported_color_modes`, want de wake-up light gebruikt alleen
            # `brightness_pct`. Toch wordt er geteld, zodat de editor ook hier de
            # twee lege gevallen uit elkaar houdt.
            _LOGGER.debug("Lamp %s valt af: zit niet in het %s-domein", entity_id, LIGHT_DOMAIN)
            afgevallen += 1
            continue
        gevonden.append(
            {"entity_id": entity_id, "name": _naam(hass, entity_id, registry.async_get(entity_id))}
        )
    return Selectie(label_exists=True, entities=gevonden, filtered_out=afgevallen)
