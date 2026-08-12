# Fase 11 — De cache-buster en de afronding

## De uitkomst van deel 1, meteen

**Gekozen route: een stabiele lader onder `/api/`.** Niet de hash in het pad, niet
een cache-control-header op de bundel, en niet iets in de registratie — die drie
lossen het probleem geen van drieën op, en waarom staat hieronder.

**Is het probleem daarmee weg? Ja, en dat is gemeten en niet beredeneerd.** Op een
verse instance, met de service worker in de staat waarin een klant hem heeft:

| | vóór de reparatie | ná de reparatie |
|---|---|---|
| server serveert | 1.0.4, 62.903 bytes | 1.0.4, 62.903 bytes |
| browser draait ná een **gewone** herlaadbeurt | **1.0.2, 55.503 bytes** | **1.0.4, 62.903 bytes** |
| nieuwe bundel-URL opgevraagd? | **nee, geen enkele keer** | ja |

Zonder harde herlaadbeurt, zonder cache legen, zonder de app af te sluiten.

**En de diagnose die tien fases lang in dit project stond, klopte niet.**

---

## Deel 1 — Het onderzoek

### Wat valkuil 62 zei, en wat er werkelijk aan de hand was

Valkuil 62 (fase 7) zei: *de `?v=` is geen cache-buster tegen HA's service
worker*, op grond van deze meting:

```js
cache.match('…card.js?v=<nieuw>', {ignoreSearch: true})   // gaf de oude bundel
```

Die vlag `ignoreSearch: true` was van **de lezer**, niet van de service worker.
Uit `sw-modern.js` van HA 2026.8, de volledige routetabel:

```js
oe(/\/(static|frontend_latest|frontend_es5)\/.+/, new se({matchOptions:{ignoreSearch:!0}}))
oe(/\/(api|auth)\/.*/,                            new ue)
oe(/\/(?:manifest\.json|onboarding\.html)/,       new ue)
oe(/\/(\?.*)?$/,       new he({matchOptions:{ignoreSearch:!0}}))
oe(/\/.*/,             new he({cacheName:"file-cache", plugins:[new W({maxAgeSeconds:86400})]}))
```

met, uit dezelfde bundel:

- `se` = CacheFirst (`cacheMatch` eerst, alleen bij een misser fetchen)
- `ue` = **NetworkOnly** (`r.fetch(e)` en verder niets — geen `cacheMatch`, geen `cachePut`)
- `he` = StaleWhileRevalidate (`fetchAndCachePut` op de achtergrond, de gecachte kopie terug)

**De file-cache-route zet géén `ignoreSearch`.** Een nieuwe `?v=` is daar dus wel
degelijk een andere cachesleutel, en hetzelfde geldt voor de HTTP-cache van de
browser (`Cache-Control: public, max-age=2678400`, gemeten met `curl`). De `?v=`
werkt.

**Wat er wél misging.** Home Assistant rendert een extra module als een
**inline import in het HTML-document**:

```html
<script>import("/domotiapp_alarm/domotiapp-alarm-card.js?v=1724b468f3e9");</script>
```

De hash staat dus in het document, en het document valt onder de laatste route:
StaleWhileRevalidate, 24 uur. Na een update krijgt de browser het document van de
vórige versie terug, met de vórige hash erin — en die bundel staat nog in de
HTTP-cache. **Niet de hash was het probleem, maar de plek waar de hash stond.**

### De reproductie, op een verse instance

Baseline: 1.0.2 als kopie geïnstalleerd, kaart geladen, caches leeg gemaakt en
opnieuw laten vullen. Wat er dan in de service worker staat:

```
file-cache → /home/overview  (6.072 bytes)  importeert ?v=3b34d9caede3
```

Daarna bijgewerkt naar 1.0.4 zoals HACS het doet (bestanden vervangen, HA
herstart). De server was aantoonbaar bij:

```
lovelace_resources → /domotiapp_alarm/domotiapp-alarm-card.js?v=1724b468f3e9
```

En toen een **gewone** herlaadbeurt:

```json
{"DRAAIT_BUNDEL": [{"v": "3b34d9caede3", "bytes": 55503}],
 "swCache":       [{"pad": "/home/overview", "importeert": ["1724b468f3e9"]}],
 "resourceZegt":  ["1724b468f3e9"]}
```

De browser draaide **1.0.2**. Bevestigd op de code zelf en niet alleen op de URL:
de geladen editor had geen `.vak` en geen `flex-wrap` op `.onderrij` — de
kenmerken van 1.0.4 en 1.0.3. En de nieuwe URL stond in **geen enkel**
resource-verzoek.

Merk op wat de service worker intussen deed: hij revalideerde het document op de
achtergrond, dus de cache bevatte ná deze laadbeurt de nieuwe hash. Dat is
precies waarom dit "vanzelf overgaat" als je opnieuw laadt — en waarom het
onzichtbaar blijft voor wie het niet meet.

### Waarom de drie aanknopingspunten uit de opdracht het niet oplossen

| Aanknopingspunt | Waarom niet |
|---|---|
| **hash in het PAD** | Het verouderde document verwijst dan naar `/domotiapp_alarm/<oudehash>/card.js`, en die URL staat nog 31 dagen in de HTTP-cache van de browser én 24 uur in de file-cache. De oude bundel laadt gewoon. `ignoreSearch` was nooit het probleem, dus eraan ontsnappen helpt niet |
| **cache-control op de statische route** | Die route is niet het probleem; de bundel-URL is al correct cache-busted. Het **document** is stale, en daar gaan onze headers niet over |
| **iets in de registratie** | Een custom element kan niet opnieuw gedefinieerd worden. Wint de oude module de race, dan is er geen weg terug — `registreer.js` kan dat alleen netjes negeren, niet omkeren |

### De gekozen constructie

In `index.html` staat sinds deze ronde niet de bundel-URL maar een **stabiele
lader**, `custom_components/domotiapp_alarm/loader.py`:

```
GET /api/domotiapp_alarm/loader.js
Cache-Control: no-store, must-revalidate
Content-Type: text/javascript; charset=utf-8

import("/domotiapp_alarm/domotiapp-alarm-card.js?v=1724b468f3e9");
```

Drie eigenschappen, en ze zijn alle drie dragend:

1. **Zijn URL verandert nooit**, dus een verouderd document wijst er nog steeds
   naar.
2. **Hij wordt nooit gecachet.** `/api/` is de enige route die de service worker
   met NetworkOnly afhandelt, en `no-store` sluit de HTTP-cache uit. Twee lagen,
   twee redenen: de eerste dekt een geïnstalleerde PWA, de tweede een gewone
   browser.
3. **Hij importeert dezelfde gehashte URL als de Lovelace-resource**, zodat beide
   routes op één modulespecifier uitkomen — één ophaling, één evaluatie, geen
   registratierace.

`requires_auth = False`, net als het statische pad van de bundel: een
`<script>`-tag stuurt geen bearer-token mee. Er staat geen enkel gegeven van de
gebruiker in het antwoord, alleen een hash uit een bestand in de installatie.

### Dat beide laadroutes nog werken

De reproductie uit fase 1 taak H, opnieuw gedaan:

- **Route 1 (index → lader).** Op `/home/overview`, waar Lovelace-resources niet
  geladen worden, werden precies twee dingen opgehaald: `loader.js` (67 bytes) en
  daarna de gehashte bundel. De kaart werkte.
- **Route 2 (Lovelace-resource).** Het gecachte document is **doctored** — onze
  importregel eruit geknipt, precies de situatie van een browser die HA al
  gebruikte vóór de installatie. Uitkomst: `laderGebruikt: false`, en tóch
  `kaartGedefinieerd: true` met de **nieuwe** bundel. De resource ving het op.

---

## Deel 2 — De updatetest

Verse Home Assistant op **8130**, integratie als **kopie** (geen bind mount),
zoals HACS hem levert. De eigenaar heeft de onboarding gedaan.

**1. Laadt de browser ná de update de nieuwe bundel, zonder harde herlaadbeurt?**
Ja. Zie de tabel bovenaan. De laatste meting is met de lader erin gedaan: 1.0.2's
bundel eronder gelegd, document laten cachen, 1.0.4's bundel eroverheen,
herladen — en de browser haalde `?v=1724b468f3e9` op en draaide 1.0.4.

**2. Welke bundel staat er in de service-workercache, vóór en ná?**

| | document in `file-cache` | importeert |
|---|---|---|
| vóór (zonder lader, 1.0.2) | `/home/overview` | `?v=3b34d9caede3` |
| vóór (zonder lader, ná update) | `/home/overview` | `?v=1724b468f3e9` — maar pas ná de laadbeurt die de oude bundel draaide |
| ná (met lader, 1.0.2 eronder) | `/home/overview` | **geen hash** — alleen `/api/domotiapp_alarm/loader.js` |
| ná (met lader, ná update) | `/home/overview` | **geen hash**, en de lader gaf de nieuwe |

De derde rij is de kern: in het gecachte document staat sinds fase 11 **geen
versie-informatie meer**. Er valt dus niets meer te verouderen.

**3. Werkt de kaart?** Ja — `docs/fase-11/1-kaart-na-update-8130.jpg` toont de
lege staat met de kopbalk en de plusknop, wat de indeling van 1.0.3+ is.

De instance is opgeruimd: `docker compose … down -v`, `.ha-install-config`
verwijderd, poort 8130 geeft geen antwoord meer.

---

## Deel 3 — De openstaande punten

### De volume-oploop haalt in

Precies het voorstel dat sinds fase 3c-bis in de tabel stond. `oploop.index_bij`
rekent uit welke stap bij de verstreken tijd hoort:

```
stap i is verschuldigd op (i + 1) * 1 s na het bedoelde begin
```

en het **bedoelde begin** is het moment waarop het volume op 0 gaat — stap 3 van
de afvuurvolgorde, dus vóór `play_media`. Blokkeert `play_media` 2,5 s, dan valt
de eerste tik op 3,5 s verstreken en is stap 2 verschuldigd: de oploop slaat twee
stappen over en is alsnog op **+20 s** klaar.

Wat er níét verandert: de volgorde van SPEC 9.1, het moment van het
`started`-event, en de 20 stappen zelf. De teller loopt bovendien nooit terug
(`max(verschuldigd, self._index)`) — terugvallen zou het volume hoorbaar laten
zakken.

Eén ding dat onderweg opviel en dat in de code staat: `time.monotonic` mag je in
een test **niet** vervangen, want asyncio plant zijn timers erop. Er staat daarom
een eigen naam `_klok` in `afvuren.py`, en de test vervangt die.

### Liegende teksten

De toets uit fase 6b toegepast op alle zeven meldingen plus de teksten in de
kaart. **Drie gevonden, alle drie hetzelfde patroon: een claim over
bereikbaarheid die de code nergens vaststelt.**

| Waar | Was | Is | Wat de code werkelijk vaststelt |
|---|---|---|---|
| `speaker_unavailable` | "was niet bereikbaar" | "was niet beschikbaar in Home Assistant" | `noodrem.py:101-102` — de state is `unavailable` of ontbreekt |
| `ma_unavailable` | "Music Assistant was niet bereikbaar" | "de Music Assistant-integratie is niet actief in Home Assistant" | `noodrem.py:108` — `async_loaded_entries(MA_DOMAIN)` is leeg. Dat kan ook betekenen dat MA niet geïnstalleerd is of dat de entry uitstaat |
| `voorbeeld.py:167` | "is niet bereikbaar" | "is niet beschikbaar in Home Assistant" | dezelfde noodrem |

Bereikbaarheid is een uitspraak over het netwerk. De code kijkt naar Home
Assistants eigen toestand en verder niets — en bij `ma_unavailable` wees de oude
tekst de klant naar zijn server terwijl het probleem in zijn integratielijst kon
zitten.

**Eén gevonden die ik NIET heb gewijzigd, en waarom.** `TEKST_PERSOON_WEG` in
`kaartconfig.js` zegt *"De gekozen persoon bestaat niet meer."* De kaart stelt
alleen vast dat `hass.states[person]` ontbreekt, en dat kan óók een hernoeming
zijn. SPEC 18.1 erkent dat zelf ("het onderscheid tussen hernoemd en verwijderd
is van buiten niet te zien") en SPEC 16.3 schrijft deze tekst **letterlijk** voor.
Wijzigen is dus een SPEC-wijziging en een productbeslissing.
**Voorstel voor de eigenaar:** *"De gekozen persoon is niet gevonden."* — dat
dekt beide gevallen en verwijst naar de kaartinstellingen, waar de oplossing zit.

### De rest van de lijst

| Punt | Wat ermee gebeurd is |
|---|---|
| `music/item_by_uri` als voorkeursroute | **blijft** — hangt aan een MA-release die er niet is; iemand moet dit blijven volgen |
| `SIMILAR_TRACKS`-providerlijst | **blijft** — moet bij elke MA-release nagelopen worden, en de terugval vangt het ergste al op |
| Volume-oploop begint te laat | **opgelost**, zie hierboven |
| Verwijderbevestiging zonder focusval/Escape | **blijft** — `ha-dialog` is in 2026.8 net verbouwd; eraan binden is duurder dan het ontbreken van een focusval bij twee knoppen |
| `endless` bij een bestaande wekker | **blijft** — is in fase 4c bewust aanvaard; het vraagt een schemawijziging voor een randgeval |
| Provider-as van `endless` niet live | **blijft** — vergt een streamingprovider op de testinstance |
| Tijdkiezer op iOS/Android | **blijft**, maar is sinds fase 10 wél de plek waar de bevinding van de eigenaar zat; hij toetst de reparatie |
| Time-out van `sound/search` | **blijft** — is nooit opgetreden; nabootsen zou de test in plaats van het gedrag toetsen |
| Kaart moet zoekresultaat uitkleden | **geschrapt** — dat is in fase 4b gebouwd en het punt was blijven staan |
| `getCardSize()` niet in masonry gemeten | **blijft, met reden erbij** — SPEC 20.1 schrijft sections voor en het ergste geval is een schatting die iets afwijkt |
| `panel: true` | **blijft, met reden erbij** — openstaand punt in HA zelf (`frontend#52570`) |

---

## Deel 4 — README, projectstand, aanpak

**De README klopte op drie punten niet meer:**

1. "via de drie puntjes **Overslaan** kiezen" — het menu is in fase 7 vervallen en
   overslaan bestaat niet meer, niet als knop, niet als commando, niet als veld.
2. "via de drie puntjes **Verwijderen**" — dat is nu één prullenbakknop per rij
   met een bevestiging die naam en tijd noemt.
3. "Onderaan staat wanneer de eerstvolgende wekker afgaat" — die kopbalk staat
   sinds fase 6b **bovenaan**.

Verder bijgewerkt: het voorbeeld zet sinds fase 8 ook de wake-up light aan, en er
staat nu een alinea dat je na een update de app niet hoeft af te sluiten.

**`docs/AANPAK.md`** is nieuw. Let op: het model waar de opdracht naar verwees
(`C:\dev\domotiapp-scene\docs\AANPAK.md`) **bestaat daar niet** — `docs/` bevat
daar alleen fasemappen. Het stuk is van nul opgezet, met `INVENTARIS.md` als
stijlvoorbeeld. Het eerlijke deel staat in §3 en de kern daarvan is: de
updatetest had fase 1 moeten zijn, valkuil 62 hield tien fases lang het
onderzoek tegen, fase 8 en 9 waren achteraf één ronde, en de aanname die een
halve dag kostte was "`box-sizing: border-box` declareren is genoeg".

---

## De tests

**346 Python-tests** (was 327) en **85 JS-tests**. Elf nieuwe Python-tests.

| Test | Label |
|---|---|
| `test_index_importeert_de_lader_en_niet_de_bundel` | NIEUW GEDRAG |
| `test_de_lader_geeft_de_hash_van_de_bundel_op_schijf` | NIEUW GEDRAG |
| `test_de_lader_mag_niet_gecachet_worden` | NIEUW GEDRAG |
| `test_de_lader_vereist_geen_token` | NIEUW GEDRAG |
| `test_de_lader_url_verandert_niet_als_de_bundel_verandert` | NIEUW GEDRAG |
| `test_de_lader_staat_onder_api` | **REGRESSIEWACHT** |
| `test_lader_en_resource_wijzen_naar_dezelfde_bundel` | **REGRESSIEWACHT** |
| `test_index_bij_geeft_de_verschuldigde_stap` (9 gevallen) | NIEUW GEDRAG |
| `test_de_oploop_is_op_twintig_seconden_klaar_hoe_laat_hij_ook_begint` | NIEUW GEDRAG |
| `test_index_bij_weigert_een_onzinnige_oploop` | NIEUW GEDRAG |
| `test_de_oploop_haalt_in_na_een_trage_play_media` (2 gevallen) | NIEUW GEDRAG + positieve controle |

### Gedraaid op de code van vóór de fix

**Eerst fout gedaan, en dat hoort erbij.** De eerste poging zette `custom_components/`
in zijn geheel terug, en dan ontbreekt `LOADER_URL_PATH` — de tests faalden met een
`ERROR` bij het verzamelen. Dat bewijst niets (CLAUDE.md: een test moet aantoonbaar
falen, niet met een importfout). De juiste opzet is `const.py` en `loader.py` laten
staan en alléén `__init__.py` terugzetten:

```
FAILED test_index_importeert_de_lader_en_niet_de_bundel
FAILED test_de_lader_geeft_de_hash_van_de_bundel_op_schijf
FAILED test_de_lader_mag_niet_gecachet_worden
FAILED test_de_lader_vereist_geen_token
FAILED test_de_lader_url_verandert_niet_als_de_bundel_verandert
FAILED test_lader_en_resource_wijzen_naar_dezelfde_bundel
FAILED test_setup_gaat_niet_stuk_zonder_lovelace_opslag
7 failed, 8 passed
```

`test_de_lader_staat_onder_api` faalt daar **niet**, want die kijkt alleen naar de
constante. Daarom staat hij als REGRESSIEWACHT en niet als NIEUW GEDRAG: hij houdt
een eigenschap vast die nergens anders afdwingbaar is, maar hij bewijst geen nieuw
gedrag.

Voor de oploop, met alleen `afvuren.py` terug op `main`: beide gevallen van
`test_de_oploop_haalt_in_na_een_trage_play_media` falen. Het geval zonder
vertraging faalt daar om een **triviale** reden — de seam `_klok` bestaat er niet —
en is dus alleen als positieve controle bruikbaar, niet als bewijs.

---

## De mutatieproef

`scripts/mutaties-fase-11.py`. **Ronde 1: 7 mutaties op wat de lader en de
inhaalslag beloven. Ronde 2: 8 mutaties op de randen.** Eindstand **15 mutaties,
14 gevangen**, na één gedicht gat, één geschrapte regel en één verantwoorde
equivalente mutant.

| | Mutatie | Gevangen |
|---|---|---|
| M1 | de lader staat niet meer onder `/api/` | ja |
| M2 | de gehashte URL gaat weer in `index.html` | ja |
| M3 | de lader mag gecachet worden | ja |
| M4 | de lader vraagt een token | ja |
| M5 | de lader laat de hash weg | ja |
| M6 | de stap is één te hoog | ja |
| M7 | geen inhaalslag — de code van vóór fase 11 | ja |
| M8 | zonder de `max`: de oploop mag terugvallen | ja |
| M9 | het nulpunt van de oploop ligt verkeerd | ja |
| M10 | bovengrens één te ruim | ja |
| M11 | ondergrens laat −1 door | ja |
| **M12** | de view wordt bij elke setup opnieuw geregistreerd | **NEE — verantwoord** |
| ~~M13~~ | de tak zonder hash | **vervallen: regel geschrapt** |
| **M14** | het content-type is geen javascript | **NEE → gedicht** |
| M15 | de oude gehashte URL wordt niet afgemeld bij een upgrade | ja |
| M16 | de resource wijst naar de lader in plaats van naar de bundel | ja |

### Wat er misging in de proef zelf, en dat is de moeite waard

De eerste ronde meldde **alles gevangen**, inclusief M13. Valkuil 46 zegt dat dat
geen goed teken is, en het klopte: bij het naspeuren welke test M13 ving, bleek
dat `test_een_onbereikbare_speaker_laat_de_wekker_niet_afgaan` — een test die
niets met de lader te maken heeft. Die faalde op **schone** code, doordat ik vlak
daarvoor de meldingstekst had gewijzigd en de assertie nog de oude woorden
gebruikte. De hele ronde draaide dus op een rode basis, en elke "GEVANGEN" was
daarmee waardeloos.

Dat is **valkuil 35** (de juiste uitkomst om de verkeerde reden) en het is de
tweede ronde op rij dat de mutatieproef er zelf in loopt. De les die er nu bij
staat: draai de suite groen vóórdat je muteert, en controleer bij een verrassende
"GEVANGEN" **welke** test faalde.

### De drie uitkomsten

**M14 — een echt testgat, gedicht.** Een module met `Content-Type: text/plain`
wordt door de browser geweigerd (strikte MIME-controle op ES-modules) terwijl de
server gewoon 200 zegt. De test keek wel naar `Cache-Control` en niet naar het
content-type. Er staat nu een assertie bij.

**M13 — onbereikbare code, dus de regel is eruit.** De lader had een tak voor
"geen hash bekend" die een lege module teruggaf. Narekenen: `async_registreer`
zet de hash in `hass.data` **voordat** het de view registreert, en niets haalt de
sleutel ooit weg — `async_unload_entry` popt `DATA_JS_URL` en `DATA_STORE`,
`async_remove_entry` popt `DATA_RESOURCE_ID`. Bestaat de route, dan bestaat de
hash. Weggehaald in plaats van er een test bij te verzinnen (valkuil 34, derde
rij), met de redenering in een comment.

**M12 — een equivalente mutant, verantwoord.** De guard die de view maar één keer
registreert wordt door geen test gevangen, en dat is nagerekend: aiohttp
accepteert een tweede route op hetzelfde pad en laat de eerste winnen, dus door
de publieke API is er niets van te zien. Hij blijft staan omdat een reload anders
bij elke keer een route aan de tabel plakt — meetbaar in geheugen, niet in
gedrag.

---

## Samenvatting

- **Valkuil 62 was fout en is rechtgezet.** De `?v=` werkt; wat verouderde was het
  **document** waarin die hash stond. De echte oorzaak is nu gevonden, gemeten en
  gerepareerd met een stabiele lader onder `/api/` — de enige route die HA's
  service worker nooit cachet.
- **De updatetest bestaat nu**, is gedraaid, en toont het verschil zwart op wit:
  vóór draaide de browser 1.0.2 achter een 1.0.4-installatie, ná draait hij 1.0.4
  bij een gewone herlaadbeurt.
- **Beide laadroutes werken nog**, met de reproductie uit fase 1 taak H.
- **De volume-oploop haalt in** en is op +20 s klaar.
- **Drie meldingen claimden bereikbaarheid** die de code niet vaststelt; herschreven.
- **De README klopte op drie punten niet meer**; bijgewerkt.
- **`docs/AANPAK.md`** is geschreven, met het eerlijke deel in §3.
- 346 Python- en 85 JS-tests, 15 mutaties in twee rondes.

## Wat niet lukte

1. **`docs/AANPAK.md` van DomotiApp Scene bestaat niet.** De opdracht noemde het
   als model. Er is geen enkel `.md`-bestand in `docs/` daar; het stuk is van nul
   opgezet.
2. **De lader is niet op een geïnstalleerde PWA getoetst**, alleen in een gewoon
   browsertabblad. De `/api/`-route is per definitie NetworkOnly, dus de
   redenering geldt, maar de meting is op een desktopbrowser gedaan.
3. **De overgang naar de lader kost nog één stale laadbeurt.** Wie van 1.0.4 naar
   1.0.5 gaat, heeft in zijn cache nog een document mét de oude hash — dat is
   precies het geval dat deze fix wegneemt, maar de fix zit pas ín de nieuwe
   versie. Vanaf 1.0.5 is het over. Dat is onvermijdelijk en het hoort gezegd.
4. **`TEKST_PERSOON_WEG` is niet gewijzigd**, omdat SPEC 16.3 hem letterlijk
   voorschrijft. Er ligt een voorstel; de beslissing is van de eigenaar.
5. **De volume-oploop is niet live nagemeten** op de dev-instance. De inhaalslag
   is in tests aangetoond met een bestuurbare klok; een livemeting zou de 2,1–2,6 s
   van `play_media` opnieuw moeten uitlokken en dat voegt aan de vaststelling niets
   toe wat de tests niet al geven.

## Aannames

1. **De updatetest gebruikt 1.0.2 als "oude versie"**, zoals de opdracht
   voorstelde. Dat is twee releases terug; de sprong 1.0.4 → 1.0.5 zou een kleiner
   hashverschil geven maar hetzelfde mechanisme.
2. **Het `/api/`-voorvoegsel blijft in HA doen wat het nu doet.** De routetabel is
   uit `sw-modern.js` van 2026.8 gelezen. Verandert HA die, dan valt de lader
   terug onder StaleWhileRevalidate — en dan is `Cache-Control: no-store` de
   tweede laag die het alsnog opvangt. Er staat een test op het voorvoegsel.
3. **De meldingsteksten zijn gewijzigd zonder de eigenaar te vragen.** Ze vielen
   onder de opdracht ("controleer of er nog liegende teksten zijn"), en de
   wijziging maakt ze smaller in plaats van anders. `TEKST_PERSOON_WEG` viel daar
   níét onder omdat SPEC hem letterlijk voorschrijft.
4. **Het versienummer is niet opgehoogd.** De releaseprocedure zegt dat de
   eigenaar tag en release maakt; de README noemt 1.0.5 als de versie waarin de
   lader zit, wat de eerstvolgende zou zijn.

## `git status --porcelain`

Vlak vóór de commit, op branch `fase-11/afronding`:

```
 M CLAUDE.md
 M README.md
 M SPEC.md
 M custom_components/domotiapp_alarm/__init__.py
 M custom_components/domotiapp_alarm/afvuren.py
 M custom_components/domotiapp_alarm/const.py
 M custom_components/domotiapp_alarm/meldingen.py
 M custom_components/domotiapp_alarm/oploop.py
 M custom_components/domotiapp_alarm/voorbeeld.py
 M tests/test_afvuren.py
 M tests/test_init.py
 M tests/test_oploop.py
 M tests/test_voorbeeld.py
?? custom_components/domotiapp_alarm/loader.py
?? docs/AANPAK.md
?? docs/fase-11/
?? scripts/mutaties-fase-11.py
```
