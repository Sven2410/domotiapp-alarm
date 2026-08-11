# Fase 6 — Drie bevindingen uit de productieomgeving

Versie 1.0.0 draait bij de eigenaar. Hij heeft een echte wekker laten afgaan en
drie dingen gevonden. Dit rapport behandelt ze in de volgorde van de opdracht.

**Eén ding vooraf, en het staat hier bovenaan omdat het buiten de gestelde grens
valt.** De opdracht zegt: *"SPEC.md alleen wijzigen voor bevinding 1 en 3."*
Bevinding 2 is echter een opdracht om een **tekst uit SPEC 11.7** te repareren.
Die tekst staat letterlijk in SPEC en `meldingen.py` schrijft hem letterlijk over.
De reparatie kan dus niet bestaan zonder SPEC 11.7 te wijzigen. Dat is gedaan,
het is de enige plek buiten bevinding 1 en 3, en het is hier gemeld in plaats van
stil doorgevoerd. De nieuwe formulering is die van de eigenaar zelf ("het
afspelen is mislukt", met de reden van MA erbij).

---

## Samenvatting in één tabel

| Bevinding | Wat het was | Wat het nu is | Live bewezen |
|---|---|---|---|
| 1. Shuffle | een afspeellijst begon elke ochtend met hetzelfde nummer | `media_player.shuffle_set` vóór `play_media` bij `playlist`, `album`, `artist` | ja — 3× hetzelfde nummer zonder, 4× vier verschillende met |
| 2. De melding liegt | *"het gekozen geluid 'X' bestaat niet meer"* terwijl het geluid bestond | *"het geluid 'X' kon niet gestart worden"*, plus de reden van MA | ja — op de kaart, met een geluid dat aantoonbaar bestaat |
| 3. De schakelaar | een afgelopen eenmalige wekker bleef aan staan | `enabled: false` bij elk verbruikt moment; opnieuw aanzetten geeft een nieuw moment | ja — kaart toont de schakelaar uit, echte klik zet hem aan, `next_fire` wordt "Morgen 18:32" |

**297 Python-tests** (was 264), **77 JS-tests** (ongewijzigd), **22 mutaties
nagelopen in twee rondes, alle 22 gevangen** — drie gaten gevonden in ronde 1 en
gedicht.

---

## Bevinding 1 — Shuffle bij afspeellijsten

### Wat de bevinding is

Een wekker met een afspeellijst begon elke ochtend met hetzelfde nummer. Voor een
wekker verliest dat zijn werking: het geluid dat je moet wekken wordt het geluid
dat je niet meer hoort.

Gevraagd: shuffle staat **altijd** aan bij media met meerdere nummers —
afspeellijst, album, artiest. Geen instelling, geen veld in de opslag.

### Hoe je het aanroept

`music_assistant.play_media` **heeft geen shuffle-veld**. De service kent
`media_id`, `media_type`, `enqueue` en `radio_mode`, meer niet. Wat wél werkt is
`media_player.shuffle_set` op de speaker.

**En het moet vóór `play_media`.** Dat is niet een voorkeur maar een meting, in
de broncode van Music Assistant 2.9.11 (`controllers/player_queues.py:1533`):

```python
shuffle = queue.shuffle_enabled and len(queue_items) > 1 and not radio_mode
```

MA past shuffle toe **op het moment dat de queue geladen wordt**, op basis van
`shuffle_enabled` zoals dat dán staat. Zet je shuffle erna, dan is het eerste
nummer al gekozen en schud je alleen de rest — precies de klacht.

Dezelfde regel laat twee dingen zien die MA zelf al goed doet en die dus niet
nagebouwd hoeven: een queue met één item wordt nooit geschud
(`len(queue_items) > 1`), en een radio-queue laat MA met opzet ongeschud
(`not radio_mode`).

### Wat er gebouwd is

- **`shuffle.py`** — een pure module met één functie, `moet_shuffelen(media_type)`.
  Puur, want het is een beslissing en geen aanroep (CLAUDE.md, werkafspraken).
- **`MEERSTUKS_SOORTEN`** in `const.py`: `{"playlist", "album", "artist"}`.
  Bewust **niet** `ONEINDIGE_SOORTEN` hergebruikt: dat gaat over **duur**, dit
  over **aantal**. Ze overlappen alleen in `playlist`. Hergebruik zou `radio`
  laten schudden (zinloos) en `album` en `artist` niet (de bevinding zelf).
  Er staat een test op die dat verschil vastlegt.
- **Stap 5 in `afvuren.py`**, vóór stap 6 (`play_media`). SPEC 9.1 telt daarmee
  acht stappen in plaats van zeven.
- **Het voorbeeld schudt mee** (`voorbeeld.py`). Een voorbeeld dat altijd met
  nummer 1 begint terwijl de wekker schudt, laat iets anders horen dan wat er
  's ochtends gebeurt.

**Een mislukte `shuffle_set` houdt de wekker niet tegen.** Er wordt op `WARNING`
gelogd en het afspelen gaat door. Shuffle is een verbetering van de wekker en
niet de wekker zelf; het faalgeval is "hij begon bij nummer 1", en dat is precies
de toestand van vóór deze regel. Een noodrem die daarvoor een stille ochtend
riskeert, zou niet in verhouding staan (valkuil 41).

### De livemeting

**Wat er nieuw is aan deze meting:** album, artiest en los nummer waren op deze
instance nooit te toetsen — er is geen streamingprovider. MA heeft echter een
ingebouwde **`test`-muziekprovider** die 5 artiesten, 25 albums en 500 tracks
genereert en ze streamt als een lang stiltebestand. Die stond al aan op deze
instance. Daarmee is `media_type: album` en `playlist` nu wél live te toetsen.
Zie "Wat niet lukte" voor de grens die de test-provider wél heeft.

Gemeten op `media_player.wekker_slaapkamer` met de afspeellijst
`library://playlist/6` ("Recently added tracks", 500 tracks in vaste volgorde).
Zelfde speaker, zelfde afspeellijst, alleen `shuffle` verschilt:

| shuffle | poging | eerste nummer |
|---|---|---|
| **uit** | 1 | `church music Test Track 4 - 4 - 19` |
| **uit** | 2 | `church music Test Track 4 - 4 - 19` |
| **uit** | 3 | `church music Test Track 4 - 4 - 19` |
| **aan** | 1 | `church music Test Track 4 - 4 - 10` |
| **aan** | 2 | `church music Test Track 4 - 3 - 3` |
| **aan** | 3 | `church music Test Track 4 - 0 - 14` |
| **aan** | 4 | `church music Test Track 4 - 1 - 17` |

Drie keer identiek zonder, vier keer verschillend met. Dat is de bevinding en de
reparatie in één tabel.

**En door het echte afvuurpad**, twee wekkers die werkelijk afgingen op dezelfde
afspeellijst:

| wekker | eerste nummer |
|---|---|
| 18:25 | `church music Test Track 4 - 0 - 15` |
| 18:28 | `church music Test Track 4 - 4 - 16` |

**De volgorde van de aanroepen**, uit één `call_service`-abonnement (valkuil 9),
tijdstempels ten opzichte van het bedoelde moment:

```
18:28:00.013546  media_player.volume_set     (0)
18:28:00.017827  media_player.shuffle_set    (true)
18:28:00.020198  music_assistant.play_media  (library|playlist/6)
```

Volume nul op **+13,5 ms**, shuffle op **+17,8 ms**, geluid op **+20,2 ms**. De
shuffle-stap kost **2,4 ms** en staat aantoonbaar vóór het geluid.

**De controle met radio**, dezelfde wekker maar met
`radiobrowser://radio/39a19b72-…` ("SomaFM Beat Blender"):

```
18:32:00.014634  media_player.volume_set     (0)
18:32:00.018517  music_assistant.play_media
```

**Geen `shuffle_set`.** Precies zoals SPEC 9.6 het voorschrijft: bij radio is er
één stream en geen volgorde om te schudden.

### Wat SPEC 9 nu zegt

Nieuwe sectie **9.6** met de tabel, de reden, de meting uit MA's broncode en het
faalgedrag. SPEC 9.1 telt nu acht stappen; stap 4 is de shuffle en de tekst
noemt uitdrukkelijk dat stap 4 vóór stap 5 dezelfde vorm heeft als stap 2 vóór
stap 5: **wat de queue bepaalt moet er zijn vóórdat de queue bestaat.**

---

## Bevinding 2 — De melding liegt

### Wat er gebeurde

Een wekker ging niet af en de melding luidde:

> De wekker van 06:45 is niet afgegaan: het gekozen geluid 'NF 🎈' bestaat niet
> meer. Kies een nieuw geluid.

Het geluid bestond. Spotify was in Music Assistant niet geautoriseerd en gaf
`"No playable items found"`.

Dit is in `docs/fase-3c/RAPPORT-BIS.md` voorspeld en er staat sinds toen een
comment in `afvuren.py` die het toegeeft: *"De tekst van SPEC 11.7 stelt het
zekerder dan wij het weten."* Er is toen niets aan gedaan. Nu wel.

### Wat de code weet, en wat hij zei

Op het punt waar deze melding ontstaat, is er precies één ding vastgesteld: de
aanroep `music_assistant.play_media` heeft geweigerd. Alles daarna is gissen. De
oude tekst deed twee beweringen die niet uit die weigering volgen:

1. **"bestaat niet meer"** — een uitspraak over het bestaan van het item, terwijl
   er niets is opgevraagd. Sinds fase 3c-bis is er geen voorafgaande
   URI-controle meer, dus er is zelfs geen zwak signaal.
2. **"Kies een nieuw geluid"** — een handeling die het probleem niet oplost als
   de oorzaak bij de provider ligt, en die de klant een werkende keuze laat
   weggooien.

### De nieuwe tekst

```
De wekker van 06:45 is niet afgegaan: het geluid 'Beat Blender' kon niet gestart
worden. Music Assistant meldde: "No playable items found". Controleer het geluid
in Music Assistant, of kies een ander.
```

Drie keuzes die erin zitten:

- **De reden van MA gaat mee**, want die is het enige dat naar de werkelijke
  oorzaak wijst. Ontbreekt hij, dan vervalt dat deel van de zin — geen leeg
  citaat en geen verzonnen oorzaak.
- **Alleen de eerste regel** van de fout. MA zet de mededeling vooraan; wat erna
  komt is context voor een log en niet voor een kaart, en `last_message` staat in
  de **opslag** en blijft daar tot iemand op "Begrepen" drukt.
- **De naam `sound_gone` blijft.** Die staat in de opslag van elke klant die
  1.0.0 draaide en de kaart vergelijkt erop (SPEC 14.2.1). Alleen de tekst is
  veranderd. Hernoemen zou oude meldingen onleesbaar maken voor een nieuwe kaart.

De reden van de **eerste** poging (mét `radio_mode`) wordt bewust niet bewaard:
die is meestal `UnsupportedFeaturedException`, en dat is een mededeling over onze
eigen providerlijst en niet over het geluid.

### Live bewezen, met een geluid dat aantoonbaar bestaat

De MA-test-provider levert albums die in de bibliotheek staan en via onze eigen
`sound/search` te vinden zijn, maar die **niet af te spelen** zijn: de provider
implementeert `get_album_tracks` niet en MA geeft `NotImplementedError`. Dat is
dus letterlijk het geval van de eigenaar: het geluid bestaat, het start niet.

Wat de kaart toont (screenshot in dit rapport genoemd, meting uit de opslag):

> De wekker van 18:36 is niet afgegaan: het geluid 'gangsta rap Test Album 0' kon
> niet gestart worden. Music Assistant meldde: "NotImplementedError". Controleer
> het geluid in Music Assistant, of kies een ander.

`kind: "sound_gone"`, `severity: "error"`, in rood met de knop **Begrepen**. De
oude tekst zou hier hebben beweerd dat een album dat gewoon in de bibliotheek
staat niet meer bestaat.

### De audit van SPEC 11.7 — wat er nog meer te veel claimt

Gevraagd: alle meldingsteksten nalopen op dezelfde fout. Alle acht zijn
nagelopen. **Twee claimen iets dat de code niet weet.** Ze zijn **niet**
gerepareerd — dat valt buiten de opdracht en de formulering is een keuze van de
eigenaar. Hier staan ze met de vindplaats.

**a) `volume_ramp_unavailable`** — *"De wekker is afgegaan **op het ingestelde
volume**; het oplopende volume was op deze speaker niet mogelijk."*

`afvuren.py:198-210`. Deze melding ontstaat doordat `volume_set(0)` faalt.
Daarna doet de code één poging tot `volume_set(doel_pct)` — met **dezelfde
service die net weigerde** — en de uitkomst daarvan wordt **weggegooid**:

```python
oploop_kan = await async_zet_volume(hass, speaker, 0)
if not oploop_kan:
    ...
    await async_zet_volume(hass, speaker, doel_pct)   # <- resultaat niet gelezen
```

De melding beweert dus als feit wat een onbeoordeelde poging was. Het
waarschijnlijke werkelijke geval: de speaker neemt geen enkel volume aan en de
wekker speelt op de stand van gisteravond — wat hard of juist onhoorbaar kan
zijn, en dat is precies wat de klant zou willen weten.

**Nauwkeuriger zou zijn:** *"De wekker is afgegaan, maar het volume was op deze
speaker niet in te stellen; het oplopende volume is overgeslagen."*

**b) `skipped_grace_window`** — *"Je wekker van 06:45 is niet afgegaan **omdat
Home Assistant uit stond**."*

`planner.py`, stap 5/6 van de inhaalslag. Wat de code vaststelt is: dit moment is
verstreken, er staat geen `last_fired` op, en het ligt verder dan 30 minuten
terug. Daaruit volgt **niet** dat Home Assistant uit stond. Een narekenbaar
tegenvoorbeeld dat geen storing is:

> Iemand maakt om 12:00 een wekker voor 06:45 op vandaag. Home Assistant draait
> de hele dag. Bij de eerstvolgende herstart vindt de inhaalslag een verstreken
> 06:45 zonder `last_fired` en meldt dat Home Assistant uit stond.

De **soort** klopt (het is een mededeling en geen fout, en de klant kon er niets
aan doen), de **oorzaak** is gegist. Nauwkeuriger zou zijn: *"Je wekker van 06:45
is niet afgegaan; Home Assistant heeft dat moment gemist."*

**De zes andere teksten claimen niet te veel:**

| `kind` | waarom hij wél klopt |
|---|---|
| `speaker_unavailable` | `noodrem.controleer_speaker` heeft de state op `unavailable` gezien |
| `ma_unavailable` | onderscheiden van de vorige op `async_loaded_entries` van de MA-entry |
| `speaker_lost_during_play` | zegt met opzet *"mogelijk niet hoorbaar geweest"* — de zwakste bewering die de meting toelaat |
| `light_failed` | de `light.turn_on` gooide; "kon niet aangezet worden" is precies dat |
| `skipped_by_user` | `skip_next` stond op `true`, en dat kan alleen de klant zetten |
| `sound_gone` | sinds deze ronde |

---

## Bevinding 3 — De schakelaar van een afgelopen eenmalige wekker

### Bug of uiteenlopen? Bug.

SPEC 14.5 staat er sinds fase 2 en zegt: *"Na afgaan wordt `enabled` op `false`
gezet."* In de code stond **nergens** iets dat dat deed. Nagezocht op elke
schrijver van `enabled`: alleen `alarms/save` (vanuit de kaart) en
`alarms/set_enabled` (de schakelaar). Het afvuren en het overslaan raakten het
veld niet aan.

Het is dus geen uiteenlopende lezing en geen ontwerpkeuze die vergeten is op te
schrijven — het is een eis die nooit geïmplementeerd is en die tot fase 6 niet
opviel omdat alle eerdere metingen met **herhalende** wekkers zijn gedaan.

### De reparatie, en waarom hij op één plek staat

Er zijn **drie** manieren waarop een moment opgaat, en ze lopen door twee
verschillende bestanden:

| Wat er gebeurde | Waar | `enabled` daarna |
|---|---|---|
| de wekker ging af | `afvuren.async_laat_afgaan`, stap 0 | `false` |
| de noodrem hield hem tegen | idem — `last_fired` gaat vóór de noodrem | `false` |
| het moment werd overgeslagen | `planner._async_sla_over` | `false` |

Welke velden er dan veranderen, staat in één functie:
`afvuren.velden_bij_verbruikt_moment(wekker, moment)`. Zonder die ene plek krijgt
de ene route wel een uitgezette wekker en de andere niet — en dat is precies het
soort verschil dat pas bij een klant opvalt.

`volgende.is_eenmalig(wekker)` beslist of het geldt. Een herhalende wekker gaat
morgen gewoon weer af.

### Opnieuw aanzetten geeft een nieuw moment

Gevraagd door de eigenaar, en het is de andere helft van dezelfde bevinding:
zonder deze regel is de schakelaar een **knop die niets doet**. `one_shot_at`
ligt in het verleden, de planner plant hem niet (rem 1, SPEC 13.1), en de kaart
toont "geen volgende keer" bij een wekker die aan staat.

`alarms/set_enabled` berekende **geen** nieuwe `one_shot_at` — gecontroleerd,
zoals gevraagd. Dat is nu gebouwd en vastgelegd in **SPEC 15.3**.

**Alleen als het moment verstreken is**, en dat is geen voorzichtigheid maar
noodzaak:

> Staat een wekker van 06:45 op morgen en zet de klant hem om 05:00 uit en weer
> aan, dan is "de eerstvolgende 06:45" **vandaag**. Een wekker die anderhalf uur
> later afgaat dan de klant zag, is erger dan de knop die we repareren.

Een herhalende wekker heeft geen `one_shot_at` en komt er niet langs. De
schemaregel in `validatie.py` weigert de combinatie van `days` en `one_shot_at`,
dus een implementatie die daar wél zou rekenen maakt de wekker **onopslaanbaar** —
en dat komt pas boven bij de eerstvolgende save. Er staat een regressiewacht op.

### De livemeting

Een eenmalige wekker van 18:32 die werkelijk afging op de dev-instance:

**Na het afgaan en stoppen**, uit `alarms/get`:

```json
{"enabled": false,
 "one_shot_at": "2026-08-11T18:32:00+02:00",
 "last_fired":  "2026-08-11T18:32:00+02:00"}
next_fire: null
```

**Op de kaart**: `18:32 — Meting — "Eenmalig — afgelopen"`, schakelaar **uit**.
Vóór deze ronde stond hij hier aan.

**Daarna een echte klik op de schakelaar** — capture-listener op `window` met
`composedPath()` (valkuil 10), coördinaten omgerekend met de factor 0,81667 uit
valkuil 43 en vlak vóór de klik met een hit-test gecontroleerd:

```json
{"isTrusted": true, "x": 1245, "y": 113,
 "doel": "button < div < slot < #document-fragment"}
```

De knop is `role="switch"`, `class="schakelaar"`,
`aria-label="Wekker Meting aan of uit"`, en `aria-checked` ging van `false` naar
`true`.

**Na de klik:**

```json
{"enabled": true,
 "one_shot_at": "2026-08-12T18:32:00+02:00",
 "last_fired":  "2026-08-11T18:32:00+02:00"}
next_fire: {"at": "2026-08-12T18:32:00+02:00", "text": "Morgen 18:32"}
```

Dezelfde wandkloktijd, één dag later. En let op `last_fired`: die blijft op
gisteren staan en ligt daarmee **vóór** het nieuwe moment, dus de bewaker uit
SPEC 13.4 stap 3 laat de wekker gewoon door.

De kaart toonde daarna **"Eenmalig"** in plaats van "Eenmalig — afgelopen", en
**"Morgen 18:32"** in de onderregel.

---

## De tests

**297 Python-tests** (was 264 na fase 5), **77 JS-tests** (ongewijzigd — er is
niets aan `src/` veranderd, de bundel is byte-identiek gebleven op
52.129 bytes / `015a09e66d81`).

### Nieuw, met hun label

Elke test hieronder is **op de code van vóór de fix gedraaid**. De uitvoer staat
onder de tabel.

| Test | Label |
|---|---|
| `test_shuffle.py` — 15 gevallen op de pure beslissing | NIEUW GEDRAG (de module bestond niet) |
| `test_een_afspeellijst_wordt_geschud_voordat_hij_start` | NIEUW GEDRAG |
| `test_radio_wordt_niet_geschud` | **REGRESSIEWACHT** |
| `test_een_mislukte_shuffle_houdt_de_wekker_niet_tegen` | NIEUW GEDRAG |
| `test_de_melding_beweert_niet_dat_het_geluid_weg_is` | NIEUW GEDRAG |
| `test_de_reden_van_music_assistant_gaat_mee_in_de_melding` | NIEUW GEDRAG |
| `test_zonder_reden_staat_er_geen_lege_toevoeging` | NIEUW GEDRAG |
| `test_alleen_de_eerste_regel_van_de_reden_komt_op_de_kaart` | NIEUW GEDRAG |
| `test_een_eenmalige_wekker_zet_zichzelf_uit_na_het_afgaan` | NIEUW GEDRAG |
| `test_een_herhalende_wekker_blijft_aan_staan` | **REGRESSIEWACHT** |
| `test_een_eenmalige_wekker_die_niet_afgaat_gaat_ook_uit` | NIEUW GEDRAG |
| `test_een_overgeslagen_eenmalige_wekker_gaat_ook_uit` | NIEUW GEDRAG |
| `test_een_overgeslagen_herhalende_wekker_blijft_aan` | **REGRESSIEWACHT** |
| `test_aanzetten_van_een_verlopen_eenmalige_wekker_geeft_een_nieuw_moment` | NIEUW GEDRAG |
| `test_uitzetten_en_aanzetten_verzet_een_toekomstige_wekker_niet` | NIEUW GEDRAG |
| `test_een_toekomstig_moment_blijft_staan_ook_als_het_afwijkt` | NIEUW GEDRAG |
| `test_aanzetten_van_een_herhalende_wekker_verzint_geen_one_shot_at` | **REGRESSIEWACHT** |

### Gedraaid op de code van vóór de fix

`custom_components/` teruggezet naar `main`, de tests laten staan:

```
=== test_shuffle.py (module bestaat nog niet) ===
ERROR tests/test_shuffle.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!

=== de rest ===
FAILED tests/test_afvuren.py::test_een_afspeellijst_wordt_geschud_voordat_hij_start
FAILED tests/test_afvuren.py::test_de_melding_beweert_niet_dat_het_geluid_weg_is
FAILED tests/test_afvuren.py::test_de_reden_van_music_assistant_gaat_mee_in_de_melding
FAILED tests/test_afvuren.py::test_zonder_reden_staat_er_geen_lege_toevoeging
FAILED tests/test_afvuren.py::test_een_eenmalige_wekker_zet_zichzelf_uit_na_het_afgaan
FAILED tests/test_afvuren.py::test_een_eenmalige_wekker_die_niet_afgaat_gaat_ook_uit
FAILED tests/test_planner.py::test_een_overgeslagen_eenmalige_wekker_gaat_ook_uit
FAILED tests/test_websocket.py::test_aanzetten_van_een_verlopen_eenmalige_wekker_geeft_een_nieuw_moment
8 failed, 122 passed in 27.73s
```

De drie regressiewachten slagen daar, zoals hun label zegt. `test_shuffle.py` kan
niet eens verzameld worden omdat de module er niet is; dat is een triviale
mislukking en daarom staat de waarde van dat bestand in de mutatieproef en niet
hier.

**Twee tests zijn ná deze run aangescherpt** omdat ze de val van *"de setup faalt
niet"* in liepen (CLAUDE.md, werkafspraken):

- `test_een_mislukte_shuffle_houdt_de_wekker_niet_tegen` slaagde op de oude code
  omdat daar geen `shuffle_set` bestaat en er dus niets kan mislukken. Er staat
  nu een positieve controle vóór (*"er is niets misgegaan om op te toetsen"*) en
  een assertie op de `WARNING`.
- `test_radio_wordt_niet_geschud` is van NIEUW GEDRAG naar **REGRESSIEWACHT**
  gezet, met in de docstring waarom: hij slaagt op de oude code per definitie, en
  zijn waarde ligt aan de andere kant — hij vangt een implementatie die *altijd*
  shuffelt.

---

## De mutatieproef

Script: `scripts/mutaties-fase-6.py`, zodat de proef herhaalbaar is en niet in
een terminaluitvoer verdwijnt. Elke mutatie is een letterlijke tekstvervanging,
wordt gezet, getest en teruggezet — ook als pytest ontploft.

**Ronde 1: 18 mutaties, 15 gevangen.** **Ronde 2: 4 mutaties erbij op de randen
die ronde 1 niet raakte.** Eindstand na het dichten: **22 van 22 gevangen.**

| | Mutatie | Gevangen |
|---|---|---|
| M1 | `moet_shuffelen` altijd `True` — ook radio | ja |
| M2 | `moet_shuffelen` altijd `False` | ja |
| M3 | geen `.strip().lower()` op `media_type` | ja |
| M4 | bij twijfel wél shuffelen | ja |
| M5 | **shuffle ná `play_media`** — de bevinding zelf | ja |
| M6 | `shuffle: False` meesturen | ja |
| M7 | de eenmalige wekker gaat niet uit | ja |
| M8 | élke wekker gaat uit na één keer afgaan | ja |
| M9 | de reden van MA wordt weggegooid | ja |
| M10 | een lege reden wordt tóch doorgegeven | ja |
| M11 | de reden komt niet bij de melding aan | ja |
| M12 | de reden altijd invoegen, ook leeg | ja |
| M13 | de oude, liegende tekst terug | ja |
| M14 | `is_eenmalig` omgedraaid | ja |
| M15 | overslaan zet de eenmalige wekker niet uit | ja |
| M16 | aanzetten berekent geen nieuw moment | ja |
| M17 | **de rem op een toekomstig moment weg** | **NEE → gedicht** |
| M18 | een herhalende wekker krijgt ook een `one_shot_at` | ja |
| M19 | **`blocking=False` op `shuffle_set`** | **NEE → gedicht** |
| M20 | **de hele foutmelding op de kaart** | **NEE → gedicht** |
| M21 | het nieuwe moment is "nu" in plaats van de wektijd | ja |
| M22 | `album` en `artist` uit `MEERSTUKS_SOORTEN` | ja |

### De drie gaten, en wat ze waren

Volgens de indeling van valkuil 34 is elk gat er één van drie soorten, en ze
vragen verschillende dingen.

**M17 — de rem op een toekomstig moment. Testgat, maar pas nadat het narekenen
klaar was.** De test die hem had moeten vangen
(`test_uitzetten_en_aanzetten_verzet_een_toekomstige_wekker_niet`) **kán** hem
niet vangen, en dat is narekenbaar:

> `one_shot_at` is door `alarms/save` berekend als "de eerstvolgende 06:45 ná
> toen". Zolang dat moment nog in de toekomst ligt, is "de eerstvolgende 06:45 ná
> nu" **dezelfde**, want elk passend moment ná nu is ook ná toen. Opnieuw rekenen
> levert daar per definitie hetzelfde op.

De verleiding was dus om de rem voor onbereikbaar te verklaren en eruit te
halen. Dat zou fout zijn geweest: er is wél een toestand waarin `one_shot_at` in
de toekomst ligt maar **niet** op de ingestelde wandkloktijd valt — na een
tijdzonewijziging (SPEC 13.2), want `one_shot_at` is een absoluut moment en de
offset eronder is verschoven. Op dát pad staat nu een test.

**M19 — `blocking=False` op de shuffle-aanroep. Testgat.** Dit is valkuil 42 in
een nieuwe jas: met `blocking=False` verpakt HA de aanroep in
`_run_service_call_catch_exceptions` (`core.py:2953-2959`) en bereikt de exceptie
onze `except` **nooit**. De aanroep lijkt dan altijd te slagen, en niemand komt
er ooit achter dat de speaker geen shuffle aankan. De ordeningstest ving het niet
omdat die een *geslaagde* shuffle gebruikt. De test op de mislukking let nu op de
`WARNING` — dat is het bewijs dat de fout ons bereikt heeft.

**M20 — de hele foutmelding op de kaart. Testgat.** Er was geen test met een
meerregelige fout. `last_message` staat in de **opslag** en blijft daar tot
iemand op "Begrepen" drukt; een stacktrace in dat veld maakt de kaart onleesbaar
en gaat niet vanzelf weg.

### Eén mutatie die met opzet niet in de lijst staat

`_reden_van` teruggeven als `str(fout)` zonder `.strip()` is een **equivalente
mutant** voor alle bereikbare invoer: een exceptie zonder tekst geeft dan `""`,
en `meldingen.tekst_voor` doet daar `(extra.get("ma_reden") or "").strip()`
overheen. De uitkomst is identiek. Er is geen test voor geschreven — een test die
een verschil vastlegt dat er niet is, suggereert dekking die er niet is (fase 4c
heeft die categorie aan valkuil 34 toegevoegd).

---

## Wat niet lukte

**1. Een album is op deze instance niet af te spelen.** De MA-`test`-provider
levert 25 albums en 500 tracks in de bibliotheek, en ze zijn via onze eigen
`sound/search` te vinden, maar `player_queues/play_media` op een album-URI geeft
`NotImplementedError`: de provider implementeert `get_album_tracks` niet. De
shuffle-meting is daarom op een **afspeellijst** gedaan en niet op een album. De
codepaden zijn identiek — `moet_shuffelen` geeft voor beide `True` en de aanroep
is dezelfde — maar dat is een redenering en geen meting, en dat hoort hier te
staan. Het geval is wel als **meting voor bevinding 2** gebruikt: een geluid dat
aantoonbaar bestaat en toch niet start, is precies wat de oude tekst verkeerd
beschreef.

**2. Artiest is niet gemeten.** Zelfde reden, en de test-provider heeft er
hetzelfde gat. `artist` staat in `MEERSTUKS_SOORTEN` op grond van de opdracht van
de eigenaar en is alleen in de Node-tests afgedekt.

**3. De eerste poging tot een derde afvuurmeting is weggegooid.** Ik las
`media_title` direct nadat het log zei dat de wekker was afgegaan, terwijl
`play_media` 2,1–2,6 s blokkeert en de state daarna pas verandert. De gemeten
titel was die van de vórige run. Dat is valkuil 37 in een variant: niet een
bevroren `hass`, maar een verse `hass` die de nieuwe waarde nog niet had. De
metingen in dit rapport wachten daarom 6 s of vergelijken op **verandering**.

**4. De WebSocket-verbinding van de meetpagina viel één keer weg**
(`ERR_CONNECTION_LOST`, code 3) na een reeks snelle commando's. Alles wat erna
kwam gaf een kale `3` als fout, wat er als een productfout uitziet en het niet
is. Een herlaadbeurt loste het op; de server logde niets. Vermeld omdat de
volgende meting er weer tegenaan kan lopen.

**5. `panel: true` en `getCardSize()` blijven onaangeraakt.** Ze staan al als
openstaand punt in `CLAUDE.md` en horen niet bij deze drie bevindingen.

---

## Waarnemingen voor de eigenaar (niet gebouwd)

**a) Shuffle blijft aan staan na de wekker.** Het volume wordt bij het stoppen
teruggezet (SPEC 9.5) met als motivatie: *"zonder dit staat de speaker de rest
van de dag op het wekvolume, en dat is een bijwerking die de klant niet heeft
gevraagd."* Precies diezelfde redenering geldt voor shuffle, en gemeten: na de
afspeellijst-wekker stond `shuffle` op de speaker nog op `true`. Speelt de klant
daarna zelf een album, dan is dat geschud zonder dat hij erom vroeg.

Niet gebouwd, want het is een uitbreiding van de opdracht en het kost een extra
state-lezing en een extra aanroep in het stoppad. **Aanbeveling:** dezelfde
behandeling als het volume — lezen vóór stap 5, terugzetten bij het stoppen,
niets terugzetten als het niet te lezen was.

**b) De twee teksten uit de audit** (`volume_ramp_unavailable` en
`skipped_grace_window`) wachten op een woordkeuze. Voorstellen staan hierboven.
Ze staan nu ook in `CLAUDE.md` als openstaand punt, naast het punt over
`sound_gone` dat met deze ronde vervalt.

**c) De MA-`test`-provider is de moeite waard om te houden.** Hij maakt
`media_type: album` en `playlist` toetsbaar op een instance zonder
streamingprovider, en hij was de enige manier om deze fase live te meten. Zijn
grens staat onder "Wat niet lukte".

---

## Aannames

1. **`artist` hoort in `MEERSTUKS_SOORTEN`** op grond van de opdracht ("media met
   meerdere nummers — afspeellijst, album, artiest") en niet op grond van een
   meting; zie "Wat niet lukte" punt 2.
2. **Het voorbeeld (SPEC 5.4) schudt mee.** De opdracht noemt alleen de wekker.
   De redenering staat in `voorbeeld.py` en in SPEC 9.6: een voorbeeld dat anders
   klinkt dan de wekker is geen voorbeeld. Terugdraaien is één regel.
3. **De nieuwe `one_shot_at` wordt alleen berekend als het moment verstreken is.**
   De opdracht zegt "pakt de eerstvolgende keer dat die tijd voorbijkomt" zonder
   die voorwaarde; zonder de voorwaarde kan de wekker naar vroeger schuiven. De
   afweging staat in SPEC 15.3 en in de docstring.
4. **SPEC 11.7 is gewijzigd**, buiten de grens "alleen voor bevinding 1 en 3" om.
   Zie de inleiding van dit rapport.

---

## `git status --porcelain`

Vlak vóór de commit, op branch `fase-6/productiebevindingen`:

```
 M CLAUDE.md
 M SPEC.md
 M custom_components/domotiapp_alarm/afvuren.py
 M custom_components/domotiapp_alarm/const.py
 M custom_components/domotiapp_alarm/meldingen.py
 M custom_components/domotiapp_alarm/planner.py
 M custom_components/domotiapp_alarm/volgende.py
 M custom_components/domotiapp_alarm/voorbeeld.py
 M custom_components/domotiapp_alarm/websocket.py
 M tests/conftest.py
 M tests/test_afvuren.py
 M tests/test_planner.py
 M tests/test_websocket.py
?? custom_components/domotiapp_alarm/shuffle.py
?? docs/fase-6/
?? scripts/mutaties-fase-6.py
?? tests/test_shuffle.py
```

Ná de commit en de push: leeg. `custom_components/domotiapp_alarm/frontend/` staat
er **niet** tussen — er is niets aan `src/` veranderd en de bundel is byte-identiek
gebleven.

**CI op de PR: alle vier groen** (bundelvergelijking, hassfest, JS-tests,
Python-tests), run `31514349229`.
