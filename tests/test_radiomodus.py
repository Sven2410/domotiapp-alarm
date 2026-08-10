"""De voorwaardelijke `radio_mode` (SPEC 8.3.1). Alles NIEUW GEDRAG.

Puur, dus zonder `hass`. Dat is geen toeval: SPEC 8.3.1 koos deze route juist omdat
de beslissing alleen van de opgeslagen `uri` en een constante afhangt, en niet van
`entry.runtime_data.mass` — de binnenkant van een andere integratie, die bij een
update **stil** breekt.
"""

from __future__ import annotations

import pytest

from custom_components.domotiapp_alarm import radiomodus
from custom_components.domotiapp_alarm.const import SIMILAR_TRACKS_PROVIDERS


@pytest.mark.parametrize(
    ("uri", "provider"),
    [
        ("somafm://radio/beatblender", "somafm"),
        ("spotify://track/4uLU6hMCjMI75M1A2tKUQC", "spotify"),
        # Twee streepjes: MA hangt een instantie-ID achter het domein zodra dezelfde
        # provider meer dan één keer gekoppeld is. Het domein is het deel ervóór.
        ("spotify--ZvzrFmgX://track/1", "spotify"),
        ("SPOTIFY://track/1", "spotify"),
        ("library://playlist/12", "library"),
        # Geen schema, dus geen provider. `None` betekent ONBEKEND, niet "geen".
        ("beatblender", None),
        ("://leeg", None),
        ("", None),
        (None, None),
        (42, None),
    ],
)
def test_provider_uit_de_uri(uri, provider) -> None:
    """NIEUW GEDRAG. Het deel vóór de `://`, en vóór een eventueel `--`."""
    assert radiomodus.provider_van(uri) == provider


def test_radio_mode_gaat_mee_bij_een_ondersteunende_provider() -> None:
    """NIEUW GEDRAG. Verplicht geval 8, eerste helft.

    Spotify ondersteunt `SIMILAR_TRACKS`, dus een los nummer is dán wél een bruikbare
    wekker: MA speelt eindeloos door in dezelfde stijl.
    """
    assert radiomodus.stuur_radio_mode_mee("spotify://track/1") is True
    assert radiomodus.stuur_radio_mode_mee("spotify--ZvzrFmgX://track/1") is True


def test_radio_mode_blijft_weg_bij_een_gratis_radioprovider() -> None:
    """NIEUW GEDRAG. Verplicht geval 8, tweede helft.

    Geen van de gratis radio- en podcastproviders heeft de feature. Blind meesturen
    zou hier HTTP 500 geven en dan speelt er **niets** — gemeten in fase 3a:
    `zonder radio_mode: HTTP 200, queue items=1` tegen
    `met radio_mode: HTTP 500, queue items=0`.
    """
    assert radiomodus.stuur_radio_mode_mee("somafm://radio/beatblender") is False
    assert radiomodus.stuur_radio_mode_mee("radiobrowser://radio/abc") is False


@pytest.mark.parametrize("uri", [None, "", "geen-schema", "://leeg", 42])
def test_bij_twijfel_geen_radio_mode(uri) -> None:
    """NIEUW GEDRAG. SPEC 8.3.1: "Faalt de controle zelf, dan géén `radio_mode`."

    Dit is de **omgekeerde** keuze van de URI-controle (SPEC 11.2.1), waar een
    mislukte controle de wekker juist laat doorgaan. Geen inconsistentie: hier kost
    twijfel een wekker die *zeker* niets speelt, daar een wekker die *misschien* niets
    speelt.
    """
    assert radiomodus.stuur_radio_mode_mee(uri) is False


def test_de_providerlijst_is_kleingeschreven_en_zonder_instantie_ids() -> None:
    """NIEUW GEDRAG, en een wacht op de constante zelf.

    De lijst wordt met de hand nagelopen bij elke MA-release (openstaand punt in
    CLAUDE.md). Deze test vangt de twee manieren waarop iemand hem dan stukmaakt:
    een hoofdletter erin zetten, of per ongeluk een instantie-ID meenemen uit een
    echte URI die hij aan het debuggen was.
    """
    for provider in SIMILAR_TRACKS_PROVIDERS:
        assert provider == provider.lower(), provider
        assert "--" not in provider, provider
        assert "://" not in provider, provider
