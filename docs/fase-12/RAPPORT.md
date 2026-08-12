# Fase 12 — De speakerdropdown is wit geworden

## Samenvatting

| | |
|---|---|
| **De oorzaak** | fase 10 zette `background: transparent` op de control. Voor een `input` klopt dat; voor een **select** niet — de browser tekent het uitklappaneel met de `background-color` van de select zélf, en transparant betekent daar "val terug op wit" |
| **Hoe erg** | gemeten op 1.1.0: `background-color: rgba(0, 0, 0, 0)` met `color: rgb(225, 225, 225)`. Wit op wit, bij **alle drie** de dropdowns |
| **De reparatie** | de select en zijn opties krijgen een eigen, opake achtergrond uit het thema; het gemarkeerde item krijgt de accentkleur |
| **Contrast ná** | gewoon item **13 : 1**, gemarkeerd item **5,5 : 1** (WCAG AA vraagt 4,5) |
| **Fase 10 intact** | ja — padding `0px/0px` en rand `0px/0px` op elk control, tijdveld met marges 17/17 px |
| **Native select behouden** | ja, en de afweging staat hieronder |

**346 Python- en 86 JS-tests**, geen nieuwe: de fout is opmaak. Wél een nieuwe
**bewaker** (`npm run check:controls`) die in CI meedraait en die aantoonbaar
faalt op de code van 1.1.0. **9 mutaties in twee rondes, 8 gevangen**; de negende
was zelf fout. Bundel van 62.902 naar **65.033 bytes**.

---

## Wat er aan de hand was

De screenshots van de eigenaar staan in deze map als `0-melding-*.jpeg`. Het
uitklappaneel is wit, de items zijn onzichtbaar, en alleen de gemarkeerde regel
is leesbaar — die krijgt van de browser een eigen lichtblauwe balk met donkere
tekst overheen.

**De aanname uit de opdracht is nagemeten en klopte**, maar niet helemaal in de
gegeven bewoording. Het uitklappaneel valt inderdaad buiten de shadow root, maar
het pakt niet zomaar "de standaardkleuren van de browser": het pakt de
`background-color` **van de select zelf**, en die stond op transparant. Gemeten in
de kaart van 1.1.0, in de Bubble Card-conditie:

```
speaker   background-color rgba(0, 0, 0, 0)   color rgb(225, 225, 225)
Soort     background-color rgba(0, 0, 0, 0)   color rgb(225, 225, 225)
lamp      background-color rgba(0, 0, 0, 0)   color rgb(225, 225, 225)
```

Dat geldt ook voor elke `option` afzonderlijk. **Alle drie** de dropdowns waren
dus stuk, niet alleen die van de speakers — precies wat de opdracht liet nagaan.

De regel die het veroorzaakte staat in fase 10:

```css
.vak input, .vak select { … background: transparent; … }
```

Voor een `input` is dat juist: het vak eronder levert de achtergrond. Voor een
`select` is het dat niet, omdat er een paneel bestaat dat niet in het vak zit.

---

## De keuze: native select houden

De opdracht vroeg af te wegen of een **eigen keuzelijst** hier niet veiliger is,
met fase 10 als argument (native controls zijn de plek waar een desktopmeting
niet overdraagt). Ik houd de native `select`, om drie redenen:

1. **Het probleem is hier niet "native gedraagt zich per platform anders", maar
   "wij hebben de kleur weggehaald".** Vóór fase 10 was deze dropdown donker en
   leesbaar, met exact dezelfde native control. De regressie is van ons, en de
   reparatie zet terug wat er was.
2. **Waar `option`-opmaak wordt genegeerd, is de vervanger juist beter.** Op iOS
   en Android tekent het systeem een eigen kiezer die altijd leesbaar is en die
   met één duim te bedienen is. Een eigen lijst zou dat weggooien — en fase 10
   liet zien dat we op die platformen niets kunnen meten. Minder native betekent
   hier dus **meer** onverifieerbaar oppervlak, niet minder.
3. **Een eigen zwevende lijst is precies de constructie die dit project al twee
   keer heeft moeten repareren.** Valkuil 57 (HA heeft geen bruikbare
   menu-component), valkuil 58 (een zwevend menu steekt onder de kaart uit) en
   valkuil 60 (een klikvangende laag) gaan alle drie over zelfgebouwde overlays
   in een pop-up. Dat opnieuw bouwen voor drie keuzelijsten is een slechte ruil.

**Wat een browser met het paneel doet, is wel nagegaan.** Op Chrome/Windows
worden `option`-kleuren toegepast — dat is hieronder zichtbaar gemaakt. Op
macOS en op mobiel tekent het systeem de kiezer en worden ze grotendeels
genegeerd; daar was en is de lijst leesbaar omdat het systeem zijn eigen
contrast bewaakt. De reparatie kan daar dus niets breken.

---

## De reparatie

In `src/editor.js`:

```css
.vak input  { background: transparent; }          /* geen paneel, mag doorzichtig */
.vak select { background-color: var(--card-background-color, #fff); }
.vak select option {
  background-color: var(--card-background-color, #fff);
  color: var(--primary-text-color);
}
.vak select option:checked {
  background-color: var(--domotiapp-accent);
  color: #fff;
}
```

Drie dingen die daarbij horen:

- **De regel voor `input` en `select` is gesplitst.** Eerst stond de nieuwe
  achtergrond ná de gedeelde `transparent`-regel en overschreef hem. Dat werkt,
  maar dan zegt de code twee dingen die elkaar tegenspreken. Nu is aan de regel
  zelf te zien welke keuze waar geldt — en de bewaker hieronder kan er iets
  zinnigs over zeggen.
- **Kleuren komen uit themavariabelen**, en `#026FA1` (`--domotiapp-accent`)
  komt alleen voor op het gemarkeerde item. Dat is dezelfde behandeling die de
  aangevinkte dagknoppen al hadden, en het is een accent zoals SPEC 1.1 het
  bedoelt.
- **Fase 10 blijft staan**: er komt geen padding en geen rand op de control. Een
  achtergrondkleur is geen van beide, dus valkuil 70 wordt niet geraakt.

**SPEC is niet gewijzigd.** De constructie verandert niet: het zijn nog steeds
dezelfde controls in dezelfde vakken, met dezelfde laadketen. Alleen de kleuren
zijn teruggezet.

---

## De browserverificatie

Gemeten in de **Bubble Card-conditie** van fase 9 (`/fase-4a/bubble-echt` via
`scripts/telefoon.html` op 390 px), op de bundel van 65.033 bytes waarvan is
aangetoond dat de browser hem van het netwerk haalde (`decodedBodySize` 64732
bij de meetronde, `transferSize` > 0).

### 1 en 2. Elke dropdown leesbaar, met de gemeten kleuren

| dropdown | select-achtergrond | itemkleur | gemarkeerd item |
|---|---|---|---|
| speaker | `rgb(28, 28, 28)` | `rgb(225, 225, 225)` | `rgb(2, 111, 161)` op `rgb(255, 255, 255)` |
| Soort | `rgb(28, 28, 28)` | `rgb(225, 225, 225)` | `rgb(2, 111, 161)` op `rgb(255, 255, 255)` |
| lamp | `rgb(28, 28, 28)` | `rgb(225, 225, 225)` | `rgb(2, 111, 161)` op `rgb(255, 255, 255)` |

`rgb(2, 111, 161)` is `#026FA1`. Contrastverhoudingen, berekend uit die waarden:

```
gewoon item      13,0 : 1
gemarkeerd item   5,5 : 1
WCAG AA vraagt    4,5 : 1
```

### 3. Binnen de pop-up op een smalle breedte

Over zes breedtes, met de positie van elke select erbij:

```
430: kaart=394  buitenKaart=0 buitenPopup=0  selects=[338@46-384, 105@229-334, 338@46-384]
390: kaart=354  buitenKaart=0 buitenPopup=0  selects=[298@46-344, 105@189-294, 298@46-344]
360: kaart=324  buitenKaart=0 buitenPopup=0  selects=[268@46-314, 105@209-314, 268@46-314]
320: kaart=284  buitenKaart=0 buitenPopup=0  selects=[228@46-274, 105@46-151,  228@46-274]
280: kaart=244  buitenKaart=0 buitenPopup=0  selects=[188@46-234, 105@46-151,  188@46-234]
244: kaart=208  buitenKaart=0 buitenPopup=0  selects=[152@46-198, 105@46-151,  152@46-198]
```

Ook `tekstLooptUit` en `teBreed` zijn overal 0.

### 4. Fase 10 is niet teruggedraaid

```
select (3×), input[time], input[text] (2×), input[range] (2×)
   padding 0px/0px      rand 0px/0px

tijdveld   marge links 17 px   marge rechts 17 px
           border-top-right-radius 6px   border-right-width 1px
           text-align center
```

### De kliks

De editor is geopend met een **echte klik** op een wekkerrij, en de speakerselect
met een **echte klik**: de listener op `mousedown` gaf `isTrusted: true`.

**Wat niet lukte: het uitgeklapte paneel staat niet op een screenshot.** Chrome
tekent dat paneel als een venster van het besturingssysteem, en de
screenshotfunctie van de browsertool legt alleen de pagina vast — het paneel is
er dus niet op te zien, ook al is het open. Dat is de buurman van valkuil 49.

**Wat er in de plaats is gedaan, en waarom het telt.** Met een **probe** is
tijdelijk `size` op de drie selects gezet. Dan rendert de engine dezelfde
optie-rijen ín de pagina, met dezelfde `option`-regels, en dát legt een
screenshot wél vast: `1-na-speaker-en-soort-leesbaar.jpg` en
`2-na-alle-drie-de-lijsten.jpg`. Daarop is te zien wat de tabel hierboven meet —
lichte tekst op de donkere kaartkleur, en het gekozen item op de accentkleur. De
probe is daarna teruggedraaid en de meting erna was weer schoon (0 buiten de
kaart). Het is een probe en geen bewijs van het paneel zelf; dat staat er zo bij.

---

## De tests

**Er is geen unittest die dit vangt, en dat kan ook niet** — dezelfde
vaststelling als in fase 9 en 10. De fout bestaat pas als een echte browser een
echte cascade toepast, jsdom is verboden en heeft geen layout, en `editor.js` is
in Node niet te importeren (het definieert een `LitElement` en `HTMLElement`
bestaat daar niet).

- **346 Python- en 86 JS-tests** draaien groen op de nieuwe code. Ze draaiden ook
  groen op de kapotte code; dat is geen tekortkoming van de tests maar de
  vaststelling dat deze laag buiten hun bereik ligt.
- **Nul nieuwe tests**, dus nul NIEUW GEDRAG en nul REGRESSIEWACHT.

**Wel een nieuwe bewaker.** `scripts/check-controls.mjs` draait mee in CI
(`npm run check:controls`) en bewaakt drie dingen in de bron: elke `<select>`
staat in een `.vak` (de eis van fase 10), select én opties hebben een eigen
`background-color` uit een variabele, en er staat nergens meer een select op
transparant. Dit is dezelfde soort bewaker als `check-registratie.mjs` bij
valkuil 1: zwakker dan een meting, maar het is de enige bescherming die
automatisch kan draaien.

Aangetoond dat hij faalt op de code van 1.1.0:

```
FOUT in de opmaak van de formuliercontrols:
  - .vak select mist een eigen background-color
  - .vak select option mist een eigen background-color
  - .vak select option:checked mist een markering
  - een .vak select staat op background transparent — dat is de fout van fase 12
exit=1
```

en slaagt op de nieuwe:

```
OK: 3 select(s), elk in een .vak, met een eigen achtergrondkleur en een markering.
```

**Wat hij níét bewijst:** dat de kleuren leesbaar zíjn. Hij kijkt of de regel er
staat, niet wat de cascade ervan maakt. Dat staat in de meting hierboven.

---

## De mutatieproef

Uitgevoerd in de browser, tegen een meetfunctie die per `option` het contrast
tussen achtergrond en tekst uitrekent en alles onder 4,5 : 1 of met alpha 0
afkeurt. Harnas met dezelfde guards als in fase 9 en 11: schoon vóór **en** na
elke mutatie.

### Ronde 1 — doet de reparatie iets, en zie je het?

| | Mutatie | Gevangen |
|---|---|---|
| M1 | select én opties weer doorzichtig (= de bug van 1.1.0) | **ja** — 6× DOORZICHTIG |
| M2 | alleen de select opaak, opties doorzichtig | **ja** |
| M3 | de accentmarkering weg | **ja** — het gemarkeerde item wordt doorzichtig |
| M4 | optietekst gelijk aan de achtergrond | **ja** — contrast 1 |

M1 is de positieve controle: hij reproduceert precies de melding van de eigenaar.

### Ronde 2 — de randen waarvan ik zou moeten toegeven dat ik ze niet toets

| | Mutatie | Gevangen | Wat het betekent |
|---|---|---|---|
| M5 | een thema **zonder** `--card-background-color` (terugval `#fff`) | **ja** — contrast 1,3 | zie hieronder |
| M6 | een thema **zonder** `--primary-text-color` | **ja** — contrast 4,2 | net onder AA, en alleen op de accentregel |
| M7 | een licht thema (witte achtergrond, donkere tekst) | **nee** | **de mutatie was zelf fout**: dat ís leesbaar (≈16 : 1). Vervangen door M7-bis |
| M7-bis | witte achtergrond met lichte tekst | **ja** — contrast 1,3 | |
| M8 | de soortkiezer (`.vak.auto`) valt buiten de regel | **ja** | de selector `.vak select` reikt aantoonbaar tot de derde dropdown |

**M5 en M6 zijn geen gaten maar een bekende zwakte, en die hoort genoemd.** De
terugval `var(--card-background-color, #fff)` zet een **lichte** achtergrond neer,
terwijl `color: var(--primary-text-color)` zonder terugval de kleur laat erven.
Ontbreekt alleen de eerste variabele, dan staat er lichte tekst op wit. Dat is
niet nieuw — de rest van de kaart doet het al zo sinds fase 4b, en Home Assistant
definieert beide variabelen altijd. Ik heb het daarom **niet** gewijzigd: dat zou
één plek anders maken dan de twintig andere en de inconsistentie is erger dan het
hypothetische geval. Het staat hier zodat een volgende ronde het bewust kan
oppakken.

**M7 is het vermelden waard omdat de mutatie zelf de fout was**, niet de code —
dezelfde uitkomst als één mutatie in fase 7. Ik had hem gelabeld als "donker op
donker" maar wit-op-donker geschreven. Verbeterd tot M7-bis, en die wordt wél
gevangen.

**Eindstand: 9 mutaties, 8 gevangen, 1 mutatie zelf fout en vervangen.**

---

## Wat niet lukte

1. **Het uitgeklapte paneel staat niet op een screenshot.** Chrome tekent het als
   een OS-venster; de browsertool legt alleen de pagina vast. De `size`-probe is
   de vervanger en dat staat er zo bij.
2. **De Bubble-pop-up ging deze ronde niet open.** Hij bouwt wel en de kaart zit
   erin — de horizontale maten zijn daardoor geldig en gelijk aan die van een
   open pop-up (kaart 18 → 372 in een pop-up van 0 → 390, zoals fase 10 al
   vaststelde) — maar de openingsanimatie voltooide niet. De **kleurmetingen**
   zijn in die conditie gedaan, de **screenshots** op `/fase-4a/smal`. Beide
   condities zijn opgeschreven bij wat waar gemeten is.
3. **Alleen Chrome op Windows.** Dat macOS en mobiel de `option`-opmaak negeren
   is beredeneerd uit hoe die platformen de kiezer tekenen, niet gemeten. Het
   risico is klein: daar bewaakt het systeem het contrast zelf, en vóór fase 10
   werkte dezelfde constructie.
4. **Geen unittest.** Zie de testsectie.

## Aannames

1. **De reparatie zet terug wat er vóór fase 10 was**, in plaats van iets nieuws
   te bedenken. Dat is bewust: de dropdown was toen leesbaar en de klant heeft er
   nooit over geklaagd.
2. **`--card-background-color` is de juiste variabele** voor het paneel. Het is de
   kleur van het vlak waar de control in staat, en het is wat de kaart overal
   gebruikt.
3. **`option:checked` is de goede haak voor het gemarkeerde item.** Chrome past
   hem toe op de geselecteerde regel; op platformen waar het systeem de kiezer
   tekent doet hij niets, en daar markeert het systeem zelf.
4. **De `size`-probe rendert dezelfde optie-rijen als het paneel.** Dat is de
   aanname onder de screenshots. Ze gebruiken dezelfde `option`-regels en dezelfde
   engine, maar het is niet hetzelfde renderpad.

## `git status --porcelain`

Vlak vóór de commit, op branch `fase-12/dropdown`:

```
 M .github/workflows/ci.yml
 M CLAUDE.md
 M custom_components/domotiapp_alarm/frontend/domotiapp-alarm-card.js
 M package.json
 M src/editor.js
?? docs/fase-12/
?? scripts/check-controls.mjs
```
