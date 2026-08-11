# Fase 4a — De kaart: lijst, schakelaars en de stoptoestand

De kaart in rusttoestand plus de stoptoestand: wekkers zijn te zien, aan en uit te
zetten, over te slaan en te verwijderen, en een afgaande wekker maakt van de kaart
één grote stopknop. Geen editor — dat is fase 4b.

Er is één ding bijgekomen dat niet in de opdracht stond en dat wél nodig bleek: een
**tiende WebSocket-commando**. Zie "De bevinding" hieronder; de eigenaar heeft daar
expliciet toestemming voor gegeven, inclusief het bijwerken van `SPEC.md`.

---

## De bevinding: SPEC 11.7 vroeg een knop die SPEC 15 niet kon bedienen

**Gevonden vóór er een regel code geschreven was**, bij het lezen van SPEC.

SPEC 11.7 schrijft voor dat de rij van een wekker met een melding een
**"Begrepen"-knop** krijgt "die hem wegneemt", en diezelfde sectie legt vast dat de
melding **in de opslag** staat "zodat hij een herstart overleeft en de kaart hem kan
tonen ook als de browser pas uren later opengaat".

Die twee eisen samen kunnen alleen door de server worden ingelost. Maar SPEC 15 kende
negen commando's en geen ervan wist `last_message`:

| Commando | Raakt `last_message`? |
|---|---|
| `alarms/save` | **weigert het veld** — `validatie.py:44` (`SERVERVELDEN`), en neemt het bij een update over uit de bestaande wekker (`websocket.py:198`) |
| `set_enabled`, `skip_next`, `delete`, `stop` | nee |
| `get`, `search`, `entities/list`, `ringing/subscribe` | lezen alleen |

SPEC 15.10 ("wat er bewust géén commando is") noemde het niet, dus het was een
omissie en geen keuze.

**Wat er zonder dat commando overbleef**, en waarom geen van beide goed was:

- de knop weglaten — dan voldoet de kaart niet aan SPEC 11.7;
- de melding **lokaal** verbergen — dan is het een knop die liegt: hij verdwijnt in
  één browser, blijft staan op het wandtablet, en komt terug na een herlaadbeurt.

De eigenaar heeft gekozen voor het tiende commando en deze ronde aangemerkt als een
ronde waarin `SPEC.md` gewijzigd mag worden, uitsluitend voor dit gat.

### Wat er is toegevoegd

`domotiapp_alarm/alarms/clear_message` — invoer `person` en `alarm_id`, uitvoer als
`alarms/get`, voor iedere ingelogde gebruiker net als de andere negen. SPEC 15.10 is
de nieuwe subsectie; het oude 15.10 is 15.11 geworden, met een extra regel erin.
SPEC 11.7 en de rechtentabel van SPEC 17 verwijzen ernaar.

### De controle die de eigenaar vroeg: geeft dit de kaart een servervelden-omweg?

**Nee, en dat is aan de vorm van het commando af te lezen.** SPEC 15.2 verbiedt dat
`skip_next`, `one_shot_at`, `last_fired` en `last_message` **met een waarde** van de
kaart komen, omdat een kaart die ze mag zetten de inhaalslag van SPEC 13.4 om de tuin
kan leiden. Drie eigenschappen houden dat overeind:

1. het commando **neemt geen waarde aan** — er is geen veld voor `text`, `kind`,
   `severity` of `at`;
2. het zet `last_message` **onvoorwaardelijk** op `null`; er is precies één uitkomst
   en die is niet door de aanroeper te sturen;
3. het raakt de andere drie servervelden **niet** aan.

Alle drie zijn getoetst, en de eerste is met een mutatie nagerekend (P4 hieronder).
`test_clear_message_kan_geen_melding_zetten` stuurt `last_message`, `message` en
`severity` mee en krijgt drie keer `invalid_format`; daarna slaagt dezelfde aanroep
**zonder** die velden — de positieve controle, want anders zou die test ook slagen op
een commando dat helemaal niet bestaat.

---

## Wat er gebouwd is

### Taak A — kaart-config en config-editor (SPEC 16)

| | |
|---|---|
| Sleutels | alleen `person`, verplicht, een `person.`-entity-ID |
| Editor | `ha-form` met één `entity`-selector, `filter: {domain: "person"}` |
| `getStubConfig` | `{type: "custom:domotiapp-alarm-card"}` — **zonder** `person` |

De drie gevallen van SPEC 16.3 zitten in `src/kaartconfig.js` en zijn los toetsbaar:
`valideerConfig` gooit **alleen** bij een `person` in het verkeerde domein, en
`personToestand` onderscheidt "ontbreekt" (geen foutkleur — dit is de toestand direct
na toevoegen) van "weg" (wel foutkleur).

Onbekende sleutels blijven staan. Lovelace hangt zelf `grid_options`,
`layout_options`, `view_layout` en `visibility` aan een kaartconfig; een validatie die
die weggooit, verliest de plaatsing van de klant bij de eerstvolgende bewerking.

### Taak B, C, D, E — de kaart

Toetsbare logica staat in **twee pure modules zonder DOM**, zoals DomotiApp Scene het
met `apply-scene.js` deed:

| Module | Wat erin zit |
|---|---|
| `src/weergave.js` | `dagenTekst`, `isAfgelopen`, `subtitel`, `meldingVan`, `stopToestand` |
| `src/kaartconfig.js` | `valideerConfig`, `stubConfig`, `personToestand`, `foutTekst` |

**Wat er bewust NIET in de kaart zit:**

- **de regel "eerstvolgende wekker" wordt niet berekend.** Die tekst komt
  kant-en-klaar uit `alarms/get` als `next_fire.text` (SPEC 3.3). Twee implementaties
  van dezelfde planning lopen uiteen — de fout die DomotiApp Scene met de
  helderheidsschaal maakte.
- **de kaart sorteert niet.** `alarms/get` levert de lijst al gesorteerd volgens
  SPEC 3.4 (`volgende.py:sorteer`). De opdracht noemde sorteren onder taak B; het
  gebeurt server-side en de volgorde is in de browser nagemeten.
- **de kaart pollt niet.** De stoptoestand komt van `ringing/subscribe`, en bij het
  openen meteen uit het veld `ringing` van `alarms/get`.

### Vormkeuzes die uitleg verdienen

**Bijna geen HA-componenten.** De schakelaar, het overloopmenu en de iconen zijn
eigen elementen; alleen `ha-card` en (in de editor) `ha-form` komen van HA. Reden: HA
laadt zijn componenten lui. Op een dashboard waar deze kaart de enige kaart is, is er
niets dat `ha-switch` of `ha-button-menu` binnenhaalt, en een **ongedefinieerd custom
element rendert als een leeg inline-element** — dan is de schakelaar onzichtbaar
zonder dat er een fout in de console staat. `ha-card` is er hoe dan ook (de
dashboardchrome laadt hem) en `ha-form` bestaat alleen binnen HA's eigen
kaarteditor-dialoog, die zelf van `ha-form` gemaakt is.

Bijkomend, en het is meetbaar beter: valkuil 8 zegt dat een klik op een knop zonder
opgehaald icoon mist. Deze knoppen hebben hun oppervlak uit CSS, niet uit een
asynchroon `ha-icon`. De iconen zijn inline SVG.

**De bevestiging bij verwijderen is een regel in de kaart**, geen dialoog. HA's eigen
bevestigingsdialoog is alleen bereikbaar via een `show-dialog`-event met een
`dialogImport` naar HA's binnenkant — precies het soort afhankelijkheid dat bij een
update stil breekt (dezelfde afweging als bij `runtime_data.mass`, SPEC 11.2.2). De
rij klapt open met de vraag en twee knoppen.

**De plusknop toont een tijdelijke melding in de kaart zelf**, zes seconden lang:
*"De editor komt in fase 4b. Zet je wekkers voorlopig via de WebSocket-API."* Geen
`hass-notification`-toast, om dezelfde reden als hierboven: dat is HA's binnenkant.
De opdracht liet de vorm vrij en vroeg te melden wat er gekozen is.

**Het overloopmenu heeft twee items** (SPEC 3.2). Het eerste heet **"Overslaan"** of
**"Toch niet overslaan"**, afhankelijk van `skip_next`. Hetzelfde commando
(`alarms/skip_next` met `skip: true|false`), en een label dat niet liegt over wat er
gaat gebeuren.

**Geen `overflow: hidden` op de `ha-card`.** Dat knipte het overloopmenu van de
onderste rij af. De stopknop draagt daarom zelf `var(--ha-card-border-radius)`.
Gemeten: het menu van de onderste rij steekt 5 px onder de kaart uit en is zichtbaar.

---

## Taak F — tests

| | vóór 4a | na 4a |
|---|---|---|
| JS (`node --test`, geen jsdom) | 8 | **40** |
| Python | 212 | **216** |

Alle tests zijn gelabeld **NIEUW GEDRAG**; er zitten geen regressiewachten in deze
ronde.

### Falen op de oude code

**De vier Python-tests zijn het interessante geval**, want `websocket.py` bestond al.
Gedraaid tegen `main` in een aparte worktree:

```
E       AssertionError: {'error': {'code': 'unknown_command', 'message': 'Unknown command.'}, ...}
E           assert 'unknown_command' == 'invalid_format'
4 failed, 50 deselected in 1.50s
```

**De JS-tests falen triviaal**, en dat wordt hier eerlijk genoemd in plaats van als
bewijs opgevoerd: `weergave.js` en `kaartconfig.js` bestaan pas in deze fase, dus
tegen `main` faalt alles met `ERR_MODULE_NOT_FOUND`:

```
Error [ERR_MODULE_NOT_FOUND]: Cannot find module '...\src\kaartconfig.js'
Error [ERR_MODULE_NOT_FOUND]: Cannot find module '...\src\weergave.js'
ℹ tests 2   ℹ pass 0   ℹ fail 2
```

Dat bewijst niets over gedrag — het is dezelfde situatie als bij `registreer.js` in
fase 1. Het echte bewijs is de mutatie-oefening hieronder.

### Positieve controles

Valkuil 36 is op vier plekken toegepast, omdat een test die alleen op falen let
doorkomt op een implementatie die *altijd* faalt:

- `subtitel` toont de herhaaldagen als er niets bijzonders is — anders zou een
  implementatie die áltijd "Morgen overgeslagen" teruggeeft door de drie
  bijzondere-gevallen-tests heen komen;
- `valideerConfig` **laat** een geldige `person` door — anders komt een implementatie
  die altijd gooit door de domeintest;
- `clear_message` zonder extra velden **slaagt** — anders slaagt de test ook op een
  commando dat niet bestaat;
- `test_clear_message_wist_de_melding_uit_de_opslag` controleert eerst dat de melding
  er **wel** is, in het antwoord én op schijf.

### De mutatie-oefening: 28 mutaties, 2 gaten

Eerste ronde, 22 mutaties (18 JS + 4 Python): **allemaal gevangen**. Dat is op zichzelf
verdacht — de oefening vond in fase 1, 3a, 3b en 3c elke keer iets — dus er is een
tweede ronde gedaan met mutaties die gericht naar gaten zochten in plaats van dekking
te bevestigen. Die vond er twee.

| | Mutatie | Uitkomst |
|---|---|---|
| J1–J12 | `weergave.js`: dagvolgorde, off-by-one, sorteren, dedup, isAfgelopen, volgorde van subtitel, severity, meldingfallback, stop-ids, tijden | gevangen |
| J13–J18 | `kaartconfig.js`: domeincontrole eruit, gooien bij ontbrekende person, Lovelace-sleutels weggooien, foutkleur, foutcodes, stub mét person | gevangen |
| J19, J20, J23, J24 | tweede ronde: `typeof`-filter op ringing, `home_assistant_error`-tak, neutrale naam, sorteren | gevangen |
| **J21** | `meldingVan`: de controle `typeof bericht !== "object"` eruit | **NIET GEVANGEN** |
| **J22** | `isAfgelopen`: de `Number.isNaN`-controle eruit | **NIET GEVANGEN** |
| P1–P4 | `clear_message`: veld niet wissen, `not_found` eruit, óók `last_fired`/`skip_next` wissen, extra velden toestaan | gevangen |

**J21 is een testgat** (valkuil 34, eerste rij): de regel is bereikbaar en doet iets
waarneembaars. Zonder die controle wordt een `last_message` die géén object is —
bijvoorbeeld een string na handmatig knoeien in `.storage` — getoond als *"Er is een
melding over deze wekker, maar de tekst ontbreekt."* Dat beweert dat er iets met de
**wekker** gebeurd is, terwijl er iets met de **opslag** mis is. Er is een test bij
gekomen; die vond meteen een echte fout, want `typeof [] === "object"` in JavaScript
en een lijst kwam er dus doorheen. De implementatie draagt nu ook `Array.isArray`.

**J22 is onbereikbare code** (valkuil 34, derde rij), en dat is nagerekend in plaats
van vermoed: `Date.parse` geeft `NaN` bij een ontbrekende of onleesbare waarde, en
**elke** vergelijking met `NaN` is `false` — dus `NaN <= nuMs` levert al "niet
afgelopen" op. Er is geen invoer waarbij die regel iets verandert. **De regel is
eruit gehaald en de meting staat in een comment.** Een test erbij verzinnen zou
dekking suggereren die er niet is.

Merk op dat de bestaande test *"verzint niets bij een ontbrekende of kapotte datum"*
op beide versies slaagt. Die test is blijven staan omdat hij het gedrag vastlegt,
maar hij bewees de weggehaalde regel niet — dat is precies valkuil 35, een test die
de juiste uitkomst om de verkeerde reden krijgt.

---

## Taak G — browserverificatie

Op de dev-instance (poort 8129), in een **eigen Lovelace-dashboard in
sections-weergave** — niet op een ingebouwd paneel, conform SPEC 20.1 punt 2.

### Verse code bewezen vóór er iets gemeten is

Container herstart, service worker afgemeld (1 registratie), vier caches gewist
(`file-cache`, `workbox-runtime`, `workbox-precache-v2`, `brands`), één harde
herlaadbeurt. Daarna `fetch(url, {cache: 'reload'})`:

| | |
|---|---|
| bundel op schijf | 32.664 bytes, sha256 `1d156f36…b60489` |
| door HA geserveerd | 32.664 bytes, sha256 **identiek** |
| `?v=` op de kaart-URL | `1d156f360009` — de eerste 12 hex van diezelfde hash |
| `customElements.get('domotiapp-alarm-card')` | aanwezig |
| `customElements.get('domotiapp-alarm-card-editor')` | aanwezig |
| `window.customCards` | 1 vermelding |

De hash zelf komt niet door de uitvoerfilter van de browsertool (hij lijkt op base64,
vergelijkbaar met valkuil 7 en 33), dus de vergelijking is **in de pagina** gedaan en
er kwam een boolean terug: `hash_gelijk_aan_schijf: true`.

### De zeven punten

**1. De lege kaart met de plusknop** — `01-lege-kaart.jpg`. "Geen wekkers ingesteld"
plus "Geen wekker actief" en de plusknop. Een echte klik op de plusknop
(`isTrusted: true`, doelelement het SVG-pad ín de knop) toont de tijdelijke melding —
`02-plusknop-melding.jpg`.

**2. Drie wekkers** — `03-drie-wekkers.jpg`:

```
05:20  Trein naar Utrecht   Eenmalig
06:45  Werk                 ma di wo do vr
09:00  Weekend              Morgen overgeslagen
       Morgen 05:20                        +
```

Sortering op tijd oplopend (SPEC 3.4), server-side. Uitlijning **gemeten** en niet op
het oog:

| | rij 1 | rij 2 | rij 3 |
|---|---|---|---|
| linkerkant tijd | 855 | 855 | 855 |
| linkerkant naam | 949 | 949 | 949 |
| linkerkant schakelaar | 1225 | 1225 | 1225 |
| linkerkant menuknop | 1281 | 1281 | 1281 |
| rijhoogte | 67 | 67 | 67 |

Accentkleur van een actieve schakelaar: `rgb(2, 111, 161)` = **#026FA1**.

**3. De schakelaar uitzetten** — echte klik, `isTrusted: true`, doel
`BUTTON.schakelaar`. Server daarna `Werk: enabled=false`, schakelaar in de kaart grijs
(`rgb(111, 111, 111)`).

`next_fire` klopte daarna, en dat is met een tweede klik aangetoond in plaats van
aangenomen: Werk uitzetten veranderde de voetregel **niet** (Trein om 05:20 was toch
al eerder). Pas toen ook Trein uitging sprong de regel van `Morgen 05:20` naar
**`Zondag 09:00`** — de overgeslagen zaterdag wordt overgeslagen en het wordt zondag.
Daarna Werk weer aan: `Morgen 06:45`.

**4. Overslaan en verwijderen via het overloopmenu** — `04-overloopmenu.jpg` en
`05-bevestiging-verwijderen.jpg`.

- *Overslaan* op Werk: subtitel wordt "Morgen overgeslagen", **de schakelaar blijft
  aan** (SPEC 3.2), en de voetregel schuift van `Morgen 06:45` naar
  `Donderdag 06:45`. Geen bevestiging gevraagd.
- *Toch niet overslaan* op Weekend: subtitel terug naar "za zo", `skip_next=false` op
  de server.
- *Verwijderen* op Trein: eerst de regel `Wekker "Trein naar Utrecht" van 05:20
  verwijderen?` met **Annuleren** en **Verwijderen** (`rgb(219, 68, 55)` =
  `--error-color`). Na bevestigen weg uit de kaart **en** van de server.

Alle vier de kliks `isTrusted: true`, met vóór elke klik een verse
`getBoundingClientRect` en een hit-test met `elementFromPoint` (valkuil 8 en 16).

**5. Een melding en "Begrepen"** — `06-melding-begrepen.jpg`. Dit is geen nagebootste
melding: er is een echte wekker gezet terwijl de speaker `unavailable` was, en de
noodrem heeft hem tegengehouden.

```
09:14:00.012 WARNING [afvuren]  Wekker f16f2387… gaat NIET af:
             speaker media_player.wekker_slaapkamer is niet bereikbaar
09:14:00.024 ERROR   [meldingen] De wekker van 11:14 is niet afgegaan: de speaker
             'media_player.wekker_slaapkamer' was niet bereikbaar.
```

De melding stond in `--error-color` (`rgb(219, 68, 55)`) met een waarschuwingsicoon en
een "Begrepen"-knop. Klik `isTrusted: true`; daarna `last_message: null` in het
antwoord, en **ook in `.storage/domotiapp_alarm.alarms` op schijf** — dat is het punt
waar het commando voor bestaat.

Drie dingen kwamen hier gratis bij:

- de rij verscheen **zonder herladen**, om 11:14:00, doordat het `failed`-event de
  kaart liet bijwerken;
- de wekker toonde **"Eenmalig — afgelopen"** terwijl `enabled` nog `true` was — de
  wekker is immers niet afgegaan. Dat is exact het geval dat de unittest
  *"kijkt naar het moment en niet naar enabled"* vastlegt, nu live;
- valkuil 18 opnieuw bevestigd: op `unavailable` bleven precies `device_class`,
  `icon`, `friendly_name` en `supported_features` over.

**6. De stoptoestand zonder herladen** — `07-stoptoestand.jpg`. Wekker "Opstaan" gezet
op 11:18, speakers weer gestart. Wat de kaart deed, gelogd met een `MutationObserver`
zodat er niet met de klok geracet hoefde te worden:

| klok | kaart | stopknop |
|---|---|---|
| 11:15:41 | de lijst met drie wekkers | nee |
| **11:18:02** | `Wekker Stoppen` | **ja** |
| 11:18:02 | `11:18 Opstaan Stoppen` | ja |

**Die twee regels op hetzelfde moment zijn het ontwerp en geen hapering.** Het
`started`-event wordt eerst plaatselijk verwerkt — dan is het ID bekend en de wekker
nog niet — en daarna komt `alarms/get` met de naam. Dat de knop in dat venster
overeind blijft met een neutrale naam is precies de regel die de unittest *"houdt de
knop overeind bij een onbekend ID"* vastlegt. Zonder die regel had de kaart in dat
venster **niets** getoond.

De hele kaart is de knop: 498 × 184 px tegen een kaart van 500 × 186 (het verschil is
de rand van de `ha-card`), achtergrond `rgb(2, 111, 161)`, en de lijst is weg.

Er kwam **echt geluid** uit, gemeten aan de **ontvangende** kant in het snapclient-log
(valkuil 38 — niet in de browser en niet op totaalduur):

| venster | duur | `No chunks available` |
|---|---|---|
| vóór de wekker | 124 s | **124 s stilte** |
| tijdens de wekker | 186 s | **0 s stilte** |
| na het stoppen | 60 s | 44 s stilte |

En de volume-oploop, in dezelfde log:

```
11-18-00.015  volume: 0      <- vóór het geluid (SPEC 9.1 stap 2)
11-18-03.757  volume: 2
11-18-04.761  volume: 4
...
11-18-22.860  volume: 40     <- 20 stappen, 1,004-1,006 s per stap
```

Klik op STOPPEN: `isTrusted: true`. Daarna `ringing: []` op de server, speaker terug
op `idle`, en **het volume terug op 0,55** — de stand van vóór de wekker (SPEC 9.5).
HA-log: `Wekker 7c224543… gestopt (user)`.

**7. Stopknop meteen bij openen** — `08-stoptoestand-bij-openen.jpg`. Terwijl de
wekker liep is de pagina **opnieuw geladen**. De verse kaart toonde onmiddellijk
`11:18 Opstaan STOPPEN`, met `ringing` uit `alarms/get` gevuld (1 ID) en de wekker
herkend in de lijst. Er kón geen `started`-event meer komen: dat was om 11:18:02
verstuurd en deze pagina bestond pas om 11:20:36.

### Taak A live

`09-spec-16-3-drie-gevallen.jpg` — drie kaarten naast elkaar:

| config | wat de kaart toont |
|---|---|
| geen `person` | "Kies een persoon in de kaartinstellingen." in `--secondary-text-color` |
| `person.bestaat_niet` | "De gekozen persoon bestaat niet meer." in `--error-color` |
| `light.bed_light` | Lovelace's eigen **"Configuratiefout"**, met onze tekst eronder in bewerkmodus: *"'light.bed_light' zit niet in het domein person. Kies een persoon, zoals person.sven."* |

De config-editor (`10-config-editor.jpg` t/m `12-editor-met-persoon.jpg`): één veld
"Persoon". De kiezer toonde **alleen `dev — Persoon`** terwijl er tientallen andere
entiteiten op de instance staan, dus de domeinbeperking werkt.

**Het tekstveld is met échte toetsaanslagen getoetst, inclusief een spatie**
(CLAUDE.md-werkafspraak, en de reden dat die er staat: in DomotiApp Scene accepteerde
een naamveld een hele fase lang geen spatie omdat er met één woord getoetst was):

```
d       isTrusted: true
e       isTrusted: true
SPATIE  isTrusted: true
v       isTrusted: true
veldwaarde: "de v"        <- de spatie staat erin
```

Na het kiezen van `dev` sprong het voorbeeld in de dialoog meteen op de volledige
lijst, en werd Opslaan actief.

### Afmetingen

| | |
|---|---|
| `getGridOptions()` | `{rows: "auto", columns: 12, min_columns: 6}` — `rows` is de **string** `"auto"`, geen getal (valkuil 12) |
| `getCardSize()` | 5 bij vier wekkers (1 per rij + 1 voetregel); 3 in de stoptoestand |
| kaarthoogte tegen sectievak | 332 px in een vak van 332 px — geen overloop |

Console na een herlaadbeurt met de consolelezer actief: **geen enkel bericht**, dus
geen fouten en geen waarschuwingen uit de bundel.

---

## Wat niet lukte

**1. De kaart ziet wijzigingen van buiten zichzelf niet.** Tijdens het meten viel op
dat wekkers die via de WebSocket-API werden aangemaakt pas na een herlaadbeurt op de
kaart verschenen. Dat is geen fout in de kaart: elk commando geeft de volledige nieuwe
toestand terug (SPEC 15.2), dus de kaart die zélf iets doet blijft actueel — maar
**SPEC 15 kent geen abonnement op opslagwijzigingen**, alleen op `ringing`. Gevolg: een
wekker die op de telefoon wordt gewijzigd, verschijnt op het wandtablet pas als dat
dashboard opnieuw opengaat.

In deze fase is dat nauwelijks zichtbaar omdat er nog geen editor is; met fase 4b
wordt het merkbaar. Dit is **niet** zelf opgelost: het vraagt een elfde commando of
een uitbreiding van `ringing/subscribe`, en dat is een SPEC-beslissing van de eigenaar.
Zie het openstaande punt in `CLAUDE.md`.

**2. `getCardSize()` is niet in een masonry-weergave nagemeten.** De methode bestaat en
geeft een plausibel getal, maar het dashboard staat in sections-weergave zoals SPEC
20.1 punt 2 voorschrijft. Dat masonry-gedrag stond al als openstaand punt en blijft dat.

**3. Twee keer is een screenshot als coördinatenbron misgegaan** voordat het opviel.
De browsertool werkt in screenshotcoördinaten (1568 px breed) en
`getBoundingClientRect` in CSS-pixels (`innerWidth` 1920) — een factor **0,8167**. De
eerste klik landde daardoor toevallig goed en de tweede meting leek te falen. Vanaf
dat punt is elke klikcoördinaat uit een verse `getBoundingClientRect` × schaalfactor
berekend, met een hit-test erna. Zie de nieuwe valkuil in `CLAUDE.md`.

**4. Het zelf door shadow roots zoeken naar de kaart faalde twee keer**, precies zoals
valkuil 10 beschrijft — één keer met "0 kaarten" terwijl de kaart op het scherm stond.
Opgelost zoals de valkuil voorschrijft: een capture-listener op `window` en de kaart
uit `event.composedPath()`.

---

## Aannames

1. **De volgorde "afgelopen vóór overgeslagen" in de subtitel is een keuze.** SPEC 3.2
   en 14.5 beschrijven beide teksten maar niet welke wint als ze samenvallen. Gekozen
   voor "Eenmalig — afgelopen", omdat een wekker waarvan het moment voorbij is sowieso
   niet meer afgaat en "Morgen overgeslagen" dan een belofte is over een morgen die
   niet komt.
2. **Het criterium voor "Eenmalig — afgelopen" is het moment, niet `enabled`.** SPEC
   14.5 beschrijft de wekker die is afgegaan (`enabled: false`, `last_fired` gevuld).
   Een eenmalige wekker die is **gemist** staat nog op `enabled: true` en is net zo
   goed afgelopen; live bevestigd bij de wekker van 11:14.
3. **Bij meerdere afgaande wekkers worden namen en tijden met "en" aaneengeregen**
   ("Werk en Reserve"). SPEC 4 eist één knop die beide stopt en laat de tekst vrij.
4. **Het menu-item heet "Toch niet overslaan" als de wekker al overgeslagen is.**
   SPEC 3.2 noemt twee items, "Overslaan" en "Verwijderen"; het label volgt de stand.
5. **De tijdelijke melding achter de plusknop staat 6 seconden in de kaart zelf.** De
   opdracht liet vorm en duur vrij.
6. **`clear_message` roept `planner.async_herplan` aan**, net als de andere muterende
   commando's. SPEC 13.5 zegt "elke wijziging in de opslag via een WebSocket-commando";
   feitelijk is het een lege ronde, maar de uitzondering zou duurder zijn dan de ronde.

---

## `git status --porcelain`

```
```

(schoon; alles staat in de commits van `fase-4a/kaart`)
