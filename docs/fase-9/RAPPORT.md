# Fase 9 — De kaart in een echte Bubble Card pop-up

Fase 8 mat de kaart smal via `grid_options` en meldde "0 van de 57 elementen valt
buiten de kaart". De eigenaar zag daarna op zijn telefoon nog steeds iets fout gaan.
Deze ronde bouwt de conditie waarin hij hem werkelijk gebruikt — een echte Bubble
Card-pop-up op telefoonbreedte — en meet daarin.

---

## Samenvatting

| | |
|---|---|
| **Wat er gevonden is** | de knop **"Verwijderen"** van de verwijderbevestiging stak bij een wekker met een lange naam **27 px buiten de kaart en 9 px buiten de pop-up** — op 390 px, de breedte van de telefoon van de eigenaar. Een deel van de knop van een **onomkeerbare** handeling was niet aan te wijzen |
| **Waarom fase 8 het miste** | die meting heeft de bevestiging nooit geopend. De 57 elementen waren de lijst en de editor; de bevestiging voegt er vier toe |
| **Het tijdveld** | **niet gereproduceerd**, en niet bij gebrek aan proberen — zie de aparte sectie. Er staat een vraag aan de eigenaar open |
| **Wat er nu staat** | een herbruikbare meetopstelling: view `/fase-4a/bubble-echt`, `scripts/telefoon.html`, `scripts/meet-afsnijden.js`, en een werkafspraak in CLAUDE.md |

**327 Python-tests, 85 JS-tests**, alle groen — en geen ervan raakt deze fix; dat
staat eerlijk in de testsectie. **11 mutaties in twee rondes**, waarvan er één een
regel uit de fix heeft **geschrapt** en één de meetfunctie zelf heeft uitgebreid.
Bundel van 55.503 naar **57.518 bytes**.

---

## Taak A — Bubble Card op 8129

**Gekozen route: het bestand in `www/` en registreren als Lovelace-resource.** Er
staat geen HACS op de dev-instance, en die er alsnog op zetten zou een tweede
onbekende toevoegen aan een ronde die juist één conditie scherp wil krijgen. Bubble
Card documenteert deze route zelf. Versie **v3.2.5**, 849.002 bytes.

Twee dingen die hierbij misgingen en die de volgende ronde tijd schelen:

- **`www/` moet bestaan vóórdat HA start.** HA registreert het statische pad bij
  het opstarten. De map is tijdens deze sessie aangemaakt en `/local/…` gaf daarna
  404 terwijl het bestand er stond; `curl` van buiten gaf ook 404. Pas na
  `docker restart ha-alarm` werd het geserveerd.
- **En daarna gaf de browser nog steeds 404**, terwijl `curl` inmiddels 200 gaf.
  Dat is valkuil 62 in zijn zuiverste vorm: HA's service worker had de 404
  vastgehouden. Cache leegmaken, service worker afmelden, harde herlaadbeurt.

De pop-up zelf is gebouwd zoals de eigenaar hem gebruikt — hij meldde dat Bubble
Card in de nieuwste releases **geen `vertical-stack` meer** gebruikt, en dat klopt:
sinds v3.2.0 is er het **standalone formaat** met de inhoud rechtstreeks onder
`cards:`. De yaml staat in `scripts/bubble-meetopstelling.md`.

### De meetconditie, en waarom er een iframe aan te pas komt

De opdracht vraagt te meten op een echte telefoonbreedte. Dat kon niet op de
gewone manier:

```
resize_window(390, 844)  ->  "Successfully resized"
window.innerWidth        ->  1920
window.outerWidth        ->  0
document.visibilityState ->  "hidden"
```

Het tabblad van de meetsessie rendert **buiten beeld** op een vaste viewport van
1920 px. Het venster van de eigenaar is ook geprobeerd (un-maximaliseren en
verplaatsen via `user32.dll`) — dat verplaatste een ánder Chrome-venster en liet
`innerWidth` op 1920. Het venster is daarna teruggezet zoals het stond.

De uitweg is `scripts/telefoon.html`: het dashboard in een iframe van een vaste
breedte. Het ingesloten document krijgt dan werkelijk een viewport van 390 px, en
daar hangt alles aan wat we willen meten — media queries, **container** queries,
HA's mobiele omslagpunt en Bubble Cards eigen breedteberekening.

**Eén regel maakt het verschil, en zonder die regel is de rig stil kapot:**

```html
<iframe name="ha-main-window">
```

HA's `get_main_window.ts` kiest zijn hoofdvenster op `window.name`. Zonder de naam
valt HA in een frame terug op `top`, en dan doet `navigate()` zijn `pushState` en
zijn `location-changed` op de **rig** in plaats van op HA. Gemeten: een echte klik
(`isTrusted: true`, de listener zag hem) op een Bubble Card-knop met
`tap_action: navigate` deed **helemaal niets** — geen fout, geen hashwijziging,
nergens. Mét de naam werkt de navigatie native.

**Wat de rig niet nabootst**, en dat hoort in elke conclusie hieronder mee te
wegen: `devicePixelRatio`, touch-invoer, het schermtoetsenbord, en de manier waarop
een telefoon `<input type="time">` zélf tekent.

---

## Taak B — De meting

Vier toestanden, elk over zes breedtes, met per element de rechthoek vergeleken met
die van de **kaart** én die van de **pop-up**, aan beide kanten.

De pop-up is op een telefoon schermvullend: bij een frame van 390 px is de pop-up
**390 px** en de kaart erin **354 px**. Let op dat een pop-up van 244 px dus een
kaart van **208 px** oplevert — dat is 36 px **strenger** dan `/fase-4a/bubble`,
waar de 244 px de breedte van de káárt is.

### Wat er kapot was

```
LIJST + BEVESTIGING, wekker "Zaterdagochtendzwemtraining", frame 390 px
  kaart          18 → 372
  pop-up          0 → 390
  span.boodschap                       (past)
  button "Annuleren"                   (past)
  button "Verwijderen"   breedte 93    27 px BUITEN DE KAART, 9 px BUITEN DE POP-UP
```

Met een korte naam gebeurt hetzelfde zodra de kaart onder **276 px** komt:

```
kaart 304 (frame 340)  ->  0
kaart 294 (frame 330)  ->  0
kaart 284 (frame 320)  ->  0
kaart 274 (frame 310)  ->  2 px buiten de kaart
kaart 264 (frame 300)  ->  12 px
kaart 254 (frame 290)  ->  22 px buiten de kaart, 4 px buiten de pop-up
kaart 208 (frame 244)  ->  68 px buiten de kaart, 50 px buiten de pop-up
```

Screenshot: `3-voor-verwijderknop-buiten-de-popup.jpg`. De rode knop loopt zichtbaar
door de rand van de pop-up.

**Waarom dit niet eerder boven kwam.** `.onderrij` was `display: flex` zonder
`flex-wrap`, en `.boodschap` had `flex: 1` — dus `min-width: auto`, en dan kan de
tekst niet onder zijn langste woord krimpen. De rij liep over en duwde de knoppen
naar buiten. Fase 8 heeft precies dit voor de voetregel en de zoekrij opgelost maar
deze rij niet meegenomen, omdat de meting de bevestiging nooit heeft geopend. Dat is
valkuil 61 in een nieuwe jas: niet een klikvolgorde die een toestand mist, maar een
**meting** die een toestand mist.

Dat het uitgerekend de knop van een **onomkeerbare** handeling is die wegvalt, is de
reden dat dit geen schoonheidsfoutje is.

### Wat er ná de fix uit komt

Alle vier de toestanden, alle zes de breedtes, op de bundel van 57.518 bytes
waarvan is aangetoond dat de browser hem werkelijk laadde (zie hieronder):

| Toestand | elementen | buiten de kaart | buiten de pop-up | tekst buiten de kaart | platgeknepen |
|---|---|---|---|---|---|
| A. lijst, 5 wekkers | 87 | 0 | 0 | 0 | 0 |
| B. bevestiging, naam van 46 tekens in één woord | 91 | 0 | 0 | 0 | 0 |
| C. editor, bestaande wekker | 49 | 0 | 0 | 0 | 0 |
| D. editor **met lopend voorbeeld**, drie knoppen | 49 | 0 | 0 | 0 | 0 |

Breedtes: 430, 390, 360, 320, 280 en 244 px frame — kaart 394 tot 208 px.
Screenshots `4-na-verwijderknop-binnen-390px.jpg` en
`5-na-bevestiging-244px-popup.jpg`.

De drie knoppen van D op 390 px, ter vergelijking met fase 8:

```
"Voorbeeld stoppen"   35 → 186   (regel 1)
"Annuleren"          258 → 355   (regel 1)
"Opslaan"            270 → 355   (regel 2)
kaart                 18 → 372
```

### Dat de container queries in de pop-up aankomen

Taak C vraagt dit expliciet, want het is een stil faalgeval. Gemeten aan het
tijdveld, dat onder een kaartbreedte van 300 px kleiner hoort te worden:

```
frame 360  kaart 324  ->  font-size 24px
frame 320  kaart 284  ->  font-size 20px   <-- de @container-regel vuurt
frame 244  kaart 208  ->  font-size 20px
```

De omslag zit tussen kaart 324 en 284, precies waar `@container domotiapp-editor
(max-width: 300px)` hem hoort te leggen. **In een echte Bubble Card-pop-up werken
de benoemde container queries van fase 8 dus gewoon.**

### Bewijs dat er verse code gemeten is

Niet met een `fetch` (valkuil 4 en 62) maar met wat de browser werkelijk binnenhaalde:

```
performance.getEntriesByType('resource')  ->  decodedBodySize 57518
                                              transferSize    57471  (dus niet uit cache)
bestand op schijf                         ->  57518 bytes
resource-URL na herstart                  ->  ?v=3f7271ea29d4  (= de nieuwe hash)
```

Voorafgaand zijn alle `file-cache`-entries van de kaart, de rig en de views
verwijderd, plus de gecachte index, plus de service worker afgemeld.

### De kliks

De pop-up is **programmatisch** geopend, langs HA's eigen navigatieweg
(`pushState` + `location-changed`) — de reden staat bij taak A. Alles daarbinnen is
met **echte kliks** gedaan; de eerste is met een hit-test op `elementFromPoint`
gecontroleerd en landde op `domotiapp-alarm-card`, en de listener zag
`isTrusted: true`. Coördinaten zijn omgerekend van CSS naar screenshotpixels met
factor 1568/1920 = 0,8167 (valkuil 43).

**Valkuil 61 nagelopen:** zes openingen over drie rijen, waaronder **twee keer
achter elkaar dezelfde prullenbak** en daarna die van een **andere rij**. Uitkomst:
tweede klik op dezelfde knop laat de bevestiging staan (idempotent, geen vastloper),
klik op een andere rij verplaatst hem — er is altijd **precies één** bevestiging en
er valt niets buiten. Geen enkele klik ging verloren; er zweeft sinds fase 7 dan ook
niets meer boven de kaart.

Het scrollen naar knoppen onder de vouw was `scrollIntoView()`, dus programmatisch
(valkuil 11); de kliks erna niet.

**De snapclients zijn geteld vóór de voorbeeldmeting** (valkuil 47): precies één
met `hostID wekker-slaapkamer`. Na het stoppen van het voorbeeld stond de lamp weer
op `off` en de speaker op `idle`, met het volume terug op 0,55.

---

## Het tijdveld — wat ik wel en niet heb kunnen vaststellen

**Het is niet gereproduceerd.** In een echte Bubble Card-pop-up, op alle breedtes
van 430 tot 244 px:

```
frame 390  ->  tijdveld 320 px breed, font 24 px, scrollWidth == clientWidth
frame 244  ->  tijdveld 174 px breed, font 20 px, scrollWidth == clientWidth
```

Verder is gemeten hoeveel ruimte het veld werkelijk **nodig** heeft, door het
tijdelijk op `width: min-content` te zetten:

| font-size | benodigde breedte |
|---|---|
| 16 px | 101 px |
| 20 px | 115 px |
| 24 px | 129 px |
| 28 px | 143 px |
| 32 px | 158 px |
| 36 px | 172 px |

Op 390 px is er **320 px beschikbaar en 129 px nodig** — een factor 2,5. Zelfs op
36 px lettergrootte past het. Op deze renderer kán de tijd niet afkappen, bij geen
enkele breedte en geen enkele lettergrootte die ik kan zetten.

Wat daarmee overblijft als verschil met de telefoon van de eigenaar is precies wat
de rig **niet** nabootst: de telefoon tekent `<input type="time">` zelf, en dat is
een ander ding dan wat Chrome op Windows tekent.

**Twee vragen aan de eigenaar**, en de tweede is de goedkoopste:

1. Een screenshot van de editor op je telefoon **met de ontwikkelaarstools open**
   op het tijdveld (`getBoundingClientRect`, `font-size`, `padding`), zodat er
   getallen tegenover deze getallen staan.
2. **Zie je de andere reparaties van fase 8 wél?** Wikkelt de voetregel
   ("Voorbeeld / Annuleren / Opslaan" over twee regels als ze niet passen), en is
   het zoekveld breed genoeg om in te lezen? Zo **niet**, dan draait je telefoon een
   oude bundel achter een nieuwe `?v=` — valkuil 62 — en is dát het antwoord, niet
   de opmaak. In dat geval: op de telefoon de site-gegevens van HA wissen en
   opnieuw laden.

Ik heb bewust **niets** aan het tijdveld veranderd. Fase 8 heeft daar al een keer
uit voorzorg aan gesleuteld zonder gemeten fout; dat nog een keer doen maakt de
code moeilijker zonder dat iemand kan zien of het hielp.

---

## Taak C — De reparatie

In `src/domotiapp-alarm-card.js`, op `.onderrij` — de rij die zowel de melding met
"Begrepen" als de verwijderbevestiging draagt:

```css
.onderrij            { flex-wrap: wrap; }
.onderrij .boodschap { flex: 1 1 8em; min-width: 0; overflow-wrap: anywhere; }
```

Drie keuzes, elk met een reden:

1. **`flex-wrap: wrap`** — dezelfde keuze als fase 8 voor de voetregel, en om
   dezelfde reden: een korter label helpt maar tot de volgende lettergrootte,
   wikkelen werkt bij elke breedte.
2. **`flex: 1 1 8em`** in plaats van `flex: 1`. Gemeten: met basis `8em` is de
   boodschap op 244 px **174 px** breed, met basis `0%` maar **82 px** — een kolom
   van een paar tekens breed. Geen afsnijding, wel onleesbaar.
3. **`overflow-wrap: anywhere`** — een wekkernaam is invoer van de klant en heeft
   geen bovengrens. Zonder deze regel loopt een lange naam uit zijn eigen element.

Er stond in de eerste opzet ook `flex: 0 0 auto` op `button.tekstknop`, geleend van
fase 8. **Die is er weer uit**; zie de mutatieproef.

---

## Taak E — De tests, eerlijk

**Er is geen unittest die deze bevinding vangt, en die kan er ook niet zijn.** De
fout is opmaak: hij bestaat pas als een echte browser een echte cascade toepast op
een echte breedte. CLAUDE.md verbiedt jsdom juist omdat dat een schijnbewijs
oplevert, en een test die de CSS-*tekst* controleert bewijst alleen dat er staat wat
er staat.

Wat er wél is gedaan:

- **327 Python-tests en 85 JS-tests draaien groen** op de nieuwe code. Ze draaiden
  ook groen op de oude — dat is geen tekortkoming van de tests maar de vaststelling
  dat deze laag buiten hun bereik ligt.
- **Het bewijs komt uit taak B en C**: gemeten posities, vóór en ná, in de conditie
  die telt, op een bundel waarvan is aangetoond dat de browser hem laadde.
- **De meetfunctie is het herbruikbare stuk geworden** (`scripts/meet-afsnijden.js`)
  en is zelf onderwerp van ronde 2 van de mutatieproef.

Labels, voor de volledigheid: er zijn **nul** nieuwe tests, dus nul NIEUW GEDRAG en
nul REGRESSIEWACHT. De regressiewacht op deze fix is de meetopstelling, en die is
daarom vastgelegd in plaats van weggegooid.

---

## De mutatieproef

Uitgevoerd in de browser, want daar zit het gedrag. Een mutatie is een `<style>` in
de shadow root van de kaart die één regel van de fix terugdraait; daarna draait
`meet()` in de toestand "bevestiging open op een wekker met een naam van 46 tekens
in één woord", op 244 px frame (kaart 208 px).

**Twee valkuilen liepen we hierbij zelf in, en dat is het vermelden waard.**

*Eerst:* de eerste zeven mutaties gaven allemaal "0 buiten de kaart", ook de mutatie
die de héle fix terugdraaide. De injectie won de cascade niet — lit gebruikt
`adoptedStyleSheets` en die gaan vóór een `<style>` in de shadow root. Zonder
`!important` heeft geen enkele mutatie iets gedaan. Een mutatieproef waarin niets
verandert ziet er precies zo uit als een mutatieproef die alles vangt.

*Daarna:* één mutatiestylesheet bleef hangen doordat de aanroep die hem moest
opruimen in een time-out liep. De metingen daarna gebeurden bovenop de vólledig
teruggedraaide CSS — en dat leverde een "bevinding" op die er geen was. Dat is
valkuil 35 (de juiste uitkomst om de verkeerde reden), nu in de meetopstelling zelf.
Het harnas controleert sindsdien vóór **en** na elke mutatie dat de basis schoon is,
en elke uitkomst hieronder draagt die twee vinkjes.

### Ronde 1 — draait de fix zelf iets waarneembaars?

| | Mutatie | Gevangen |
|---|---|---|
| M1 | `flex-wrap` terug naar `nowrap` | **ja** — 2 px buiten de kaart op 244 px (op 390 px niet) |
| M2 | `min-width: 0` terug naar `auto` | nee — zie hieronder |
| M3 | `overflow-wrap` terug naar `normal` | **ja** — 93 px tekst voorbij de kaart |
| M7 | **alles** van fase 9 terug = de code van `main` | **ja** — 27 px buiten de kaart, 1 element buiten de pop-up. Dit is de **positieve controle**: het reproduceert de oorspronkelijke bevinding op de cijfer nauwkeurig |

### Ronde 2 — de regels waarvan ik zou moeten toegeven dat ik ze niet toets

| | Mutatie | Gevangen | Wat het betekent |
|---|---|---|---|
| M4 | knoppen mogen krimpen (`flex: 1 1 auto`) | nee | zie M11 |
| M5 | boodschap terug naar `flex: 1 1 0%` | nee | **geen afsnijding, wel onleesbaar**: 82 px in plaats van 174 px. De meetfunctie vraagt "valt er iets buiten" en dit valt daar niet onder. Apart gemeten en in de code vastgelegd |
| M6 | `white-space` op de knop weg | nee | bestaande code, geen onderdeel van deze fix; zonder `nowrap` breekt de knoptekst binnen de knop af en valt er niets buiten |
| M8 | `overflow-wrap` **én** `min-width` beide weg | **ja** — 93 px, en nu valt het **element zelf** buiten de kaart én de pop-up | dit is het antwoord op M2 |
| M11 | `flex: 0 0 auto` op de knop **weghalen** (terug naar de standaard `0 1 auto`) | nee, op 390, 244 én 180 px | **regel geschrapt** |

### De uitkomsten, langs valkuil 34

**M3 — een testgat in de meetfunctie, niet in de code.** Zonder `overflow-wrap`
loopt de tekst uit zijn eigen element: `clientWidth 174, scrollWidth 284`, dus
110 px tekst buiten het element en 93 px voorbij de kaart — terwijl de
**rechthoekvergelijking niets meldde**, want het element zelf blijft staan waar het
stond. Dat is valkuil 63 in spiegelbeeld: daar vond `scrollWidth` te weinig en was
de rect het antwoord, hier andersom. `meet-afsnijden.js` heeft er daarom een derde
controle bij gekregen, met als maat niet "loopt de tekst uit zijn element" (dat doet
in een flexindeling van alles een paar pixels) maar **"eindigt de tekst buiten de
kaart"**. Elementen die met `overflow: hidden` en een ellips met opzet afkappen —
`.naam` in de wekkerlijst — vallen er expliciet buiten; zonder die filter meldde de
eerste versie er dertien op een rij, allemaal terecht afgekapt.

**M2 — een equivalente mutant** (valkuil 34, vierde uitkomst). `min-width: auto`
betekent "niet kleiner dan je min-content", en met `overflow-wrap: anywhere` ís de
min-content van die tekst één teken. Zolang de zusterregel er staat, doen `auto` en
`0` hetzelfde. **M8 laat zien dat het geen dode code is**: haal ze allebei weg en het
is erger dan alleen `overflow-wrap` weghalen — dan valt het element zelf buiten de
pop-up in plaats van alleen de tekst. Dus: niets doen, en het narekenen opschrijven.

**M11 — onbereikbare code, dus de regel is eruit.** `flex: 0 0 auto` op
`button.tekstknop` is uit fase 8 overgenomen, waar het voor de voetregel wél nodig
was. Hier niet, en dat is narekenbaar: deze knoppen dragen `white-space: nowrap`, en
flexbox kan een knop die niet mag afbreken niet onder zijn tekstbreedte knijpen — er
valt niets te krimpen. Gemeten op 390, 244 en 180 px: geen enkele positie verandert.
Valkuil 34 derde rij zegt dan niet "verzin een test" maar "haal de regel weg", met de
meting in een comment. Dat is gebeurd.

**Eindstand: 11 mutaties, 4 gevangen, 1 regel geschrapt, 1 controle toegevoegd aan
de meetfunctie, 5 nagerekend en verantwoord.**

---

## Taak D — Wat er is vastgelegd

| Wat | Waar |
|---|---|
| de view in de dev-instance | `/fase-4a/bubble-echt` — echte pop-up, standalone formaat |
| hoe je de hele opstelling opnieuw bouwt | `scripts/bubble-meetopstelling.md` |
| de telefoonrig | `scripts/telefoon.html` |
| de meetfunctie | `scripts/meet-afsnijden.js` |
| de werkafspraak | CLAUDE.md, plus valkuilen 66 t/m 69 |

Op de instance staan **vijf** wekkers, waaronder
**"Zaterdagochtendzwemtraining"**. Die naam is geen grap: hij is wat de bevinding
blootlegde, en hij hoort te blijven staan.

---

## Wat niet lukte

1. **Het tijdveld is niet gereproduceerd.** Zie de eigen sectie hierboven. Er staan
   twee vragen open bij de eigenaar; de tweede kan het probleem verplaatsen van de
   opmaak naar de cache.
2. **Het browservenster is niet te verkleinen.** Het tabblad rendert buiten beeld op
   een vaste viewport van 1920 px. De rig lost dat op, maar bootst geen touch, geen
   `devicePixelRatio` en geen native tijdweergave na.
3. **Geen echte telefoon.** Dat blijft de enige plek waar de laatste onbekende zit.
4. **De pop-up gaat programmatisch open.** Een echte klik op de Bubble-knop werkt
   niet binnen de rig zolang HA's navigatie op het hoofdvenster mikt; met
   `name="ha-main-window"` op het frame kwam de navigatie wél op de goede plek
   terecht, maar het openen in de metingen hierboven is bewust langs HA's eigen weg
   gedaan zodat elke meting op dezelfde manier begint. Alles binnen de pop-up is met
   echte kliks bediend.
5. **Bubble Card bouwt de pop-up alleen als de hash bij het laden aanwezig is** en
   breekt hem bij het sluiten af. Een meetronde die de pop-up sluit, moet het frame
   opnieuw laden. Staat in de meetopstelling.

---

## Aannames

1. **De pop-up is nagebouwd op wat de eigenaar heeft gezegd**, niet op wat ik
   aannam: standalone formaat zonder `vertical-stack` (zijn opmerking),
   sections-weergave op een telefoon, standaardinstellingen. Hij heeft de exacte
   yaml niet gegeven; die van `scripts/bubble-meetopstelling.md` is de eenvoudigste
   vorm die daaraan voldoet.
2. **390 px is de meetconditie** (iPhone 12–16 in portret). Er is óók op 430, 360,
   320, 280 en 244 px gemeten, dus de keuze bepaalt niet de uitkomst.
3. **De wekker met de lange naam is toegevoegd om de rij te belasten.** Een
   wekkernaam is vrije invoer en de bevestiging citeert hem; dat was niet gevraagd,
   maar zonder zo'n naam breekt de rij pas onder 276 px kaartbreedte en zou de
   bevinding op de telefoon van de eigenaar onvindbaar zijn gebleven.
4. **De meetfunctie is uitgebreid tijdens de ronde** (de derde controle uit M3). Dat
   verandert de meting van fase 8 met terugwerkende kracht niet, maar het betekent
   wel dat de "0 van 57" van toen met minder gereedschap is vastgesteld dan de "0
   van 91" van nu.
5. **`flex: 1 1 8em` is een leesbaarheidskeuze**, geen afsnijdingsreparatie, en is
   als zodanig apart gemeten (174 tegenover 82 px).

---

## `git status --porcelain`

Vlak vóór de commit, op branch `fase-9/bubble-card`:

```
 M CLAUDE.md
 M custom_components/domotiapp_alarm/frontend/domotiapp-alarm-card.js
 M src/domotiapp-alarm-card.js
?? docs/fase-9/
?? scripts/bubble-meetopstelling.md
?? scripts/meet-afsnijden.js
?? scripts/telefoon.html
```
