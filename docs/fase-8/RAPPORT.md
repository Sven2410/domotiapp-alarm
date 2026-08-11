# Fase 8 — Afsnijden in een bubble card, en het voorbeeld toont ook de lamp

De eigenaar draait de kaart in een bubble pop-up op zijn telefoon en heeft twee
dingen gevonden.

---

## Samenvatting

| | Wat het was | Wat het nu is |
|---|---|---|
| **Bevinding 1** | de knoppenrij liep de kaart uit en het zoekveld werd platgeknepen | de voetregel **wikkelt**, de zoekrij wikkelt, en de kaart past zich aan zijn **eigen** breedte aan. Gemeten bij 244 px: **0 van de 57 elementen** valt nog buiten de kaart |
| **Bevinding 2** | het voorbeeld speelde alleen geluid | het zet ook de wake-up light aan, en zet hem bij het stoppen terug. Live: `uit → 100 % → uit`, en `128 → 255 → 128` |

**327 Python-tests** (was 326 op `main`, 314 vóór deze ronde… zie hieronder),
**85 JS-tests**. **14 mutaties in twee rondes, alle 14 gevangen** na drie gaten,
waarvan er één onbereikbare code bleek en tot het schrappen van een regel leidde.
Bundel van 51.714 naar **55.503 bytes**.

*Aantallen precies: `main` had 314 Python-tests; deze ronde voegt er 13 toe.*

---

## Bevinding 1 — Twee dingen worden afgesneden

### De meetconditie

Fase 4c meet op **373 px** (`grid_options: {columns: 9}`). Een bubble card is
smaller, dus er is een view bijgekomen met `columns: 6` → **gemeten 244 px**. Alle
metingen hieronder komen uit die conditie, tenzij anders vermeld.

### Wat er kapot was, gemeten

De methode uit fase 4c is `scrollWidth > clientWidth`. **Die vindt dit geval
niet**, en dat is de eerste les van deze ronde:

```
.voet          clientWidth 244   scrollWidth 244    (geen overloop!)
button.knop    left 767          right 864
ha-card        left 833          right 1079
```

De voetregel meldt geen overloop, maar de knop "Voorbeeld" begint op **767** bij
een kaart die op **833** begint: **67 px buiten de linkerrand**. Oorzaak:
`.voet` is `justify-content: flex-end`, dus de overloop spilt naar **links**, en
`scrollWidth` meet in een LTR-document alleen overloop naar **rechts**.

De juiste meting is de rechthoek van elk element vergelijken met die van de kaart.
Dat is wat er nu gebeurt, over **alle** elementen van de editor, en het leverde
meteen een derde probleem op dat niet gemeld was:

```
zoekrij (212 px):  input "Zoek media"  27 px
                   select "Alles"     127 px
                   knop vergrootglas   42 px
```

Een zoekveld van **27 px**. Je ziet niet wat je typt. Ook dit is met
`scrollWidth` onzichtbaar, want het veld is leeg en er is dus niets om over te
lopen — het is *platgeknepen*, niet *afgesneden*.

En in dezelfde conditie bleek de **lijst** (niet de editor, dus buiten de melding)
net zo stuk: de naam werd tot één letter geknepen — gemeten `.naam` breedte **10
px** — en de herhaaldagen stapelden verticaal. Zie
`docs/fase-8/1-voor-lijst-244px.jpg`.

### Wat er gerepareerd is, en waarom zo

**1. De voetregel wikkelt.** `flex-wrap: wrap` plus `flex: 0 0 auto` op de
knoppen.

De opdracht liet de keuze tussen een korter label, wikkelen of een andere
indeling. Gekozen: **wikkelen**, om twee redenen. Een korter label ("Stoppen")
verliest betekenis naast Annuleren en Opslaan — stoppen wát? — en het helpt maar
tot de volgende lettergrootte; wie groot leest heeft hetzelfde probleem weer.
Wikkelen werkt bij **elke** breedte en elke tekstgrootte. `flex: 0 0 auto` hoort
erbij: zonder dat knijpt flexbox de knoppen eerst plat vóór hij wikkelt, en dan
staat de tekst tegen de rand van zijn eigen knop.

**2. De zoekrij wikkelt**, met `flex: 1 1 8em; min-width: 8em` op het veld. Onder
de ondergrens gaat de soortkiezer met het vergrootglas naar de volgende regel in
plaats van dat het veld verdwijnt.

**3. De kaart en de editor meten zich aan hun EIGEN breedte.** Beide krijgen
`container: <naam> / inline-size` en een `@container`-regel voor kleinere cijfers
onder de 300 px. Een media query zou hier precies het verkeerde meten: in een
bubble pop-up is de kaart smal terwijl het **venster** breed is.

Twee dingen die daarbij misgingen en die het opschrijven waard zijn:

- **`container-type` doet niets op een inline element.** Gemeten: HA geeft de
  kaarthost `display: inline`, en dan wordt de host geen query-container en komt de
  regel nooit aan bod — zonder fout, zonder waarschuwing. `display: block` erbij is
  hier geen opmaakvoorkeur maar een voorwaarde.
- **Een naamloze `@container` kan bij de buurman uitkomen.** Zonder naam pakt de
  browser de dichtstbijzijnde container-voorouder, en dat kan er een van HA zelf
  zijn. Beide containers hebben nu een naam.

### De meting erna, bij 244 px

| | vóór | ná |
|---|---|---|
| elementen buiten de kaart (57 onderzocht) | 1 (`button.knop.voorbeeld`, 67 px links) | **0** |
| zoekveld | 27 px | **212 px**, op een eigen regel |
| tijdveld | 24 px lettergrootte, `padding: 10px` | **20 px**, `padding: 10px 12px` |
| naam in de lijst | 10 px ("S") | leesbaar met ellips ("Werk…"), tijd op 22 px |

Met een **spelend voorbeeld** staan er drie knoppen, en die passen:

```
"Voorbeeld stoppen"  850 → 1001   (regel 1)
"Annuleren"          872 →  969   (regel 2)
"Opslaan"            977 → 1062   (regel 2)
kaart                834 → 1078
```

`kapot: []` over alle 57 elementen, mét de drie knoppen in beeld. Screenshot:
`docs/fase-8/3-editor-met-voorbeeld-en-lamp.jpg`; de lijst vóór en ná staat in
`1-voor-lijst-244px.jpg` en `2-na-lijst-244px.jpg`.

### Over het tijdveld, eerlijk

De eigenaar meldde dat de tijd tegen de rand van het veld loopt. **Dat heb ik niet
kunnen reproduceren**: bij 244 px houdt "05:20" op 24 px nog **130 px** over
binnen zijn veld. Wat er wél is: de cijfers staan op 10 px van de rand en de
browser tekent dit veld zelf — op een telefoon is dat een breder ding dan op een
desktop, en dat kan ik hier niet nabootsen.

De wijziging is daarom **voorzorg en geen reparatie van een gemeten fout**: meer
horizontale ruimte (`10px 12px`) en kleinere cijfers onder de 300 px. Beide
gemeten vóór en ná.

---

## Bevinding 2 — Het voorbeeld toont de lamp

Het voorbeeld zet nu ook de wake-up light aan, op de ingestelde helderheid, als er
een lamp gekozen is. Bij het stoppen gaat hij terug zoals hij stond.

### De regels, alle drie geleend van het volume

1. **Lezen vóór zetten.** Erna lees je je eigen waarde terug.
2. **Niet te lezen is niets terugzetten.** Een lamp die weg of `unavailable` is
   heeft geen leesbare stand, en `turn_off` sturen zou een keuze maken die we niet
   kennen.
3. **Niet aangezet is niet terugzetten.** Geen lamp gekozen betekent dat er geen
   enkele lamp wordt aangeraakt.

**Wat er bewaard wordt is minimaal**: aan of uit, en de helderheid. Geen kleur,
geen kleurtemperatuur, geen effect — die bewaren zou betekenen dat we ze ook
moeten kunnen terugzetten, en een half herstelde kleur is erger dan een helderheid
die terugkomt.

**De lamp gaat aan ná het geluid**, omgekeerd aan een wekker. Bij een wekker staat
de lamp vóór het geluid omdat `play_media` 2,1–2,6 s blokkeert; bij een voorbeeld
zou een mislukt afspelen anders een lamp laten flitsen die meteen weer uitgaat.
Het scheelt ook een derde terugzetting in het faalpad.

**De lamp wordt gekeurd zoals bij het opslaan.** `preview/start` haalt hem door
`valideer_light` en `is_wekkerlamp` — dezelfde functies als `alarms/save`. Zonder
die controle is het voorbeeld een afstandsbediening voor elke lamp in huis.

### De livemeting

Beide keren met echte kliks (`isTrusted: true`), op de dev-instance met
`light.bed_light`:

| Manier van stoppen | vóór | tijdens | ná |
|---|---|---|---|
| **stopknop** | `off` | `on`, brightness **255** (100 %) | `off` |
| **Annuleren** | `on`, brightness **128** | `on`, brightness **255** | `on`, brightness **128** |

De tweede meting is de sterkste: de lamp komt terug op **precies** zijn oude
helderheid, niet alleen op "aan". Het volume ging in beide gevallen mee terug
(0,20 → 0,55) en de speaker stond daarna op `idle`.

### Elke manier van beëindigen

Gevraagd om te controleren dat óók het wegvallen van de verbinding de lamp
terugzet. Dat is het geval, en het is geen toeval: alle manieren komen uit bij
`voorbeeld.async_stop`, en het terugzetten staat daar en niet in de
afmeldcallback. Er zijn drie routes en alle drie hebben een test:

| Route | Test |
|---|---|
| afmelden (stopknop, opslaan, annuleren, X, Escape) | `test_stoppen_zet_de_lamp_terug_zoals_hij_stond` |
| verbinding valt weg (tabblad dicht, wifi weg) | `test_een_weggevallen_verbinding_zet_de_lamp_ook_terug` |
| de maximumtimer van vijf minuten | `test_het_maximum_zet_de_lamp_ook_terug` |

De tweede sluit het tabblad écht af (`client.close()`) in plaats van netjes af te
melden.

---

## De tests

**327 Python-tests**, **85 JS-tests**. Dertien nieuwe tests, allemaal in
`tests/test_voorbeeld.py`.

| Test | Label |
|---|---|
| `test_het_voorbeeld_zet_de_lamp_aan_op_de_ingestelde_helderheid` | NIEUW GEDRAG |
| `test_de_lamp_gaat_na_het_geluid_aan` | NIEUW GEDRAG |
| `test_stoppen_zet_de_lamp_terug_zoals_hij_stond` | NIEUW GEDRAG |
| `test_een_lamp_die_aan_stond_gaat_terug_naar_zijn_helderheid` | NIEUW GEDRAG |
| `test_een_onleesbare_lampstand_wordt_niet_teruggezet` | NIEUW GEDRAG |
| `test_een_falende_lamp_laat_het_geluid_gewoon_spelen` | NIEUW GEDRAG |
| `test_een_weggevallen_verbinding_zet_de_lamp_ook_terug` | NIEUW GEDRAG |
| `test_het_maximum_zet_de_lamp_ook_terug` | NIEUW GEDRAG |
| `test_een_lamp_zonder_label_wordt_geweigerd` | NIEUW GEDRAG |
| `test_een_helderheid_buiten_bereik_wordt_geweigerd` | NIEUW GEDRAG |
| `test_een_helderheid_die_geen_getal_is_telt_als_onbekend` | NIEUW GEDRAG |
| `test_een_voorbeeld_zonder_lamp_raakt_geen_enkele_lamp_aan` | **REGRESSIEWACHT** |
| `test_een_mislukt_voorbeeld_laat_de_lamp_met_rust` | **REGRESSIEWACHT** |

### Gedraaid op de code van vóór de fix

`custom_components/` en `src/` teruggezet naar `main`, de tests laten staan:

```
FAILED tests/test_voorbeeld.py::test_het_voorbeeld_zet_de_lamp_aan_op_de_ingestelde_helderheid
FAILED tests/test_voorbeeld.py::test_de_lamp_gaat_na_het_geluid_aan
FAILED tests/test_voorbeeld.py::test_stoppen_zet_de_lamp_terug_zoals_hij_stond
FAILED tests/test_voorbeeld.py::test_een_lamp_die_aan_stond_gaat_terug_naar_zijn_helderheid
FAILED tests/test_voorbeeld.py::test_een_onleesbare_lampstand_wordt_niet_teruggezet
FAILED tests/test_voorbeeld.py::test_een_falende_lamp_laat_het_geluid_gewoon_spelen
FAILED tests/test_voorbeeld.py::test_een_weggevallen_verbinding_zet_de_lamp_ook_terug
FAILED tests/test_voorbeeld.py::test_het_maximum_zet_de_lamp_ook_terug
FAILED tests/test_voorbeeld.py::test_een_lamp_zonder_label_wordt_geweigerd
9 failed, 17 passed
```

**Twee tests zijn ná die run bijgesteld.** `test_een_mislukt_voorbeeld_laat_de_lamp_met_rust`
slaagde daar triviaal (er wordt op de oude code sowieso geen lamp aangeraakt) en is
naar REGRESSIEWACHT gegaan. `test_een_helderheid_buiten_bereik_wordt_geweigerd`
slaagde daar om de **verkeerde reden** — `light` was toen een onbekende sleutel, dus
de fout ging over iets anders. Die assertie kijkt nu naar de tekst van de fout.

De opmaakwijzigingen van bevinding 1 hebben **geen** unittests: het is CSS, en
CLAUDE.md verbiedt jsdom. Die kant is met gemeten posities in de browser
vastgelegd.

---

## De mutatieproef

`scripts/mutaties-fase-8.py`. **Ronde 1: 10 mutaties, 8 gevangen. Ronde 2: 5
mutaties op de randen, 3 gevangen.** Eindstand: **14 van de 14**, na het dichten
van twee gaten en het **schrappen** van één regel.

| | Mutatie | Gevangen |
|---|---|---|
| M1 | het voorbeeld zet de lamp helemaal niet aan | ja |
| M2 | de lamp gaat aan zonder helderheid | ja |
| M3 | de lamp blijft na het voorbeeld branden | ja |
| M4 | **een onleesbare stand wordt tóch teruggezet** | **NEE → gedicht** |
| M5 | een lamp die uit stond blijft aan | ja |
| M6 | de oude helderheid gaat verloren | ja |
| M7 | de oude stand wordt gelezen maar niet bewaard | ja |
| M8 | een `unavailable` lamp levert toch een stand op | ja |
| M9 | elke lamp in huis is via het voorbeeld aan te zetten | ja |
| M10 | de lamp gaat ongekeurd door naar `light.turn_on` | ja |
| M11 | *(vervallen — zie hieronder)* | — |
| M12 | de bewaarde stand wordt overschreven met een vaste "uit" | ja |
| M13 | **een helderheid die geen getal is gaat zo door** | **NEE → gedicht** |
| M14 | een falende lamp breekt het voorbeeld alsnog af | ja |
| M15 | de lamp-aanroep valt weg maar de context blijft | ja |

### De drie uitkomsten, en ze zijn alle drie anders

**M4 — een testgat dat over een logregel gaat.** Zonder de `stand is None`-controle
gooit `stand["aan"]` een `TypeError`, die de `except` opvangt: de klant merkt
niets, maar er staat een `WARNING` in het log dat het terugzetten **mislukt** is
terwijl er niets te doen was. Dat is dezelfde soort onwaarheid als de meldingen uit
fase 6 en 6b, nu in een logregel. De test let er nu op dat die waarschuwing er niet
staat.

**M13 — een verdediging tegen data van een ánder.** `brightness` is een attribuut
van een `light` die niet van ons is; HA typeert hem als `int | None` maar dwingt
niets af. Zonder de `isinstance` gaat een `"128"` zo naar `light.turn_on`. Geen
enkele test bood zo'n waarde aan, want alle tests gebruiken ons eigen testdubbel.
Dit is valkuil 59, opnieuw.

**M11 — onbereikbare code, dus de regel is eruit.** De controle op een lege
`entity_id` werd niet gevangen, en narekenen wees uit waarom: de enige weg naar
`_async_lamp_aan` is `preview/start`, en die haalt de lamp door `valideer_light`,
die een `entity_id` in het `light.`-domein eist en anders `invalid_format` geeft.
Er is dus geen invoer waarbij die regel iets verandert. Volgens valkuil 34, derde
rij, is het antwoord dan **niet** een test verzinnen maar de regel schrappen, met
de meting in een comment. Dat is gedaan; de mutatie is uit het script gehaald.

---

## Wat niet lukte

**1. Het tijdveld is niet gereproduceerd.** Zie hierboven: bij 244 px houdt de tijd
130 px over binnen zijn veld. De wijziging is voorzorg. Om dit echt te toetsen is
een telefoon nodig — de native tijdweergave is precies wat een desktopbrowser
anders tekent.

**2. Geen echte bubble card.** De meetconditie is `grid_options: {columns: 6}` →
244 px, wat **smaller** is dan een bubble pop-up op een telefoon (~330 px). Dat is
met opzet strenger dan de werkelijkheid, maar het is niet dezelfde component: een
bubble card brengt eigen CSS mee die ik hier niet heb.

**3. Geen echte telefoon**, dus geen touch-doelen, geen schermtoetsenbord en niet
de lettergrootte-instelling van de klant.

**4. De breedtesweep werkte niet.** Ik wilde per element vaststellen bij wélke
breedte het breekt, door de kaart programmatisch te versmallen. Dat lukt niet: de
kaartbreedte komt uit het sections-grid en `style.width` op de host wordt
overschreven. De metingen komen daarom uit twee vaste condities (373 en 244 px) en
niet uit een sweep.

---

## Aannames

1. **De lijst is óók gerepareerd**, terwijl de melding over de editor ging. In
   dezelfde bubble-conditie was de naam 10 px breed en stapelden de dagen
   verticaal; dat op `main` laten staan terwijl de editor ernaast wél klopt, zou de
   eigenaar meteen zien. De wijziging is één container query.
2. **De zoekrij is óók gerepareerd.** Niet gemeld, wel gemeten (27 px zoekveld), en
   het valt onder de opdracht om de héle editor te meten.
3. **De lamp gaat aan ná het geluid** in plaats van ervoor. De redenering staat in
   SPEC 5.4 en in de code; het verschil is de 2,1–2,6 s die `play_media` blokkeert.
4. **`preview/start` keurt de lamp** met dezelfde functies als `alarms/save`. Niet
   gevraagd, wel nodig: zonder die controle zet het voorbeeld elke lamp in huis aan.
5. **Kleur en kleurtemperatuur worden niet bewaard en niet teruggezet.** Alleen aan
   of uit en de helderheid. Vastgelegd in SPEC 5.4.

---

## `git status --porcelain`

Vlak vóór de commit, op branch `fase-8/bubble-en-voorbeeld`:

```
 M CLAUDE.md
 M SPEC.md
 M custom_components/domotiapp_alarm/frontend/domotiapp-alarm-card.js
 M custom_components/domotiapp_alarm/voorbeeld.py
 M custom_components/domotiapp_alarm/websocket.py
 M src/domotiapp-alarm-card.js
 M src/editor.js
 M tests/conftest.py
 M tests/test_voorbeeld.py
?? docs/fase-8/
?? scripts/mutaties-fase-8.py
```

Ná de commit en de push: leeg.
