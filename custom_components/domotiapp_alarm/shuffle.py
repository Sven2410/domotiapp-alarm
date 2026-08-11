"""Wel of niet shuffelen (SPEC 9.6). Puur.

## Waarom dit bestaat

Een wekker met een afspeellijst begon elke ochtend met hetzelfde nummer. Voor een
wekker verliest dat zijn werking: het geluid dat je moet wekken wordt het geluid
dat je niet meer hoort. Gevonden in productie op 1.0.0.

**Shuffle staat altijd aan bij media met meerdere nummers.** Geen instelling, geen
veld in de opslag — het is gedrag, net als de volume-oploop.

## Wanneer het iets doet, en wanneer niet

`ONEINDIGE_SOORTEN` uit `const.py` gaat over *duur*; deze lijst gaat over
*aantal*. Dat zijn twee verschillende vragen over dezelfde `media_type` en ze
overlappen maar deels:

| soort | meerdere nummers | shuffle |
|---|---|---|
| `playlist`, `album`, `artist` | ja | **aan** |
| `radio` | nee — één doorlopende stream | uit |
| `track`, `podcast`, `audiobook` | nee — één item | uit |

Bij radio is het begrip er niet: er is één stream en geen volgorde om te
schudden.

## Waarom vóór het afspelen en niet erna

**GEMETEN in de broncode van Music Assistant 2.9.11**
(`controllers/player_queues.py:1533`):

```python
shuffle = queue.shuffle_enabled and len(queue_items) > 1 and not radio_mode
```

MA past shuffle toe **op het moment dat de queue geladen wordt**, op basis van
`shuffle_enabled` zoals dat dán staat. Zet je shuffle ná `play_media`, dan is het
eerste nummer al gekozen en schud je alleen de rest — precies de klacht uit
productie. Daarom staat `media_player.shuffle_set` in SPEC 9.1 vóór het starten
van het geluid.

Twee dingen die MA daar zelf al goed doet, en die dus niet hier hoeven:

- **`len(queue_items) > 1`** — een enkel item wordt nooit geschud. Onze lijst
  hierboven is daarmee een verfijning en geen noodzaak; hij bestaat zodat we niet
  onnodig een service aanroepen en zodat de bedoeling leesbaar is.
- **`not radio_mode`** — een radio-queue laat MA met opzet ongeschud, want die is
  al in een patroon gezet dat hij wil behouden (SPEC 8.3.1).
"""

from __future__ import annotations

from .const import MEERSTUKS_SOORTEN


def moet_shuffelen(media_type: str | None) -> bool:
    """Heeft dit geluid meerdere nummers, en moet er dus geschud worden?

    Bij twijfel — een onbekende of ontbrekende soort — **niet** shuffelen. Dat is
    hier de goedkope kant: een niet-geschudde afspeellijst is hinderlijk, maar een
    shuffle-aanroep op iets waarvan we de vorm niet kennen levert niets op en kan
    in het ergste geval een aanroep kosten die faalt vlak vóór het geluid.
    """
    if not isinstance(media_type, str):
        return False
    return media_type.strip().lower() in MEERSTUKS_SOORTEN
