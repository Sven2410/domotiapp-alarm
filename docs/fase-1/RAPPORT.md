# Fase 1 — Rooktest: de integratie serveert en registreert haar eigen kaart

Doel: een lege integratie die haar eigen kaart-JS serveert en registreert via
**beide** laadroutes, met een werkende buildketen en CI. De kaart rendert één
tekstregel.

Dit was DomotiApp Scene fase 1, 9 en een deel van 6 in één ronde. Dat kon omdat
daar al is uitgezocht wat werkt; de vindplaatsen staan in `CLAUDE.md`.

**Gemeten op:** Home Assistant **2026.8.1** (image `:2026.8`), Node **24.18.1**,
lit **3.3.1**, esbuild **0.25.10**. Bundel **16.713 bytes**,
sha256 `94ab01436dc82e922db27c13430e7a996be053d65c8ad15f2951b78209658784`,
`?v=`-hash **`94ab01436dc8`**.

---

## Samenvatting

Alles wat gevraagd was, is gebouwd en geverifieerd. Twee dingen zijn de moeite
van het uitlichten waard.

**1. Een gat in mijn eigen tests, gevonden met een mutatietest.** De opdracht
vroeg om NIEUW GEDRAG "mechanisch te onderbouwen waar dat kan". In plaats van
dat op te schrijven heb ik vier mutaties in de implementatie doorgevoerd en
gekeken of de tests echt falen. Drie werden gevangen, **één niet**: het weghalen
van `await collectie.async_get_info()` — precies de valkuil waar `resource.py`
zelf voor waarschuwt. Oorzaak: mijn testopzet laadde de resourcecollectie zélf,
waardoor de valkuil verdween. Gedicht met een test die rechtstreeks in de opslag
schrijft vóórdat de collectie is aangeraakt. Zie
[Taak F](#taak-f--tests-en-de-mutatietest).

**2. De fase-7-bevinding van DomotiApp Scene deed zich op de verse instance
spontaan voor.** Ik hoefde de service-workercache niet te vervuilen: die was het
al. De browser had tijdens de onboarding een `index.html` van **6006 bytes**
gecached, van vóórdat de integratie bestond. De live index is **6072 bytes** —
**exact 66 bytes verschil**, hetzelfde getal dat in `CLAUDE.md` valkuil 3 staat.
Binnenkomen via de wortel-URL leverde dus een document zónder onze import, en de
kaart rendert tóch, dankzij de Lovelace-resource. Dat is het sterkste bewijs dat
deze ronde kon opleveren voor de tweede laadroute, en het is geen kunstmatige
opstelling. Zie [Taak H](#taak-h--verificatie-op-een-verse-instance).

---

## Taak A — Buildopzet

| Wat | Keuze |
|---|---|
| Frontend-bibliotheek | lit **3.3.1**, meegebundeld |
| Bundelaar | esbuild **0.25.10** |
| Bron | `src/domotiapp-alarm-card.js`, `src/const.js`, `src/registreer.js` |
| Uitvoer | `custom_components/domotiapp_alarm/frontend/domotiapp-alarm-card.js` |
| Versies gepind | `package-lock.json`, en CI gebruikt `npm ci` |

De bundel is **zelfstandig**: `format: "esm"`, `bundle: true`, geen externals,
dus geen imports naar buiten. En **reproduceerbaar**: geen tijdstempel, geen
contenthash in de bestandsnaam, `legalComments: "none"`, `minify: true`.

**Eén bron voor het versienummer.** `scripts/build.mjs` leest `version` uit
`manifest.json` en injecteert die via `define: { __CARD_VERSION__ }`.
`package.json` heeft bewust geen `version`, met een `description` die dat uitlegt.

```
Gebouwd: custom_components/domotiapp_alarm/frontend/domotiapp-alarm-card.js
  versie 0.1.0
  16713 bytes
  sha256 94ab01436dc82e922db27c13430e7a996be053d65c8ad15f2951b78209658784
```

Eén codepad voor beide modi: `--check` bouwt in geheugen en vergelijkt
byte-voor-byte, dus de vergelijking kan niet afwijken van de build.

```
OK: bundel is actueel (versie 0.1.0, 16713 bytes, sha256 94ab0143...).
OK: alleen src/registreer.js registreert, en de bundel wacht op "home-assistant".
```

**De bundel wordt meegecommit** — HACS levert wat er in de repo staat.

`.gitattributes` met `* text=auto eol=lf` staat er nu in. Dat was valkuil 17 en
is daarmee afgehandeld: bij de eerste commit van fase 0 gaf git nog "LF will be
replaced by CRLF" op vier bestanden; nu normaliseert git naar LF, zodat de
bytevergelijking op Windows niet faalt zonder dat er iets mis is.

---

## Taak B — CI

Vier jobs in `.github/workflows/ci.yml`:

| Job | Wat hij vangt |
|---|---|
| **Bundel komt overeen met de bron** (`npm run verify`) | een gecommitte bundel die niet uit de huidige bron komt — inclusief een versieverhoging zonder rebuild, want de versie zit in de bytes |
| **Registratieregel** (`npm run check:registratie`) | de registry-race: alleen `registreer.js` mag `customElements.define` aanroepen, en de marker moet in de gebouwde bundel staan |
| **Manifest volgens Home Assistant** (hassfest) | ongeldige `iot_class`, kapotte vertaling, kapotte config flow |
| **JS-tests** en **Python-tests** | de rest |

Twee details die makkelijk wegvallen en dan uren kosten, beide overgenomen:
`npm ci` in plaats van `npm install` (anders kan de esbuild-versie afwijken en
faalt de bytevergelijking), en hassfest **op een schone uitcheck** in plaats van
op de werkmap (valkuil 15).

De bundeljob heeft een `if: failure()`-stap die `npm run build` draait en de diff
toont, zodat een mislukking meteen leesbaar is.

**Niet in CI gedraaid.** De workflow is nog nooit uitgevoerd — er is niets
gepusht vóór deze PR. Dat de jobs slagen is dus **niet aangetoond**; wat wel
aangetoond is, is dat de vier commando's die ze draaien lokaal slagen, en dat de
Python-tests in een Linux-container slagen op dezelfde HA-versie. De eerste
CI-run gebeurt op deze PR.

---

## Taak C — De integratie

`custom_components/domotiapp_alarm/`, negen bestanden:

| Bestand | Wat |
|---|---|
| `manifest.json` | domein `domotiapp_alarm`, `dependencies: ["http","frontend","lovelace"]`, `config_flow: true`, `integration_type: service`, `iot_class: calculated`, `version: 0.1.0` |
| `const.py` | URL-pad, hashlengte, `hass.data`-sleutels, `RESOURCE_TYPE = "module"` |
| `__init__.py` | statisch pad, `add_extra_js_url` met de bundelhash, en de resource |
| `resource.py` | de tweede laadroute |
| `config_flow.py` | lege flow, één bevestigingsstap zonder velden |
| `strings.json`, `translations/nl.json`, `translations/en.json` | Nederlands, met en.json als fallback |
| `frontend/domotiapp-alarm-card.js` | de gebundelde kaart |

**De `?v=` is de hash van het bundelbestand, niet het versienummer.** SHA-256 van
de bytes, afgekapt op 12 tekens, berekend in een executor omdat bestand lezen
blokkerende I/O is. Alleen zo verandert de URL precies wanneer de inhoud
verandert.

**`resource.py`** is overgenomen uit
`C:\dev\domotiapp-scene\custom_components\domotiapp_scene\resource.py` en houdt
alle eisen aan:

- precies **één** resource, met **exact dezelfde URL** als `add_extra_js_url` —
  bewust dezelfde `js_url`-variabele en geen tweede opgebouwde string;
- een afwijkende hash wordt **bijgewerkt** (`async_update_item`), niet
  gedupliceerd;
- resources van anderen blijven staan; bij meer dan één van ons wordt de eerste
  bijgewerkt en de rest gelogd maar niet weggegooid;
- verwijderen gebeurt in **`async_remove_entry`** en niet in
  `async_unload_entry`, want unload draait óók bij elke reload;
- het **gooit nooit**: alles in een `try/except Exception` met
  `_LOGGER.exception`, en YAML-resourcemodus levert een INFO-regel op en verder
  niets.

De `await collectie.async_get_info()` staat er met commentaar bij waarom, omdat
het het soort regel is dat er stilletjes weer uit sluipt — en de mutatietest
hieronder laat zien dat dat gevaar echt is.

---

## Taak D — `src/registreer.js`

Overgenomen uit DomotiApp Scene, ongewijzigd op het commentaar na. De module
heeft **nul imports**, dus hij is in een gewone Node-test te toetsen met
nagebootste registry's — geen DOM, geen jsdom.

Wat hem herbruikbaar maakt: hij wacht op het bestaan van `home-assistant` als
**signaal** in plaats van op een timeout, leest `customElements` bij **elke**
poging opnieuw (zodat hij het vervangen van het registry-object overleeft), heeft
een harde bovengrens van 10 s waarna hij alsnog registreert, en overleeft een
dubbele evaluatie zonder fout — wat hier meteen nodig is, want de bundel komt
langs twee routes binnen.

`scripts/check-registratie.mjs` bewaakt twee dingen: dat alléén `registreer.js`
in `src/` `customElements.define` aanroept, en dat de markernaam nog in de
**gebouwde** bundel staat, zodat een weggeoptimaliseerde wachtlus opvalt.

---

## Taak E — De kaart

Eén lit-element `domotiapp-alarm-card` met één `ha-card` en één tekstregel:
**"DomotiApp Alarm — rooktest (v0.1.0)"**. Kleuren via HA-themavariabelen
(`--primary-text-color`, `--secondary-text-color`), nooit hardcoded.

- `setConfig` bewaart alleen de config; er valt niets in te stellen.
- `getStubConfig()` staat erin, zodat de kaart via de kaartkiezer toe te voegen
  is.
- `getGridOptions()` geeft **`rows: "auto"`**, geen getal — valkuil 12. Een getal
  geeft de kaart in het sections-grid een vaste hoogte en dan loopt hij over zijn
  vak heen zodra hij hoger wordt. Een wekkerkaart gaat van hoogte veranderen, dus
  dit is hier geen theorie.
- `window.customCards` wordt meteen gevuld, buiten de wachtlus om, zodat de kaart
  in de kiezer staat ook als het registreren nog even duurt.

Geen editor, geen `getConfigElement`.

---

## Taak F — Tests, en de mutatietest

**8 JS-tests** op `registreer.js` en **10 Python-tests** op de laadketen. Alle
groen:

```
ℹ tests 8    ℹ pass 8    ℹ fail 0
..........                        [100%]   10 passed in 1.83s
```

Alle tests zijn **NIEUW GEDRAG** — de integratie bestond niet, dus elke test
faalt op de code van ervoor met een importfout. Dat is een triviale mislukking
en bewijst niets, dus in plaats van dat label te plakken heb ik het **mechanisch
onderbouwd**: vier mutaties in de implementatie, met de vraag of de tests echt
falen.

| Mutatie | Wat het nabootst | Gevangen door |
|---|---|---|
| 1. `?v={integration.version}` in plaats van de bundelhash | de fout die een klant een verouderde bundel uit zijn cache laat halen | **4 tests** |
| 2. `resource.py` krijgt een zelf opgebouwde URL (`hash[:6]`) | de twee routes lopen uit elkaar | **2 tests** |
| 3. `await collectie.async_get_info()` weggehaald | de valkuil uit `resource.py`: een tweede resource naast de bestaande | **niemand — gat** |
| 4. `async_verwijder_resource` óók in `async_unload_entry` | de resource verdwijnt bij elke reload | **1 test** |

Mutatie 1, uitvoer:

```
FAILED tests/test_init.py::test_index_import_heeft_bundelhash
FAILED tests/test_init.py::test_beide_routes_dezelfde_url
FAILED tests/test_init.py::test_resource_wordt_bijgewerkt_bij_hashwissel
FAILED tests/test_init.py::test_setup_gaat_niet_stuk_zonder_lovelace_opslag
4 failed, 5 passed
```

**Mutatie 3 kwam er ongehinderd door: `9 passed`.** Dat is een echte
tekortkoming in mijn testopzet, niet in de implementatie. Oorzaak: mijn
hulpfunctie riep zelf `async_get_info()` aan vóórdat ze een resource aanmaakte,
waardoor de collectie geladen was en de valkuil verdwenen. In de andere tests
stond er niets in de opslag, dus was een lege lijst óók het juiste antwoord.

Gedicht met `test_geen_tweede_resource_bij_ongeladen_collectie`, die de echte
situatie nabootst: **rechtstreeks in `hass_storage` schrijven** vóórdat de
collectie ooit is aangeraakt — precies wat er bij een herstart van HA gebeurt.
Daarna:

```
BASELINE met nieuwe test:  10 passed
MUTATIE 3 opnieuw:         FAILED test_geen_tweede_resource_bij_ongeladen_collectie
                           1 failed, 9 passed
```

Verder heeft elke "de setup faalt niet"-test een **positieve controle vooraf**,
want zo'n test is triviaal waar in code die het betreffende ding niet doet
(valkuil uit de werkafspraken). `test_setup_gaat_niet_stuk_zonder_lovelace_opslag`
bewijst eerst dát de index-import er staat en dát de entry `LOADED` is, en pas
daarna dat de resource netjes op `None` is uitgekomen.

**Geen jsdom.** De JS-tests bootsen de registry na met een `Map`; er is geen DOM
bij betrokken.

---

## Taak G — Browserverificatie op de dev-instance (8129)

Werkwijze uit `CLAUDE.md` gevolgd: `docker restart ha-alarm`, wachten tot HA
antwoordt, service worker afmelden en caches wissen, verse code bewijzen, en pas
daarna meten.

**Opruimen:**

```
serviceWorkersVoor: 1  ->  serviceWorkersNa: 0
cachesVoor: ["workbox-runtime-...", "workbox-precache-v2-...", "file-cache", "brands"]
cachesNa:   []
```

**Bewijs dat er verse code gemeten wordt** — niet alleen de service worker
gewist, maar de bundel opgehaald met `cache: 'reload'` en in de browser gehasht:

| | Waarde |
|---|---|
| bundel in de browser | **16.713 bytes** |
| sha256 in de browser == sha256 op schijf | **true** |
| hash in de index | `94ab01436dc8` |
| hash op schijf | `94ab01436dc8` |

### 1. De import in `index.html` met de `?v=`-hash

```
indexBytes: 6072
aantalImportRegelsVoorOnzeKaart: 1
indexBevatVerwachteImport: true
hashInIndex: "94ab01436dc8"   hashOpSchijf: "94ab01436dc8"   hashesGelijk: true
```

Precies **één** importregel, met de hash van het bestand.

### 2. De Lovelace-resource, door de integratie zelf aangemaakt

```
aantalResourcesTotaal: 1
onzeResources: [{ pad: "/domotiapp_alarm/domotiapp-alarm-card.js",
                  hash: "94ab01436dc8", type: "module", heeftId: true }]
andereResources: []
```

Dezelfde hash als de index-import. De eigenaar heeft niets toegevoegd.

### 3. `customElements.get('domotiapp-alarm-card')` geeft een class

```
customElementsGet: "function"        isFunctie: true
erftVanHTMLElement: true             heeftSetConfig: true
heeftGetStubConfig: true             heetZoals: "T"   (geminificeerd)
```

### 4. Precies één ophaling van de bundel

Gemeten op een **echt Lovelace-dashboard** (`/rook-test/0`), want daar zijn
**beide** routes actief. Op HA's ingebouwde panelen worden resources niet
geladen, dus daar zou één ophaling niets bewijzen.

```
aantalOphalingenVanDeBundel: 1
ophalingen: [{ initiatorType: "script", encodedBodySize: 16713, startMs: 13 }]
```

Eén URL, twee routes, één ophaling — de modulekaart van de browser dedupliceert.

### 5. De kaart in de kaartkiezer

Met een echte klik: hit-test op het klikpunt vooraf (er lag een `ha-svg-icon`),
en de klik zelf was echt — `isTrusted: true`, met als `composedPath`
`ha-svg-icon → button → div → ha-sortable → ShadowRoot → hui-grid-section`.

```
dialoogTag: "hui-dialog-create-card"      dialoogNaMs: 1
onzeKaartInKiezer: true                   gevondenNaMs: 3
tekst: "DomotiApp Alarm  Wekkerkaart van DomotiApp (v0.1.0)."
aantalKaartOpties: 18
```

De kaart staat onder **"Gemeenschapskaarten"**. Het in beeld brengen ging
**programmatisch** met `scrollIntoView` — het muiswiel van de browsertool
bereikt de dialoogbody niet (valkuil 11). De klik die de dialoog opende was wél
echt.

### 6. De kaart rendert op een dashboard

Sections-weergave:

```
kaartInDom: true       kaartTag: "domotiapp-alarm-card"
kaartTekst: "DomotiApp Alarm — rooktest (v0.1.0)"
haCardAanwezig: true   afmetingen: { width: 500, height: 56 }
configuratiefoutOpDePagina: false
```

Screenshots (illustratie, geen bewijs):
`screenshot-1786372097110-0.jpg` (kaart op het dashboard) en
`screenshot-1786372251848-1.jpg` (de kaartkiezer).

---

## Taak H — Verificatie op een verse instance

Verse HA op **poort 8130**, eigen compose-project
`domotiapp-alarm-installatietest`, configmap **buiten de repo** (in de
scratchpad), zodat de dev-instance op 8129 onbereikbaar is voor deze test. De
integratie erin gezet als **kopie**, zoals HACS het doet — negen bestanden, geen
`src/`, geen `tests/`, geen `node_modules`, bundelhash `94ab01436dc8`.

De eigenaar heeft de onboarding zelf gedaan.

### Uitgangstoestand — de positieve controle

```
integratieVooraf: 0        resourcesVooraf: 0
kaartInCustomCardsVooraf: false     elementVooraf: "undefined"
```

**Nul** resources. Dat "de resource verschijnt" is daarna dus niet triviaal waar.

### De integratie toevoegen, en de resource verschijnt vanzelf

```
stap1: { type: "form", step_id: "user" }        (lege flow, geen velden)
stap2: { type: "create_entry", title: "DomotiApp Alarm" }
entries: [{ title: "DomotiApp Alarm", state: "loaded", source: "user" }]

aantalResources: 1
resources: [{ pad: "/domotiapp_alarm/domotiapp-alarm-card.js",
              hash: "94ab01436dc8", type: "module" }]
```

Van 0 naar 1, met de hash van de bundel op schijf. De klant hoeft niets toe te
voegen.

### De kaart op een dashboard in sections-weergave

```
viewType: "sections"
kaartRendert: true      kaartTekst: "DomotiApp Alarm — rooktest (v0.1.0)"
haCard: true            afmeting: { w: 500, h: 56 }
aantalOphalingen: 1     configuratiefout: false
elementGeregistreerd: "function"
```

### De fase-7-reproductie — en die was niet nodig

De opdracht was: vervang de index in de service-workercache door een versie
zonder de import. **Dat hoefde niet: de cache was het al.**

Alleen gelezen met `cache.match`, nooit met `fetch('/')` — die zou door de
service worker gaan en `StaleWhileRevalidate` zou de verse index meteen
terugschrijven, waarmee de controle zijn eigen meting kapotmaakt (valkuil 4).

```
caches: ["workbox-runtime-http://localhost:8130/", "workbox-precache-v2-...",
         "file-cache", "brands"]
serviceWorkers: [{ scope: "http://localhost:8130/", actief: true, staat: "activated" }]

wortelEntries: [{ cache: "workbox-runtime-...", sleutel: "/",
                  bytes: 6006, bevatOnzeImport: false }]
```

De gecachte index is **6006 bytes en bevat onze import niet**. Server-side
opgehaald, buiten de service worker om, is de live index:

```
bytes: 6072
bevat onze import: 1 regel
domotiapp_alarm/domotiapp-alarm-card.js?v=94ab01436dc8

verschil: 6072 - 6006 = 66 bytes
```

**Exact 66 bytes**, hetzelfde getal als in `CLAUDE.md` valkuil 3. De browser had
tijdens de onboarding een index gecached van vóórdat de integratie bestond, en
hield die vast. Dit is de toestand waarin bij vrijwel elke klant elk dashboard
"Configuratiefout" toont — hier spontaan ontstaan, zonder dat ik er iets voor
hoefde te doen.

**Binnenkomen via de wortel-URL**, en dan de toestand vóór en na een
client-side navigatie (`history.pushState` + `location-changed`, dus **geen**
paginalading — het verouderde document blijft staan):

| | vóór (`/home/overview`) | ná (`/rook-test/0`) |
|---|---|---|
| import in het document | **false** | true (zie hieronder) |
| ophalingen van de bundel | **0** | **1** (16.713 bytes) |
| `customElements.get(...)` | **undefined** | **function** |
| kaart rendert | — | **true**, na 123 ms |
| "Configuratiefout" | — | **false** |

Het serverdocument dat de service worker aanleverde had dus **geen** import, de
bundel was **niet** opgehaald en het element was **niet** geregistreerd. Op
`/home/overview` — een ingebouwd paneel van HA, waar Lovelace-resources niet
worden geladen — bleef dat zo. Na het client-side navigeren naar het
Lovelace-dashboard **rendert de kaart alsnog**.

Dat de import na de navigatie wél in het document staat, is geen tegenspraak
maar juist het bewijs van de tweede route. Nagemeten welke tag dat is:

```
totaalAantalScripts: 6 -> 7
toegevoegde tag: { type: "module", ouder: "body",
                   srcPad: "/domotiapp_alarm/domotiapp-alarm-card.js",
                   srcHeeftHash: true }
```

Het oorspronkelijke document had **6** scripts, allemaal inline, geen enkele met
ons pad. De **resource-loader van Lovelace** heeft er een zevende bijgezet: een
`<script type="module">` met onze gehashte URL, aan `<body>`. Dat is de tweede
laadroute die zijn werk doet.

Screenshot: `screenshot-1786372779498-2.jpg` (de kaart op de verse instance, na
binnenkomst via de wortel-URL).

### Opgeruimd

```
Container ha-alarm-vers Stopped / Removing / Removed
Network domotiapp-alarm-installatietest_default Removing / Removed
poort 8130: HTTP 000  (niet meer bereikbaar)
compose-projecten over: domotiapp-alarm-dev, domotiapp-alarm-ma
```

---

## Wat niet lukte

1. **CI is nog nooit gedraaid.** De workflow bestaat, maar er is niets gepusht
   vóór deze PR, dus dat de vier jobs slagen is **niet aangetoond**. Lokaal
   slagen alle commando's die ze draaien, en de Python-tests slagen in een
   Linux-container op HA 2026.8.1. De eerste echte run is die van deze PR; blijkt
   daar iets uit, dan hoort dat in dezelfde PR gerepareerd te worden.

2. **hassfest is niet lokaal gedraaid.** Dat kan ook niet zinnig: op de werkmap
   loopt hij `.venv/` in en keurt HA's eigen integraties af (valkuil 15). Of het
   manifest, de vertalingen en de config flow zijn goedgekeurd, blijkt pas uit de
   CI-job.

3. **Eén mutatietest legde een gat in mijn eigen tests bloot.** Zie taak F. Het
   is gedicht, maar het is wel het tweede rapport op rij waarin een meting van
   mij eerst het verkeerde antwoord gaf. In fase 0b was dat naieve
   fold-rekenkunde en een dubbel geformatteerd logrecord; hier een testopzet die
   de valkuil wegnam die hij moest vangen. De les die zich opdringt: **een test
   die slaagt is pas bewijs als hij ook aantoonbaar kan falen.**

4. **De kaartkiezer is niet met het muiswiel gescrold.** `scrollIntoView` was
   programmatisch; de klik die de dialoog opende was echt en `isTrusted` is
   getoond. Dit is een beperking van de meetopstelling (valkuil 11), geen
   waargenomen gedrag van de dialoog.

5. **Geen `getCardSize()` op de kaart.** In masonry-weergaven gebruikt Lovelace
   die voor de kolomverdeling. De kaart is alleen in **sections**-weergave
   geverifieerd, zoals gevraagd. Masonry is niet gemeten en `getCardSize`
   ontbreekt; dat hoort erbij zodra de kaart een echte hoogte krijgt.

6. **Panelweergave (`panel: true`) is niet gemeten.** Dat staat in DomotiApp
   Scene als openstaand punt (`frontend#52570`) en is hier ook niet aangeraakt.
   Kiosk-opstellingen gebruiken vaak juist `panel: true`.

---

## Aannames

1. **De verse-instancetest is met dezelfde browser gedaan die 8129 al kende, maar
   op een andere origin.** `localhost:8130` is voor de service worker een eigen
   scope, dus de cachevervuiling die ik aantrof is die van 8130 zelf, ontstaan
   tijdens de onboarding. Dat is de situatie van een klant die HA al gebruikte
   vóór de installatie — maar het is niet *letterlijk* dezelfde: bij een klant
   ligt er meer tijd tussen. Voor de bevinding maakt dat niets uit, want het
   verschil zit in de inhoud van de gecachte index en niet in de ouderdom.

2. **`0.1.0` als beginversie** is mijn keuze, niet opgedragen. De opdracht vroeg
   een `version` in het manifest; er is nog geen release en de kaart doet nog
   niets, dus een `1.x` zou misleidend zijn.

3. **De hashlengte van 12 tekens** is overgenomen uit DomotiApp Scene zonder er
   opnieuw over te beslissen.

Geen andere aannames gedaan.

---

## `git status --porcelain`

Zie de terminaluitvoer van deze ronde; op het moment van committen leeg op de
bestanden van deze fase na.
