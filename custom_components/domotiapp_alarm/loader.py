r"""De laadroute die een verouderde `index.html` niet kan bederven (fase 11).

## Het probleem, gemeten en niet aangenomen

Home Assistant rendert een extra module als een **inline** import in de HTML:

```html
<script>import("/domotiapp_alarm/domotiapp-alarm-card.js?v=1724b468f3e9");</script>
```

De hash staat dus **in het document**. En dat document wordt door HA's service
worker gecachet. Uit `sw-modern.js` van 2026.8, de laatste route:

```js
oe(/\/.*/, new he({cacheName: "file-cache", plugins: [new W({maxAgeSeconds: 86400})]}))
```

`he` is StaleWhileRevalidate: hij geeft eerst de gecachte kopie terug en haalt
pas daarna een verse op. Gevolg na een update: het document dat de browser
krijgt is dat van de vórige versie, met de vórige hash erin, en die bundel
staat nog in de HTTP-cache (`Cache-Control: public, max-age=2678400`). De klant
draait dan de oude kaart terwijl de server de nieuwe heeft.

**Dat is in fase 11 op een verse instance gereproduceerd.** 1.0.2 geïnstalleerd,
kaart geladen, bijgewerkt naar 1.0.4, gewoon herladen — de browser draaide
1.0.2 (55.503 bytes) terwijl de server 1.0.4 (62.903 bytes) serveerde, en de
nieuwe URL werd niet één keer opgevraagd.

**Wat NIET het probleem is:** de `?v=` zelf. Valkuil 62 schreef die af als
cache-buster, en dat was te streng. De file-cache-route hierboven zet géén
`matchOptions: {ignoreSearch: true}` — alleen de wortelroute doet dat. Een
nieuwe `?v=` is dus wel degelijk een andere cachesleutel. Wat fase 7 mat was een
`cache.match(..., {ignoreSearch: true})` van onszelf, en die vlag was van de
lezer en niet van de service worker.

## De oplossing

In diezelfde service worker staat één route die **nooit** cachet:

```js
oe(/\/(api|auth)\/.*/, new ue)      // ue = NetworkOnly: alleen r.fetch(), geen cachePut
```

Alles onder `/api/` gaat gegarandeerd naar de server. Daarom staat de
importregel in `index.html` sinds fase 11 niet meer op de bundel zelf maar op
een **stabiele lader** onder `/api/`, die bij elke paginalading vers wordt
opgehaald en de dan geldende hash teruggeeft:

```js
import("/domotiapp_alarm/domotiapp-alarm-card.js?v=<hash van dit moment>");
```

Drie eigenschappen die daarbij horen, en ze zijn alle drie nodig:

1. **De URL van de lader verandert nooit.** Een verouderd document verwijst dus
   naar precies dezelfde lader, en die lader is vers.
2. **De lader wordt nooit gecachet.** `/api/` is NetworkOnly in de service
   worker, en `Cache-Control: no-store` sluit de HTTP-cache uit.
3. **De lader wijst naar dezelfde gehashte URL als de Lovelace-resource.** Beide
   routes komen dus op één modulespecifier uit; de browser haalt de bundel één
   keer op en evalueert hem één keer. Zonder dat gelijkloop zouden er twee
   modules zijn en zou de registratierace uit valkuil 1 weer kunnen ontstaan.

`requires_auth = False`, net als het statische pad waar de bundel zelf op staat:
een `<script>`-tag stuurt geen bearer-token mee, en de bundel is toch al
openbaar. Er staat geen enkel gegeven van de gebruiker in dit antwoord — alleen
een hash die uit een bestand in de installatie komt.
"""

from __future__ import annotations

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import CARD_URL_PATH, DATA_LOADER_REGISTERED, DOMAIN, LOADER_URL_PATH


class KaartLaderView(HomeAssistantView):
    """Geeft een importregel terug met de hash van dit moment."""

    url = LOADER_URL_PATH
    name = f"api:{DOMAIN}:loader"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def get(self, request: web.Request) -> web.Response:
        """De hash komt uit hass.data en niet uit het bestand.

        Bewust: het bestand lezen zou blokkerende I/O op elke paginalading zijn.
        De waarde wordt bij setup berekend en bij elke reload bijgewerkt, en dat
        is precies het moment waarop hij kan veranderen.
        """
        # Hier stond een tak voor "geen hash bekend", die een lege module
        # teruggaf. De mutatieproef ving hem niet, en narekenen wees uit dat hij
        # onbereikbaar is: `async_registreer` zet de hash in `hass.data` VOORDAT
        # het de view registreert, en niets haalt de sleutel ooit weer weg —
        # `async_unload_entry` popt DATA_JS_URL en DATA_STORE, `async_remove_entry`
        # popt DATA_RESOURCE_ID, en geen van beide raakt DATA_LOADER_REGISTERED.
        # Bestaat deze route, dan bestaat de hash. Weggehaald in plaats van er een
        # test bij te verzinnen (valkuil 34, derde rij).
        hash_nu = self._hass.data[DOMAIN][DATA_LOADER_REGISTERED]

        return web.Response(
            text=f'import("{CARD_URL_PATH}?v={hash_nu}");\n',
            content_type="text/javascript",
            headers={
                # De service worker cachet /api/ al niet; dit sluit de
                # HTTP-cache van de browser uit. Beide zijn nodig: de eerste
                # dekt een geïnstalleerde PWA, de tweede een gewone browser.
                "Cache-Control": "no-store, must-revalidate",
            },
        )


def async_registreer(hass: HomeAssistant, bundel_hash: str) -> None:
    """Zet de lader klaar en werk de hash bij.

    Idempotent. De view zelf wordt één keer geregistreerd — HA kent geen
    manier om een view te verwijderen — maar de hash wordt bij elke setup
    opnieuw gezet, want die is wat er na een update verandert.
    """
    data = hass.data.setdefault(DOMAIN, {})
    # Deze guard wordt door geen enkele test gevangen, en dat is nagerekend en
    # geen gat: aiohttp accepteert een tweede route op hetzelfde pad en laat de
    # eerste winnen, dus door de publieke API is er niets van te zien. Hij blijft
    # staan omdat een reload anders bij elke keer een route aan de tabel plakt —
    # meetbaar in geheugen, niet in gedrag (valkuil 34, vierde uitkomst).
    al_geregistreerd = DATA_LOADER_REGISTERED in data
    data[DATA_LOADER_REGISTERED] = bundel_hash
    if not al_geregistreerd:
        hass.http.register_view(KaartLaderView(hass))
