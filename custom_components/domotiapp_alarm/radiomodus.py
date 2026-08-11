"""Wel of geen `radio_mode` meesturen (SPEC 8.3.1). Puur.

Geen HA-imports. De beslissing hangt alleen af van de opgeslagen `uri` en een
constante lijst, en dat is precies de reden dat SPEC 8.3.1 deze route koos: de
alternatieve route leest `entry.runtime_data.mass` — de binnenkant van de
`music_assistant`-integratie — en die breekt bij een update **stil**.

## Waarom dit een aparte beslissing is en geen `if` in het afvuurpad

`radio_mode` is het enige veld in dit product waar **twijfel de andere kant op
valt** dan bij de noodrem:

| | Bij twijfel meesturen | Bij twijfel weglaten |
|---|---|---|
| provider kan het wél | eindeloos doorspelen | geluid stopt na het item — hinderlijk |
| provider kan het **niet** | **HTTP 500, geen geluid** | geluid stopt na het item — hinderlijk |

De rechterkolom heeft geen enkel geval waarin er niets klinkt. Bij de URI-controle
(SPEC 11.2.1) is het omgekeerd, en die twee staan in code op elkaar te lijken —
daarom staan ze in verschillende modules.

## De prijs, expliciet

`SIMILAR_TRACKS_PROVIDERS` is afgeleid uit MA's broncode en kan **stil** verouderen.
Verdwijnt een provider die de feature nog heeft, dan stopt het geluid na het item:
hinderlijk, niet stil. Blijft een provider erin staan die de feature verliest, dan
geeft MA HTTP 500 en gaat de wekker **niet** af — en dat is de reden dat
`afvuren.py` die 500 opvangt en het **opnieuw probeert zonder** `radio_mode`, in
plaats van op deze lijst te vertrouwen. De lijst is een optimalisatie; de terugval
is de garantie.
"""

from __future__ import annotations

from .const import ONEINDIGE_SOORTEN, SIMILAR_TRACKS_PROVIDERS

# Het scheidingsteken tussen provider en pad in een MA-URI: `somafm://radio/…`.
_SCHEMA_SCHEIDING = "://"

# MA hangt achter het domein een instantie-ID met twee streepjes ertussen zodra
# dezelfde provider meer dan één keer gekoppeld is: `spotify--ZvzrFmgX`. Het domein
# is het deel ervóór.
_INSTANTIE_SCHEIDING = "--"


def provider_van(uri: str | None) -> str | None:
    """Het providerdomein uit een MA-URI, of `None` als dat er niet uit te halen is.

    `somafm://radio/beatblender`  -> `somafm`
    `spotify--ZvzrFmgX://track/1` -> `spotify`

    `None` betekent **onbekend** en niet "geen". De aanroeper hoort daar hetzelfde mee
    te doen als met een mislukte controle: geen `radio_mode`.
    """
    if not isinstance(uri, str):
        return None
    kop, scheiding, _ = uri.partition(_SCHEMA_SCHEIDING)
    if not scheiding or not kop:
        return None
    domein, _, _ = kop.partition(_INSTANTIE_SCHEIDING)
    return domein.lower() or None


def blijft_doorspelen(uri: str | None, media_type: str | None) -> bool:
    """Blijft dit geluid eindeloos doorspelen (SPEC 8.3.1 en 15.6)?

    Dit is het veld dat `sound/search` per treffer teruggeeft. Het bestaat omdat de
    **kaart** de vraag niet kan beantwoorden: de providerlijst staat hier, en hem
    ook in de kaart zetten zou de tweede implementatie opleveren die dit product
    overal vermijdt. De kaart interpreteert niets — hij toont de waarschuwing uit
    SPEC 8.3 wanneer dit `False` is, en anders niet.

    Twee onafhankelijke redenen om `True` te zijn, en ze staan bewust in deze
    volgorde:

    1. **De soort houdt uit zichzelf niet op.** Radio en een afspeellijst hebben een
       onbepaalde duur (SPEC 8.3), en dat geldt ongeacht de provider. Een
       radiostation van een provider zonder `SIMILAR_TRACKS` speelt net zo goed door.
    2. **`radio_mode` gaat mee.** Dan speelt Music Assistant na het gekozen item
       eindeloos door in dezelfde stijl, en is ook een los nummer een bruikbare
       wekker.

    Dezelfde bron als `stuur_radio_mode_mee`, en dat is geen toeval: zou hier een
    tweede lijst staan, dan kan de editor "dit speelt door" beloven terwijl het
    afvuren `radio_mode` weglaat. Fase 3a-bis legde vast dat die lijst **stil** kan
    verouderen; één lijst betekent dat hij ook maar op één plek fout kan staan.
    """
    if isinstance(media_type, str) and media_type.strip().lower() in ONEINDIGE_SOORTEN:
        return True
    return stuur_radio_mode_mee(uri)


def stuur_radio_mode_mee(uri: str | None) -> bool:
    """Ondersteunt de provider van deze URI `SIMILAR_TRACKS`? (SPEC 8.3.1)

    `False` bij elke vorm van twijfel — een onbekend schema, een lege URI, een
    provider die niet in de lijst staat. SPEC 8.3.1: *"Faalt de controle zelf, dan
    géén `radio_mode`."* Het veld wordt dan **weggelaten** en niet op `False` gezet,
    zodat Music Assistant zijn eigen standaard houdt; dat verschil zit in
    `afvuren.py`, waar de aanroep wordt samengesteld.
    """
    provider = provider_van(uri)
    if provider is None:
        return False
    return provider in SIMILAR_TRACKS_PROVIDERS
