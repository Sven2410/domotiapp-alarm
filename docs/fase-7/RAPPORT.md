# Fase 7 — Prullenbak in plaats van menu, en overslaan eruit

Versie 1.0.1 draait bij de eigenaar. Hij meldde dat het overloopmenu "maar heel af
en toe" opent, en hij heeft het overslaan geschrapt.

---

## Samenvatting

| | Wat het was | Wat het nu is |
|---|---|---|
| **De bevinding** | het menu opende bij ongeveer de helft van de kliks niet | oorzaak gevonden en gemeten: een laag over het hele venster ving elke klik weg. Zes van de zes prullenbakkliks openen nu de bevestiging bij de eerste poging |
| **Wijziging 1** | overloopmenu met twee items | één prullenbakknop per rij, met een bevestiging die naam en tijd noemt; Annuleren doet niets |
| **Wijziging 2** | `skip_next` in commando, schema, planner, kaart | overal weg, met een migratie van schemaversie **1 → 2** |

**314 Python-tests** (was 313), **85 JS-tests** (was 89 — `menu.test.mjs` met zijn acht tests is met de module vervallen, en er zijn er vier bij gekomen). **15 mutaties in twee rondes, 14
gevangen**; de vijftiende was een verkeerd gekozen mutatie en dat staat hieronder
uitgeschreven. Bundel van 55.356 naar **51.714 bytes** — de kaart is kleiner
geworden.

---

## De bevinding — waarom het menu niet opende

Gevraagd: zoek het uit vóór je iets vervangt, want de oorzaak kan elders
terugkomen. Dat is gedaan, en de oorzaak is **niet** wat de opdracht als
mogelijkheid noemde (een lit-hertekening die de listener kwijtraakt) en ook niet
wat ik zelf als eerste vermoedde (de scroll-listener uit fase 6b).

### De meting

Menu open op rij 1, daarna een **echte klik** op de ⋮ van rij 3. Eerst de
hit-test op dat punt, vóór de klik:

```
elementFromPoint(1300, 411) →
  home-assistant › home-assistant-main › ha-panel-lovelace › hui-root ›
  hui-sections-view › hui-grid-section › domotiapp-alarm-card › div.sluiter
```

En de klik zelf, uit een capture-listener op `window`:

```json
{"isTrusted": true, "x": 1300, "y": 411,
 "raakte": "sluiter", "keten": "sluiter < SLOT < window"}
```

Uitkomst: `menuOpen: false`. De klik kwam **niet** bij de knop aan; hij landde op
`div.sluiter` en sloot alleen het openstaande menu.

De scroll-hypothese is met dezelfde meting **uitgesloten**: de tellers stonden op
`{scroll: 0, resize: 0}`. Er is niets gescrold; de listener uit fase 6b had er
niets mee te maken.

### Wat er aan de hand was

`.sluiter` is de laag die het menu afsluit als je ernaast klikt:

```css
.sluiter { position: fixed; inset: 0; z-index: 2; }
```

`inset: 0` op een `fixed` element is **het hele venster**, en `z-index: 2` legt
hem boven alles in de kaart dat geen eigen stapelcontext heeft — dus boven élke
knop. Zolang het menu openstond, was de hele kaart onklikbaar.

Vanuit de klant gezien: tik op ⋮ → menu. Tik nog eens → het menu verdwijnt en er
gebeurt verder niets. Tik op de ⋮ van een **andere** rij → hetzelfde, je krijgt
dat menu nooit. Grofweg de helft van de tikken doet zichtbaar niets, en dat is
precies *"het opent maar heel af en toe"*.

### De laag stamt uit fase 4a, niet uit 6b

```
$ git log --oneline -S "sluiter" --reverse -- src/domotiapp-alarm-card.js
d5b9990 Fase 4a: de kaart in rusttoestand en de stoptoestand
```

Fase 6b veranderde de **plaatsing** van het menu, niet de laag eronder. De fout
zat er dus vanaf het begin in.

**Waarom vier browserrondes hem niet vonden**, en dit is het deel dat blijft
gelden: elke meting opende het menu **vanuit gesloten toestand** en klikte daarna
op een menu-item. Fase 6b deed letterlijk ⋮ → item → ⋮ → item. Dat is de ene
volgorde waarin de fout zich nooit voordoet. Een klikvolgorde die alleen het
gelukkige pad afloopt, komt nooit in de toestand die vastloopt.

Als valkuil 60 en 61 in `CLAUDE.md` gezet.

---

## Wijziging 1 — Prullenbak in plaats van menu

Eén prullenbakknop per rij (`mdi:trash-can-outline`), met
`aria-label="Wekker <naam> verwijderen"`. Het menu, de laag eronder en
`src/menu.js` met zijn acht tests zijn verdwenen.

### HA's dialoogcomponent: gemeten, geprobeerd, en toch niet gebruikt

Gevraagd: gebruik HA's eigen dialoog als die er is, en controleer dat eerst — zoals
fase 6b met de menu-componenten deed. Dat is in **twee** stappen gedaan, en de
tweede is de interessante.

**Stap 1 — bestaat hij?** Ja. Verse pagina, zonder een enkele klik, en nog eens
vijf seconden later hetzelfde antwoord:

| Component | `customElements.get(...)` |
|---|---|
| `ha-dialog` | **gedefinieerd** |
| `ha-alert`, `ha-button`, `ha-icon-button` | gedefinieerd |
| `ha-md-dialog` | niet gedefinieerd |

Dat is een ánder antwoord dan fase 6b voor de menu's kreeg, dus de vraag was
terecht gesteld.

**Stap 2 — werkt hij?** Nee, niet met de aanroep die je uit HA's eigen broncode
van een jaar geleden zou overnemen. Een `ha-dialog` met `slot="primaryAction"` en
`slot="secondaryAction"` gaf een dialoog met onze tekst en een kruisje, en
**zonder knoppen**:

```json
{"dialoog": {"w": 0, "h": 0},
 "heading": "Wekker verwijderen",
 "knoppen": [{"slot": "secondaryAction", "tekst": "Annuleren",
              "rect": {"w": 0, "h": 0}, "gedefinieerd": true, "heeftShadow": true},
             {"slot": "primaryAction", "tekst": "Verwijderen",
              "rect": {"w": 0, "h": 0}, "gedefinieerd": true, "heeftShadow": true}]}
```

De knoppen zijn gedefinieerd, hebben een shadow root, en meten `0 × 0`. De oorzaak
staat in de shadow root van `ha-dialog` zelf:

```json
{"shadowKinderen": ["wa-dialog"],
 "slots": ["header", "headerNavigationIcon", "headerTitle", "headerSubtitle",
           "headerActionItems", "(default)", "footer"],
 "mwcAanwezig": {"mwcButton": false, "mwcDialog": false}}
```

**`ha-dialog` is in 2026.8 van mwc naar Web Awesome gegaan.** `primaryAction` en
`secondaryAction` bestaan niet meer; wat er is heet `footer`. Onze knoppen kwamen
in de default-slot terecht, waar de dialoog ze geen plaatsing geeft. Screenshot:
`docs/fase-7/1-ha-dialog-zonder-knoppen.jpg`.

**De keuze: een regel binnen de kaart, altijd.** Dat is een afwijking van de
opdracht en staat als aanname hieronder. De redenen, in volgorde van gewicht:

1. Het faalgeval is **stil**: een dialoog met een vraag die je niet kunt
   beantwoorden. Precies het soort fout dat deze hele fase opruimt.
2. Er is **geen unittest die het vangt** — jsdom is hier verboden, dus de enige
   bewaker zou een browsermeting per HA-versie zijn.
3. Het slotcontract van `ha-dialog` is net onder onze voeten veranderd. Het kan
   opnieuw.

De regel in de kaart is van onszelf, staat er sinds fase 4a, en is al getoetst.
Voor een bevestiging op een **onomkeerbare** handeling weegt "aantoonbaar
bedienbaar" zwaarder dan mooiere chroom.

### De tekst

`bevestigingsTekst()` in `src/bevestiging.js`, puur en met zes tests. **Naam én
tijd**, want een lijst met vier wekkers heeft er zo twee van "Werk". Ontbreekt er
een, dan valt dat deel weg; ontbreken ze allebei, dan staat er *"Wil je deze
wekker verwijderen?"* — nooit een verzonnen naam, want die verwijst naar een
wekker die de klant niet herkent.

---

## Wijziging 2 — Overslaan verdwijnt

Weggehaald, in de volgorde van de opdracht:

| Wat | Waar |
|---|---|
| het commando `alarms/skip_next` | `websocket.py`; SPEC 15.5 is nu **VERVALLEN** |
| het veld `skip_next` | `validatie.py`, SPEC 14.2, 14.4 |
| de stap in het respijtvenster | `planner.py`, SPEC 13.4 stap 4 |
| de regel in `set_enabled` | `websocket.py`, SPEC 15.3 |
| `"Morgen overgeslagen"` | `weergave.js`, SPEC 3.2 |
| de meldingssoort `skipped_by_user` | `meldingen.py`, SPEC 11.7 en 19.5 |
| de tak in `volgend_moment_van_wekker` | `volgende.py` |

**De nummering van SPEC 15 en van SPEC 13.4 blijft staan.** 15.5 is een sectie met
"VERVALLEN" erin, en stap 4 idem. Doorschuiven zou tientallen verwijzingen in de
code, de rapporten en de commitgeschiedenis stil naar iets anders laten wijzen.

**De naam `skipped_by_user` blijft leesbaar in oude opslag.** Een klant kan zo'n
`last_message` nog hebben staan; de kaart toont `text` en `severity` uit het
opgeslagen object en raadpleegt de tabel in `meldingen.py` niet.

---

## De migratie — het punt waar het stil mis kan gaan

### Major of minor? Major.

SPEC 14.6 stelt de vraag scherp: gaat `minor_version` omhoog als de nieuwe code
oude data **zonder aanpassing** kan lezen, en `version` als dat niet kan.

Hier kan het niet. `validatie.py` weigert onbekende velden, dus een wekker met
`skip_next` erin maakt de **hele persoon onleesbaar** (SPEC 19.2 geval B). Zonder
migratie verliest een bestaande klant al zijn wekkers, en hij ziet daar niets van
tot de eerste ochtend dat er niets afgaat.

Dus **versie 1 → 2**, en `minor_version` terug naar 1 (die telt binnen een
majorversie). Vastgelegd in een versietabel in SPEC 14.6.

### Wat de migratie wel en niet doet

`_migreer_v1_naar_v2` haalt uitsluitend de velden uit `VERVALLEN_VELDEN_V1` weg.
Al het andere gaat **letterlijk** door naar de validatie: onbekende velden,
kapotte structuren, alles. Een migratie die "opschoont" naar wat de code van
vandaag verwacht, zou een schrijffout onzichtbaar maken en de scheiding tussen
gezonde en kapotte personen van zijn werk beroven.

### Twee dingen die SPEC beweerde en die niet waar waren

**a) "Migratie slaat kapotte personen over."** Dat stond sinds fase 2 in SPEC 14.6
en het is niet uitvoerbaar: HA draait `_async_migrate_func` **binnen**
`Store.async_load`, dus vóórdat onze code één persoon heeft gezien. De scheiding
gezond/kapot bestaat op dat moment nog niet. SPEC 14.6 is gecorrigeerd.

**b) "Migraties zijn puur en zonder verlies."** Deze migratie verliest met opzet
een veld. De bullet is aangescherpt: verlies mag, mits het veld **bij naam in SPEC
staat**; wat je niet kunt omzetten laat je falen.

En één ding dat we niet kiezen maar wel moeten weten: **een geslaagde migratie
schrijft**, ook als de opslag daarna onbruikbaar blijkt (geval C). HA doet dat
zelf, direct na de migratie. De inhoud blijft ongemoeid; alleen het versienummer
gaat omhoog. Dat kostte twee bestaande tests hun aanname, en die zijn aangepast
door de fixture standaard op de **huidige** versie te laten schrijven — wie de
migratie wil toetsen, geeft nu expliciet `version=1` mee.

### Live gemeten, op een echte oude opslag

De dev-instance had nog een `.storage` van vóór deze ronde. Eerst `skip_next: true`
op één wekker gezet, om zeker te weten dat er iets weg te halen viel:

```
VOOR: version 1 minor 1 | wekkers: 4
  - 06:45 Werkdagen   skip_next=False
  - 08:30 Weekend     skip_next=False
  - 05:20 Sport       skip_next=False
  - 17:15 Boodschappen skip_next=True
```

Home Assistant herstart, en daarna:

```
NA: version 2 minor 1 | wekkers: 4
  - 06:45 Werkdagen    | skip_next aanwezig: False
  - 08:30 Weekend      | skip_next aanwezig: False
  - 05:20 Sport        | skip_next aanwezig: False
  - 17:15 Boodschappen | skip_next aanwezig: False
```

En in het log: `Opslag gelezen: 1 gezonde personen, 0 onleesbaar`. Alle vier de
wekkers overleefden, het veld is weg, en de persoon is niet als kapot gemarkeerd.

---

## De tests

**314 Python-tests** (was 313), **85 JS-tests**. De vier verplichte gevallen:

| # | Geval | Test |
|---|---|---|
| 1 | opslag met `skip_next` migreert en blijft werken | `test_een_opslag_met_skip_next_migreert_en_de_wekker_blijft_werken` |
| 2 | `alarms/skip_next` geeft `unknown_command` | `test_skip_next_bestaat_niet_meer` |
| 3 | verwijderen werkt, annuleren doet niets | browser (zie hieronder) plus `test_delete_verwijdert_en_onbekende_id_geeft_not_found` |
| 4 | het respijtvenster werkt nog zonder de skip-stap | `test_een_wekker_gaat_elke_dag_af_zonder_uitzondering` |

Geval 1 doet alle drie de dingen die moeten kloppen: de persoon is niet corrupt,
de wekker komt met naam en tijd uit `alarms/get` **en** heeft een `next_fire`, en
`skip_next` is ook **op schijf** weg.

### Nieuw, met hun label

| Test | Label |
|---|---|
| `test_een_opslag_met_skip_next_migreert_en_de_wekker_blijft_werken` | NIEUW GEDRAG |
| `test_de_migratie_laat_alles_behalve_skip_next_met_rust` | NIEUW GEDRAG |
| `test_de_migratie_valt_niet_om_op_kapotte_data` (4 gevallen) | NIEUW GEDRAG |
| `test_skip_next_bestaat_niet_meer` | NIEUW GEDRAG |
| `test_skip_next_is_ook_geen_veld_meer` | NIEUW GEDRAG |
| `test_een_wekker_gaat_elke_dag_af_zonder_uitzondering` | NIEUW GEDRAG |
| `test_set_enabled_zet_uit_en_laat_next_fire_vervallen` | NIEUW GEDRAG |
| `bevestigingsTekst` — 4 gevallen | NIEUW GEDRAG |
| `test_een_vervallen_veld_verandert_niets_meer` (`volgende.py`) | **REGRESSIEWACHT** |
| `subtitel` — "noemt een afgelopen wekker niet alsnog naar zijn dagen" | **REGRESSIEWACHT** |

### Gedraaid op de code van vóór de fix

`custom_components/` en `src/` teruggezet naar `main`, de tests laten staan:

```
FAILED tests/test_store.py::test_een_opslag_met_skip_next_migreert_en_de_wekker_blijft_werken
FAILED tests/test_store.py::test_de_migratie_laat_alles_behalve_skip_next_met_rust
FAILED tests/test_store.py::test_de_migratie_valt_niet_om_op_kapotte_data[geen-object]
FAILED tests/test_store.py::test_de_migratie_valt_niet_om_op_kapotte_data[alarms-geen-lijst]
FAILED tests/test_store.py::test_de_migratie_valt_niet_om_op_kapotte_data[persoon-geen-object]
FAILED tests/test_volgende.py::test_een_vervallen_veld_verandert_niets_meer
FAILED tests/test_websocket.py::test_skip_next_bestaat_niet_meer
FAILED tests/test_websocket.py::test_skip_next_is_ook_geen_veld_meer
8 failed, 305 passed
```

`tests/js/bevestiging.test.mjs` faalt daar met `ERR_MODULE_NOT_FOUND` — een
triviale mislukking, en daarom staat de waarde van dat bestand in de mutatieproef.

---

## De mutatieproef

`scripts/mutaties-fase-7.py`, met een filter `py`/`js`. **Ronde 1: 10 mutaties, 8
gevangen. Ronde 2: 5 mutaties op de randen, 4 gevangen.** Eindstand na het
dichten: **14 van de 15**.

| | Mutatie | Gevangen |
|---|---|---|
| M1 | **de migratie doet niets** — de klant raakt al zijn wekkers kwijt | ja |
| M2 | de migratie houdt alléén het vervallen veld over | ja |
| M3 | de lijst met vervallen velden is leeg | ja |
| M4 | de schemaversie gaat niet omhoog, dus de migratie draait nooit | ja |
| M5 | de migratie valt om op kapotte data | ja |
| M6 | een persoon met kapotte `alarms` verdwijnt uit de opslag | ja |
| M7 | `skip_next` staat weer als serverveld genoteerd | **NEE → gedicht** |
| M8 | een commando dubbel registreren | **NEE — verkeerde mutatie, zie hieronder** |
| M12 | de tijd valt uit de bevestiging | ja |
| M13 | een afgelopen eenmalige wekker heet weer "Eenmalig" | ja |
| M14 | een **onbekende** oudere versie wordt stil doorgelaten | ja |
| M15 | `minor_version` telt door over de majorsprong heen | ja |
| M16 | een wekker die geen object is wordt vervangen door `{}` | **NEE → gedicht** |
| M17 | het volgende moment slaat er stiekem één over (de oude skip-tak) | ja |
| M18 | een naam die geen tekst is komt zo in de bevestiging | ja |

### De twee gaten

**M7 — `skip_next` terug in `SERVERVELDEN`.** Beide paden geven `invalid_format`,
dus de foutcode verandert niet. Wat wél verandert is de **reden**: "deze velden
beheert de server zelf" over een veld dat niet meer bestaat. Dat is dezelfde soort
onwaarheid als de meldingen uit fase 6 en 6b, nu in een foutmelding. De test toetst
nu op de tekst.

**M16 — een wekker die geen object is wordt `{}`.** Echt testgat. De migratie
belooft dat kapotte data kapot blijft, want anders verliest de admin het bewijs dat
hem vertelt wát er stuk is (SPEC 19.2 geval B). De vier gevallen dekten
`persons`-geen-object, `alarms`-geen-lijst en persoon-geen-object, maar niet een
**geldige lijst met rommel erin**. Er is een vierde parameter bij.

### De mutatie die fout was, en dat is ook een uitkomst

**M8 registreert een commando dubbel.** Niet gevangen, en dat hoort ook niet: HA's
`async_register_command` overschrijft, dus een dubbele registratie doet niets
waarneembaars. De mutatie modelleert **geen defect**. Het omgekeerde — een
commando dat *ontbreekt* — is wél gevaarlijk en wordt door de tests van dat
commando zelf gevangen.

Dit is de spiegel van valkuil 46 ("een oefening die 100 % vangt heeft de verkeerde
mutaties"): een mutatie die *niet* gevangen wordt is niet automatisch een gat. Hij
kan ook gewoon geen fout beschrijven. Het onderscheid is de vraag: **welke klant
merkt hier iets van?** Bij M8 is het antwoord "niemand", en dan is er niets te
dichten.

---

## Browserverificatie

Kaart via `grid_options: {columns: 9}` op **gemeten 373 px** — telefoonbreedte.
Verse code bewezen door **alleen uit de service-workercache te lezen** en te
vergelijken met de schijf: 51.714 bytes, `9061c4ab1060`, gelijk aan
`npm run verify` en aan de `?v=` die de integratie registreerde.

### 1. De bevestiging overlapt niets

Bevestiging open op rij 3, alles in CSS-pixels:

| | top | bottom |
|---|---|---|
| kaart | 80 | 457 |
| rij 3 (Weekend) | 276 | **341** |
| **bevestiging** | **341** | **392** |
| rij 4 (Boodschappen) | **392** | 456 |

`overlaptEenRij: false` (rechthoek-snijtest tegen alle vier de rijen),
`binnenKaart: true`, en **0 px** speling aan beide kanten: de bevestiging heeft de
rijen uit elkaar **geduwd** in plaats van eroverheen te gaan.

En het structurele bewijs dat de bevinding niet kan terugkomen:

```json
{"lagenBovenDeKaart": []}
```

Er is in de hele kaart geen enkel `position: fixed`- of `absolute`-element met een
z-index meer. Er is niets dat een klik kan opvangen.

Screenshot: `docs/fase-7/2-bevestiging-op-373px.jpg`.

### 2. Verwijderen werkt, annuleren doet niets

Beide met echte kliks (`isTrusted: true`):

| Handeling | Uitkomst |
|---|---|
| prullenbak "Sport" → **Annuleren** | bevestiging weg, **4 wekkers over** |
| prullenbak "Weekend" → **Verwijderen** | bevestiging weg, **4 → 3 wekkers**, rij uit de DOM |

### 3. Zes keer achter elkaar, over vier rijen — de kern

Dit is waar het menu op stukliep, dus één geslaagde klik telt niet.

| # | Klik op | Opende bij de **eerste** klik? | Tekst |
|---|---|---|---|
| 1 | rij 1 (Sport) | ja | *Wil je de wekker "Sport" van 05:20 verwijderen?* |
| 2 | rij 3 (Weekend) | ja | *… "Weekend" van 08:30 …* |
| 3 | rij 2 (Werkdagen) | ja | *… "Werkdagen" van 06:45 …* |
| 4 | rij 4 (Boodschappen) | ja | *… "Boodschappen" van 17:15 …* |
| 5 | rij 1 opnieuw | ja | *… "Sport" van 05:20 …* |
| 6 | rij 3 opnieuw | ja | *… "Weekend" van 08:30 …* |

`aantalPrullenbakKliks: 6`, `allemaalIsTrusted: true`,
`allemaalRaakDeKnop: true` — elke klik landde op de bedoelde knop en niet op iets
dat ervoor lag. Met de oude code zouden 3 van deze 6 alleen een menu hebben
gesloten.

### 4. Geen restanten van overslaan

```json
{"geenMenuKlasse": true, "geenSluiter": true, "geenOverslaanTekst": true,
 "knoppenPerRij": [["Wekker Sport bewerken", "Wekker Sport aan of uit",
                    "Wekker Sport verwijderen"], …],
 "aantalKnoppenPerRij": [3, 3, 3]}
```

Drie knoppen per rij, geen ⋮, geen `.menu`, geen `.sluiter`, en nergens de tekst
"Overslaan" of "overgeslagen". De subregels tonen alleen `di do`,
`ma di wo do vr` en `Eenmalig`. Screenshot: `docs/fase-7/3-na-verwijderen.jpg`.

---

## Wat niet lukte

**1. De eerste browsermeting mat de verkeerde bundel, twee keer, en de oorzaak is
erger dan gedacht.** De opdracht waarschuwde ervoor en het gebeurde alsnog. Wat er
onder zit is scherper dan de valkuil die er al stond:

- `fetch(url, {cache: 'reload'})` gaat **door de service worker heen**. Het
  vervalt de HTTP-cache, niet de SW-cache. Twee keer achter elkaar de oude bundel
  gekregen terwijl `curl` van buiten de browser de nieuwe gaf.
- HA's SW matcht met **`ignoreSearch`**. Gemeten, en dit is de kern:
  `cache.match('…card.js?v=9061c4ab1060', {ignoreSearch: true})` gaf **52.229
  bytes / `fb8e38dfde1e`** terug — de bundel van een versie eerder. **De `?v=` is
  dus geen cache-buster tegen de service worker.**
- Gevolg dat verder gaat dan meten: de kaart wordt langs **twee** routes geladen
  (index-import én Lovelace-resource, valkuil 3). Kwam de index uit de cache met
  een oude `?v=`, dan wint de **oude** module de registratierace en draait de klant
  een oude kaart achter een nieuwe URL. Dat is precies wat hier gebeurde: de pagina
  toonde de `ha-dialog`-versie terwijl het `<script>`-element de nieuwe `?v=`
  droeg.

De enige betrouwbare uitweg bleek: alle `file-cache`-entries van de kaart **en**
de gecachte index verwijderen, de service worker afmelden, en dan pas navigeren.
Alle metingen in dit rapport komen daarna. Als valkuil 62 opgeschreven.

**2. Het toetsenbord.** De bevestiging is een rij met twee gewone knoppen, dus
Tab en Enter werken, maar er is geen focusval en Escape doet niets. Dat was een van
de dingen die HA's dialoog zou hebben opgelost. Het stond al als openstaand punt
in `CLAUDE.md` en het blijft staan.

**3. Geen echte telefoon.** De 373 px komt uit `grid_options`, niet uit een
apparaat — dezelfde beperking als in fase 4c en 6b.

---

## Aannames

1. **De bevestiging is een regel in de kaart en geen `ha-dialog`**, terwijl de
   opdracht die dialoog voorschreef "als die er is". Hij ís er, maar hij werkt niet
   met het slotcontract dat er een versie geleden nog was, en het faalgeval is
   stil. De meting staat hierboven en in de kop van `src/bevestiging.js`.
   Terugdraaien kan: de sloten heten nu `headerTitle` en `footer`. Dan bindt de
   kaart zich wel aan de binnenkant van een HA-component die net is verbouwd.
2. **De nummering van SPEC 15 en SPEC 13.4 schuift niet door.** 15.5 en stap 4
   blijven bestaan met "VERVALLEN" erin. Doorschuiven zou tientallen verwijzingen
   stil laten liegen.
3. **`skipped_by_user` is uit de code verwijderd maar blijft leesbaar in oude
   opslag.** De kaart rendert `text` en `severity` uit het opgeslagen object; er is
   geen pad dat de soortentabel raadpleegt bij het **tonen**.
4. **De testfixture `schrijf_opslag` schrijft voortaan de huidige schemaversie.**
   Anders zou elke test die hem gebruikt ongemerkt door de migratie lopen. Wie de
   migratie toetst, geeft `version=1` expliciet mee.

---

## `git status --porcelain`

Vlak vóór de commit, op branch `fase-7/prullenbak`:

```
 M CLAUDE.md
 M SPEC.md
 M custom_components/domotiapp_alarm/const.py
 M custom_components/domotiapp_alarm/frontend/domotiapp-alarm-card.js
 M custom_components/domotiapp_alarm/meldingen.py
 M custom_components/domotiapp_alarm/planner.py
 M custom_components/domotiapp_alarm/store.py
 M custom_components/domotiapp_alarm/validatie.py
 M custom_components/domotiapp_alarm/volgende.py
 M custom_components/domotiapp_alarm/websocket.py
 M src/const.js
 M src/domotiapp-alarm-card.js
 M src/editorlogica.js
 D src/menu.js
 M src/weergave.js
 M tests/conftest.py
 M tests/js/editorlogica.test.mjs
 D tests/js/menu.test.mjs
 M tests/js/weergave.test.mjs
 M tests/test_abonnement.py
 M tests/test_afvuren.py
 M tests/test_init.py
 M tests/test_planner.py
 M tests/test_store.py
 M tests/test_volgende.py
 M tests/test_websocket.py
?? docs/fase-7/
?? scripts/mutaties-fase-7.py
?? src/bevestiging.js
?? tests/js/bevestiging.test.mjs
```

Ná de commit en de push: leeg.
