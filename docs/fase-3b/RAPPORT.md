# Fase 3b — De planner

De klok erbij. De planner beslist **wanneer** een wekker afgaat, het respijtvenster
beslist of een gemiste wekker nog ingehaald wordt, en `afvuren.py` is de naad waar
fase 3c het geluid in hangt. Er wordt in deze fase **niets afgespeeld**: geen
`music_assistant.play_media`, geen volume-oploop, geen lamp, geen noodrem-uitvoering,
geen stoptimer van 30 minuten.

**SPEC.md is niet gewijzigd.** Er is één plek waar SPEC 13.4 twee lezingen toelaat;
die is letterlijk geïmplementeerd en hieronder gemeld, niet zelf gecorrigeerd — zie
[De dubbelzinnigheid in SPEC 13.4 stap 4](#de-dubbelzinnigheid-in-spec-134-stap-4).

---

## Samenvatting

### Wat er nieuw is

| Bestand | Wat het doet |
|---|---|
| `planner.py` | **Nieuw.** De `Planner`-klasse: plant, haalt in, slaat over, herplant. |
| `afvuren.py` | **Nieuw.** De naad met fase 3c. In 3b: boekhouding en events. |
| `meldingen.py` | **Nieuw.** `last_message`, `persistent_notification` en de repair issues die fase 3a openliet. |
| `volgende.py` | `laatste_verstreken_moment()` erbij — nog steeds puur, nog steeds nul HA-imports. |
| `const.py` | `DATA_PLANNER`, `RESPIJT_MINUTEN = 30`. |
| `__init__.py` | Repair issues bijwerken, planner starten; bij unload de planner stoppen **vóór** de opslag. |
| `websocket.py` | Herplannen na elke mutatie; `delete` en `stop` stoppen een lopende wekker. |
| `strings.json`, `translations/*` | Teksten voor de twee repair issues. |

**Tests: 137 geslaagd** (112 uit eerdere fases, 25 nieuw), 8 JS-tests geslaagd,
bundel onveranderd, registratieregel intact.

### De twee remmen tegen dubbel vuren

Dit is de kern van de fase en het verdient de nadruk, want de valkuil is stil:
`async_track_point_in_time` met een moment in het **verleden** vuurt niet later — hij
vuurt **onmiddellijk**. Eén rem is dus niet genoeg, want een rem die zelf op het
verkeerde moment staat, wordt zonder waarschuwing overgeslagen.

**Rem 1, bij het plannen.** Een eenmalige wekker waarvan `one_shot_at` in het
verleden ligt, wordt niet ingepland. Punt. Dit voorkomt het onmiddellijke vuren aan
de bron.

**Rem 2, bij het afvuren.** `_async_vuur()` weigert alsnog, op twee gronden:
`last_fired >= moment` (deze wekker ging al af voor dit moment), en `nu - moment >
30 minuten` (buiten het respijtvenster). Deze rem zit in het pad dat de **callback**
gebruikt, waar rem 1 niet komt.

Zoals de opdracht eiste: `last_fired` is de **enige** bewaker tegen dubbel vuren, en
hij is niet omzeilbaar. `afvuren.py` schrijft `last_fired` **vóór** het geluid, niet
erna. Die volgorde is geen stijlkeuze:

- crasht HA tussen `last_fired` en geluid, dan is de ergste uitkomst **een wekker die
  niet klonk**;
- andersom zou de ergste uitkomst zijn: **een wekker die na elke herstart opnieuw
  afgaat**.

De eerste is een vervelende ochtend. De tweede is een wekker die je niet meer uit
krijgt.

### `last_fired` houdt het *bedoelde* moment vast, niet "nu"

Twee redenen, en beide zijn met een mutatietest gecontroleerd (P13):

1. `async_track_time_change` vuurt met 50–500 ms **jitter** ná de hele seconde. Zou
   `last_fired` op `nu` gezet worden, dan staat er `07:00:00.213` waar `07:00:00`
   hoort. De vergelijking `last_fired >= moment` blijft dan nog kloppen, maar
   schuift elke keer mee op.
2. Bij een **inhaalslag** liggen "nu" en het bedoelde moment tot 30 minuten uit
   elkaar. `last_fired` op "nu" zetten betekent dat de vergelijking in SPEC 13.4
   stap 3 elke herstart verder mee opschuift, en dan kan dezelfde wekker alsnog twee
   keer afgaan.

In de callback wordt het moment daarom teruggerekend uit de wandklok
(`nu.replace(second=0, microsecond=0)`) in plaats van uit `nu` zelf.

### De dagfiltering zit in de callback, niet in de planner

Zoals de opdracht voorschreef. `async_track_time_change` krijgt alleen uur en minuut;
de callback controleert `nu.isoweekday() in dagen` en stapt eruit als het niet klopt.
Dat is de vorm die HA zelf gebruikt en die de zelf-herplannende listener intact
laat. Mutatie P1 (dagfiltering weg) wordt gevangen.

### Najaars-DST vuurt twee keer, en dat is met opzet

SPEC 13.1 schrijft voor dat een wekker op 02:30 in de nacht van 25 oktober 2026
**twee keer** afgaat. Dat botst op het eerste gezicht met `last_fired`, dus dit is
expliciet nagemeten.

Het werkt omdat de vergelijking op een **absoluut moment** gaat, niet op wandtijd:

| | wandtijd | UTC | `last_fired` erna |
|---|---|---|---|
| eerste keer | 02:30 CEST (`fold=0`) | 00:30 | `02:30:00+02:00` |
| tweede keer | 02:30 CET (`fold=1`) | 01:30 | `02:30:00+01:00` |

`02:30+01:00` is een uur **later** dan `02:30+02:00`, dus `last_fired >= moment` is
bij de tweede beurt onwaar en de wekker gaat af. De tweede `last_fired` is strikt
groter dan de eerste — nagemeten in
`test_najaar_0230_vuurt_twee_keer`. In het voorjaar (29 maart 2026) bestaat 02:30
niet en gaat de wekker die nacht **niet** af; ook nagemeten.

Antwoord op de vraag uit taak D, expliciet: **nee, `last_fired` blokkeert de tweede
najaarsbeurt niet.** Dat was niet vanzelfsprekend en is de reden dat de vergelijking
op absolute momenten en niet op tijdstrings gaat.

### Herplannen bouwt van nul op

Bij elke aanleiding — setup, elke WebSocket-mutatie, `EVENT_CORE_CONFIG_UPDATE`,
unload — worden **alle** listeners opgezegd en wordt de planning opnieuw opgebouwd.
Geen delta-boekhouding. Dat is meer werk per mutatie (in de praktijk een handvol
listeners) en het scheelt de hele klasse bugs waarin een oude listener na een
wijziging blijft leven.

Dat er geen verdwaalde listener achterblijft, is niet aangenomen maar getoetst:
`test_wijzigen_zegt_de_oude_planning_op` zet een wekker van 07:00 naar 08:00, laat
de klok over **beide** momenten lopen en eist dat er precies één keer gevuurd is —
op 08:00. Mutatie P8 (listeners niet opzeggen) wordt daardoor gevangen.

Voor de tijdzone was een extra bevinding nodig: `_TrackUTCTimeChange`
(`helpers/event.py:1750`) luistert **zelf niet** op `EVENT_CORE_CONFIG_UPDATE` —
alleen `SunListener` doet dat. Een wekker van 07:00 die na een tijdzonewijziging niet
herplant wordt, gaat dus op de oude UTC-offset af. De planner luistert daarom zelf.
Live bleek dit meteen: HA vuurt tijdens het opstarten twee keer
`EVENT_CORE_CONFIG_UPDATE`, en de planner herplande netjes twee keer (zie de
tijdlijn onder taak G).

### De meldingen, en waarom drie kanalen

`meldingen.py` heeft drie kanalen omdat ze verschillende mensen bereiken:

| Kanaal | Voor wie | Wanneer |
|---|---|---|
| `last_message` in de opslag | de klant, op de kaart | elke fout **en** elke mededeling |
| `persistent_notification` | de klant, in HA's meldingenlijst | **alleen** bij `severity: "error"` |
| repair issue | de beheerder | **alleen** bij onleesbare opslag (SPEC 19.2) |

De klant is geen admin (SPEC 17) en repair issues zijn admin-only, dus een repair
issue over een mislukte wekker zou de persoon die zich verslaapt nooit bereiken. En
een `persistent_notification` bij elke mededeling zou de lijst vullen met dingen
waar niets aan te doen is; dan leest niemand hem meer.

`severity_van()` gooit bij een onbekende soort in plaats van terug te vallen op
"mededeling". Een stille default zou een fout als mededeling kunnen laten doorgaan,
en dat is precies het gedrag dat SPEC 19.1 verbiedt.

De **repair issues** die fase 3a bewust openliet zijn hier gebouwd, geval B (één
kapotte persoon, naam van de persoon erin zodat een admin niet in logs hoeft) en
geval C (opslag onbruikbaar). De functie is **idempotent** en loopt bij elke setup:
een gerepareerde opslag laat geen melding achter. Dat laatste is apart getoetst
(`test_geen_repair_issue_bij_gezonde_opslag`) — zonder die test zou "er is een
issue" ook waar kunnen zijn omdat er altijd één is.

### Wat de mutatietests opleverden

17 mutaties op `planner.py`, `afvuren.py`, `__init__.py` en `websocket.py`. **16
werden meteen gevangen.** De 17e is het vermelden waard, want het is dezelfde les
als in fase 3a maar één laag dieper.

**P3 — de `last_fired`-vergelijking in `_async_vuur` weghalen** veranderde eerst
niets: alle tests bleven groen. De verleiding is dan om de regel dood te verklaren
en te schrappen. Dat is hier fout, en het onderscheid is de moeite waard:

- de **inhaalslag** heeft dezelfde controle er al vóór staan, dus via dat pad is de
  regel inderdaad overbodig;
- de **callback** heeft die controle niet. Vuurt de callback twee keer voor hetzelfde
  moment — een herplanning die met een tik samenvalt, een dubbele listener — dan is
  dit de enige rem.

Het is dus **dubbele verdediging op het inhaalpad en enige verdediging op het
callbackpad**, en het gat zat in de tests, niet in de code.
`test_de_rem_weigert_een_tweede_keer_op_hetzelfde_moment` roept `_async_vuur` twee
keer met hetzelfde moment aan en eist dat de tweede weigert. Daarna wordt P3
gevangen en zijn **alle 17 mutaties gedekt**.

### De verplichte gevallen

Alle elf staan in `tests/test_planner.py`, met het nummer in de docstring:

| # | Geval | Test |
|---|---|---|
| 1 | herhalende wekker op de juiste dagen | `test_herhalende_wekker_vuurt_op_de_juiste_dagen` |
| 2 | eenmalige wekker vuurt één keer | `test_eenmalige_wekker_vuurt_een_keer` |
| 3 | herstart 5 min te laat → inhalen | `test_herstart_5_minuten_te_laat_haalt_in` |
| 4 | herstart 45 min te laat → overslaan + mededeling | `test_herstart_45_minuten_te_laat_slaat_over_met_mededeling` |
| 5 | herstart te laat met `last_fired` → niet opnieuw | `test_herstart_te_laat_met_last_fired_vuurt_niet_opnieuw` |
| 6 | `skip_next` slaat over en wordt gewist | `test_skip_next_slaat_een_moment_over_en_wordt_gewist` |
| 7 | wijzigen zegt de oude planning op | `test_wijzigen_zegt_de_oude_planning_op` |
| 8 | verwijderen laat niets meer vuren | `test_verwijderen_laat_niets_meer_vuren` |
| 9 | tijdzonewijziging herplant | `test_tijdzonewijziging_herplant` |
| 10 | DST voorjaar en najaar | `test_voorjaar_0230_wordt_overgeslagen`, `test_najaar_0230_vuurt_twee_keer` |
| 11 | uitgezette wekker: niet gepland, niet ingehaald | `test_uitzetten_zegt_de_planning_op`, `test_uitgezette_wekker_wordt_niet_ingehaald` |

Alle 25 tests zijn **NIEUW GEDRAG**: er was geen planner, dus er is niets te
bewaken. De regressiewacht op wat fase 3a bouwde staat in `test_store.py` en
`test_websocket.py` en is ongewijzigd geslaagd.

---

## Taak G — De livecontrole op 8129

Een eenmalige wekker op `2026-08-10T20:05:00+02:00`, gezet om 20:01, HA herstart,
en dan wachten.

### De planner vuurde op 20:05:00.012 — **12 ms afwijking**

Server-side tijdlijn uit `docker logs ha-alarm` (tijden in UTC, CEST = UTC+2):

```
18:01:12.678  planner   Planning opgebouwd: 1 wekker(s) gepland (met inhaalslag)
18:01:19.184  planner   Kernconfiguratie gewijzigd; planning wordt opnieuw opgebouwd
18:01:19.184  planner   Planning opgebouwd: 1 wekker(s) gepland
18:01:19.189  planner   Kernconfiguratie gewijzigd; planning wordt opnieuw opgebouwd
18:01:19.189  planner   Planning opgebouwd: 1 wekker(s) gepland
18:05:00.012  afvuren   Wekker 3b00…00 (Livecontrole fase 3b) afgegaan voor moment 2026-08-10T20:05:00+02:00
18:08:35.683  afvuren   Wekker 3b00…00 gestopt (user)
18:09:06.365  planner   Planning opgebouwd: 0 wekker(s) gepland
```

**Gemeten afwijking: +12 ms** ten opzichte van 20:05:00.000. Het `started`-event
kwam in de browser aan op `18:05:00.012Z` — dezelfde 12 ms, dus de weg van planner
naar kaart is binnen de meetprecisie gratis.

Ter vergelijking: fase 0 mat +3,4 ms op een `async_track_point_in_time`. Beide ruim
binnen wat voor een wekker uitmaakt.

### En de rest van de eisen, met de meting erbij

| Eis | Vóór | Ná |
|---|---|---|
| `last_fired` gevuld | `null` | `2026-08-10T20:05:00+02:00` |
| `last_fired` is het **bedoelde** moment | — | ja, exact gelijk aan de wektijd (geen jitter, geen "nu") |
| `ringing` gevuld | `[]` | `[<alarm_id>]` |
| `started`-event uit | — | 1 event, `{event:"started", person:"person.dev", name:"Livecontrole fase 3b", time:"20:05"}` |
| `next_fire` | `{at:"2026-08-10T20:05:00+02:00", text:"Vandaag 20:05"}` | `null` (eenmalig, dus op) |
| `last_message` | `null` | `null` — geen fout en geen mededeling, precies goed |

**Bonus, want het is één aanroep en het toetst de andere kant van de naad:**
`alarms/stop` twee keer aangeroepen. De eerste haalde de wekker uit `ringing` en
stuurde het `stopped`-event met `reason: "user"`; de tweede gaf geen fout en stuurde
**geen tweede event** — er staat ook maar één "gestopt"-regel in het log. Idempotent
zoals SPEC 15.8 eist, live bevestigd.

### Afwijking van de opdracht: de wekker is niet via `alarms/save` gezet

De opdracht vroeg de wekker "via de WebSocket-API" te zetten. Dat kon op 8129 niet,
en dat is een eigenschap van de testinstance, geen keuze:

**8129 heeft geen `music_assistant` config entry.** De geladen entries zijn
`sun, go2rtc, analytics, backup, shopping_list, radio_browser, google_translate,
domotiapp_alarm`. De koppeling mislukte in fase 0b (Spotify's OAuth-callback komt
niet terug, RadioBrowser's API antwoordt niet) en dat is toen bewust niet opgelost.
Zonder die entry is er geen enkele `media_player` met
`platform == "music_assistant"`, en dan **hoort** `alarms/save` de speaker af te
keuren met `not_allowed` — dat is de validatie uit SPEC 7.2 die precies doet wat ze
moet doen.

De wekker is daarom rechtstreeks in `.storage/domotiapp_alarm.alarms` gezet en HA
herstart. Wat dit wél en niet aantoont:

- **wel:** de planner leest de opslag, plant, vuurt op tijd, vult `last_fired` en
  `ringing`, stuurt het event, en `stop` werkt — alles wat taak G moest aantonen;
- **niet:** dat `alarms/save` een herplanning uitlokt. Dat is apart getoetst in
  `test_websocket_save_herplant`, een test die de klok bewust **niet** beweegt en
  alleen de draad tussen WebSocket en planner bewijst. En het `alarms/delete` aan het
  eind van de livecontrole liep wél via de WebSocket-API: de regel
  "Planning opgebouwd: 0 wekker(s)" om 18:09:06 is die herplanning, live.

Wat de eigenaar zou moeten doen om het volledig te sluiten: een werkende Music
Assistant-provider op 8129 koppelen (of MA aan de instance hangen met een provider
die geen OAuth nodig heeft), en dan een wekker via de kaart zetten. Zonder dat blijft
dit ene randje ongetoetst op de live instance.

---

## Wat niet lukte

### De dubbelzinnigheid in SPEC 13.4 stap 4

**Dit is het enige punt waarop SPEC volgens mij bijgewerkt moet worden, en ik heb
het niet zelf gedaan.**

SPEC 13.4 beschrijft de inhaalslag in zeven stappen. Stap 4 zegt: staat `skip_next`
aan, sla dan over en wis `skip_next`. Wat er niet staat, is of dat óók geldt voor een
moment dat **al voorbij was toen HA uit stond**.

Twee lezingen, en ze geven verschillende ochtenden:

- **letterlijk** (wat er nu staat, en wat ik heb gebouwd): de inhaalslag verbruikt
  `skip_next` op het gemiste moment. Zet je vrijdagavond "morgen overslaan" aan,
  gaat HA uit, en start hij zaterdag weer op, dan is `skip_next` verbruikt op
  zaterdag — ook al is er niets afgegaan. Maandag gaat de wekker normaal af.
- **naar bedoeling**: `skip_next` hoort te gelden voor de eerstvolgende keer dat de
  wekker écht zou afgaan, en een moment dat buiten het respijtvenster viel is nooit
  afgegaan, dus verbruikt hij niets.

Ik heb de letterlijke lezing gebouwd, omdat SPEC bindend is en de bedoeling raden
erger is dan een gemelde dubbelzinnigheid. Dit kostte wel een test: mijn eerste
`skip_next`-test viel om omdat de inhaalslag `skip_next` opsnoepte op het vrijdagse
moment, waarna maandag gewoon vuurde. Die test is aangepast (de wekker krijgt
`last_fired` op de vorige beurt, zodat de inhaalslag stil is) en toetst nu de regel
zelf, niet de wisselwerking.

**De vraag aan de eigenaar:** welke lezing is bedoeld? Bij de tweede moet SPEC 13.4
stap 4 een clausule krijgen ("alleen als het moment binnen het respijtvenster valt")
en verhuist de `skip_next`-controle in de inhaalslag naar ná de venstertoets.

### De WebSocket-API en een bevroren klok gaan niet samen

Bijna alle planner-tests gaan via de opslag plus `planner.async_herplan(hass)` in
plaats van via de WebSocket. Dat is geen luiheid, en het staat ook in de docstring
van de testmodule zodat niemand het later "opruimt":

het access token van `hass_ws_client` is een **JWT met `iat` en `exp`**. Een test die
de klok naar 29 maart 2026 zet, zet hem daarmee ook vóór het moment waarop het token
is uitgegeven, en dan is het antwoord `auth_invalid`. Daar bovenop gaven open
WebSocket-verbindingen bij grote kloksprongen `Lingering timer ...
WebSocketResponse._send_heartbeat`.

Eén test gebruikt daarom wél de WebSocket en beweegt de klok **niet**
(`test_websocket_save_herplant`): die bewijst de draad. De rest bewijst het gedrag.
Deze scheiding is bewust en niet gratis — het betekent dat de combinatie
"WebSocket-mutatie tijdens een DST-overgang" niet in een test staat.

### Windows kan geen `Europe/Amsterdam`

De Python op deze machine heeft geen `tzdata`, dus `ZoneInfo("Europe/Amsterdam")`
gooit `ZoneInfoNotFoundError`. Voor de scripts die de dev-opslag vulden is
`dt.timezone(dt.timedelta(hours=2))` gebruikt: in augustus levert dat exact dezelfde
ISO-string op. De **tests** draaien in Linux (`python:3.14-slim`) en gebruiken de
echte zone-database, dus de DST-tests zijn niet met deze omweg gemeten.

---

## Aannames

1. **`RESPIJT_MINUTEN` is een eigen constante**, geen hergebruik van de 30 minuten
   van de stoptimer uit SPEC 9.4. Dat die twee getallen beide 30 zijn, is toeval:
   het ene is "hoe lang na een gemiste wekker is het nog zinvol", het andere is "hoe
   lang blijft geluid aan". Ze zullen los van elkaar veranderen.

2. **De inhaalslag kijkt alleen naar het láátste gemiste moment**, niet naar alle
   gemiste momenten. Staat HA drie dagen uit, dan is er niet drie keer iets in te
   halen — er is één ochtend waarop het nog zinvol kan zijn. Getoetst in
   `test_inhaalslag_kijkt_alleen_naar_het_laatste_moment`. SPEC 13.3 ("geen catch-up
   in HA") wijst dezelfde kant op, maar zegt het niet met zoveel woorden.

3. **Overslaan zet `last_fired` op het overgeslagen moment.** Anders zou de volgende
   herstart binnen het venster hetzelfde moment opnieuw als "gemist" zien en alsnog
   afgaan. Geldt voor beide redenen om over te slaan (`skip_next` en buiten het
   venster).

4. **`async_herplan()` gooit nooit.** Een mutatie die slaagt maar waarvan de
   herplanning stukloopt, mag de WebSocket geen fout teruggeven — de wekker ís
   opgeslagen. De fout gaat naar het log. Het risico dat daar tegenover staat, is dat
   een structureel kapotte planner stil blijft; daarom logt hij op `exception`, met
   stacktrace.

5. **Het bedoelde moment wordt in de callback teruggerekend uit de wandklok**
   (`nu.replace(second=0, microsecond=0)`) in plaats van meegegeven aan de closure.
   De closure sluit alleen om de ID's, zodat de wekker op vuurmoment **opnieuw uit de
   opslag gelezen** wordt. Anders zou een wijziging die tussen plannen en vuren komt
   met een oude kopie afgaan.

6. **De naad met 3c is een aanroep, geen terugmelding.** `async_laat_afgaan()` krijgt
   alles als argument en geeft niets terug wat de planner gebruikt. Faalt het geluid,
   dan legt `afvuren.py` de melding vast en hoort de planner er niets van: een
   mislukte wekker mag de plánning niet stukmaken. `afvuren.py` documenteert per regel
   wat 3c waar invult.

---

## Opruimen van de dev-instance

- **De livecontrole-wekker is verwijderd**, via `alarms/delete` over de WebSocket
  (waarmee die route ook meteen live getoetst is). `.storage` bevat weer
  `{"persons": {"101e…0ec0": {"alarms": []}}}`.
- **Het `logger:`-blok in `.ha-dev-config/configuration.yaml` blijft staan.** Het zet
  `custom_components.domotiapp_alarm` op `debug` en levert de server-side
  tijdstempels waarmee de 12 ms hierboven gemeten is; fase 3c heeft hem net zo hard
  nodig. `.ha-dev-config/` staat in `.gitignore`, dus geen van beide wijzigingen komt
  in de repo terecht.

---

## `git status --porcelain`

```
 M custom_components/domotiapp_alarm/__init__.py
 M custom_components/domotiapp_alarm/const.py
 M custom_components/domotiapp_alarm/strings.json
 M custom_components/domotiapp_alarm/translations/en.json
 M custom_components/domotiapp_alarm/translations/nl.json
 M custom_components/domotiapp_alarm/volgende.py
 M custom_components/domotiapp_alarm/websocket.py
?? custom_components/domotiapp_alarm/afvuren.py
?? custom_components/domotiapp_alarm/meldingen.py
?? custom_components/domotiapp_alarm/planner.py
?? tests/test_planner.py
```

`SPEC.md` staat er niet tussen, en dat is de bedoeling. De bundel onder
`custom_components/domotiapp_alarm/` is na `npm run build` onveranderd: fase 3b raakt
geen frontend-code.
