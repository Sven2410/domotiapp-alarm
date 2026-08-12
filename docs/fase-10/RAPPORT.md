# Fase 10 — Native formuliercontrols, en waarom een desktopmeting daar niet over gaat

De eigenaar draait 1.0.3, heeft de app volledig afgesloten en opnieuw geopend, en
ziet het tijdveld op zijn iPhone nog steeds fout. Fase 9 had gemeten dat het ruim
past: 320 px beschikbaar, 129 px nodig. Deze ronde legt uit waarom die meting waar
was en toch niets zei, en haalt de hele klasse fouten weg.

---

## Samenvatting

| | |
|---|---|
| **De oorzaak** | **iOS past `box-sizing: border-box` niet toe op `input[type="time"]`.** Onze `width: 100%` gold daar voor de *content*box, en de padding en rand kwamen er bovenop: 324 px beschikbaar, **348,9 px getekend** |
| **Wat je ziet** | niet afgekapte cijfers, maar een **veld** dat te breed is: geen afgeronde rechterhoek meer, de rand loopt door tot voorbij de kaart, en de tijd staat 12,5 px uit het midden |
| **De reparatie** | rand, radius, achtergrond en padding naar een `div.vak`; de control zelf krijgt `width: 100%` en **padding 0 / rand 0**. Contentbox en borderbox zijn dan per constructie gelijk — het boxmodel doet er niet meer toe |
| **Bijvangst** | vier andere controls met dezelfde vorm nagelopen, en één **echte** tweede fout gevonden: bij een kaart van 208 px liep een zoekresultaat 16 px buiten de kaart |
| **Het gereedschap** | `meet-afsnijden.js` heeft een vierde controle: getekende breedte tegen beschikbare breedte, in plaats van alleen positie |

**327 Python- en 85 JS-tests** groen. **12 mutaties in twee rondes**, waarvan er drie
de diagnose bewijzen en één tot het schrappen van een regel leidde. Bundel van
57.518 naar **62.903 bytes**.

---

## De diagnose, uit de screenshots

De screenshot is 945 × 2048 (verhouding 0,4614 = iPhone 1179 × 2556 @3x), dus
**1 beeldpixel = 0,4159 CSS px** en het scherm is **393 CSS px** breed. Alle
getallen hieronder zijn met randdetectie op de helderheid uit het beeld gehaald,
niet geschat.

```
kaart                        CSS   18,3 → 374,7   (breedte 356,4)
binnenruimte (16px padding)  CSS   34,5 → 358,5   (breedte 324,0)

naamveld   (input[type=text])  eigen rand eindigt op   358,5   goed
speaker    (select)            eigen rand eindigt op   358,5   goed
TIJDVELD   (input[type=time])  eigen rand eindigt op   372,6   FOUT
```

Ter controle op de rig: die mat de kaart op 354 px bij een venster van 390 px. De
telefoon geeft 356,4 bij 393 px. **De rig klopte**; het lag niet aan de breedte.

**Waar de 348,9 px vandaan komt.** De cijfers lopen van 180,5 tot 237,5, dus hun
midden ligt op **209,0**. iOS centreert de waarde van een tijdveld, en de
linkerrand staat op 34,5, dus de rechterrand is `2 × 209,0 − 34,5 = 383,4`. En:

```
zoals onze CSS het bedoelde (border-box):  324,0
met padding en rand erbovenop:             324 + 2×12 + 2×1 = 350,0
gemeten:                                   348,9
```

Het veld stak daarmee **~9 px voorbij de kaartrand**, waar het werd afgeknipt — en
dat verklaart precies wat er op de foto ontbreekt: geen afgeronde rechterhoek, en
de kaartrand die op die hoogte niet te zien is omdat de achtergrond van het veld
eroverheen wordt getekend. Zie `meldingen/detail-rechterkant-tijdveld-vs-naamveld.png`:
boven het tijdveld, onder het naamveld met zijn nette hoek op 358,5.

**Dat het aan de control ligt en niet aan onze opmaak** is meetbaar: de `select`
ernaast draagt dezelfde `box-sizing` en dezelfde padding en eindigt wél op 358,5.

### De bundel was niet oud

Het zoekveld is op de foto **143 px** breed (34,5 → 177,5), met de soortkiezer en
het vergrootglas ernaast op één regel. In de kapotte staat van fase 8 was dat veld
27 px. Dat is een fase-8-markering in de screenshot zelf, dus valkuil 62 is
uitgesloten op bewijs en niet alleen op het woord van de eigenaar.

### Wat fase 9 verkeerd deed, en het was niet de meting

De meting "320 px beschikbaar, 129 px nodig" was juist. Hij beantwoordde alleen de
verkeerde vraag: hoeveel ruimte de **tekst** nodig heeft, terwijl het probleem is
hoe breed de **doos** getekend wordt. `meet-afsnijden.js` zou dit gevangen hebben —
het veld steekt 9 px buiten de kaart — maar alleen op iOS. Op Chrome is datzelfde
veld 324 px en is er niets te vinden. **Het gat zat niet in het gereedschap maar in
de engine**, en dat is precies het stuk dat de rig van fase 9 per definitie niet
dekt.

---

## Taak 1 — De hele kaart nagelopen

Het risicopatroon: **een native control met `width: 100%` dat zelf padding of een
rand draagt.** Gemeten in de pop-up op 390 px, met `box-sizing` en de werkelijke
breedtes erbij:

| control | box-sizing komt van | padding | rand | getekend / beschikbaar | oordeel |
|---|---|---|---|---|---|
| `input[type="time"]` | **onze CSS** | 12/12 | 1/1 | 320 / 320 | **het geval van de eigenaar** |
| `input[type="text"]` (naam) | **onze CSS** | 10/10 | 1/1 | 320 / 320 | zelfde vorm, zelfde risico |
| `input[type="text"]` (zoek) | **onze CSS** | 10/10 | 1/1 | 135 / 135 | zelfde vorm, zelfde risico |
| `select` (speaker, soort, lamp) | **onze CSS** | 10/10 | 1/1 | 320 / 320 | zelfde vorm, zelfde risico |
| `button.treffer` | **de UA van Chrome** | 10/10 | 0 | 303 / 303 | zelfde vorm, en wij verklaren niets |
| `button.stopknop` | **de UA van Chrome** | 16/16 | 0 | 352 / 352 | idem, en het is de knop die de wekker uitzet |
| `input[type="range"]` (2×) | content-box | 0/0 | 0/0 | 320 / 320 | **veilig** — geen padding, geen rand |

Twee dingen die hieruit volgen en die het opschrijven waard zijn:

1. **`box-sizing: border-box` declareren is geen garantie.** Wij deden dat op de
   drie bovenste rijen, en iOS negeert het bij het tijdveld. Wat wél helpt is de
   padding en de rand er niet op zetten.
2. **De schuiven laten zien dat het boxmodel niet de kwaal is.** Ze staan op
   `content-box` en zijn tóch precies 320 px, omdat er niets bij op te tellen valt.
   De padding is de kwaal.

### De reparatie

Vijf controls (tijd, naam, zoek, speaker, soort, lamp) zitten nu in een
`div.vak` die de rand, de radius, de achtergrond en de padding draagt. De control
erbinnen:

```css
.vak input, .vak select {
  display: block; width: 100%; box-sizing: border-box;
  padding: 0; border: 0; margin: 0; background: transparent;
}
```

Gemeten na de wijziging, op 390 px: het vak loopt 35 → 355 en de control 48 → 342,
met `padding 0px` en `border 0px`. De control kán niet meer breder worden dan zijn
vak, op geen enkele engine.

De twee knoppen (`.treffer`, `.stopknop`) krijgen een **expliciete**
`box-sizing: border-box` in plaats van te leunen op de UA-stylesheet van de browser.
De schuiven krijgen expliciet `padding: 0; border: 0` — niet omdat er iets mis was,
maar omdat de regel dan in de code staat en niet alleen in dit rapport.

### `text-align: center`, en wat het wel en niet oplevert

Gevraagd en gedaan. Gemeten: het midden van het vak, van de control én van de kaart
vallen alle drie op **195**, en de marge links en rechts is **17 / 17 px**.

Wat het **niet** oplevert is een gelijk beeld op desktop en telefoon, en dat hoort
er eerlijk bij. Uit dezelfde glyph-meting op een Chrome-screenshot:

```
cijfers "05:20"   CSS 145,7 → 204,5   midden 175,1
klokicoon         CSS 315,9 → 335,5
midden van de kaart              195,0     afwijking −19,9
```

Chrome tekent zelf een klokknop aan de rechterkant en centreert de waarde in wat
daarvan overblijft. iOS heeft die knop niet en centreert dus echt. **De doos is nu
op beide gelijk; het beeld erbinnen niet.**

---

## Taak 3 — De meetopstelling uitgebreid

`scripts/meet-afsnijden.js` had drie controles, en die kijken allemaal naar waar
iets **uitkomt**. Daardoor zien ze een fout pas als hij aan de buitenkant zichtbaar
wordt — en dat is per engine anders. De vierde controle meet de **oorzaak**:

> past de borderbox van het kind in de contentbox van zijn ouder?

Een element dat 26 px te breed is maar toevallig ruimte heeft, valt nergens buiten
en is met de oude controles onzichtbaar. Met deze niet.

**Twee guards zitten erin en die zijn nergens uitgeoefend**: absoluut/vast
gepositioneerde kinderen en negatieve marges worden overgeslagen. Gemeten over 148
elementen in de editor: **0 gepositioneerd, 0 met een negatieve marge**. Ze filteren
op dit moment dus niets. Ze blijven staan omdat dit een *meetinstrument* is en een
vals alarm daar duurder is dan in productiecode — de volgende ronde gaat dan een
niet-bestaande fout achterna. Maar ze zijn niet getoetst, en dat staat hier.

---

## De tweede bevinding, die niemand had gemeld

Bij het nalopen van alle toestanden bleek de **zoekresultatenlijst** nooit eerder
gemeten te zijn — fase 8 en 9 hebben nooit een zoekopdracht gedaan. Bij een kaart
van 208 px (pop-up 244 px):

```
span.soort "podcast"           16 px buiten de kaart
button.treffer                 clientWidth 157, scrollWidth 206
```

Oorzaak: de naam van een treffer is vrije tekst uit Music Assistant zonder
bovengrens, en hij kon niet krimpen. Dezelfde vorm als de bevestigingsregel van
fase 9, in een toestand die nog nooit opengezet was. Gerepareerd met `min-width: 0`
plus een ellips op de naam. Ná: 0 buiten de kaart op alle breedtes.

---

## De verificatie

Alles op bundel **62.503 bytes**, waarvan is aangetoond dat de browser hem
werkelijk laadde (`decodedBodySize` 62503 = bytes op schijf, `transferSize` > 0 dus
niet uit cache). *De uiteindelijke bundel is 62.903 bytes; het verschil is één
herschreven commentaarblok in de CSS, zonder regels.*, na het legen van de `file-cache` en het afmelden van de service
worker.

| Toestand | elementen | buiten kaart | buiten pop-up | tekst buiten kaart | te breed getekend |
|---|---|---|---|---|---|
| lijst, 5 wekkers | 72 | 0 | 0 | 0 | 0 |
| editor + 23 zoekresultaten | 148 | 0 | 0 | 0 | 0 |
| editor (zonder resultaten) | 55 | 0 | 0 | 0 | 0 |
| stoptoestand | 6 | 0 | 0 | 0 | 0 |

Breedtes: frame 430, 390, 360, 320, 280 en 244 px — kaart 394 tot 208 px.
Screenshots: `1-na-editor-390px.jpg` en `2-na-editor-244px.jpg`.

**De kliks.** De pop-up is met een **echte klik** op de Bubble-knop geopend
(`isTrusted` bevestigd via de listener), en in de editor zijn het zoekveld en de
zoekknop met echte kliks bediend. In het zoekveld is met **echte toetsaanslagen**
"Beat Blender" getypt, mét een expliciete spatie: `keydown { key: " ",
isTrusted: true }`. Het scrollen naar velden onder de vouw was `scrollIntoView()`
respectievelijk `scrollTop`, dus programmatisch (valkuil 11); de kliks erna niet.
De stoptoestand is met een **echt afgegane wekker** gemeten en met een echte klik op
de stopknop beëindigd; daarna stond de speaker op `idle`.

**Eén eerlijkheid over de laatste ronde.** Bij de allerlaatste meting (op bundel
62.503) bouwde Bubble de pop-up wel maar voltooide hij de open-animatie niet meer;
de meting is in de **gesloten** stand gedaan. Dat verandert niets aan de horizontale
maten — Bubble verplaatst de pop-up puur verticaal
(`transform: matrix(1,0,0,1,0,777)`) — en de gemeten waarden zijn dan ook tot op de
pixel gelijk aan die van de **open** pop-up eerder in de sessie: kaart 18 → 372
(354 px) in een pop-up van 0 → 390. De open staat is op bundel 61.997 volledig
doorgemeten; het enige verschil met de eindbundel is de regel die de mutatieproef
als no-op aanwees (zie M10).

---

## De tests

**Er is opnieuw geen unittest die dit vangt, en dat kan ook niet.** De fout bestaat
alleen wanneer een engine een boxmodel toepast, en de engine die hem maakt draait op
een telefoon. jsdom is verboden en zou hier bovendien niets bewijzen: het heeft geen
layout.

- **327 Python- en 85 JS-tests draaien groen** op de nieuwe code, en draaiden ook
  groen op de oude. Nul nieuwe tests, dus **nul NIEUW GEDRAG en nul
  REGRESSIEWACHT**.
- Het bewijs komt uit de metingen hierboven en uit de mutatieproef.
- De regressiewacht is de meetopstelling, en die is daarom uitgebreid in plaats van
  weggegooid.

---

## De mutatieproef

Uitgevoerd in de browser tegen `meet()`, met een harnas dat vóór **én** na elke
mutatie controleert dat de basis schoon is (valkuil 35 en 68, allebei in fase 9
zelf opgelopen). Toestand: editor open, 390 px tenzij anders vermeld.

### Ronde 1 — doet de fix iets, en zie je het?

| | Mutatie | Gevangen |
|---|---|---|
| **M1** | **iOS-boxmodel (`content-box`) op de NIEUWE opzet** | **nee — en dat ís het resultaat** |
| **M2** | **OUDE opzet + iOS-boxmodel** | **ja** — 4 buiten de kaart, 11 tekstoverlopen, 5 te breed |
| **M3** | **OUDE opzet + Chrome-boxmodel** | **nee** |
| M4 | `text-align: center` weg | nee |
| M8 | `width: 100%` van de control weg | ja — `input 159/113 (+46)` |

**Dit drietal is de kern van de ronde.** M2 reproduceert de fout van de eigenaar op
een desktop, en de getallen kloppen op de pixel met de telefoon:

```
input (tijd)     346 / 320   (+26)      <- de telefoon gaf 350 / 324 = +26
input (naam)     342 / 320   (+22)
select (speaker) 342 / 320   (+22)
input (zoek)     157 / 135   (+22)
select (lamp)    342 / 320   (+22)
```

M3 laat zien **waarom fase 8 en 9 dit nooit konden vinden**: met het boxmodel van
Chrome is de oude code aantoonbaar goed. En M1 is de positieve controle voor de
reparatie: zet het iOS-boxmodel op de nieuwe opzet en er verandert **niets**. Dat is
geen "we hebben het gerepareerd", dat is "het kan niet meer gebeuren".

### Ronde 2 — de regels waarvan ik zou moeten toegeven dat ik ze niet toets

| | Mutatie | Gevangen | Wat het betekent |
|---|---|---|---|
| M5 | treffer-naam mag niet krimpen (244 px) | ja — 26 buiten de kaart, `span 182,7/137 (+45,7)` | de reparatie van de tweede bevinding draagt |
| M6 | `.soort { flex: 0 0 auto }` weg (244 px) | **nee** | zie M10 |
| M7 | de padding van het **vak** weg | nee | maakt smaller, niet breder; geen overloop. De meting vraagt niet naar leesbaarheid |
| M9 | `.treffer` met iOS-boxmodel (244 px) | ja — alle 23 treffers `177/157 (+20)` | de expliciete `box-sizing` op `.treffer` verdient zijn plek |
| **M10** | **M5 én M6 samen** | ja, **met exact dezelfde getallen als M5** | **regel geschrapt** |
| M11 | `.stopknop` met iOS-boxmodel | *niet uitgevoerd* | de stoptoestand bestond op dat moment niet meer; alleen live gemeten (352/352) |

### De uitkomsten, langs valkuil 34

**M4 — de meting stelt deze vraag niet.** `text-align` gaat over uitlijning, niet
over breedte. Apart gemeten en hierboven vastgelegd (drie middens op 195, marges
17/17).

**M6 en M10 — onbereikbare code, dus de regel is eruit.** `flex: 0 0 auto` op
`.soort` verandert niets, ook niet in combinatie: M10 gaf tot op de tiende dezelfde
uitkomst als M5. De reden is `white-space: nowrap` — een badge die niet mag
afbreken kan door flexbox niet onder zijn tekstbreedte geknepen worden, dus er valt
niets te krimpen. Dat is **letterlijk dezelfde bevinding als M11 in fase 9**, bij
`button.tekstknop`, en dat het twee rondes op rij gebeurt is het vermelden waard:
`flex: 0 0 auto` naast `white-space: nowrap` is een reflex, geen maatregel.

**M11 — niet uitgevoerd, en dat staat er.** De `box-sizing` op `.stopknop` is alleen
live gemeten in de echte stoptoestand (352 getekend bij 352 beschikbaar, `border-box`
van de UA). Dat de expliciete declaratie hem tegen een andere UA beschermt, is
narekenbaar maar niet gemeten.

**Eindstand: 12 mutaties, 5 gevangen, 1 regel geschrapt, 1 niet uitgevoerd, 5
nagerekend en verantwoord.**

---

## Wat niet lukte

1. **De reparatie is niet op een iPhone geverifieerd.** Dat kan hier niet, en het is
   de enige stap die overblijft. De falsifieerbare toets staat hieronder.
2. **De laatste meetronde liep met een gesloten pop-up**, zie de verificatiesectie.
   Horizontaal maakt dat niets uit en dat is aangetoond, maar het is niet hoe het
   bedoeld was.
3. **De rig is wisselvallig in het openen van de pop-up.** Bubble bouwt een
   standalone pop-up alleen als de hash bij het laden aanwezig is, breekt hem bij het
   sluiten af, en bouwt hem daarna niet altijd opnieuw. Het kostte deze ronde
   meerdere volledige herlaadbeurten. Staat als aanvulling in
   `scripts/bubble-meetopstelling.md`.
4. **HA's sections-view rendert lui.** Na een harde herlaadbeurt stonden de
   bubble-kaarten er soms 15 seconden niet; een tabwissel of een klik wekt ze.
   Wachten en dan pas meten.

---

## Aannames

1. **Het scherm van de eigenaar is 393 CSS px breed.** Afgeleid uit de
   beeldverhouding (945 × 2048 → 1179 × 2556 @3x). Alle CSS-getallen uit de
   screenshots hangen aan die aanname. Dat de kaart daarmee op 356,4 px uitkomt —
   binnen 2,4 px van de 354 px die de rig bij 390 px meet — is de controle erop.
2. **iOS centreert de waarde van een tijdveld.** Daar is de veldbreedte van 348,9 px
   uit afgeleid. Het alternatief (links uitgelijnd met 146 px linkerpadding) is niet
   plausibel, maar het is een afleiding en geen directe meting.
3. **De schuiven zijn niet ingepakt.** Ze dragen geen padding en geen rand, dus het
   patroon geldt er niet voor; ze krijgen die twee nu wel expliciet op nul.
4. **De zoekresultaten zijn gerepareerd** hoewel dat niet gemeld was. Het viel onder
   de opdracht om de hele kaart na te lopen, en het was een echte overloop.
5. **`text-align: center` is meegenomen zoals gevraagd**, met de kanttekening dat
   desktop en telefoon er niet gelijk van worden — zie de meting.

---

## Voor de eigenaar: de toets op je telefoon

Twee dingen, allebei met het blote oog te zien:

1. Het tijdveld heeft rechts een **zichtbare afgeronde hoek**, net als het naamveld
   eronder.
2. De ruimte **links en rechts** van het tijdveld is even groot (op de desktop
   gemeten: 17 en 17 px).

Klopt een van beide niet, dan is de diagnose onvolledig en heb ik aan een screenshot
met de ontwikkelaarstools op dat veld genoeg.

---

## `git status --porcelain`

Vlak vóór de commit, op branch `fase-10/native-controls`:

```
 M CLAUDE.md
 M custom_components/domotiapp_alarm/frontend/domotiapp-alarm-card.js
 M scripts/bubble-meetopstelling.md
 M scripts/meet-afsnijden.js
 M src/domotiapp-alarm-card.js
 M src/editor.js
?? docs/fase-10/
```
