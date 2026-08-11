# Fase 6b — Vier bevindingen: UI, teksten en shuffle

Twee bevindingen komen van de eigenaar, die de kaart op zijn telefoon heeft
doorlopen. Twee komen uit de audit die fase 6 zelf opleverde en toen bleef liggen
omdat de woordkeuze aan hem was.

---

## Samenvatting

| Bevinding | Wat het was | Wat het nu is | Bewijs |
|---|---|---|---|
| 1. Het overloopmenu overlapt | hing altijd 40 px onder de knop en stak bij de onderste rij **71 px** onder de kaart uit | blijft binnen de kaart; past het er onder niet, dan klapt het erboven | gemeten op een kaart van **373 px** |
| 2. De kopbalk naar boven | de eerstvolgende wektijd en de plusknop stonden onderaan | kopbalk bovenaan, lijst eronder | gemeten: kop op y 81, eerste rij op 146 |
| 3. Nog twee liegende teksten | *"op het ingestelde volume"* en *"omdat Home Assistant uit stond"* | zeggen wat is vastgesteld | 2 nieuwe tests, tegenvoorbeeld uitgeschreven |
| 4. Shuffle blijft aan staan | bleef aan op de speaker na de wekker | gaat terug, met dezelfde drie regels als het volume | live: `false → true → false` |

**308 Python-tests** (was 297), **91 JS-tests** (was 77), **23 mutaties in twee
rondes, alle 23 gevangen** na twee gaten in ronde 2. Bundel van 52.129 naar
**55.356 bytes**, hash `b038dc6e3eff`.

SPEC gewijzigd voor bevinding 2, 3 en 4, zoals de opdracht toestaat: secties 3.1,
3.2, 3.3, 9.5, 9.6 en 11.7. **Bevinding 1 heeft óók een SPEC-regel gekregen** —
zie "Aannames", punt 1.

---

## Bevinding 1 — Het overloopmenu overlapt

### Eerst gemeten: welke HA-component is er?

De opdracht was uitdrukkelijk om HA's eigen menu te gebruiken als dat er is, en om
niet aan te nemen dat het er is (fase 4b vond `ha-time-input` en `ha-textfield`
niet geladen terwijl `ha-card` en `ha-select` dat wel waren). Gemeten op
`/fase-4a/0`, met een verse pagina en nog eens vier seconden later:

| Component | `customElements.get(...)` |
|---|---|
| `ha-md-menu` | **niet gedefinieerd** |
| `ha-md-menu-item` | **niet gedefinieerd** |
| `ha-button-menu` | **niet gedefinieerd** |
| `ha-md-button-menu` | **niet gedefinieerd** |
| `ha-menu` | **niet gedefinieerd** |
| `ha-card`, `ha-form`, `ha-select`, `ha-switch`, `ha-list-item`, `ha-icon`, `ha-icon-button`, `ha-tooltip` | gedefinieerd |
| `ha-textfield`, `ha-time-input` | niet gedefinieerd (ongewijzigd sinds 4b) |

**Geen enkele menu-component bestaat op een gewoon dashboard.** Dat is valkuil 44
en 50 op hun scherpst: een `<ha-button-menu>` in het template zou renderen als een
leeg inline-element — een **onzichtbaar menu**, zonder fout in de console. De
opdracht is daarmee beantwoord met een meting in plaats van met een keuze: het kan
niet.

Eén verschuiving ten opzichte van fase 4b is het opmerken waard: **`ha-switch` is
nu wél gedefinieerd** op dit dashboard, terwijl fase 4a hem juist vermeed. De les
van valkuil 50 blijft dus staan, en met een extra rand: welke component geladen is
verschilt niet alleen per component maar ook **per HA-versie en per dashboard**.
Erop bouwen blijft onverstandig; onze eigen schakelaar blijft staan.

### Wat er mis was, en wat de regel nu is

Het menu stond `position: absolute` in de rij, altijd 40 px onder de knop. Bij de
onderste rij stak het daarmee onder de kaart uit, over wat er op het dashboard
onder stond.

De regel is nu meetbaar: **het menu blijft binnen de kaart.** Past het onder de
knop niet, dan klapt het erboven. Past het in geen van beide richtingen — een
kaart met één rij is lager dan het menu hoog is — dan wint het **venster**: liever
een randje over de kaart dan een menu dat half buiten beeld valt en niet aan te
klikken is.

De berekening staat in een nieuwe **pure** module `src/menu.js` (`plaatsMenu`), met
acht Node-tests. De hoogte wordt **gemeten** en niet uit de CSS afgeleid: twee
items zijn het altijd, maar de tekst verschilt ("Overslaan" tegenover "Toch niet
overslaan") en de lettergrootte komt uit het thema van de gebruiker. Een geraden
hoogte zou het menu bij een grote letter alsnog over de rand duwen — dezelfde
bevinding, maar dan alleen bij wie groot leest.

Twee dingen die daarbij horen. Het menu rendert eerst **onzichtbaar**
(`visibility: hidden`), want een element zonder layout heeft geen hoogte om te
meten; en het **sluit bij scrollen en bij resizen**, omdat een `fixed` menu anders
stil blijft staan terwijl de knop wegloopt.

### De livemeting op 373 px

Kaart op `grid_options: {columns: 9}` — **gemeten breedte 373 px**, de
telefoonbreedte uit fase 4c. Vier wekkers, echte klik op de ⋮ van de **onderste**
rij (`isTrusted: true`, coördinaten omgerekend met de factor 0,81667 uit
valkuil 43).

| | y-top | y-onder |
|---|---|---|
| kaart | 80 | **406** |
| ⋮-knop van de onderste rij | 353 | 393 |
| **menu, nu** | **265** | **349** |
| menu, zoals het vóór 6b zou staan | 393 | **477** |

- **Nu:** het menu klapt omhoog, eindigt op 349 en houdt **57 px** over tot de
  onderrand van de kaart. Het gat tot de knop is **4 px** (`MENU_MARGE`), en het is
  **exact** rechts uitgelijnd op de knop (verschil 0 px).
- **Vóór 6b:** het zou op 393 beginnen en op 477 eindigen — **71 px onder de kaart**,
  precies wat de eigenaar zag.

En de andere richting, dezelfde kaart, de ⋮ van de **bovenste** rij:

| | waarde |
|---|---|
| knop | 158 → 198 |
| menu | 202 → 286, richting **onder** |
| gat tot de knop | 4 px |
| binnen de kaart (80 → 341) | ja |

`position: fixed`, `z-index: 3` — bevestigd met `getComputedStyle`.

Screenshot: `docs/fase-6b/2-menu-op-373px-klapt-omhoog.jpg`.

### Beide menu-items werken nog

Alles met echte kliks, alle vijf `isTrusted: true`:

| Handeling | Uitkomst |
|---|---|
| ⋮ op "Boodschappen" → **Overslaan** | `skip_next` `false → true`, de subregel werd **"Morgen overgeslagen"**, het menu ging dicht |
| ⋮ opnieuw → **Verwijderen** | bevestigingsregel *"Wekker "Boodschappen" van 17:15 verwijderen?"* |
| **Verwijderen** in die regel | 4 wekkers → 3, en de rij verdween uit de DOM |

Het menu toonde bij de tweede opening **"Toch niet overslaan"** in plaats van
"Overslaan" — de omkeerbaarheid uit SPEC 3.2, en meteen het geval waarvoor de
hoogte gemeten en niet geraden wordt.

---

## Bevinding 2 — De kopbalk naar boven

De eerstvolgende wektijd en de plusknop stonden onderaan de kaart. Met tien
wekkers moest je scrollen om te zien wanneer je wekker gaat en om er een toe te
voegen — de twee dingen waarvoor je de kaart openslaat.

### De keuze bij de lege staat, en waarom

De opdracht laat open of de plusknop bij een lege lijst in de kopbalk hoort of in
het midden blijft. **Gekozen: de kopbalk is er altijd, en bij een lege lijst is hij
de hele kaart.** De regel luidt dan "Geen wekkers ingesteld" met de plusknop
ernaast.

Waarom niet de kopbalk plus een aparte lege regel eronder:

1. Er zouden **twee ontkenningen onder elkaar** staan — "Geen wekker actief" boven
   "Geen wekkers ingesteld". Dat is omslachtig voor "je hebt er nog geen".
2. De kaart zou **twee plusknoppen** krijgen, of één die verspringt zodra de eerste
   wekker er is. De plusknop staat nu altijd op dezelfde plek.
3. SPEC 3.1 vroeg al *"één regel en een plusknop, niets anders"*. Met de balk
   bovenaan ís dat de kopbalk; er hoeft niets bij.

**Bijvangst, en die is meer dan cosmetisch:** "geen wekkers" en "geen wekker
actief" zijn nu **uit elkaar getrokken**. Ze vragen iets anders van de gebruiker —
"maak er een" tegenover "zet er een aan" — en vielen daarvoor samen. Vastgelegd in
SPEC 3.3 en in `kopTekst()`.

### De livemeting

Vier wekkers op het brede dashboard, venster 855 px hoog, `scrollY = 0`:

| | y-top | y-onder |
|---|---|---|
| kaart | 80 | 406 |
| **kopbalk** | **81** | **146** |
| rij 1 (05:20 Sport) | 146 | 211 |
| rij 2 (06:45 Werkdagen) | 211 | 276 |
| rij 3 (08:30 Weekend) | 276 | 341 |
| rij 4 (17:15 Boodschappen) | 341 | 405 |

De kopbalk is het **eerste** element in de kaart en staat boven alle vier de rijen.
Tekst links: **"Morgen 06:45"** — letterlijk `next_fire.text` van de server. Plus
rechts: 1281 → 1321, tegen een kaartrand op 1338, met
`aria-label="Wekker toevoegen"`.

De hele kaart (80 → 406) past in een venster van 855 px, dus de kopbalk is
zichtbaar **zonder scrollen** — met vier wekkers ruimschoots, en de kopbalk blijft
per constructie het eerste element hoeveel wekkers er ook bij komen.

Lege staat, gemeten na het verwijderen van alles:

| | waarde |
|---|---|
| kaart | 80 → 146, hoogte **66 px** |
| kopbalk-klasse | `kop leeg` |
| tekst | **"Geen wekkers ingesteld"** |
| plusknop | 1154 → 1194, label "Wekker toevoegen" |
| aantal `.rij` | 0 |
| aantal extra regels (`.mededeling`) | **0** |
| rand onder de kop | **0px** — er staat niets om van te scheiden |

Screenshots: `docs/fase-6b/1-kopbalk-met-vier-wekkers.jpg` en
`docs/fase-6b/3-lege-staat.jpg`.

---

## Bevinding 3 — Nog twee liegende teksten

De eigenaar gaat akkoord met de voorstellen uit `docs/fase-6/RAPPORT.md`. Beide
zijn letterlijk overgenomen.

### `volume_ramp_unavailable`

| | |
|---|---|
| was | "De wekker is afgegaan **op het ingestelde volume**; het oplopende volume was op deze speaker niet mogelijk." |
| is | "De wekker is afgegaan, maar het volume was op deze speaker **niet in te stellen**; het oplopende volume is overgeslagen." |

Wat er misging staat in `afvuren.py:198-210`. De melding ontstaat doordat
`volume_set(0)` weigert. Daarna doet de code één poging tot het ingestelde
niveau — met **dezelfde service die net weigerde** — en die uitkomst wordt niet
gelezen. De bestaande test
`test_een_speaker_die_geen_volume_aanneemt_gaat_af_zonder_oploop` bewijst het zelfs:
hij telt **twee** geweigerde `volume_set`-aanroepen. De speaker speelt dus op de
stand van gisteravond, en die kan net zo goed onhoorbaar zijn als oorverdovend.

### `skipped_grace_window`

| | |
|---|---|
| was | "Je wekker van 06:45 is niet afgegaan **omdat Home Assistant uit stond**." |
| is | "Je wekker van 06:45 is niet afgegaan; **Home Assistant heeft dat moment gemist**." |

Het tegenvoorbeeld staat nu als test in `test_planner.py`
(`test_de_mededeling_beweert_niet_dat_home_assistant_uit_stond`) en het is
letterlijk uitgevoerd, niet beschreven: Home Assistant draait de hele tijd, en er
komt om 12:00 een wekker bij voor 06:45 vandaag. De eerstvolgende herplanning met
inhaalslag — een herstart, in productie — meldt dat moment als gemist. Correct
gedrag, en de oude tekst zou hier aantoonbaar hebben gelogen.

### De overige teksten, opnieuw nagelopen

Alle acht zijn opnieuw langsgelopen. **Er staat er nu geen meer die iets claimt
wat de code niet vaststelt.**

| `kind` | waarom hij klopt |
|---|---|
| `speaker_unavailable` | de state stond op `unavailable`; dat is gezien |
| `ma_unavailable` | onderscheiden op `async_loaded_entries` van de MA-entry |
| `sound_gone` | sinds fase 6: "kon niet gestart worden", met de reden van MA |
| `speaker_lost_during_play` | zegt met opzet *"mogelijk niet hoorbaar geweest"* — de zwakste bewering die de meting toelaat |
| `light_failed` | de `light.turn_on` gooide |
| `volume_ramp_unavailable` | sinds deze ronde |
| `skipped_grace_window` | sinds deze ronde |
| `skipped_by_user` | `skip_next` stond op `true`, en dat kan alleen de klant zetten |

### Het patroon, want dit is de tweede ronde op rij

Gevraagd: als er een patroon in zit, meld dat. Dat is er, en het is scherper te
formuleren dan "wees voorzichtig met teksten".

**Alle drie de gevallen ontstonden op dezelfde manier: de tekst is geschreven bij
de SPEC-sectie, niet bij de regel code die hem verstuurt.** SPEC beschrijft een
*situatie* ("de speaker kan geen volume aan", "Home Assistant stond uit", "het
geluid bestaat niet meer") en de tekst beschrijft die situatie netjes. De code
stelt iets veel smallers vast: één aanroep weigerde, één moment verstreek, één
`play_media` gaf een fout. Het gat tussen die twee is precies de leugen.

Twee dingen die eruit volgen:

1. **De grammaticale toets werkt.** Elke tekst met een *"omdat"*, een *"want"* of
   een bijvoeglijke bewering over de buitenwereld ("bestaat niet meer", "op het
   ingestelde volume") is verdacht. Die woorden vullen het *waarom* in; de code
   kent alleen het *wat*.
2. **Het is geen tekstprobleem maar een vindplaatsprobleem.** De reparatie was
   alle drie de keren: kijk naar de regel die de melding *stuurt*, en schrijf op
   wat daar bekend is. `meldingen.py` draagt daarom sinds deze ronde per
   herschreven tekst een comment met de vindplaats in de code — niet in SPEC.

Dit is als valkuil 53 aangescherpt in `CLAUDE.md`.

---

## Bevinding 4 — Shuffle blijft aan staan

Het volume gaat bij het stoppen terug met de motivatie *"geen bijwerking die de
klant niet vroeg"* (SPEC 9.5). Die redenering geldt woordelijk voor shuffle: wie
's middags een album opzet, hoort dat niet geschud te krijgen omdat zijn wekker dat
's ochtends nodig had.

### De drie regels, allemaal van SPEC 9.5 geleend

1. **Lezen vóór zetten.** Erna lees je je eigen `true` terug, en dan zet het
   stoppen de shuffle van iedereen aan.
2. **Niet te lezen is niets terugzetten.** Een speaker die geen `shuffle`-attribuut
   meldt, is niet hetzelfde als een speaker waarvan shuffle uit staat. `false`
   terugzetten zou een keuze maken die we niet kennen — en het is precies het geval
   van valkuil 18: extra state attributes verdwijnen bij `unavailable`, dus juist op
   het moment dat je de stand wilt kennen is hij weg.
3. **Niet aangezet is niet terugzetten.** Bij radio raken we shuffle niet aan; de
   stand is dan die van de klant. Zou er tóch teruggezet worden, dan draaien we een
   wijziging terug die hij zélf tijdens de wekker maakte — een bijwerking in plaats
   van het weghalen van een bijwerking.

Regel 2 en 3 delen dezelfde uitkomst (`None` = niets doen) en dat is met opzet;
`async_shuffle_aan_voor()` documenteert waarom.

**Het voorbeeld (SPEC 5.4) doet hetzelfde**, inclusief het pad waarin `play_media`
faalt — daar is het volume al verzet en shuffle ook, en er komt geen `async_stop`
achteraan die het alsnog herstelt.

### Botst het met de volgorde uit fase 6?

Nee, en dat is nagegaan. Fase 6 stelde vast dat `shuffle_set` **vóór** `play_media`
moet, omdat MA shuffle toepast bij het **laden van de queue**
(`controllers/player_queues.py:1533`). Het terugzetten gebeurt ná `media_stop`, dus
er wordt op dat moment geen queue geladen — er valt niets te beïnvloeden.

Live bevestigd dat het ook **blijft staan**: negen seconden na het stoppen was de
stand nog steeds de teruggezette waarde. MA houdt `shuffle_enabled` per speler
vast, ook zonder queue.

### De livemeting

Eén wekker met `library://playlist/6`, speaker `media_player.wekker_slaapkamer`,
beginstand bewust op `false` gezet zodat "terug" iets anders is dan "aan":

| Moment | `shuffle` | `volume_level` |
|---|---|---|
| **vóór** de wekker | `false` | 0,55 |
| **tijdens** (4 s na afgaan, oploop bezig) | **`true`** | 0,15 |
| **ná** `alarms/stop` | **`false`** | 0,55 |
| 9 s later, ter controle | `false` | 0,55 |

Er speelde werkelijk iets: `media_title` was
`church music Test Track 4 - 4 - 0`.

---

## De tests

**308 Python-tests** (was 297), **91 JS-tests** (was 77). Bundel van 52.129 naar
**55.356 bytes**, hash `b038dc6e3eff` — en dat is de hash die de integratie ook in
de `?v=` zette, gecontroleerd in de browser.

### Nieuw, met hun label

| Test | Label |
|---|---|
| `tests/js/menu.test.mjs` — 8 gevallen op `plaatsMenu` | NIEUW GEDRAG (module bestond niet) |
| `kopTekst` — 6 gevallen, waaronder "REKENT de tekst niet zelf uit" | NIEUW GEDRAG |
| `test_de_melding_beweert_niet_dat_het_ingestelde_volume_gehaald_is` | NIEUW GEDRAG |
| `test_de_mededeling_beweert_niet_dat_home_assistant_uit_stond` | NIEUW GEDRAG |
| `test_shuffle_gaat_bij_het_stoppen_terug_naar_wat_het_was` | NIEUW GEDRAG |
| `test_shuffle_die_al_aan_stond_blijft_aan` | NIEUW GEDRAG |
| `test_shuffle_wordt_gelezen_voordat_hij_gezet_wordt` | NIEUW GEDRAG |
| `test_een_shuffle_die_geen_boolean_is_telt_als_onleesbaar` | NIEUW GEDRAG |
| `test_een_onbereikbare_speaker_levert_geen_shuffle_stand` | NIEUW GEDRAG |
| `test_het_voorbeeld_zet_shuffle_terug_bij_afmelden` | NIEUW GEDRAG |
| `test_een_onleesbare_shuffle_wordt_niet_teruggezet` | **REGRESSIEWACHT** |
| `test_radio_laat_de_shuffle_van_de_klant_met_rust` | **REGRESSIEWACHT** |
| `test_het_voorbeeld_laat_shuffle_met_rust_bij_radio` | **REGRESSIEWACHT** |

### Gedraaid op de code van vóór de fix

`custom_components/` en `src/` teruggezet naar `main`, de tests laten staan:

```
FAILED tests/test_afvuren.py::test_shuffle_gaat_bij_het_stoppen_terug_naar_wat_het_was
FAILED tests/test_afvuren.py::test_shuffle_die_al_aan_stond_blijft_aan
FAILED tests/test_afvuren.py::test_shuffle_wordt_gelezen_voordat_hij_gezet_wordt
FAILED tests/test_afvuren.py::test_een_mislukte_shuffle_houdt_de_wekker_niet_tegen
FAILED tests/test_afvuren.py::test_de_melding_beweert_niet_dat_het_ingestelde_volume_gehaald_is
FAILED tests/test_planner.py::test_herstart_45_minuten_te_laat_slaat_over_met_mededeling
FAILED tests/test_planner.py::test_de_mededeling_beweert_niet_dat_home_assistant_uit_stond
FAILED tests/test_voorbeeld.py::test_het_voorbeeld_zet_shuffle_terug_bij_afmelden
8 failed, 87 passed
```

En aan de JS-kant:

```
tests/js/menu.test.mjs   → Cannot find module '../../src/menu.js'
tests/js/weergave.test.mjs → SyntaxError: does not provide an export named 'kopTekst'
```

**Drie tests zijn ná die run van NIEUW GEDRAG naar REGRESSIEWACHT gezet.** Ze
slaagden op de oude code, en dat is narekenbaar in plaats van toevallig: daar
bestaat het terugzetten helemaal niet, dus "er wordt niets teruggezet" is er
triviaal waar. Dat is de val van *"de setup faalt niet"*, en het juiste antwoord is
niet ze weggooien maar ze **eerlijk labelen**: hun waarde ligt aan de andere kant,
tegen een implementatie die bij het stoppen altijd iets zet.

De twee nieuwe tests op `shuffle_van` (`isinstance` en `unavailable`) zijn er pas
ná de mutatieproef bij gekomen; zie hieronder.

---

## De mutatieproef

Script: `scripts/mutaties-fase-6b.py`, met een filter `py`/`js` omdat de
Python-tests alleen in Linux draaien en de JS-tests overal. **23 mutaties in twee
rondes.**

**Ronde 1 (M1–M16): 16 mutaties, 15 gevangen.** **Ronde 2 (M17–M23): 7 mutaties
die naar gaten zochten in plaats van dekking te bevestigen, 6 gevangen.**
Eindstand na het dichten: **23 van 23**.

| | Mutatie | Gevangen |
|---|---|---|
| M1 | shuffle wordt bij het stoppen **niet** teruggezet — de bevinding zelf | ja |
| M2 | bij het stoppen wordt shuffle **uit** gezet in plaats van teruggezet | ja |
| M3 | de stand wordt **ná** het zetten gelezen | ja |
| M4 | ook radio krijgt een shuffle-aanroep | ja |
| M5 | een ontbrekende shuffle wordt als `False` gelezen | **NEE → gedicht** |
| M6 | het voorbeeld zet shuffle niet terug | ja |
| M7 | de oude volumetekst terug | ja |
| M8 | de oude overslaantekst terug | ja |
| M9 | **het menu hangt altijd onder de knop** — het gedrag van vóór 6b | ja |
| M10 | omhoog klappen bestaat niet meer | ja |
| M11 | bij omhoog klappen telt de menuhoogte niet mee | ja |
| M12 | het menu wordt links uitgelijnd in plaats van rechts | ja |
| M13 | de klemvolgorde omgedraaid | ja |
| M14 | een lege lijst krijgt weer "Geen wekker actief" | ja |
| M15 | de tekst van de server wordt genegeerd | ja |
| M16 | een lege tekst uit de server komt zo op de kaart | ja |
| M17 | shuffle wordt **niet aangezet** als de oude stand onleesbaar is | ja |
| M18 | de oude stand wordt gelezen maar niet bewaard | ja |
| M19 | de context krijgt een vaste `True` | ja |
| M20 | `binnenKaart` is altijd waar | ja |
| M21 | `MENU_MARGE` op 0 | ja |
| M22 | de reden van MA valt weg (regressie op fase 6) | ja |
| M23 | een `unavailable` speaker levert toch een stand op | **NEE → gedicht** |

### De twee gaten, en wat ze waren

Ze zaten allebei in `shuffle_van()`, en ze zijn van hetzelfde soort: **een
verdediging tegen data van een ánder, niet tegen onze eigen logica.** Dat is een
categorie die de vorige mutatierondes niet raakten, want daar ging het steeds over
onze eigen beslissingen.

**M5 — de `isinstance(stand, bool)`-controle.** `shuffle` is een attribuut van een
`media_player` die niet van ons is. HA's eigen `MediaPlayerEntity` typeert hem als
`bool | None`, maar de statemachine dwingt niets af, en een integratie die er
`"true"` in zet houdt niemand tegen. Zonder de controle gaat die string door naar
`shuffle_set`. Geen enkele test bood een niet-booleaanse waarde aan, want alle
tests gebruiken ons eigen Speelhuis dat zich netjes gedraagt.

Het was verleidelijk om hem equivalent te noemen: bij een **ontbrekend** attribuut
geeft `.get()` al `None` en verandert de mutatie niets. Maar het narekenen moet
tot het einde (valkuil 55), en er ís bereikbare invoer waarbij hij iets doet.

**M23 — de `STATE_UNAVAILABLE`-controle.** In de praktijk verdwijnen extra state
attributes zodra een entiteit `unavailable` is, dus dan is `shuffle` er tóch niet.
Maar dat is een **gemeten eigenschap van Home Assistant** (valkuil 18) en geen
garantie waar onze code op hoort te leunen. De test die dit dicht bouwt de
combinatie die HA in de praktijk niet maakt maar wel toestaat — `unavailable` mét
een `shuffle` erin — en legt vast dat de state wint van het attribuut. Precies
valkuil 34, tweede rij: redundante maar bereikbare verdediging, dus **testen op
dat pad** in plaats van hem dood te verklaren.

`volume_pct_van()` heeft allebei dezelfde controles en staat sinds fase 3c
ongetoetst op precies deze twee punten. De tweede test dekt hem meteen mee.

---

## Wat niet lukte

**1. Het menu is niet met het toetsenbord te bedienen.** De opdracht noemde HA's
componenten onder meer *"omdat die de toetsenbordafhandeling al hebben opgelost"*.
Die zijn er niet, en wat er nu staat lost dat **niet** op: het menu is met de muis
en met een tik te bedienen, maar er is geen pijltjesnavigatie, geen focusval en
geen Escape. De knop heeft wel `aria-haspopup="menu"` en `aria-expanded`, en de
items hebben `role="menuitem"`, dus een schermlezer kondigt het correct aan. Voor
een wandtablet en een telefoon — de doelapparaten uit SPEC 20.1 — is dat genoeg;
voor toetsenbordgebruik is het een **openstaand punt**, en het staat als zodanig in
`CLAUDE.md`.

**2. De eerste versheidsmeting van de bundel was fout, en dat is het melden waard.**
Een `fetch(url, {cache:'reload'})` op de **kale** URL gaf 52.129 bytes /
`015a09e66d81` — de bundel van fase 6 — terwijl de integratie al
`?v=b038dc6e3eff` registreerde. De tweede meting, op zowel de kale als de
versie-URL, gaf 55.356 bytes / `b038dc6e3eff`, gelijk aan het bestand op schijf.
Met andere woorden: **de eerste `cache:'reload'` repareerde de cache en de tweede
mat pas verse code.** Dat is valkuil 4 in een nieuwe jas, en het is precies de
reden dat de werkafspraak "vergelijk hash of lengte met het bestand op schijf"
bestaat — zonder die vergelijking had ik de oude bundel gemeten en niets gemerkt.
Alle metingen in dit rapport komen ná die tweede fetch en na een herlaadbeurt.

**3. `getCardSize()` is opnieuw niet in een masonry-weergave nagemeten.** Het getal
klopt nog (één per rij plus één voor de kopbalk in plaats van voor de voetregel),
maar het staat al sinds fase 4a als openstaand punt en deze ronde verandert daar
niets aan.

**4. Geen echte telefoon.** De 373 px komt uit `grid_options`, niet uit een
apparaat. Dat is de methode die fase 4c heeft vastgelegd omdat een gemaximaliseerd
venster niet te verkleinen is, maar het blijft een simulatie: touch-doelen,
schermtoetsenbord en de werkelijke lettergrootte van de klant zijn er niet mee
getoetst.

---

## Aannames

1. **Bevinding 1 heeft óók een SPEC-regel gekregen**, terwijl de opdracht zegt
   "SPEC.md alleen wijzigen voor bevinding 2, 3 en 4". Wat er is toegevoegd aan
   SPEC 3.2 is de **eis** dat het menu binnen de kaart blijft, plus de meting dat
   HA's menu-componenten er niet zijn. Zonder die regel staat de bevinding nergens
   vastgelegd en is de volgende ronde vrij om het menu weer onder de kaart te laten
   hangen. Terugdraaien is één alinea; dan blijft de bevinding alleen in dit
   rapport staan.
2. **Het voorbeeld zet shuffle ook terug.** De bevinding gaat over de wekker. Het
   voorbeeld heeft sinds fase 6 dezelfde shuffle en daarmee dezelfde bijwerking, en
   het herstelt het volume al. Het ongelijk laten zou betekenen dat één keer op de
   voorbeeldknop drukken de shuffle van de klant permanent omzet.
3. **De kopbalk staat er ook bij een lege lijst**, en de plusknop dus ook. De
   opdracht laat die keuze uitdrukkelijk aan mij; de verantwoording staat bij
   bevinding 2.
4. **Het menu sluit bij scrollen en resizen** in plaats van mee te bewegen. Dat is
   niet gevraagd en niet verboden; het is de goedkoopste manier om een `fixed` menu
   niet te laten wegdrijven, en HA's eigen menu's doen hetzelfde.

---

## `git status --porcelain`

Vlak vóór de commit, op branch `fase-6b/ui-en-teksten`:

```
 M CLAUDE.md
 M SPEC.md
 M custom_components/domotiapp_alarm/afvuren.py
 M custom_components/domotiapp_alarm/frontend/domotiapp-alarm-card.js
 M custom_components/domotiapp_alarm/meldingen.py
 M custom_components/domotiapp_alarm/voorbeeld.py
 M src/domotiapp-alarm-card.js
 M src/weergave.js
 M tests/conftest.py
 M tests/js/weergave.test.mjs
 M tests/test_afvuren.py
 M tests/test_planner.py
 M tests/test_voorbeeld.py
?? docs/fase-6b/
?? scripts/mutaties-fase-6b.py
?? src/menu.js
?? tests/js/menu.test.mjs
```

Ná de commit en de push: leeg.
