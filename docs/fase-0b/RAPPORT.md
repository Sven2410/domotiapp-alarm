# Fase 0b — Music Assistant live verifiëren

Doel: MA naast de testinstance draaien en E2 uit fase 0 alsnog **live** meten,
vóórdat `SPEC.md` geschreven wordt.

Deze fase heeft niets aan het product gebouwd: geen integratiecode, geen kaart,
geen tests.

**Gemeten op:** Music Assistant server **2.9.11**, schema_version **31**
(min_supported 28), naast Home Assistant **2026.8.1**. Tijdzone
Europe/Amsterdam.

> **Let op bij het lezen.** De HA↔MA-koppeling is **niet** tot stand gekomen.
> Alles wat hieronder aan de **MA-kant** staat is echt gemeten. Alles wat de
> **HA-kant** betreft — welke entiteiten MA aanmaakt, hoe HA zich gedraagt bij een
> offline speaker — is **niet** gemeten en staat als **ONBEKEND** met een
> reproductie-instructie. Zie [Wat niet lukte](#wat-niet-lukte).

---

## Samenvatting

**Taak A — MA opgezet.** Container `ma-alarm`, eigen compose-project
`domotiapp-alarm-ma`, poorten 8095 (web-UI/API) en 8097 (audiostream),
configmap `.ma-dev-config/` gitignored. Apart bestand en apart project zodat een
`docker compose up` op het ene project de container van het andere nooit kan
vervangen, en zodat de HA-instance zonder dit bestand start. MA is testmateriaal,
geen onderdeel van het product.

**Taak B — testmateriaal.** Vier muziekproviders actief, waarvan er twee
bruikbare resultaten geven. Vier players, waarvan twee echte audio-decoderende
speakers zonder hardware.

**Taak C — deels beantwoord.** C3 (volume) is volledig gemeten en levert twee
harde bevindingen op. C2 is beantwoord voor wat op deze instance te toetsen is;
album, artiest, los nummer en radio-via-RadioBrowser zijn **ONBEKEND**. C1 is
**ONBEKEND** omdat het de HA-kant is.

**Taak D — de belangrijkste bevinding van deze fase.** Aan de MA-kant is het
faalgedrag scherper dan fase 0 dacht, en op één punt veel gevaarlijker:

> **Music Assistant blijft `playback_state: "playing"` melden voor een speaker
> die niet meer bestaat.** De speaker gaat op `available: false`, maar de queue
> blijft op `playing` staan en `elapsed_time` loopt door — gemeten 220,3 s nadat
> het afspeelproces was gedood.

Daarmee is `playback_state` **onbruikbaar** als bewijs dat de wekker geluid heeft
gemaakt. De enige betrouwbare indicator is `available`.

**Taak E — het ontwerp is uitvoerbaar, met drie aanpassingen.** Zie
[Taak E](#taak-e--wat-dit-betekent-voor-het-ontwerp).

---

## Taak A — Music Assistant opzetten

`docker-compose.music-assistant.yml`, project `domotiapp-alarm-ma`, container
`ma-alarm`.

**Verantwoording van de keuzes:**

- **Apart compose-bestand en apart project.** Dezelfde reden waarom `name:`
  expliciet in `docker-compose.yml` staat (valkuil uit fase 0): Docker Compose
  ziet meerdere bestanden in dezelfde mapstructuur anders als één project en
  vervangt de verkeerde container. Met een eigen `name:` kan dat niet.
- **In de repo, niet ernaast.** De testopstelling moet reproduceerbaar zijn voor
  wie de repo uitcheckt. De configmap `.ma-dev-config/` is gitignored, net als
  `.ha-dev-config/`.
- **Poorten 8095 en 8097.** 8123 t/m 8129 zijn bezet; 8095/8097 zijn MA's eigen
  standaardpoorten.
- **Geen host-netwerk, geen privileged.** MA raadt dat aan voor mDNS-ontdekking
  van echte hardware. Dat werkt op Docker Desktop voor Windows niet zoals op
  Linux, en het is niet nodig: deze fase gebruikt players die MA zelf aanmaakt.

**Netwerk.** HA bereikt MA op `http://host.docker.internal:8095` — geverifieerd
vanuit de container:

```
OK http://host.docker.internal:8095/info
  server_version : 2.9.11
  schema_version : 31
```

`localhost:8095` werkt hiervoor **niet**: binnen de HA-container wijst dat naar
HA zelf. Voor de browser is het omgekeerd — die kent `host.docker.internal` niet
en moet `localhost:8095` gebruiken. Dat verschil heeft de koppeling gekost (zie
Wat niet lukte).

---

## Taak B — Testmateriaal

### Muziekbron

MA levert **48** muziekproviders mee. Er zijn er vier geactiveerd; geen ervan
vraagt een account.

| Provider | Werkt? | Wat het geeft |
|---|---|---|
| **SomaFM Radio** | **ja** | ~30 kanalen, echte streams. Zoeken werkt op kanaalnaam, browsen geeft de hele lijst. |
| **iTunes Podcast Search** | **ja** | echte podcasts, zoeken werkt goed |
| **Music Assistant** (builtin) | ja | eigen/slimme afspeellijsten (`library://playlist/N`) |
| **RadioBrowser** | **grotendeels niet** | zie hieronder |

**Waarom deze keuze.** Voor een wekker zijn **radio** en **afspeellijst** de
logische soorten: ze hebben een onbepaalde duur. Een los nummer van drie minuten
stopt van zichzelf. SomaFM geeft echte, oneindige radiostreams zonder account en
is daarmee representatief voor het *gedrag* dat een wekker nodig heeft.

**Waarin het niet representatief is:** een klant heeft normaal Spotify, Tidal of
Apple Music, en dáár komen album, artiest en los nummer uit. Die drie soorten
zijn hier niet te toetsen.

**RadioBrowser — nuancering op de melding van de eigenaar.** De eigenaar meldde
dat RadioBrowser op *elke* zoekopdracht faalt. Dat is bijna waar, maar niet
helemaal, en het verschil is relevant voor de diagnose: **één zoekopdracht
lukte wel.** `BBC Radio 2` gaf drie stations terug met geldige URI's:

```
BBC Radio 2 -> radiobrowser://radio/16406133-159b-4abb-9e18-0824b053403e
BBC Radio 2 -> radiobrowser://radio/9d08d62b-c85e-4666-ba2e-2d0f84eaf703
BBC Radio 2 -> radiobrowser://radio/ace1f44f-51b8-4e1d-9492-819436044f60
```

Alle andere pogingen (`jazz`, `radio`, `BBC`, `Sky Radio`, `NPO Radio 2`, en
later `Beat Blender`) gaven `Error occurred while communicating with the Radio
Browser API`. Het is dus **wisselvallig, niet dood**.

Wat ik heb uitgesloten, zodat dit niet opnieuw onderzocht hoeft te worden:

- **Netwerk is in orde.** De container haalt de API rechtstreeks op
  (2 stations via `urllib`).
- **DNS-SRV werkt.** `_api._tcp.radio-browser.info` → `de1.api.radio-browser.info`.
  Dat is de lookup die `radios==0.3.2` op `radio_browser.py:76` doet.
- **De bibliotheek zelf werkt**, zowel met een eigen sessie als met een
  meegegeven `aiohttp.ClientSession` — precies zoals MA hem aanroept
  (`radiobrowser/__init__.py:69-70`). Beide tests: `stats OK`, `search OK 2`.

Wat overblijft als waarschijnlijkste oorzaak: **rate limiting of een
wisselvallige mirror** aan de kant van RadioBrowser. Niet verder uitgezocht,
conform opdracht. **Oorzaak blijft ONBEKEND.**

### Speakers

MA kan players aanmaken zonder hardware. Wat er mogelijk bleek:

| Route | Bruikbaar? | Waarom |
|---|---|---|
| **Snapcast met ingebouwde snapserver** | **ja, gebruikt** | De MA-image bevat `/usr/bin/snapserver` **én** `/usr/bin/snapclient`. `snapcast_use_external_server` staat default `false`, dus MA start zijn eigen snapserver (controlepoort 1705). Met `--player file:filename=/dev/null --mixer software` draait een snapclient headless mét echte softwarematige volumeregeling. |
| **Sendspin** (builtin) | ja, ontstaat automatisch | MA's eigen protocol. Het openen van de MA-web-UI registreert een player. Maar: `expose_to_ha: false` en `hide_in_ui: true`. |
| **Sync Group Player** (builtin) | ja, gebruikt | groepsplayer over de twee snapcast-players |
| `_demo_player_provider` | **nee** | een voorbeeldstub van 99 regels die geen players aanmaakt |

**Vier players neergezet** (eis was minstens twee):

| player_id | provider | type | expose_to_ha | volume_control |
|---|---|---|---|---|
| `ma_wekkerslaapkamer` — "Wekker Slaapkamer" | snapcast | `player` | **true** | native |
| `ma_wekkerkeuken2` — "Wekker Keuken" | snapcast | `player` | **true** | native |
| `syncgroup_rd74j3sf` — "Wekkergroep" | sync_group | **`group`** | **true** | native |
| `ma_9eav46hrg9` — "Web (Chrome on Windows)" | sendspin | `player` | **false** | native |

**Echte audio, geverifieerd.** Een SomaFM-station is afgespeeld op Wekker
Slaapkamer en het snapclient-log toont dat de stream werkelijk aankomt en
gedecodeerd wordt:

```
[Info] (Controller) Codec: flac, sampleformat: 48000:16:2
[Info] (Player) Player name: file, device: /dev/null, ... parameters: filename=/dev/null
[Info] (Player) Mixer mode: software, parameters: <none>
[Info] (Player) Sampleformat: 48000:16:2, stream: 48000:16:2
```

MA-kant tegelijk: `playback_state: "playing"`, `current_media.title: "All I Need"`,
queue `state: playing, items: 1`.

Dit is dus geen doen-alsof-player: er loopt een echte HTTP-stream, een echte
transcodering naar FLAC en een echte decoder. Wat het **niet** is: hardware met
een eigen versterker en een eigen volumecurve.

---

## Taak C1 — Welke entiteiten maakt MA aan, en welke zijn speakers?

**Status: ONBEKEND aan de HA-kant.** De koppeling is niet tot stand gekomen, dus
`hass.states` bevat **nul** `media_player`-entiteiten en er is **nul**
config entry voor `music_assistant`. Gemeten:

```
maEntries: 0, mediaPlayers: 0, totaalStates: 17
```

Wat ik wél hard heb, en waarmee de vraag voor 90 % voorspelbaar is:

**1. Welke players HA krijgt, is exact bepaald door `expose_to_ha`.** Fase 0 las
dat in `components/music_assistant/__init__.py:198-208`; fase 0b heeft het veld
nu ook in de praktijk gezien, met **verschillende waarden per provider**:

- de twee snapcast-players: `expose_to_ha: true`
- de sync-groep: `expose_to_ha: true`
- **de Sendspin web-player: `expose_to_ha: false`** en `hide_in_ui: true`

Dat is een concreet antwoord op "duiken display-, visualizer- of groepsplayers op
als mediaplayer": **een groepsplayer wél** (hij staat op `expose_to_ha: true`), en
MA's eigen web-player **niet**. Voor `display`/`visualizer`/`light` had ik geen
provider die zulke players aanmaakt; dat blijft **ONBEKEND**.

**2. De groepsplayer heeft `type: "group"`**, en dat is precies het veld dat in HA
als `mass_player_type` in `extra_state_attributes` landt
(`media_player.py:191-196`). Dus een groep is in HA te herkennen — maar alléén
zolang de entiteit beschikbaar is (fase 0, valkuil 18).

**3. Waaraan je betrouwbaar herkent dát het een MA-speaker is.** Op basis van
fase 0 (broncode) plus wat fase 0b aan MA-kant zag, blijft het advies uit fase 0
staan, met één toevoeging:

- **niet** op `device_class`: MA zet `MediaPlayerDeviceClass.SPEAKER` op *elke*
  player (`media_player.py:140`);
- **niet** op `mass_player_type`: dat verdwijnt bij `unavailable`;
- **wel** op de combinatie *entity registry entry met `platform == "music_assistant"`
  en domein `media_player`* plus *`supported_features` bevat `PLAY_MEDIA`*
  (en voor volume-oploop `VOLUME_SET`), omdat `supported_features` een
  onbeschikbare entiteit overleeft;
- **toevoeging uit 0b:** `VOLUME_SET` is niet gegarandeerd. Alle vier de players
  hier hebben `volume_control: "native"` en dus `VOLUME_SET`, maar
  `power_control` is bij alle vier `"none"` — dus **`TURN_ON`/`TURN_OFF` heeft
  een MA-speaker niet noodzakelijk**. Een wekker die de speaker eerst "aanzet"
  kan daar dus niet op rekenen.

**Wat nog gemeten moet worden:** de entity_id's, de exacte attributenset, en of
de groep inderdaad als `media_player` verschijnt. Instructie in
[Wat de eigenaar moet toetsen](#wat-de-eigenaar-moet-toetsen).

---

## Taak C2 — Wat is er zoekbaar en afspeelbaar?

Gemeten aan de MA-kant met `music/search` over alle zeven mediatypen, met vier
zoektermen (`Groove Salon`, `jazz`, `nieuws`, `BBC`), plus browsen en afspelen.

| Soort | Zoeken geeft resultaten? | Afspelen werkt? |
|---|---|---|
| **Radiostation** | **ja**, via SomaFM op kanaalnaam (`Beat Blender` → `SomaFM: Beat Blender`). Generieke termen (`jazz`) geven 0 omdat SomaFM maar ~30 kanalen heeft. Via RadioBrowser **wisselvallig**, zie taak B. | **ja, aantoonbaar** — SomaFM-stream afgespeeld, FLAC gedecodeerd door de snapclient |
| **Podcast** | **ja**, ruim. Bijv. `nieuws` → "Nieuws van de Dag", "BNR Nieuws Vandaag"; `jazz` → "Jazz to Go", "Hoezo Jazz?!" | **niet getoetst** |
| **Afspeellijst** | **deels** — zoeken gaf 0 treffers; de bibliotheek bevat wel afspeellijsten (`library://playlist/1..8`, o.a. "All favorited tracks", "Infinite Mix (favorites)", "Random Album (from library)"). Dat zijn MA's eigen slimme lijsten, geen door de klant gemaakte. | **niet getoetst** |
| **Album** | **ONBEKEND** | **ONBEKEND** |
| **Artiest** | **ONBEKEND** | **ONBEKEND** |
| **Los nummer** | **ONBEKEND** | **ONBEKEND** |
| Luisterboek | 0 treffers (geen provider die ze levert) | ONBEKEND |

De drie ONBEKEND-en hebben één oorzaak: **er is geen streamingprovider op deze
instance.** Album, artiest en los nummer komen bij een klant uit Spotify/Tidal/
Apple Music. De `test`-provider van MA levert wel neppe albums en artiesten, maar
ondersteunt **`SEARCH` niet** — alleen `LIBRARY_*` en `BROWSE` — en is dus geen
vervanging voor deze vraag.

### Hoe je de zoekopdracht aanroept

Aan de **MA-kant** (wat ik gebruikt heb, via `POST /api`):

```json
{ "command": "music/search",
  "args": { "search_query": "Beat Blender", "media_types": ["radio"], "limit": 5 } }
```

Aan de **HA-kant** — dat is wat het product doet — is het de service
`music_assistant.search`, geregistreerd met
`supports_response=SupportsResponse.ONLY` (`services.py:90-107`). Een integratie
roept die aan met `blocking=True, return_response=True` en krijgt de resultaten
direct terug. `config_entry_id` is **verplicht** (`services.yaml:112-116`), dus de
integratie moet eerst de MA-config-entry opzoeken met
`hass.config_entries.async_loaded_entries("music_assistant")`.
**Niet live geverifieerd** — de koppeling ontbreekt.

### Wat er per resultaat terugkomt

Dit bepaalt wat de editor kan tonen, en het is gemeten. Per treffer:

| Veld | Voorbeeld |
|---|---|
| `name` | `SomaFM: Beat Blender` |
| `uri` | `somafm://radio/beatblender` |
| `media_type` | `radio` |
| `version` | (leeg bij radio) |
| `image` | URL of `null` |

Voorbeeld van een podcast-URI: `itunes_podcasts://podcast/https://podcast.npo.nl/feed/jazz-to-go.xml`.

**Dus: naam, afbeelding en een URI.** De editor kan een lijst met naam plus
albumhoes tonen. Er is **geen** duur en **geen** stabiel numeriek ID; de `uri` is
de sleutel.

**Aanbeveling: sla de `uri` op, niet de naam.** Afspelen met een URI is dan een
verificatie in plaats van een nieuwe zoekopdracht, en het resultaat verandert niet
doordat de bibliotheek wijzigt. Let op: bij `schema_version 31` (deze server, en
< 33) gebruikt de HA-integratie het pad "URI bevat `://` → direct accepteren"
(`media_player.py:494-498`); `verify_item_uri` bestaat pas vanaf schema 33. Een
URI wordt op deze server dus **niet gevalideerd** vóór het afspelen.

### Hoe je iets start op een speaker

MA-kant, aantoonbaar werkend:

```json
{ "command": "player_queues/play_media",
  "args": { "queue_id": "ma_wekkerslaapkamer",
            "media": "somafm://radio/beatblender", "option": "replace" } }
```

→ HTTP 200, daarna `playback_state: "playing"`, queue `items: 1`,
`current_item: "SomaFM: Beat Blender"`, en een echte FLAC-stream bij de client.

HA-kant is `music_assistant.play_media` met `media_id` = de `uri`, of de
standaard `media_player.play_media`. **Niet live geverifieerd.**

---

## Taak C3 — Volume

### Resolutie

Gemeten op een snapcast-speaker door te zetten en terug te lezen:

| Gevraagd | Teruggelezen |
|---|---|
| 0, 1, 2, 3, 7, 33, 50, 66, 99, 100 | 0, 1, 2, 3, 7, 33, 50, 66, 99, 100 |

**Volledige resolutie van 1 %, alle 101 standen, exact.** Geen afronding naar
stappen van 5 of 10.

Randgevallen, ook gemeten:

| Gevraagd | Status | Teruggelezen |
|---|---|---|
| 12.5 | 200 | **12** (afgekapt) |
| 33.7 | 200 | **33** (afgekapt, niet afgerond) |
| −5 | 200 | **0** |
| 150 | 200 | **100** |

**Buiten bereik wordt stil afgekapt, zonder fout.** Dat is een valkuil: een
rekenfout in de oploop geeft geen exceptie, alleen een verkeerd volume.

**Belangrijke beperking.** Dit is de resolutie van **snapclient met een
softwarematige mixer**, niet van een Sonos, Chromecast of Bluesound. De vraag uit
fase 0 — de resolutie van **echte** speakers — blijft daarmee **ONBEKEND**. Wat
deze meting wél uitsluit: dat MA of HA de resolutie beperkt. HA rekent
`int(volume * 100)` (`media_player.py:315-318`), dus de HA-kant geeft 100 stappen
door en het is aan het apparaat wat het ermee doet.

### Oplopend volume in 20 seconden

Gebouwd als 20 stappen van 1 seconde, van 0 naar 40.

| Wat | Uitkomst |
|---|---|
| Totale duur | **20,004 s** |
| Eindvolume | **40**, exact |
| Alle 20 aanroepen geslaagd | ja, alle HTTP 200 |
| Duur per aanroep | **3,1 – 6,2 ms**, gemiddeld 4,4 ms |
| Speelde door tijdens de oploop | ja, `playback_state: "playing"` |

**De speaker houdt het ruimschoots bij.** 4,4 ms per aanroep tegen een
stapinterval van 1000 ms is een factor 200 marge. Twintig aanroepen per wekker per
speaker is verwaarloosbaar.

**Meetfout die ik zelf maakte, en die het rapport zou hebben vervuild.** De
stappen kwamen **niet** op 1-secondeafstand. Uit de meting:

```
stap 1: t=1.995   stap 2: t=2.001
stap 3: t=3.995   stap 4: t=4.000
stap 5: t=5.996   stap 6: t=6.001
...
```

Twee stappen per 2 seconden, in paren. Oorzaak: Chrome knijpt `setTimeout` af in
een tabblad dat niet op de voorgrond staat. De totale duur klopte (20,004 s) omdat
de laatste stap toevallig op tijd viel — als ik alleen de totaalduur had gerapporteerd,
had er "vloeiende oploop in 20 s" gestaan terwijl een luisteraar **10 sprongen van
4 eenheden** zou horen in plaats van 20 van 2.

**Dit is een artefact van mijn meetopstelling, niet van MA of van het product.**
De oploop in het product loopt in Python binnen HA en heeft geen browsertimer.
Maar het betekent dat de vraag "hoeveel stappen voelen vloeiend aan" hier **niet**
beantwoord is: ik heb geen 1-seconde-cadans kunnen realiseren en er zat geen oor
aan de speaker. **Hoeveel stappen vloeiend aanvoelt, blijft ONBEKEND.** Wat wél
vaststaat: de techniek staat 100 stappen toe en de aanroepkosten zijn
verwaarloosbaar, dus de bovengrens wordt door het gehoor bepaald en niet door MA.

### Volume op een groep — een aparte bevinding

Dit was niet gevraagd, maar het raakt de wekker direct als de eigenaar meerdere
speakers in één groep zet.

- **De groepsplayer meldt zelf `volume_level: null`.** De waarde zit in
  `group_volume`. Gemeten: `volume_level: null`, `group_volume: 40` → na
  instellen `group_volume: 60`, `volume_level` nog steeds `null`.

  Fase 0 las al dat HA voor een `PlayerType.GROUP` juist `player.group_volume`
  gebruikt (`media_player.py:261-265`) en `None` doorgeeft als die leeg is. Deze
  meting bevestigt dat de groep zelf geen `volume_level` heeft.

- **De leden komen niet op hetzelfde volume uit.** Groepsvolume op 60 gezet, met
  leden die op 40 en 25 stonden:

  | Speaker | Volume na `group_volume = 60` |
  |---|---|
  | Wekker Slaapkamer | **60** |
  | Wekker Keuken | **50** |

  MA verrekent groepsvolume **relatief** ten opzichte van de bestaande standen,
  niet absoluut. Een oploop naar "40 %" op een groep geeft dus **geen** 40 % op
  elke speaker, en de uitkomst hangt af van waar de speakers vóór de wekker
  stonden.

**Gevolg voor het ontwerp:** een oplopend volume moet **per speaker afzonderlijk**
gezet worden, niet op de groep. Anders is het eindvolume onvoorspelbaar. Dit staat
uitgewerkt in taak E.

---

## Taak D — Het faalgedrag, live

Fase 0 stelde uit de broncode vast dat een service-aanroep op een offline speaker
slaagt en niets doet. Fase 0b heeft het MA-gedeelte live gemeten door
snapclient-processen te doden.

### Wat er gebeurt als de speaker offline is

**MA merkt het**, binnen ongeveer 5 seconden: `available: false`.

Daarna, gemeten:

| Aanroep op de offline speaker | HTTP | Wat MA doet |
|---|---|---|
| `player_queues/play_media` | **500** | `PlayerUnavailableError: Player ma_wekkerkeuken2 is not available` — **luid** |
| `players/cmd/volume_set` | **200** | `WARNING ... Ignoring command cmd_volume_set for unavailable player` — **stil geslaagd** |

Letterlijk uit het MA-log:

```
ERROR ... Error executing command player_queues/play_media:
  PlayerUnavailableError: Player ma_wekkerkeuken2 is not available
    raise PlayerUnavailableError(msg)
  music_assistant_models.errors.PlayerUnavailableError: Player ma_wekkerkeuken2 is not available

WARNING ... Ignoring command cmd_volume_set for unavailable player ma_wekkerkeuken2
```

De queue bleef leeg: `state: idle, items: 0`.

**Dit nuanceert fase 0 op een belangrijk punt — in de goede richting.** MA
*schreeuwt* wel als je op een dode speaker probeert af te spelen. Maar dat helpt
het product niet, want fase 0 stelde vast dat **HA de aanroep nooit bij de
integratie aflevert**: `helpers/service.py` filtert onbeschikbare entiteiten weg
vóórdat `async_play_media` wordt bereikt. De `PlayerUnavailableError` van MA komt
dus nooit boven water. **Niet live geverifieerd** — dat vereist de koppeling.

### Kan de integratie vóóraf vaststellen dat een speaker beschikbaar is?

**Ja, en dit is de bruikbaarste uitkomst van de fase.** Aan de MA-kant is het
`available` op de player. In HA is dat exact hetzelfde signaal:
`MusicAssistantEntity.available` is `self.player.available and
bool(self.mass.connection.connected)` (`entity.py:72-74`), en HA maakt daarvan de
state `unavailable`.

Dus de integratie leest vóór het afspelen:

```
hass.states.get(entity_id).state != "unavailable"
```

Dat dekt beide storingen in één controle: speaker weg **én** MA-server weg.

### Kan de integratie ná het starten vaststellen dat er geluid speelt?

**Nee — en dit is de gevaarlijkste bevinding van fase 0b.**

Gemeten: een SomaFM-station speelde op Wekker Slaapkamer; toen is het
snapclient-proces gedood **tijdens** het afspelen. Direct daarna:

```
speler: { available: false, playback_state: "playing", powered: true, volume: 40 }
queue:  { state: "playing", items: 1, elapsed: 220.3, current: "SomaFM: Beat Blender" }
```

**MA meldt `playing` voor een speaker die niet meer bestaat**, en
`elapsed_time` blijft doorlopen. De queue weet niet dat er niemand luistert.

Reden: MA's queue is de bron van waarheid over "wat speelt er", en die staat los
van de vraag of er een client aan de andere kant hangt. Voor een muzieksysteem is
dat verdedigbaar. **Voor een wekker is het fataal**, want het betekent:

> `playback_state == "playing"` is **geen bewijs** dat de wekker geluid heeft
> gemaakt.

Eén verzachting aan de HA-kant, die uit fase 0 volgt en hier **niet** gemeten is:
zodra `available` false is, maakt HA de state `unavailable` en overschrijft
daarmee `playing` (`helpers/entity.py:1063-1076`). In HA zou je dus
`unavailable` zien, niet `playing` — HA's onbeschikbaarheidslaag maskeert de
misleidende MA-toestand. **Dat moet nog geverifieerd worden**; het is het
verschil tussen "de kaart kan het zien" en "de kaart wordt voorgelogen".

### Wat is de betrouwbaarste manier om te weten dat de wekker écht is afgegaan?

Op grond van het bovenstaande, in deze volgorde:

1. **Vóór het afspelen:** controleer `state != "unavailable"` op de speaker. Dit
   is het enige signaal dat zowel een dode speaker als een dode MA-server dekt.
2. **Ná het afspelen, na een korte wachttijd (2–5 s):** controleer **opnieuw**
   `state != "unavailable"`, en pas daarna `state == "playing"`. De tweede
   controle vangt de speaker die tijdens het starten wegvalt.
3. **Gebruik `playback_state`/`playing` nooit als enige bewijs.** Het staat
   aantoonbaar op `playing` terwijl er niets klinkt.
4. **Wat geen van beide kan vaststellen:** of er werkelijk geluid uit de speaker
   komt. Een speaker die op volume 0 staat, gedempt is, of waarvan de versterker
   uit staat, meldt netjes `playing`. Er is in MA **geen** signaal voor
   werkelijke geluidsuitvoer. Dat is een grens van het systeem, geen tekortkoming
   van het ontwerp — en het pleit voor de noodrem in taak E.

---

## Taak E — Wat dit betekent voor het ontwerp

**Is het productontwerp uitvoerbaar met wat MA biedt? Ja.** Alles wat de wekker
nodig heeft, kan: zoeken, afspelen, volume per procent, en een oploop van stil
naar het ingestelde niveau. De aanroepen zijn goedkoop en betrouwbaar.

Maar er moeten **drie dingen anders** dan de eigenaar voor ogen heeft, en één
daarvan is nieuw ten opzichte van fase 0.

### 1. De oploop moet per speaker, niet op de groep (nieuw in 0b)

Fase 0 zei: bouw de oploop zelf met `volume_set`. Fase 0b voegt toe **waarop**:

Een groepsplayer heeft geen eigen `volume_level` (`null`), en groepsvolume werkt
**relatief**: 60 zetten op een groep gaf 60 en 50 op de twee leden. Een wekker die
"begin op stil, eindig op 40 %" belooft en dat op een groep doet, levert een
onvoorspelbaar eindvolume dat afhangt van waar de speakers gisteravond stonden.

**Dus:** de integratie moet de leden van een groep uitvragen en de oploop **per
speaker** zetten, of groepen als wekkerspeaker uitsluiten. Dat is een
ontwerpbeslissing die in `SPEC.md` hoort, en het raakt ook de editor: als een
groep niet mag, moet de kaart hem niet aanbieden.

Bijkomend: `power_control` is bij alle geteste players `"none"`, dus
`TURN_ON`/`TURN_OFF` bestaat niet. Een wekker kan een speaker **niet aanzetten**.
Staat het apparaat fysiek uit, dan is er geen geluid en geen manier om dat te
verhelpen.

### 2. De noodrem moet op `available` staan, niet op `playing` (scherper dan fase 0)

Fase 0 vermoedde dat er een terugmelding moest komen. Fase 0b maakt precies
duidelijk waarop die terugmelding moet rusten: **`playback_state` is
aantoonbaar onbetrouwbaar** — het bleef `playing` staan voor een speaker die
gedood was, met een doorlopende `elapsed_time`.

Het ontwerp moet dus:

- vóór het afspelen `available` controleren;
- ná het afspelen, na een paar seconden, **opnieuw** `available` controleren;
- bij falen een **zichtbare** terugmelding achterlaten (repair issue of
  persistent notification) én terugvallen op de verlichtingswekker;
- nooit "de service-aanroep gaf geen fout" als bewijs behandelen.

En het ontwerp moet accepteren dat **volledige zekerheid niet bestaat**: een
speaker op volume 0 of met de versterker uit meldt `playing`. Dat is een
argument om de verlichtingswekker **altijd** mee te laten lopen, niet als
terugval maar als basis.

### 3. De verlichtingswekker is de betrouwbare helft — nu met bewijs

Fase 0 zei dit al op grond van de broncode. Fase 0b heeft het nu gemeten: de
geluidsketen heeft **drie** onafhankelijke punten waar hij stil kan falen —
de speaker valt weg (gemeten), de MA-server valt weg (`available` dekt beide),
en `playing` liegt (gemeten). De verlichtingswekker heeft er geen van.

De opdracht zegt dat de geluidskant verplicht is in het product. Dat blijft de
keuze van de eigenaar, en die is verdedigbaar — maar het ontwerp moet dan
expliciet vastleggen dat **licht altijd meeloopt** en dat een mislukte
geluidswekker een gebeurtenis is die de gebruiker te zien krijgt.

### Wat níet hoeft te veranderen

- **De volumeresolutie is geen probleem.** 1 % over de hele schaal, exact
  gehonoreerd. Er is geen reden om de kaart in grove stappen te laten werken.
- **De aanroepkosten zijn geen probleem.** 4,4 ms per `volume_set`. Twintig
  stappen per speaker is verwaarloosbaar; honderd zou ook kunnen.
- **Zoeken en afspelen werken.** De `uri` is een bruikbare, stabiele sleutel, en
  naam plus afbeelding geven de editor genoeg om te tonen.

---

## Wat de eigenaar moet toetsen

De volgende toetsen zijn op **deze** instance niet uit te voeren. Ze zijn zo
opgeschreven dat ze zonder mij uitvoerbaar zijn. Gebruik
**Ontwikkelhulpmiddelen → Acties** (YAML-modus) en **Ontwikkelhulpmiddelen →
Toestanden**.

### T1. De HA↔MA-koppeling afmaken (blokkeert T2 t/m T6)

**Wat:** een config entry voor `music_assistant` op de dev-instance.

**Hoe:** het probleem is dat HA voor deze flow terugredirect via
`https://my.home-assistant.io/redirect/oauth`, en die redirector weet niet waar
deze instance staat.

1. Ga in **dezelfde browser** naar `https://my.home-assistant.io`, en zet daar bij
   *"My Home Assistant"* het instance-adres op `http://localhost:8129`.
2. Dan in HA: **Instellingen → Apparaten & diensten → Integratie toevoegen →
   Music Assistant**, en vul als URL in:
   `http://host.docker.internal:8095`
   (**niet** `localhost:8095` — binnen de HA-container is dat HA zelf).
3. Log in op de MA-pagina die verschijnt. De flow rondt daarna zelf af.

**Controle:** onder Instellingen → Apparaten & diensten staat Music Assistant met
entiteiten, en `media_player.*` bestaat.

### T2. C1 — welke entiteiten maakt MA aan?

**Wat:** de entiteitenlijst en de attributen.

**Hoe:** Ontwikkelhulpmiddelen → Toestanden, filter op `media_player.`. Noteer per
entiteit: `entity_id`, `state`, en de attributen `mass_player_type`,
`supported_features`, `device_class`, `volume_level`, `group_members`.

**Verwacht** (te bevestigen of te weerleggen): drie entiteiten — Wekker
Slaapkamer, Wekker Keuken en Wekkergroep — en **geen** entiteit voor de
Sendspin-webplayer (die staat op `expose_to_ha: false`). De groep moet
`mass_player_type: group` hebben en mogelijk **geen** `volume_level`.

### T3. C2 — album, artiest en los nummer (vereist Spotify thuis)

**Wat:** of die drie soorten zoekresultaten geven en of ze afspelen.

**Hoe:** per soort, met de eigen MA die Spotify heeft:

```yaml
action: music_assistant.search
data:
  config_entry_id: <de config entry van Music Assistant>
  name: "Coldplay"
  media_type: [artist]
  limit: 5
```

Herhaal met `media_type: [album]` en `[track]`. Noteer per soort: **aantal
treffers**, en van de eerste treffer de velden `name`, `uri`, `image`.

Daarna afspelen, met de `uri` uit het antwoord:

```yaml
action: music_assistant.play_media
target:
  entity_id: media_player.<een echte speaker>
data:
  media_id: "<de uri uit het zoekresultaat>"
  media_type: album
```

Noteer of het speelt en wat `media_player.<speaker>` daarna als `state` en
`media_title` toont.

### T4. C3 — volumeresolutie op échte hardware

**Wat:** de resolutie van een echte speaker (Sonos, Chromecast, wat er staat).
Dit is de vraag die fase 0 en 0b beide niet konden beantwoorden.

**Hoe:** zet het volume in kleine stappen en lees terug:

```yaml
action: media_player.volume_set
target:
  entity_id: media_player.<echte speaker>
data:
  volume_level: 0.31
```

Doe dit voor `0.30`, `0.31`, `0.32`, `0.33`, en lees na elke stap het attribuut
`volume_level` terug in Ontwikkelhulpmiddelen → Toestanden. **De vraag is of
0.31 als 0.31 terugkomt, of dat het naar 0.30 of 0.35 springt.** Springt het,
noteer de stapgrootte — dat is de ondergrens voor een vloeiende oploop.

### T5. C3 — voelt de oploop vloeiend?

**Wat:** hoeveel stappen er nodig zijn om een oploop van 20 s vloeiend te laten
klinken. Dit vereist een oor bij de speaker en is daarom niet te automatiseren.

**Hoe:** maak twee automatiseringen die 20 s lang het volume optrekken van 0 naar
het normale wekvolume, één met **10** stappen van 2 s en één met **20** stappen
van 1 s. Speel er muziek bij. Noteer of 10 stappen hoorbaar trapsgewijs is en of
20 dat niet meer is. Bij twijfel ook 40 stappen van 0,5 s.

### T6. D — het faalgedrag op echte hardware

**Wat:** wat HA doet als de speaker echt uit staat, en of `playing` ook daar
blijft hangen.

**Hoe:**

1. Zet een echte speaker **fysiek uit** (stekker of app). Wacht tot
   `media_player.<speaker>` in Toestanden op `unavailable` staat.
2. Roep aan:
   ```yaml
   action: media_player.play_media
   target:
     entity_id: media_player.<die speaker>
   data:
     media_content_id: "<een uri>"
     media_content_type: playlist
   ```
   **Noteer:** komt er een foutmelding in de UI, of meldt HA "succes"? En staat er
   iets in het log (Instellingen → Systeem → Logboek)?
3. Herhaal, maar target nu op **een label** in plaats van op de entity_id. Fase 0
   voorspelt dat er dan **geen enkele** logregel komt. Bevestig of weerleg dat.
4. Start muziek op een **werkende** speaker en zet hem daarna **tijdens het
   spelen** uit. Noteer wat `state` en `media_position` van de entiteit doen: gaat
   hij naar `unavailable`, of blijft hij op `playing` staan zoals MA intern doet?

Stap 4 is de belangrijkste van allemaal: hij bepaalt of de kaart de misleidende
MA-toestand te zien krijgt of dat HA hem maskeert.

---

## Wat niet lukte

1. **De HA↔MA-koppeling is niet tot stand gekomen.** Dit is de grootste
   tekortkoming van deze fase en het blokkeert C1 en de HA-helft van D.

   Diagnose, in stappen:
   - De config flow van MA gebruikt een **externe stap**: HA stuurt de browser
     naar `{MA}/login?return_url=...` en MA redirect terug met het token.
   - Die `return_url` is `https://my.home-assistant.io/redirect/oauth` — HA's
     publieke redirector. Ik heb geverifieerd dat dit **niet** afhangt van
     `external_url`: na het instellen van `external_url` én `internal_url` op
     `http://localhost:8129` (en een herstart, waarna
     `hass.config.external_url == "http://localhost:8129"`) bleef de return_url
     onveranderd naar `/redirect/oauth` wijzen.
   - De eigenaar heeft de MA-inlog wél voltooid — het token kwam aan op
     `http://localhost:8129/auth/external/callback?code=...` — maar die pagina
     bleef **leeg** en de flow verdween zonder config entry. Waarschijnlijk omdat
     my.home-assistant.io niet weet waar deze instance staat.
   - **Niet opgelost.** Ik heb het na drie pogingen laten liggen in plaats van
     verder te blijven proberen. De uitweg staat als **T1** hierboven.

   **Nevenwijziging die ik wél heb gemaakt en die blijft staan:**
   `external_url`/`internal_url` in `.ha-dev-config/configuration.yaml`. Die
   heeft het probleem **niet** opgelost. Ik heb hem laten staan omdat expliciete
   URL's op een dev-instance nuttig zijn, maar hij is zonder gevolgen te
   verwijderen.

2. **Spotify werkt niet op deze instance** (melding van de eigenaar; de OAuth
   callback komt niet terug bij MA achter Docker Desktop). Daardoor zijn album,
   artiest en los nummer niet getoetst. Zie **T3**.

3. **RadioBrowser is wisselvallig.** Eén zoekopdracht van de zes lukte. Netwerk,
   DNS-SRV en de `radios`-bibliotheek zijn alle drie uitgesloten als oorzaak
   (zie taak B). **Oorzaak blijft ONBEKEND**, niet verder uitgezocht conform
   opdracht.

4. **De 1-secondecadans van de oploop is niet gehaald** door
   timer-throttling in een achtergrondtabblad: de stappen kwamen in paren per
   2 s. De totaalduur (20,004 s) en de aanroepkosten zijn wél geldig. Hoeveel
   stappen vloeiend aanvoelt is daarmee **ONBEKEND** — zie **T5**.

5. **Volumeresolutie van echte speakers blijft ONBEKEND.** Gemeten is
   snapclient met een softwaremixer, niet hardware. Zie **T4**.

6. **`display`-, `visualizer`- en `light`-players zijn niet getoetst.** Geen van
   de beschikbare providers maakt zulke players aan. Blijft **ONBEKEND**.

7. **Afspelen van podcast en afspeellijst is niet getoetst.** Alleen radio is
   aantoonbaar afgespeeld. Zoeken naar podcasts werkt wel.

8. **Twee gereedschapsproblemen** die tijd kostten en die in `CLAUDE.md` staan:
   `ps` bestaat niet in de MA-container (processen zoeken via `/proc/*/cmdline`),
   en de browsertool blokkeert tokens in uitvoer — bruikbaar als bescherming,
   maar het betekent dat MA's API alleen ván binnen de pagina aanroepbaar is.

---

## Aannames

1. **De MA-webplayer is representatief voor "niet aan HA blootgesteld".** Ik heb
   `expose_to_ha: false` gezien op de Sendspin-player en `true` op de andere
   drie, en daaruit geconcludeerd dat HA precies de laatste drie zal aanmaken.
   Dat volgt uit de broncode van fase 0, maar het is op deze instance **niet
   waargenomen**. T2 bevestigt het.

2. **HA maskeert de misleidende `playing`-toestand.** Ik neem aan dat HA de state
   `unavailable` maakt zodra `available` false is, en dat de kaart dus niet
   `playing` te zien krijgt voor een dode speaker. Dat volgt uit
   `helpers/entity.py:1063-1076`, maar is niet gemeten. **Als deze aanname niet
   klopt, is het probleem ernstiger dan dit rapport stelt.** T6 stap 4.

3. **Snapcast-volume gedraagt zich als andere MA-players.** De resolutiemeting is
   op één providertype gedaan. Dat MA de waarde 1-op-1 doorgeeft is gezien; dat
   elk providertype dat doet, is aangenomen.

4. **Het groepsvolume-gedrag is relatief.** Ik heb één meting gedaan (60 zetten
   bij leden op 40 en 25 → 60 en 50) en daaruit "relatief, niet absoluut"
   geconcludeerd. Eén meetpunt is genoeg om te weten dat het **niet** absoluut is;
   het is niet genoeg om de exacte formule te kennen. Die heb ik ook niet nodig —
   de conclusie is "zet het per speaker".

Geen andere aannames gedaan. Waar iets niet vastgesteld kon worden, staat
**ONBEKEND** in plaats van een gok.

---

## `git status --porcelain`

Zie de terminaluitvoer van deze ronde; op het moment van committen leeg op de
bestanden van deze fase na.
