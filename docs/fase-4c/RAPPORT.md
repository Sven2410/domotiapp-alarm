# Fase 4c — Twee SPEC-gaten dichten en het zoekveld op mobiel

Twee gaten die fase 4b als openstaand punt achterliet, plus één bevinding van de
eigenaar. Beide gaten hadden dezelfde vorm: **de server wist iets wat de kaart
nodig had en gaf het niet door**, waarna de kaart een keuze maakte die soms
onwaar was.

---

## De bevinding — het zoekveld op een telefoon

De eigenaar zag de placeholder afkappen tot "Zoek in Music As". Dat is nagemeten
op een kaart van **373 px** (een iPhone SE is 375, een Galaxy S8 360):

| | breedte | past in 132 px? |
|---|---|---|
| oude placeholder `Zoek in Music Assistant…` | **159 px** | **nee** |
| nieuwe placeholder `Zoek media` | **73 px** | ja, met 59 px over |

De 132 px is de werkelijke binnenruimte van het invoerveld op die breedte,
gemeten met `clientWidth` minus de padding; de tekstbreedtes zijn gemeten met
`measureText` in het lettertype van het veld zelf.

De knop "Zoeken" is een **vergrootglas** geworden (`mdi:magnify`), 42 px breed in
plaats van de tekstbreedte. Hij houdt zijn betekenis voor schermlezers in
`aria-label="Zoeken"` én `title="Zoeken"`; `textContent` is leeg.

### De rest van de editor kapt niet af

Nagelopen op dezelfde 373 px, met `scrollWidth > clientWidth` over **elk**
element in de editor plus een aparte meting per placeholder:

```
overlopende_elementen: []
placeholders:
  "Bijvoorbeeld: Werk"  116 px in 317 px  -> past
  "Zoek media"           73 px in 132 px  -> past
```

Er is dus **niets anders gerepareerd**, conform de opdracht. Wat wél opviel en
hier als waarneming staat: op **200 px** (de kaart op 6 van de 12 kolommen, wat
smaller is dan elke telefoon) kappen de wekkernamen in de lijst wél af tot "T.",
"W", "S". Dat is `text-overflow: ellipsis` die zijn werk doet en geen defect —
bij 373 px staan alle namen er voluit.

---

## Gat 1 — `sound/search` geeft `SIMILAR_TRACKS` niet terug

### Wat er mis was

SPEC 8.3.1 beperkt de waarschuwing *"Dit geluid stopt van zichzelf"* tot geluiden
waarvan de provider `SIMILAR_TRACKS` **niet** ondersteunt. Kan de provider het
wel, dan gaat `radio_mode` mee en speelt MA eindeloos door — en dan is de
waarschuwing onwaar.

De kaart kon dat onderscheid niet maken en waarschuwde op `media_type` alleen.
Een los nummer van Spotify kreeg dus te horen dat het geluid van zichzelf stopt,
terwijl het juist doorspeelt. **Een waarschuwing die soms onwaar is, is er een
die mensen leren negeren** — en dan werkt hij ook niet meer in de gevallen
waarvoor hij bedoeld is.

### Wat er nu staat

`sound/search` geeft per treffer **`endless`** terug: een boolean die zegt of het
geluid eindeloos doorspeelt. De editor toont de waarschuwing wanneer die `false`
is, en interpreteert verder niets.

`true` bij **een** van twee onafhankelijke redenen:

| Reden | Voorbeeld |
|---|---|
| de **soort** houdt uit zichzelf niet op: `radio` of `playlist` | `radiobrowser://radio/…` |
| **`radio_mode`** gaat mee, dus MA speelt door in dezelfde stijl | `spotify--…://track/…` |

**Dezelfde bron als het afvuren.** `radiomodus.blijft_doorspelen()` staat naast
`stuur_radio_mode_mee()` en leest dezelfde `SIMILAR_TRACKS_PROVIDERS`. Dat is de
kern van de oplossing en niet een detail: zou de kaart die lijst óók hebben, dan
bestaat hij twee keer en kan de editor *"dit speelt door"* beloven terwijl
`afvuren.py` `radio_mode` weglaat. Fase 3a-bis legde vast dat die lijst **stil**
kan verouderen; één lijst betekent dat hij ook maar op één plek fout kan staan.
Er staat een test op die die twee antwoorden aan elkaar knoopt.

Bij twijfel — onbekend URI-schema, lege URI, ontbrekende soort — is het `false`,
dus waarschuwen. Dat is de goede kant om fout te zitten: hinderlijk in plaats van
een belofte dat het geluid doorspeelt terwijl het na drie minuten stopt.

### Wat er bewust niet in de opslag staat

`endless` is een eigenschap van de **provider**, niet van de keuze, en kan
veranderen zonder dat de klant iets doet. `sound` houdt zijn vier velden
(SPEC 8.2). Gevolg, en het is aanvaard: opent de klant een **bestaande** wekker,
dan weet de editor het niet en waarschuwt hij niet. De waarschuwing hoort bij het
**kiezen** van een geluid, en daar is het veld er wel.

---

## Gat 2 — `entities/list` maakte twee meldingen niet onderscheidbaar

SPEC 7.4 kent drie situaties met elk een eigen melding. Er waren drie situaties
en twee signalen:

| Situatie | `label_exists` | `entities` | `filtered_out` |
|---|---|---|---|
| het label bestaat niet | `false` | leeg | 0 |
| het label bestaat, er hangt niets aan | `true` | leeg | **0** |
| er hing wél iets aan, maar het viel af op 7.2 | `true` | leeg | **> 0** |

De onderste twee zagen er identiek uit. Voor de eigenaar zijn het twee heel
verschillende boodschappen — *"zet het label op je speakers"* tegenover *"die
speakers zijn geen Music Assistant-speakers"* — en dus twee verschillende
handelingen.

`entities/list` geeft nu **`filtered_out`** terug: het aantal gelabelde
entiteiten dat is afgevallen. Een **getal** en geen lijst met redenen: de melding
van SPEC 7.4 is één zin die alle afvalredenen samenvat, en de reden per entiteit
staat al op `DEBUG` in het log. Een lijst zou de kaart uitnodigen er zelf zinnen
van te maken, en dan staat de uitleg op twee plekken.

Ook bij de **lampen**, waar de enige eis het domein is: een `Verlichting
Wekker`-label op iets dat geen lamp is, telt mee en levert een eigen tekst op.

---

## Tests

| | vóór 4c | na 4c |
|---|---|---|
| JS (`node --test`, geen jsdom) | 74 | **77** |
| Python | 238 | **264** |

Alle nieuwe tests zijn **NIEUW GEDRAG**. Drie bestaande tests zijn aangepast
omdat het gedrag veranderde: de sleutels van `conceptVan` (er kwam `endless` bij),
de aanroepvorm van `eindigeDuurWaarschuwing`, en de twee `entities/list`-tests
die nu ook `filtered_out` verwachten.

### De drie verplichte gevallen

1. **Provider mét `SIMILAR_TRACKS` geeft geen waarschuwing, zonder wel** —
   `test_blijft_doorspelen_per_soort_en_provider`, met van elke soort een paar
   `spotify` / `somafm`. Een implementatie die alleen naar de soort kijkt faalt op
   het eerste paar, een die alleen naar de provider kijkt op het radio-paar.
2. **Drie situaties, drie uitkomsten** — `test_de_drie_situaties_zijn_onderscheidbaar`
   toetst niet drie losse waarden maar dat de drie **kenmerken verschillen**; een
   implementatie die `filtered_out` altijd op 0 zet komt door de losse tests heen
   en faalt hier. Aan de kaartkant doet
   `onderscheidt de drie situaties uit SPEC 7.4` hetzelfde met een `Set`-grootte.
3. **Radio en afspeellijst waarschuwen nooit, ongeacht de provider** — vier rijen
   in dezelfde tabel, twee providers × twee soorten.

### Falen op de oude code

`test_spec_gaten.py` tegen `main`:

```
E   AttributeError: module '…radiomodus' has no attribute 'blijft_doorspelen'
E   KeyError: 'filtered_out'
E   AssertionError: Right contains 1 more item: {'filtered_out': 2}
```

Het eerste is triviaal (de functie is nieuw); het tweede en derde zijn dat niet —
daar bestaat de code wél en levert ze het veld niet.

`editorlogica.test.mjs` tegen `main`: **0 van 77 geslaagd**, want de
functiesignaturen zijn veranderd. Triviaal, en dat staat hier zo in plaats van
als bewijs opgevoerd.

### De mutatie-oefening: 23 mutaties, twee rondes

**Ronde 1 ving 18 van de 18** die van toepassing waren. Zoals in 4a en 4b is dat
een reden voor argwaan (valkuil 46), dus volgde een tweede ronde die naar gaten
zocht.

| | Mutatie | Uitkomst |
|---|---|---|
| A1–A7 | `blijft_doorspelen`: elk van de twee redenen apart weghalen, de soortenlijst wijzigen, `endless` hardcoderen of op `stuur_radio_mode_mee` alleen baseren | gevangen |
| B1–B4 | `filtered_out` niet tellen, een verkeerde standaard, altijd 0 teruggeven, de lampen niet tellen | gevangen |
| C1–C6 | de waarschuwing omdraaien, altijd/nooit tonen, de `filtered_out`-tak uitschakelen, de "er valt te kiezen"-tak weghalen | gevangen |
| C8, C9 | twee van de drie meldingen weer op één tekst gooien | gevangen |
| **C7 → C10, C11** | het uitlezen van `endless` uit een treffer | **NIET GEVANGEN → deels gerepareerd** |
| **A8** | `isinstance(media_type, str)` → `media_type is not None and str(...)` | **NIET GEVANGEN — equivalente mutant** |

**C7 was een echt gat, en het wees iets structureels aan.** Het uitlezen van
`endless` stond in `editor.js` — de renderlaag, die per CLAUDE.md geen
unittests heeft (geen jsdom). Dat is precies het criterium uit CLAUDE.md: *kan ik
dit gedrag in een gewone Node-test opschrijven? Zo nee, dan staat het op de
verkeerde plek.* Het antwoord was ja, dus is het `endlessVan()` geworden in
`editorlogica.js`, met eigen tests. Mutatie C10 op de nieuwe functie wordt nu
**wel** gevangen.

Wat blijft: **C11**, de *aanroep* van `endlessVan` in de renderlaag, wordt niet
door een unittest gevangen. Dat is de grens van wat unittests hier kunnen
bereiken en het is bewust zo — het net eronder is de browsermeting, punt 2
hieronder.

**A8 is een equivalente mutant**, en dat is een vierde uitkomst die de tabel van
valkuil 34 niet kent. Nagerekend: de twee varianten verschillen alleen voor een
`media_type` dat géén `str` is maar waarvan `str()` exact `"radio"` of
`"playlist"` oplevert. Over de WebSocket is alles JSON, dus `str` of `null`; uit
MA's service-antwoord komt hooguit een `StrEnum`, en die ís een `str`. Er is geen
bereikbare invoer waarbij het verschil maakt. Geen test erbij (die zou dekking
suggereren die er niet is) en niets weggehaald (de controle zelf is wél nodig —
mutatie A2, die hem helemaal weghaalt, wordt gevangen).

**Wat A8 wél opleverde is een vraag die alleen live te beantwoorden was:** wat
voor type ís `media_type` op het moment dat `_plat` het ziet? Zou het een Enum
zijn die geen `str` is, dan zou radio `endless: false` krijgen en waarschuwen —
precies de fout die deze fase repareert. Dat is gemeten; zie hieronder.

---

## Browserverificatie

Verse code bewezen vóór er iets gemeten is: service worker afgemeld, drie caches
gewist, één harde herlaadbeurt. Bundel op schijf en door HA geserveerd
byte-identiek — **52.129 bytes**, sha256 `4e0febfb…71ddc`, en `?v=4e0febfb156a`
is de prefix van diezelfde hash.

**De vraag uit mutatie A8, live beantwoord.** Een echte zoekopdracht op de
dev-instance:

| soort | provider | `endless` |
|---|---|---|
| `radio` | `radiobrowser` (géén `SIMILAR_TRACKS`) | **true** |
| `podcast` | `itunes_podcasts` (géén `SIMILAR_TRACKS`) | **false** |

Radio krijgt `true` van de **soort**-tak, en dat kan alleen als
`isinstance(media_type, str)` waar was. MA levert dus een echte `str`. De
typecontrole doet in productie wat hij hoort te doen.

### 1. Het zoekveld op een smal scherm

Het browservenster stond gemaximaliseerd en liet zich niet verkleinen. In plaats
daarvan is de **kaart** op telefoonbreedte gezet met een echte Lovelace-indeling
— een sections-view met `grid_options: {columns: 9}`, wat 373 px oplevert. Dat is
geen stijltruc: het is de layoutmachinerie die de kaart op een telefoon ook
gebruikt, en de gemeten breedte ligt tussen die van een Galaxy S8 (360) en een
Pixel 7 (412).

Screenshot `01-zoekveld-op-telefoonbreedte.jpg`: "Zoek media" staat er voluit, het
vergrootglas ernaast. De metingen staan bovenaan dit rapport.

Het vergrootglas is met een echte klik bediend (`isTrusted: true`), en de klik
droeg `aria-label: "Zoeken"` en `title: "Zoeken"` — het label dat een schermlezer
voorleest. Met een zoekterm erin leverde dezelfde knop 23 treffers.

### 2. Een treffer mét en zonder eindeloos doorspelen

Twee echte kliks in dezelfde resultatenlijst:

| gekozen | `endless` | waarschuwing |
|---|---|---|
| `SomaFM Beat Blender (128k AAC)` (radio) | `true` | **geen** — 0 waarschuwingen in de DOM |
| `RADIO RADIO` (podcast) | `false` | **wel**, letterlijk de tekst uit SPEC 8.3 |

De waarschuwing stond in `rgb(155, 155, 155)` — secondary, geen foutkleur — en
blokkeerde niets. Screenshot `02-waarschuwing-bij-podcast.jpg`.

**Wat hier niet live te tonen was:** dezelfde *soort* bij twee verschillende
providers. Op deze instance is geen streamingprovider gekoppeld — Spotify werkt
niet achter Docker Desktop (fase 0b) — dus `spotify://track/…` bestaat hier
niet. De provider-as is daarom met unittests gedekt
(`test_blijft_doorspelen_per_soort_en_provider`), en live is de soort-as
aangetoond. Dat onderscheid staat hier omdat het het verschil is tussen wat
gemeten is en wat beredeneerd is.

### 3. De drie meldingen uit SPEC 7.4

De labels zijn tijdelijk verzet. Wat `entities/list` per situatie teruggaf, en wat
de editor daarvan maakte:

| situatie | antwoord | gerenderde melding |
|---|---|---|
| label weg | `label_exists: false, entities: [], filtered_out: 0` | "Het label 'Music Assistant Wekker' bestaat nog niet. De beheerder moet dat label aanmaken en op de speakers zetten die als wekker mogen dienen." |
| label leeg | `label_exists: true, entities: [], filtered_out: 0` | "Er zijn nog geen speakers met het label 'Music Assistant Wekker'." |
| alles valt af | `label_exists: true, entities: [], filtered_out: 1` | "De gelabelde speakers zijn geen Music Assistant-speakers, of ze kunnen geen volume instellen." |

Voor de derde is het label op `media_player.wekkergroep` gezet — een MA-groep, die
op SPEC 7.3 afvalt. In alle drie de gevallen: `rgb(155, 155, 155)` (geen
foutkleur), **Opslaan uitgeschakeld**, en **geen speakerkiezer** — precies wat
SPEC 7.4 voorschrijft. Screenshot `03-spec-7-4-situatie-3.jpg`.

**De labels zijn naderhand teruggezet en dat is geverifieerd**, niet aangenomen:
dezelfde twee `label_id`'s (`music_assistant_wekker`, `verlichting_wekker`),
dezelfde entiteiten eraan (`media_player.wekker_slaapkamer` en
`light.bed_light`), en `filtered_out: 0` voor beide. Het enige verschil met de
beginstand is de **volgorde** waarin het label-register ze teruggeeft; dat is
invoegvolgorde en heeft geen betekenis.

Het openen van de editor is bij deze drie **programmatisch** gedaan
(`_openEditor`), zodat de drie situaties achter elkaar door konden. Dat de
plusknop met een echte klik opent is in fase 4b gemeten en in punt 1 hierboven
opnieuw. De `entities/list`-aanroep en het renderen zijn in alle drie de gevallen
echt.

**Console:** na een herlaadbeurt met de consolelezer actief geen enkel bericht.

---

## Wat niet lukte

**1. Het browservenster liet zich niet verkleinen.** `resize_window` meldde succes
maar `innerWidth` bleef 1920 — het venster was gemaximaliseerd. De uitweg (de
kaart via `grid_options` op 373 px) meet dezelfde conditie, want de placeholder
kapte af doordat de **kaart** smal was en niet doordat het venster smal was. Wat
er níét mee gemeten is: hoe HA's eigen chrome (zijbalk, koptekst) zich op een
echte telefoon gedraagt.

**2. De provider-as van `endless` is niet live aangetoond**, alleen de soort-as.
Er is geen streamingprovider op deze instance; dat is een bekende beperking sinds
fase 0b. Unittests dekken het.

**3. De waarschuwing bij een bestaande wekker blijft weg.** Dat is een bewuste
keuze (zie gat 1), geen omissie — maar het betekent dat een klant die een oude
wekker met een los nummer opent, de waarschuwing niet ziet. Wie hem daar ook wil,
moet `endless` in de opslag zetten of `alarms/get` het laten meesturen; beide zijn
grotere wijzigingen dan deze ronde toestond.

**4. C11 blijft ongevangen door unittests** — de aanroep van `endlessVan` in de
renderlaag. Dat is de grens van wat zonder jsdom te toetsen is; de browsermeting
van punt 2 is het net eronder.

---

## Aannames

1. **De veldnaam is `endless`.** De opdracht vroeg "één veld dat zegt of het
   geluid eindeloos zal doorspelen"; de naam is een keuze.
2. **`playlist` telt als eindeloos.** Een afspeellijst is niet oneindig maar wel
   van onbepaalde duur, en in de praktijk langer dan de stoptimer van 30 minuten.
   SPEC 8.3 noemt radio en afspeellijst samen als "de soorten die bij een wekker
   passen".
3. **`artist` en `album` tellen als eindig.** Ze staan niet in SPEC 8.3's lijstje
   met eindige soorten (`track`, `podcast`, `audiobook`), maar ze houden wel op.
   SPEC 8.3.1 is hierop bijgewerkt.
4. **`filtered_out` is een getal en geen lijst met redenen** — zie gat 2.
5. **De derde SPEC 7.4-melding voor lampen is nieuw geformuleerd:** "De entiteiten
   met het label 'Verlichting Wekker' zijn geen lampen." SPEC 7.4 gaf alleen de
   speakervariant. Vastgelegd in SPEC.
6. **Het pictogram is `mdi:magnify`**, zoals de opdracht vroeg, als inline SVG en
   niet als `ha-icon` — valkuil 44/50: die component is op dit dashboard niet
   geladen.

---

## `git status --porcelain`

```
```

(schoon; alles staat in de commits van `fase-4c/spec-gaten`)
