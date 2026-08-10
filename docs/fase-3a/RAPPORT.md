# Fase 3a — De opslaglaag en de WebSocket-API

De volledige server-side laag **zonder klok**: opslag, validatie, foutgedrag,
labelfiltering en de negen WebSocket-commando's. Geen planner, geen afvuren, geen
noodrem-uitvoering — dat is fase 3b.

**SPEC.md is niet gewijzigd.** Er is één plek waar de bevindingen van taak A om een
SPEC-correctie vragen; die is gemeld en niet zelf doorgevoerd, zie
[Taak A](#taak-a--de-twee-vragen-die-spec-doorschoof).

---

## Taak A — De twee vragen die SPEC doorschoof

### A1 — `radio_mode`: **tak B geldt**

**De waarschuwing uit SPEC 8.3 blijft staan.** Niet omdat het parameter niet
bestaat, maar omdat het op deze instance **hard faalt** en er dan niets speelt.

**Wat er wél werkt.** Het parameter is van begin tot eind doorverbonden:

| Laag | Vindplaats |
|---|---|
| HA-service accepteert het | `components/music_assistant/services.py:141` — `vol.Optional(ATTR_RADIO_MODE): vol.Coerce(bool)` |
| HA-integratie geeft het door | `components/music_assistant/media_player.py:406, 556` — `radio_mode=radio_mode or False` |
| Client accepteert het | `music_assistant_client/player_queues.py:204-214` — `radio_mode: bool = False` |

**Wat er niet werkt — gemeten, met een controle ernaast.** Op de draaiende
MA-server (2.9.11, schema 31) is dezelfde track twee keer afgespeeld op een
snapcast-speaker:

```
zonder radio_mode : HTTP 200, queue items=1, current="church music Test Track 4 - 0 - 0"
met    radio_mode : HTTP 500, queue items=0, state=idle
```

De serverfout:

```
UnsupportedFeaturedException: No Music Provider found that supports requesting
similar tracks.
  music_assistant/controllers/player_queues.py:1484 in _handle_play_media
  music_assistant/controllers/player_queues.py:2773 in _get_radio_tracks
```

`radio_mode` heeft dus een muziekprovider nodig met de feature
**`ProviderFeature.SIMILAR_TRACKS`** (`music_assistant_models/enums.py:627`). Op
deze instance heeft geen enkele provider die. Welke providers hem wél hebben,
uit hun broncode: `spotify`, `tidal`, `apple_music`, `ytmusic`, `deezer`,
`soundcloud`, `plex`, `jellyfin`, `emby`, `opensubsonic` — kortom precies de
providers die een echte klant heeft, en geen van de gratis providers.

**Twee dingen die het rapport hierbij moet zeggen.**

1. **Het faalgedrag is erger dan een nummer dat afloopt.** Zonder een
   `SIMILAR_TRACKS`-provider geeft `radio_mode: true` een **exceptie** en speelt er
   **niets**. Een los nummer dat na drie minuten stopt is hinderlijk; een wekker
   die helemaal niet afgaat is stuk. Blind `radio_mode` meesturen zou dus een
   verslechtering zijn, niet een verbetering.

2. **Er is een derde mogelijkheid die SPEC niet beschrijft, en die meld ik in
   plaats van hem zelf te kiezen.** De feature is **opvraagbaar**: `providers`
   geeft per provider zijn `supported_features`, dus de integratie kán
   `radio_mode` meesturen *alleen wanneer* er een provider met `similar_tracks`
   is, en anders de waarschuwing tonen. Dat is niet tak A en niet tak B maar een
   voorwaardelijke variant. **SPEC 8.3.1 kent die niet**, en SPEC wijzigen is in
   deze fase uitgesloten — dus tak B is wat er nu geldt, en de voorwaardelijke
   variant is een SPEC-correctie die de eigenaar kan overwegen.

Voor fase 3a heeft dit geen gevolgen: er wordt in deze fase niets afgespeeld.

### A2 — De URI-controle: **er is een directe route, maar niet via Home Assistant**

Dit is geen schone tak A en geen schone tak B, en het verschil is belangrijk genoeg
om precies op te schrijven.

**Er zijn twee directe controles in de MA-client**, gevonden in
`music_assistant_client/music.py`:

| Aanroep | Regel | Schema | Uitkomst |
|---|---|---|---|
| `music/verify_item_uri` | 721-739 | **≥ 33 vereist** | `bool` — precies waarvoor SPEC 11.2 hoopte |
| `music/item_by_uri` | 714-719 | geen eis | het media-item, of een exceptie |

**Gemeten op de draaiende server (schema 31):**

```
verify_item_uri  library://track/401              -> HTTP 400 "Invalid Command"
item_by_uri      library://track/401              -> HTTP 200, media_type=track
item_by_uri      somafm://radio/beatblender       -> HTTP 200, media_type=radio
item_by_uri      library://track/99999999         -> HTTP 500
item_by_uri      somafm://radio/bestaat-niet-xyz  -> HTTP 500
item_by_uri      spotify--AAAAAAAA://track/4uLU…  -> HTTP 500
```

`verify_item_uri` is dus onbruikbaar op schema 31 — de `require_schema=33` in de
client weigert hem — en `item_by_uri` werkt op elke versie.

**En het onderscheid dat SPEC 11.2.1 nodig heeft, bestaat.** Over de JSON-RPC komt
alles als HTTP 500 terug, maar de exceptietypen verschillen:

```
MediaNotFoundError:      radio://bestaat-niet-xyz not found on provider somafm
ProviderUnavailableError: spotify--AAAAAAAA is not available
```

Dat is beter dan SPEC verwachtte. Het geeft **drie** uitkomsten in plaats van twee:

| Uitkomst | Betekenis | Gedrag volgens SPEC 11.2.1 |
|---|---|---|
| item terug | de URI bestaat | wekker gaat af |
| `MediaNotFoundError` | de URI bestaat **niet** | wekker gaat **niet** af, melding `sound_gone` |
| `ProviderUnavailableError` | de **provider** is er niet | de controle kon niet worden uitgevoerd → wekker gaat **wél** af |

Die derde is precies het scenario waar de eigenaar in fase 2b op wees: een
provider die opnieuw gekoppeld is, heeft een ander instantie-ID
(`spotify--ZvzrFmgX`). Dat de provider weg is, bewijst niet dat het nummer weg is.

**Maar: geen enkele HA-service stelt dit beschikbaar.** Music Assistant biedt zes
services — `play_media`, `play_announcement`, `transfer_queue`, `get_queue`,
`search`, `get_library` (`components/music_assistant/services.yaml`). `item_by_uri`
en `verify_item_uri` zitten er niet bij. Om ze te gebruiken moet onze integratie de
client uit **de binnenkant van een andere integratie** halen:

```
components/music_assistant/__init__.py:72   mass: MusicAssistantClient
components/music_assistant/__init__.py:158  entry.runtime_data = MusicAssistantEntryData(mass, …)
```

Dat is `entry.runtime_data.mass` van de MA-config-entry. Het werkt, en het is
precies het soort afhankelijkheid dat in DomotiApp Scene bewust is vermeden (de
groep-constanten in `store.py` daar, met de aantekening dat een wijziging in HA's
groep-integratie dan **stil** breekt).

**De keuze die hieruit volgt, en die niet aan mij is:**

| | Voordeel | Prijs |
|---|---|---|
| **`entry.runtime_data.mass`** | één aanroep, exact, met het drievoudige onderscheid | afhankelijk van de binnenkant van `music_assistant`; breekt stil bij een wijziging daar |
| **`music_assistant.search`** (tak B uit SPEC) | alleen de publieke API | niet waterdicht; vals negatief maakt van een werkende wekker een stille |

**Dit blokkeert fase 3a niet**: de URI-controle hoort bij de noodrem en dus bij
fase 3b. Het staat hier zodat 3b niet opnieuw hoeft te zoeken.

---

## Samenvatting

Zes nieuwe modules, 112 Python-tests, 13 mutaties nagelopen.

| Module | Wat | Puur? |
|---|---|---|
| `volgende.py` | wanneer gaat een wekker af; teksten; sorteren | **ja** — geen `hass`, geen HA-imports |
| `validatie.py` | het schema uit SPEC 14.2, per veld | **ja** |
| `store.py` | opslag, de kapotte-data-scheiding, entity-ID → registry-entry-ID | nee |
| `entiteiten.py` | labelfiltering en de zes speaker-eisen | nee |
| `ringing.py` | register plus doorgeefluik voor de afgaan-toestand | nee |
| `websocket.py` | de negen commando's | nee |

### `volgende.py` is puur, en dat is een eis en geen stijlkeuze

SPEC vroeg de rekenkunde voor `next_fire` in een aparte module zodat fase 3b hem
hergebruikt. Hij is zó geschreven dat hij **niets** uit Home Assistant importeert.
Dat is te controleren: `tests/test_volgende.py` draait zonder `hass`-fixture, en
zou de module iets uit HA importeren, dan was hij op Windows niet eens te
importeren (`fcntl`).

De zomertijdgevallen zitten erin en zijn getoetst met een vaste `nu`:

- **voorjaar** — 02:30 op 29 maart 2026 bestaat niet, dus die dag wordt
  **overgeslagen** en het eerstvolgende moment is 30 maart 02:30. Dat is het gedrag
  van `find_next_time_expression_time` en dus van de planner uit 3b.
- **najaar** — 02:30 op 25 oktober komt twee keer voor; `volgende_momenten` geeft
  het **eerste** (fold=0, +02:00, UTC 00:30). Dat de planner hem die nacht twee keer
  laat afgaan is gedrag van de planner, niet van "wanneer is de eerstvolgende keer".
- **06:45** heeft op beide overgangsdagen precies één moment — dat staat er als
  regressiewacht, zodat de twee gevallen hierboven het normale wekuur niet raken.

### De kapotte-data-scheiding werkt, en dat is het belangrijkste geval

`test_kapotte_persoon_blokkeert_gezonde_niet` toetst drie dingen in één test:
de kapotte persoon geeft `home_assistant_error` en kan niet opslaan, de gezonde
persoon kan wél opslaan, en **na die schrijfronde staat de kapotte data er nog
letterlijk** — inclusief een veld `ietsWatWijNietKennen` met een geneste lijst dat
nergens in ons schema voorkomt.

### Wat de mutatietests opleverden

Dertien mutaties. **Elf werden gevangen**, en de twee die het niet werden waren
leerzaam:

| Mutatie | Uitkomst |
|---|---|
| M1 kapotte data opnieuw opgebouwd i.p.v. letterlijk teruggeschreven | gevangen |
| M2 geval C schrijft alsnog | **eerst niet gevangen** → test toegevoegd |
| M3 `registry_id` valt terug op het entity-ID | gevangen |
| M4 / M4b / M4c servervelden | **niet gevangen — en dat was juist** |
| M5 `one_shot_at` niet berekend | gevangen |
| M6 groepen niet uitgesloten | gevangen |
| M7 de voorjaarscontrole valt weg | gevangen |
| M8 `skip_next` genegeerd bij `next_fire` | gevangen |
| M9 validatie draait ná de toestemmingscontrole | gevangen |
| M10 `wekkers()` geeft de opslag zelf terug | gevangen |
| M11 platformcheck op `music_assistant` weg | gevangen |
| M12 `VOLUME_SET` niet meer vereist | gevangen |

**M2 was een echt gat.** De guard in `_async_schrijf` bleek via de WebSocket-API
onbereikbaar: elk pad daarheen gaat eerst langs `_eis_bruikbaar`, dus het weghalen
van de guard veranderde niets. Dat maakt hem geen dode code maar een **vangnet voor
fase 3b** — de planner schrijft `last_fired` weg en die route hoeft niet langs een
leesactie. Gedicht met `test_geval_c_schrijft_ook_niet_langs_de_interne_route`, die
de schrijflaag rechtstreeks toetst.

**M4 was géén gat, en dat kostte drie mutaties om vast te stellen.** Het weghalen
van de expliciete weigering van servervelden liet geen test falen. Dat leek een
gat, maar de eigenschap is **dubbel verdedigd**: servervelden zitten niet in
`GEBRUIKERSVELDEN`, dus de onbekende-veldcontrole weigert ze óók. Ik heb dat
uitgezocht met een vierde mutatie die **beide** verdedigingen weghaalt én de
kaartwaarden laat winnen:

```
M4d (beide verdedigingen weg, kaartwaarden winnen)
  gevangen: 2 failed, 110 passed
    FAILED test_servervelden_worden_geweigerd
    FAILED test_save_neemt_last_fired_nooit_van_de_kaart_over
```

**De les die ik hieruit meeneem:** een mutatie die overleeft is niet automatisch een
testgat — het kan ook redundante verdediging zijn. Het onderscheid maak je door de
redundantie óók weg te halen. Dat is nu de derde ronde waarin een meting van mij
eerst iets anders leek te zeggen dan er aan de hand was.

Ik heb daarnaast `test_save_neemt_last_fired_nooit_van_de_kaart_over` toegevoegd,
omdat de bestaande test alleen de **foutcode** toetste en niet de eigenschap
waar het om gaat: **wat er in de opslag komt te staan**. Die test bewijst nu beide
richtingen — een save mag `last_fired` niet zetten én niet wissen. Daar rust de
inhaalslag van SPEC 13.4 op.

### Eén implementatiebug die de tests vonden

De toestemmingscontrole op speaker en lamp draaide **vóór** de schemavalidatie.
Gevolg: een `brightness_pct` van 0 gaf `not_allowed` in plaats van
`invalid_format`, en welke foutcode je kreeg hing af van of het label toevallig
bestond. SPEC 15.2 schrijft `invalid_format` voor. Omgezet naar: **eerst het
schema, dan de toestemming**, met de reden in een commentaar. Mutatie M9 bewaakt
het nu.

Daarbij is ook de domeincontrole op `speaker` uit `validatie.py` gehaald: die
stond op twee plekken en liet dezelfde afkeuring onder twee verschillende
foutcodes uitkomen, afhankelijk van welke controle eerst draaide. De zes eisen van
SPEC 7.2 staan nu op één plek, in `entiteiten.is_ma_speaker`, en leveren
`not_allowed`.

---

## Wat niet lukte

1. **De negen commando's zijn niet live op 8129 geverifieerd.** Dat was geen eis
   (taak F), en de reden om het niet te doen is dat het niets zou toevoegen: de
   tests praten over een **echte WebSocket-verbinding** via `hass_ws_client`, dus de
   schema's, de foutcodes en de rechten zijn die van HA zelf. Wat een live-test wél
   zou toevoegen is de MA-koppeling — en die is er niet, want de HA↔MA-koppeling is
   in fase 0b niet gelukt.

2. **`sound/search` is alleen op zijn foutpad getoetst.** Er is geen geladen
   MA-config-entry op de testinstance, dus de test bewijst dat het commando
   `not_found` geeft met de juiste tekst, en niet dat een echte zoekopdracht een
   platte lijst oplevert. Het platmaken van de acht emmers (`_plat`) is daarmee
   **ongetoetst**. Dat kan pas als de koppeling er is; het staat hier zodat het niet
   als gedekt wordt aangenomen.

3. **De time-out van 10 seconden is niet getoetst.** Om dat te doen zou ik een
   trage MA-service moeten nabootsen. De code gebruikt `asyncio.timeout`, wat het
   juiste gereedschap is, maar het gedrag bij een overschrijding is niet gemeten.

4. **`ringing` is een leeg register.** Er is in deze fase niets dat een wekker laat
   afgaan, dus het veld `ringing` in `alarms/get` is alleen getoetst door het
   register in de test zelf te vullen. Dat is eerlijk gezegd de helft van het bewijs:
   het doorgeefluik werkt, maar dat er ooit iets in komt moet 3b aantonen.

5. **Geval A (het bestand is geen geldige JSON) is niet getoetst.** Dat handelt HA
   zelf af (`helpers/storage.py:369-421`) en SPEC 19.2 zegt dat wij daar niets aan
   mogen toevoegen. Wat ik wél heb getoetst is het pad dat eruit volgt:
   `async_load` geeft `None` en de laag begint met een lege lijst.

6. **Geen repair issues aangemaakt.** SPEC 19.2 geval B regel 4 en geval C regel 3
   vragen een repair issue bij een kapotte persoon en bij een onbruikbare opslag. De
   integratie **logt** nu op `ERROR` met de reden erin, maar maakt geen
   `issue_registry`-melding aan. Dat is een gat ten opzichte van SPEC en het is
   bewust niet stil gelaten: het hoort in 3b of in een eigen ronde, samen met de
   `persistent_notification` uit SPEC 11.7 — die twee gebruiken dezelfde
   machinerie en het is zonde ze los te bouwen. **Dit is het enige punt waarop de
   opgeleverde code minder doet dan SPEC voorschrijft.**

---

## Aannames

1. **De testpersonen zijn via het entity registry aangemaakt en niet via de
   `person`-integratie.** Die vraagt een gebruiker en een opslagcollectie, en wat
   SPEC 6.2 gebruikt is precies wat de fixture maakt: een entiteit met een
   `unique_id` en dus een registry-entry met een stabiel `id`. De aanname is dat een
   echte `person` daarin niet verschilt — onderbouwd door fase 0
   (`components/person/__init__.py:448`), niet zelf nagemeten op een draaiende
   instance.

2. **`mass_player_type` ontbreekt bij een onbeschikbare speaker, en dan geldt hij
   als niet-groep.** Het attribuut verdwijnt bij `unavailable`. Weigeren bij twijfel
   zou een onbereikbare speaker onbewerkbaar maken, wat erger is dan het risico dat
   een groep als niet-groep doorgaat. Staat als commentaar in `entiteiten.py`.

3. **Bij meerdere MA-config-entries wordt de eerste genomen**, met een
   `DEBUG`-regel. Dat is wat SPEC 8.1 als VOORSTEL vastlegt.

4. **`_plat()` neemt `artists` en `album` over zoals MA ze geeft**, zonder ze te
   normaliseren. De vorm ervan is uit de metingen van de eigenaar bekend
   (genest, met afbeelding), maar niet door mij gezien; daarom worden ze
   doorgegeven en niet geïnterpreteerd.

Geen andere aannames gedaan.

---

## `git status --porcelain`

Zie de terminaluitvoer van deze ronde; op het moment van committen leeg op de
bestanden van deze fase na.
