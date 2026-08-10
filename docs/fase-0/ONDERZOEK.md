# Fase 0 — Architectuurverificatie

Vier onbekenden, nagemeten in de broncode van de **draaiende container**
(`ha-alarm`, image `ghcr.io/home-assistant/home-assistant:2026.8`, feitelijke
versie **2026.8.1**) en in de broncode van Music Assistant zoals die in diezelfde
container is geïnstalleerd.

Alle paden zijn relatief aan `/usr/src/homeassistant/homeassistant/` voor HA
zelf, en aan `/usr/local/lib/python3.14/site-packages/` voor de
Music Assistant-bibliotheken. De regelnummers zijn die van 2026.8.1 met
`music-assistant-client==1.4.3` en `music-assistant-models==1.1.152`.

Waar iets niet met zekerheid is vastgesteld, staat dat er expliciet als
**ONBEKEND**.

---

## Versies waarop dit gemeten is

| Wat | Versie | Hoe vastgesteld |
|---|---|---|
| Home Assistant | 2026.8.1 | `docker exec ha-alarm python -c "from homeassistant.const import __version__; print(__version__)"` |
| Music Assistant (integratie) | kernintegratie, `quality_scale: bronze` | `components/music_assistant/manifest.json` |
| `music-assistant-client` | 1.4.3 | `manifest.json` `requirements` + dist-info in de container |
| `music-assistant-models` | 1.1.152 | dist-info in de container |
| Tijdzone bij de metingen | Europe/Amsterdam | expliciet gezet in de meetscripts |

**Music Assistant zelf draait niet** in deze testinstance — er is geen
MA-server. Alles onder E2 is daarom uit de **broncode** vastgesteld, niet uit
waargenomen gedrag tegen een echte server. Dat staat per antwoord aangegeven.

---

## E1 — Plannen dat een herstart overleeft

Dit is het grootste verschil met DomotiApp Scene: die kaart was reactief. Deze
moet om 06:45 afgaan, ook als er geen browser openstaat en HA vannacht herstart
is.

### E1.1 — Welke planner hoort bij welk geval?

Er zijn twee kandidaten, en ze zijn **niet** uitwisselbaar.

**`async_track_point_in_time` (`helpers/event.py:1419-1447`)** — vuurt **één
keer** op een absoluut moment. Het mechaniek zit in `_TrackPointUTCTime`
(`helpers/event.py:1453-1495`):

```python
# helpers/event.py:1461-1466
def async_attach(self) -> None:
    """Initialize track job."""
    loop = self.hass.loop
    self._cancel_callback = loop.call_at(
        loop.time() + self.expected_fire_timestamp - time.time(), self
    )
```

Het is dus een gewone `loop.call_at` op de monotone klok, met een delta die
**één keer** bij het plannen wordt berekend. Er zit een correctie in voor te
vroeg vuren (`helpers/event.py:1482-1486`, "Called %f seconds too early,
rearming"), maar **geen** correctie voor te laat vuren.

**`async_track_time_change` (`helpers/event.py:1852-1864`)** — vuurt **elke keer
dat de lokale wandklok op een patroon past**, en herplant zichzelf na elke
vuurbeurt. Het is een dunne wrapper om `async_track_utc_time_change`
(`helpers/event.py:1805-1846`) met `local=True`, en het rekenwerk zit in
`_TrackUTCTimeChange` (`helpers/event.py:1749-1802`). Die klasse plant zich
telkens opnieuw via `async_track_point_in_utc_time`, met de volgende
passende tijd uit `find_next_time_expression_time`:

```python
# helpers/event.py:1773-1778
def _calculate_next(self, utc_now: datetime) -> datetime:
    """Calculate and set the next time the trigger should fire."""
    localized_now = dt_util.as_local(utc_now) if self.local else utc_now
    return dt_util.find_next_time_expression_time(
        localized_now, *self.time_match_expression
    ).replace(microsecond=self.microsecond)
```

**Welke hoort bij welk geval — en dit is niet uit ons geheugen maar uit HA's
eigen tijdtrigger** (`components/homeassistant/triggers/time.py`), die precies
deze keuze maakt:

| Geval | Planner | Vindplaats |
|---|---|---|
| Terugkerende wandkloktijd (`at: "06:45"`) | `async_track_time_change` | `triggers/time.py:284-292` |
| Eenmalig absoluut moment (datum + tijd) | `async_track_point_in_time` | `triggers/time.py:176-200` |

Voor een wekker die elke werkdag om 06:45 afgaat is
**`async_track_time_change` de juiste**: hij herplant zichzelf, en hij rekent de
wandklok-naar-UTC-omzetting elke ronde opnieuw, inclusief zomertijd.

Voor "deze ene wekker, morgen om 06:45, daarna niet meer" is
`async_track_point_in_time` de juiste — met de kanttekening uit E1.4.

### E1.2 — Wat gebeurt er bij een herstart?

**Er is geen persistentie en geen inhaalmechanisme.** Twee onafhankelijke
vaststellingen:

1. **De planner is een timer in het geheugen.** `loop.call_at`
   (`helpers/event.py:1464-1466`) leeft in de asyncio-eventloop van het proces.
   Er is in `helpers/event.py` geen `Store`, geen schrijfactie en geen
   herstelpad. Een herstart gooit alle geplande taken weg.

2. **HA's eigen tijdtrigger slaat een gemist moment stil over.** Bij een
   absoluut moment plant hij alleen als het in de toekomst ligt:

   ```python
   # components/homeassistant/triggers/time.py:190-191
   # Only set up listener if time is now or in the future.
   if trigger_dt >= dt_util.now():
       remove = async_track_point_in_time(
   ```

   Staat het moment in het verleden, dan wordt er niets gepland, en er is geen
   `else` met een log of een melding. Voor een automatisering is dat het gewenste
   gedrag. **Voor een wekker is het precies de faalmodus die het product niet
   mag hebben.**

**Dus: ja, de integratie moet zelf herplannen bij setup.** En omdat er niets is
dat gemiste momenten bijhoudt, moet de integratie dat ook zelf doen. Wat daarvoor
in HA beschikbaar is:

- **Het startsignaal.** `helpers/start.py:56-89` biedt `async_at_start`
  (op `EVENT_HOMEASSISTANT_START`) en `async_at_started` (op
  `EVENT_HOMEASSISTANT_STARTED`). Beide vuren meteen als HA al draait, wat een
  config entry die later wordt toegevoegd ook goed afhandelt.
- **Eigen opslag.** Dezelfde `Store`-aanpak als in DomotiApp Scene. Er is niets
  in HA dat dit voor je doet.

**Hoe je zorgt dat een gemiste wekker niet stil overgeslagen wordt** — het
mechanisme is er, maar het is scherp:

> **Een `async_track_point_in_time` op een moment in het verleden vuurt
> onmiddellijk.** Gemeten (zie E1.5): een moment van twee uur terug vuurde
> +0,0002 s na het plannen.

Dat is dus een werkend inhaalmechanisme, maar zonder rem knalt een wekker van
06:45 om 14:00 aan wanneer HA op dat moment herstart. De integratie moet zelf:

1. bij setup het laatst *daadwerkelijk uitgevoerde* moment per wekker opslaan;
2. bij setup vaststellen of er een moment tussen "laatst uitgevoerd" en "nu"
   ligt dat gemist is;
3. een **respijtvenster** afwegen — hoe lang na de bedoelde tijd is afgaan nog
   gewenst in plaats van hinderlijk. Dat is een productbeslissing, geen
   technische; hij hoort in `SPEC.md`.

Wat er expliciet **niet** is: HA heeft geen "gemiste taken"-voorziening, geen
persistent-scheduler-helper en geen equivalent van cron's `anacron`. Gezocht in
`helpers/event.py`, `helpers/start.py` en HA's eigen tijdtrigger; niets
gevonden.

### E1.3 — Zomertijd en wintertijd

Dit is uitgezocht in `util/dt.py:436-555`
(`find_next_time_expression_time`), en daarna **gemeten** door de herplanlus van
`_TtrackUTCTimeChange` exact na te bootsen: telkens vanuit een echte
UTC-instant, met `as_local()` voor de fold, precies zoals
`helpers/event.py:1780-1795` het doet.

De code behandelt beide gevallen expliciet:

- **Voorjaar, niet-bestaande tijd** (`util/dt.py:500-514`): als de uitkomst niet
  bestaat, schuift hij `now` één seconde op en probeert opnieuw, tot de uitkomst
  bestaat. Het commentaar zegt het zelf: met patroon "02:30" op 28 maart *"don't
  run on 28 mar (such a wall time does not exist on this day) instead run at
  02:30 the next day"*.
- **Najaar, dubbele tijd** (`util/dt.py:516-555`): met `fold` wordt bepaald of de
  volgende match binnen de huidige fold valt of in de tweede.

**Gemeten uitkomsten, Europe/Amsterdam, 2026** (DST-overgangen: 29 maart en
25 oktober):

| Wekker | Nacht | Aantal keer | Uitkomst |
|---|---|---|---|
| 02:30 | 28→29 mrt (uur vooruit) | **0** | eerstvolgende is **30 mrt** 02:30+02:00 |
| 06:45 | 28→29 mrt | 1 | 29 mrt 06:45+02:00 (UTC 04:45) |
| 02:30 | 25 okt (uur terug) | **2** | 02:30+02:00 (UTC 00:30) **en** 02:30+01:00 (UTC 01:30) |
| 06:45 | 25 okt | 1 | 06:45+01:00 (UTC 05:45) |

Dus, letterlijk op de vraag:

- **Een wekker op 02:30 bestaat één nacht per jaar niet.** Met
  `async_track_time_change` gaat hij die ochtend **niet af** en schuift naar de
  volgende dag. Geen fout, geen log, geen melding — stil.
- **Een wekker op 02:30 bestaat één nacht per jaar twee keer.** Met
  `async_track_time_change` gaat hij die nacht **twee keer** af, een uur na
  elkaar.

**En een derde uitkomst, voor dezelfde wens.** Wie het met
`async_track_point_in_time` op een naieve lokale tijd doet, krijgt iets anders:

```
naief             = 2026-03-29T02:30:00
as_utc()          = 2026-03-29T01:30:00+00:00
terug naar lokaal = 2026-03-29T03:30:00+02:00
```

`dt_util.as_utc` interpreteert de naieve tijd als lokaal en levert een instant
die in lokale tijd **03:30** is. De wekker schuift dus stil een uur op in plaats
van overgeslagen te worden.

**Drie verschillende uitkomsten voor "wek mij om 02:30".** Welke gewenst is, is
een productbeslissing die in `SPEC.md` hoort. Voor 06:45 — het realistische
wekkeruur — maakt het geen verschil: precies één keer, op beide overgangsdagen.

### E1.4 — Een tijdzonewijziging herplant niet

Niet gevraagd, wel gevonden, en het raakt dezelfde vraag. Alleen `SunListener`
luistert op `EVENT_CORE_CONFIG_UPDATE`:

```
helpers/event.py:1672   EVENT_CORE_CONFIG_UPDATE, self._handle_config_event
```

Dat zit in `SunListener` (`helpers/event.py:1656`). `_TrackUTCTimeChange`
(`helpers/event.py:1750`) heeft **geen** zo'n listener. Verandert de eigenaar de
tijdzone van HA, dan blijft een lopende `async_track_time_change` op het al
berekende moment staan en corrigeert pas na de eerstvolgende vuurbeurt. De
integratie moet zelf op `EVENT_CORE_CONFIG_UPDATE` herplannen.

### E1.5 — Hoe nauwkeurig is het?

De eis: een wekker die een minuut te laat is, is stuk. Gemeten op een echte
`HomeAssistant`-eventloop in de container:

| Planner | Gepland op | Vuurde op | Afwijking |
|---|---|---|---|
| `async_track_time_change` | 13:34:25+02:00 | 13:34:25.289127 | **+0,2891 s** |
| `async_track_point_in_time` | 13:34:28.289280 | 13:34:28.292699 | **+0,0034 s** |
| `async_track_point_in_time`, moment 2 uur in het **verleden** | 11:34:28 | onmiddellijk | **+0,0002 s** |

De afwijking van `async_track_time_change` is **opzettelijk** en geen slordigheid:

```python
# helpers/event.py:1832-1835
# Avoid aligning all time trackers to the same fraction of a second
# since it can create a thundering herd problem
# https://github.com/home-assistant/core/issues/82231
microsecond = randint(RANDOM_MICROSECOND_MIN, RANDOM_MICROSECOND_MAX)
```

met `RANDOM_MICROSECOND_MIN = 50000` en `RANDOM_MICROSECOND_MAX = 500000`
(`helpers/event.py:87-88`). Een wekker vuurt dus **50 tot 500 ms ná** de hele
seconde, nooit ervoor — het rearm-mechanisme uit `helpers/event.py:1482-1486`
sluit te vroeg vuren uit.

**Conclusie: nauwkeurigheid is geen risico.** Een halve seconde tegen een eis van
een minuut is twee ordes van grootte marge. Twee kanttekeningen:

- De timer is een monotone `loop.call_at` met een delta die één keer wordt
  berekend. Springt de **systeemklok vooruit** (NTP-correctie na een lange
  downtime, of een VM die uit een snapshot komt), dan vuurt de timer te laat en
  is er **geen** correctie — de rearm-logica in `helpers/event.py:1482-1486`
  vangt alleen te vroeg. Hoe groot dit in de praktijk is: **ONBEKEND**, niet
  gemeten, want het vergt manipuleren van de containerklok.
- De meting is op een onbelaste eventloop gedaan. Wat een druk bezette
  eventloop met de afwijking doet, is **ONBEKEND**.

---

## E2 — Music Assistant

Music Assistant draait bij alle klanten; de kaart hoeft niet zonder te werken.

> **Belangrijke beperking van deze fase:** er is geen MA-server in de
> testinstance. Alles hieronder komt uit de broncode van de integratie en de
> twee bibliotheken, niet uit waargenomen gedrag tegen een echte server. Wat
> per antwoord onzeker blijft, staat als **ONBEKEND** benoemd.

### E2.1 — Vaststellen dat MA aanwezig is

MA is een **kernintegratie** met een config flow
(`components/music_assistant/manifest.json`: `"domain": "music_assistant"`,
`"config_flow": true`, `"integration_type": "service"`). Aanwezigheid is dus een
vraag over config entries, niet over een `DOMAIN in hass.data`-truc.

De nette route is `hass.config_entries.async_loaded_entries("music_assistant")`
(`config_entries.py:2213`), die alleen de entries teruggeeft die daadwerkelijk
geladen zijn. `async_entries(domain)` (`config_entries.py:2190`) geeft ook
entries die nog niet of niet meer geladen zijn.

**Waarom dit ertoe doet:** de MA-services (`search`, `get_library`) hebben
`config_entry_id` als **verplicht** veld (`services.yaml:112-116, 162-166`), dus
je hebt dat ID nodig, niet alleen de wetenschap dat MA bestaat.

### E2.2 — Welke van zijn entiteiten zijn speakers?

Dit is subtieler dan het lijkt, en er zijn drie valstrikken.

**Wat er niet werkt:**

- **`device_class` filtert niets.** Elke MA-mediaplayer krijgt
  `MediaPlayerDeviceClass.SPEAKER`, ongeacht wat het ding is:
  ```python
  # components/music_assistant/media_player.py:140
  self._attr_device_class = MediaPlayerDeviceClass.SPEAKER
  ```
- **Niet elke MA-player is een speaker.** `PlayerType`
  (`music_assistant_models/enums.py:401-422`) heeft acht waarden, en drie ervan
  maken geen geluid — het commentaar in de enum zegt het zelf:

  | `PlayerType` | Wat het is |
  |---|---|
  | `player` | gewone speaker |
  | `stereo_pair` | twee speakers als paar |
  | `group` | (sync)groep of playergroup |
  | `protocol` | AirPlay/Chromecast/DLNA zonder native support, *"wrapped by a Universal Player and hidden from the UI"* |
  | `display` | *"shows metadata … but does not play audio"* |
  | `visualizer` | visualiseert muziek op een scherm |
  | `light` | visualiseert muziek met licht (Hue sync, WLED) |
  | `unknown` | — |

- **`mass_player_type` is niet betrouwbaar te lezen.** Het staat in
  `extra_state_attributes` (`media_player.py:191-196`), en die verdwijnen zodra
  de entiteit `unavailable` is (`helpers/entity.py:1118-1124`). Gemeten: bij een
  onbeschikbare entiteit bleven precies `friendly_name` en `supported_features`
  over. Juist een weggevallen speaker is het geval waarin je wil weten wat hij
  was.

**Wat wél werkt:** filter op de combinatie van

1. **domein en integratie** — entity registry entries met `domain == "media_player"`
   en `platform == "music_assistant"`; en
2. **`supported_features`**, dat een unavailable entiteit **overleeft**
   (`helpers/entity.py:1169-1170`). Alle MA-players krijgen
   `MediaPlayerEntityFeature.PLAY_MEDIA` uit `SUPPORTED_FEATURES_BASE`
   (`media_player.py:72-92`), en `VOLUME_SET` alleen als de player
   volumeregeling heeft:
   ```python
   # components/music_assistant/media_player.py:776-778
   if self.player.volume_control != PLAYER_CONTROL_NONE:
       supported_features |= MediaPlayerEntityFeature.VOLUME_STEP
       supported_features |= MediaPlayerEntityFeature.VOLUME_SET
   ```
   Voor een wekker met oplopend volume is `VOLUME_SET` dus een **harde eis** aan
   de speaker, en die is uit de state te lezen ook als de speaker weg is.

**Nog een filter dat MA zelf al toepast:** een player wordt alleen een
HA-entiteit als `player.expose_to_ha` waar is
(`components/music_assistant/__init__.py:198-208`), een per-player instelling aan
de MA-kant met default `True` (`music_assistant_models/player.py:380-382`). De
klant kan dus speakers uit HA weghouden buiten onze kaart om.

**Combineer dit met het label uit E4.** De eigenaar zet "Music Assistant Wekker"
op de entiteiten die hij als wekkerspeaker wil; de integratie controleert daarna
dat wat eruit komt inderdaad een MA-mediaplayer met `PLAY_MEDIA` (en voor
volume-oploop `VOLUME_SET`) is. Het label bepaalt de bedoeling, de features
bepalen de haalbaarheid.

Wat **ONBEKEND** blijft: of `display`/`visualizer`/`light`-players in de praktijk
`expose_to_ha=False` krijgen van MA, of dat ze als HA-mediaplayer met
device_class `speaker` verschijnen. Dat is niet uit de HA-broncode te zien; het
zit in de MA-server. Zonder MA-server niet te meten.

### E2.3 — Zoeken naar afspeelbare media

Er is een service `music_assistant.search`, geregistreerd met
`supports_response=SupportsResponse.ONLY`
(`components/music_assistant/services.py:90-107`). Die is dus vanuit een
integratie aan te roepen met `blocking=True, return_response=True` en geeft de
resultaten terug — geen omweg langs een template of een event nodig.

Velden (`services.yaml:110-158`): `config_entry_id` (verplicht), `name`
(verplicht, de zoekterm), `media_type` (meervoud toegestaan), `artist`, `album`,
en onder `search_options` een `limit` (1–100, default 5) en `library_only`.

De handler (`services.py:181-231`) bouwt de zoekterm samen als
`"artist - album - name"` wanneer die velden meegegeven zijn, en geeft **zeven
emmers** terug: `artists`, `albums`, `tracks`, `playlists`, `radio`,
`audiobooks`, `podcasts`.

Elk resultaat heeft een vast schema (`schemas.py:59-67`, gevuld op regel 82-87):
`media_type`, **`uri`**, `name`, `version`, `image`, en optioneel `favorite` en
`explicit`. **De `uri` is wat je later afspeelt.**

**Per soort — te zoeken en af te spelen?** De zoekopties komen uit
`services.yaml:122-135`, de afspeelopties uit `services.yaml:16-29`:

| Soort | Te zoeken? | Af te spelen? |
|---|---|---|
| Afspeellijst (`playlist`) | ja | ja |
| Radiostation (`radio`) | ja | ja |
| Album (`album`) | ja | ja |
| Artiest (`artist`) | ja | ja |
| Los nummer (`track`) | ja | ja |
| Luisterboek (`audiobook`) | ja | ja |
| Podcast (`podcast`) | ja | ja |
| Map (`folder`) | **nee** | ja |
| Genre (`genre`) | **nee** (wel in `MediaType.ALL`, geen eigen emmer in het antwoord) | nee |

Twee aantekeningen:

- `MediaType.ALL` (`music_assistant_models/enums.py:12-24`) bevat óók `GENRE`, en
  `handle_search` gebruikt `MediaType.ALL` als default wanneer `media_type`
  ontbreekt — maar `SEARCH_RESULT_SCHEMA` (`schemas.py:116-...`) heeft geen
  emmer voor genres. Genre-resultaten komen dus niet terug bij deze service.
- Voor een wekker zijn **afspeellijst** en **radiostation** de twee soorten die
  het meest logisch zijn: ze hebben een onbepaalde duur. Een los nummer van drie
  minuten stopt van zichzelf.

Er is daarnaast `music_assistant.get_library` (`services.yaml:160-248`), ook
`SupportsResponse.ONLY`, met `favorite`, paginering en `order_by` (waaronder
`random`). Voor "kies uit mijn favoriete afspeellijsten" is dat een betere
ingang dan zoeken.

**ONBEKEND:** of alle zeven soorten bij deze klant daadwerkelijk resultaten
opleveren. Dat hangt af van de muziekproviders die in MA zijn ingesteld —
`library_only=false` zoekt bij de providers, en welke providers er zijn is niet
uit de HA-broncode te zien.

### E2.4 — Welke service roep je aan om af te spelen?

Twee routes, en de tweede is de betere.

**Route 1 — `media_player.play_media`**, de standaard-HA-service. MA implementeert
`async_play_media` (`media_player.py:375-407`), die media-source-ID's oplost en
daarna doorschuift naar zijn eigen geavanceerde handler.

**Route 2 — `music_assistant.play_media`**
(`services.py:130-145`, velden in `services.yaml:3-54`). Dit is de route van MA
zelf, met velden die de standaardservice niet heeft:

| Veld | Waarvoor |
|---|---|
| `media_id` (verplicht) | de `uri` uit het zoekresultaat |
| `media_type` | artist, album, audiobook, folder, playlist, podcast, track, radio |
| `artist`, `album` | verfijning bij zoeken op naam |
| `enqueue` | play, replace, next, replace_next, add |
| `radio_mode` | oneindig doorspelen in dezelfde stijl |
| `username` | welke MA-gebruiker |

De target is beperkt tot `media_player`-entiteiten van de integratie
`music_assistant` met `PLAY_MEDIA` (`services.yaml:4-9`) — HA dwingt dat af, dus
een niet-MA-speaker kun je hier niet per ongeluk in stoppen.

**Hoe `media_id` wordt opgelost** (`media_player.py:452-557`), in deze volgorde:
een URI wordt geverifieerd met `verify_item_uri` (schema ≥ 33) of direct
geaccepteerd als hij `://` bevat (< 33); een numerieke waarde wordt een
`library://`-URI; en als laatste redmiddel zoekt hij op naam met
`get_item_by_name`. Lukt niets, dan is het **luid**:

```python
# components/music_assistant/media_player.py:539-542
if not media_uris:
    raise HomeAssistantError(
        f"Could not resolve {media_id} to playable media item"
    )
```

Dat is precies het gedrag dat je wil. **Maar het wordt nooit bereikt als de
speaker offline is** — zie E2.6.

**Aanbeveling:** sla de `uri` uit het zoekresultaat op, niet de naam. Dan is
afspelen een verificatie in plaats van een nieuwe zoekopdracht, en verandert het
resultaat niet doordat de bibliotheek is gewijzigd.

**Nog een route, voor de volledigheid:** `music_assistant.play_announcement`
(`services.yaml:56-84`) speelt een URL af met `announce_volume` (1–100) en een
optionele voor-toon. Dat is bedoeld voor deurbellen, en niet voor 20 minuten
wekmuziek — maar het is wél de enige MA-service met een volume-argument erin.

### E2.5 — Volume, en kan dat oplopend?

**Volume zetten** gaat met de standaardservice `media_player.volume_set`, die bij
MA hier uitkomt:

```python
# components/music_assistant/media_player.py:313-318
@catch_musicassistant_error
@override
async def async_set_volume_level(self, volume: float) -> None:
    """Send new volume_level to device."""
    volume = int(volume * 100)
    await self.mass.players.player_command_volume_set(self.player_id, volume)
```

HA werkt met 0.0–1.0, MA met 0–100. Aan de clientkant is dat
`players.volume_set(player_id, volume_level)`
(`music_assistant_client/players.py:82-86`).

Voor een **groep** leest HA het groepsvolume in plaats van het spelervolume:

```python
# components/music_assistant/media_player.py:261-265
if player.type == PlayerType.GROUP:
    volume: int | None = player.group_volume
else:
    volume = player.volume_level
self._attr_volume_level = volume / 100 if volume is not None else None
```

`group_volume` is het **gemiddelde** van de kinderen en is `None` als geen enkel
kind volumeregeling heeft (`music_assistant_models/player.py:387-391`).

**Kan het oplopend? Niet via een aanroep. Dit is een harde bevinding.**

Er ís een `fade_in` in Music Assistant, maar hij is op drie manieren
onbereikbaar voor dit doel:

1. Hij is een **boolean**, geen duur:
   `player_queues.play_index(..., fade_in: bool = False)`
   (`music_assistant_client/player_queues.py:188-202`) en
   `player_queues.resume(queue_id, fade_in)` (regel 101-106).
2. `player_queues.play_media` — de functie die de HA-integratie
   **daadwerkelijk** aanroept (`media_player.py:551-557`) — heeft **geen**
   `fade_in`-parameter (`player_queues.py:204-214`).
3. De HA-integratie roept `fade_in`, `play_index` en `resume` **nergens** aan.
   Gezocht met grep over alle `components/music_assistant/*.py`: nul treffers.

Bovendien is `streamdetails.fade_in` gemarkeerd als *"managed by the queue/stream
controller and may not be set by providers"*
(`music_assistant_models/streamdetails.py:207-214`).

Vanuit HA is er dus alleen:

| Service | Wat het doet |
|---|---|
| `media_player.volume_set` | absoluut zetten, één waarde |
| `media_player.volume_up` / `volume_down` | één stap, stapgrootte door de speaker bepaald |
| `media_player.volume_mute` | dempen |

**Dus: de oploop van stil naar het ingestelde volume in 20 seconden moet de
integratie zelf maken**, als een reeks `volume_set`-aanroepen op een timer. Dat
is goed te doen — het is een `async_track_time_interval` of een simpele lus met
`asyncio.sleep` — maar het is **ons** werk, geen MA-functie, en het heeft
gevolgen die in `SPEC.md` horen:

- **Hoeveel stappen?** 20 stappen van 1 s is 20 service-aanroepen per wekker per
  speaker. Bij drie speakers is dat 60. Dat is niet veel, maar het is ook niet
  nul: elke aanroep gaat over de WebSocket naar de MA-server en van daar naar het
  apparaat.
- **Niet elke speaker heeft een fijne volumeschaal.** `VOLUME_SET` zegt dát het
  kan, niet met welke resolutie. Bij een grove schaal wordt de "oploop"
  hoorbaar trapsgewijs. **ONBEKEND** zonder echte hardware.
- **Wat als de gebruiker tijdens de oploop zelf aan het volume draait?** De lus
  moet dat merken en stoppen, anders vecht de integratie met de gebruiker. Dit is
  hetzelfde patroon als de terugvalwaarde-valkuil uit DomotiApp Scene.
- **Het volume moet na de wekker terug.** Zet de integratie het volume op 15 %
  voor een zachte start, dan staat de speaker daarna op 15 % voor de rest van de
  dag. Er moet een herstelstap zijn — en de oorspronkelijke waarde moet
  *vóór* het wijzigen gelezen worden, want als de speaker later wegvalt is
  `volume_level` niet meer te lezen (valkuil 18).

### E2.6 — Wat als de speaker offline is op het moment van afspelen?

**Dit is de gevaarlijkste bevinding van deze fase, en hij is gemeten.**

HA filtert onbeschikbare entiteiten uit een service-aanroep weg, zonder
exceptie:

```python
# helpers/service.py, in _resolve_entity_service_call_entities (regel 676)
entity_candidates = [e for e in entity_candidates if e.available]
```

Er is één log-mogelijkheid, en die is voorwaardelijk. `log_missing`
(`helpers/target.py:136-155`) logt een `WARNING`, maar hij wordt gevoed met
`referenced.referenced` — de entiteiten die **expliciet op entity_id** genoemd
zijn. Entiteiten die via een **label, gebied of apparaat** binnenkomen staan in
`indirectly_referenced`, en het commentaar zegt letterlijk *"Should not trigger a
warning when they don't exist"* (`helpers/target.py:123-125`).

**Gemeten** met een echte `EntityComponent`, een echte entity service en twee
entiteiten (een beschikbare, een onbeschikbare), beide met het label
"Music Assistant Wekker":

| Aanroep | Exceptie? | Handler aangeroepen op | Waarschuwingen |
|---|---|---|---|
| op `entity_id` van de offline speaker | nee | `[]` | 1: *"Referenced entities nepspeaker.speaker_uit are missing or not currently available"* |
| op `label_id` (beide speakers) | nee | `['nepspeaker.speaker_aan']` | **0** |
| op `entity_id` van de beschikbare speaker (controle) | nee | `['nepspeaker.speaker_aan']` | 0 |

Dus:

> **Een wekker die op een offline speaker afgaat, "slaagt" en maakt geen geluid.
> Bij targeting op label komt er niet eens een regel in het log.**

De regel `raise HomeAssistantError("Could not resolve ... to playable media
item")` uit E2.4 wordt **niet** bereikt: de filtering gebeurt vóór de
integratiecode.

En als de speaker wél beschikbaar is maar de MA-server valt weg, is de entiteit
ook onbeschikbaar — `available` is de conjunctie van beide:

```python
# components/music_assistant/entity.py:72-74
def available(self) -> bool:
    """Return availability of entity."""
    return self.player.available and bool(self.mass.connection.connected)
```

**Gevolg voor het ontwerp.** De integratie mag afspelen niet aan HA's
service-dispatch overlaten. Ze moet vóór het afspelen zelf de state van de
speaker lezen, en bij `unavailable` zelf handelen. Wat "handelen" is, is een
productbeslissing voor `SPEC.md`, maar de opties zijn:

1. een andere speaker uit het label pakken die wél beschikbaar is;
2. terugvallen op de verlichtingswekker alleen, en dat **zichtbaar** melden;
3. een `persistent_notification` of repair issue achterlaten, zodat de eigenaar
   weet dat de wekker niet gewerkt heeft.

Optie 3 is niet optioneel: zonder terugmelding is dit een fout die de klant pas
ontdekt doordat hij zich verslaapt.

---

## E3 — De person-entiteit als opslagsleutel

### E3.1 — Heeft een person-entiteit een registry-entry met een stabiel ID?

**Ja.** En daarmee geldt dezelfde constructie als bij de light group van
DomotiApp Scene.

De keten, stap voor stap:

1. **Een person-entiteit heeft een `unique_id`.** Hij komt uit de `id` in de
   opslag:
   ```python
   # components/person/__init__.py:448
   self._attr_unique_id = config[CONF_ID]
   ```
   Dat geldt voor **beide** soorten persons: `PERSON_SCHEMA` maakt `CONF_ID`
   verplicht voor YAML-persons (`person/__init__.py:74-84`), en
   `PersonStorageCollection` genereert hem voor persons uit de UI.

2. **Een entiteit met een `unique_id` krijgt een entity registry entry.**
   `entity_platform.py:1014-1035` roept `entity_registry.async_get_or_create(...)`
   aan; de `else`-tak op regel 1045 (`# entity.unique_id is None`) slaat de
   registry over. Person-entiteiten gaan via een `EntityComponent` met
   `collection.sync_entity_lifecycle` (`person/__init__.py:369-392`), dus ze
   komen langs dat pad.

3. **Dat registry-entry heeft een stabiel, willekeurig ID:**
   ```python
   # helpers/entity_registry.py:234-235
   id: str = attr.ib(
       converter=attr.converters.default_if_none(factory=uuid_util.random_uuid_hex)
   )
   ```
   Een `random_uuid_hex`, één keer gezet bij het aanmaken, onafhankelijk van
   naam en van entity_id. **Dit is de opslagsleutel die je wil.**

### E3.2 — Wat is er nog stabiel, en wat gebeurt er bij hernoemen of verwijderen?

Er zijn zelfs **twee** stabiele ID's, en het is nuttig te weten dat ze niet
hetzelfde zijn.

| Wat | Voorbeeld | Stabiel bij hernoemen? |
|---|---|---|
| `RegistryEntry.id` | `4f2a…` (uuid hex) | **ja** |
| `unique_id` = person-`id` | `sven` | **ja** |
| `entity_id` | `person.sven` | zie hieronder |
| `name` | `Sven` | nee, dat is juist wat je hernoemt |

De person-`id` wordt bij het aanmaken **uit de naam geslugificeerd**:

```python
# components/person/__init__.py:285-289
@callback
@override
def _get_suggested_id(self, info: dict[str, str]) -> str:
    """Suggest an ID based on the config."""
    return info[CONF_NAME]
```

en `IDManager.generate_id` maakt daar `slugify(suggestion)` van, met
`_2`, `_3` … bij botsingen (`helpers/collection.py:96-106`). Een person "Sven"
krijgt dus `id` `sven`.

**Bij hernoemen blijft die `id` staan.** `_update_data` voegt alleen de
gewijzigde velden samen en laat `id` ongemoeid:

```python
# components/person/__init__.py:291-301
async def _update_data(self, item: dict, update_data: dict) -> dict:
    """Return a new updated data object."""
    update_data = self.UPDATE_SCHEMA(update_data)
    ...
    return {**item, **update_data}
```

Dus: hernoem je "Sven" naar "Sven Kool", dan blijft `unique_id` `sven` en blijft
`RegistryEntry.id` hetzelfde. **De wekkers verdwijnen niet.** Dat is precies de
eigenschap die bij DomotiApp Scene de reden was om op het registry-entry-ID op
te slaan.

**Bij verwijderen** verdwijnt de person uit de collection en daarmee het
registry-entry. De opgeslagen wekkers blijven dan aan een ID hangen dat nergens
meer op wijst. Dat is hetzelfde gedrag als bij DomotiApp Scene, en de les daar
was: **maak er een opruimoverzicht voor**, en beschrijf in de klantdocumentatie
dat een opnieuw aangemaakte person leeg begint.

**Aanbeveling: gebruik `RegistryEntry.id`, niet `unique_id`.** Beide zijn
stabiel, maar:

- `RegistryEntry.id` is de conventie die DomotiApp Scene al gebruikt, dus de
  Store-laag en het opruimoverzicht kunnen dezelfde vorm houden;
- `unique_id` is voor een person een slug van de naam, en dat ziet er in de
  opslag uit als iets dat betekenis heeft. Dat leidt tot de verleiding om erop te
  matchen. Bij een tweede person "Sven" is het `sven_2`, en dat is precies zo'n
  detail waar later een aanname op sneuvelt.

**Niet geverifieerd:** dit is uit de broncode vastgesteld, niet op een draaiende
instance met echte persons. De testinstance is niet ge-onboard (zoals opgedragen),
en zonder onboarding bestaat er geen person en geen gebruiker. **Dit hoort in
fase 1 op de instance nagemeten te worden**, met één handeling: maak een person
aan, lees zijn registry-entry uit, hernoem hem, lees opnieuw.

---

## E4 — Filteren op labels

De eigenaar zet twee labels op entiteiten: "Verlichting Wekker" en
"Music Assistant Wekker".

Dit is het enige onderdeel dat **volledig empirisch** is nagemeten, met echte
registries op een echte `HomeAssistant` in de container.

### E4.1 — Hoe leest een integratie de labels van een entiteit?

Labels zitten op **drie** registries, elk als een eigen `set[str]` van
`label_id`'s:

| Waar | Vindplaats |
|---|---|
| entity registry entry | `helpers/entity_registry.py:237` |
| device registry entry | `helpers/device_registry.py:413` |
| area registry entry | `helpers/area_registry.py:82` |

**Het label heeft een eigen ID, en dat is een slug van de naam.** Gemeten:

```
'Verlichting Wekker'      -> label_id = 'verlichting_wekker'
'Music Assistant Wekker'  -> label_id = 'music_assistant_wekker'
```

Opzoeken op naam gaat met `async_get_label_by_name`
(`helpers/label_registry.py:120-123`). Let op: `LabelEntry` heeft **ook** een
`normalized_name`, en die is iets anders — gemeten:
`normalized_name='verlichtingwekker'`, zonder underscore. Gebruik `label_id`.

Rechtstreeks de entiteiten met een label opvragen kan met
`er.async_get(hass).entities.get_entries_for_label(label_id)`. Maar dat vindt
**alleen** labels die op de entiteit zelf staan.

### E4.2 — Werkt dat ook als het label op het apparaat of het gebied staat?

**Rechtstreeks lezen: nee. Via de target-helper: ja.**

Gemeten met vier entiteiten — één met het label op de entiteit, één op een
apparaat met het label, één in een gebied met het label, en één verborgen
entiteit met het label:

```
2. DRIE PLAATSEN waar het label kan staan
   (a) entiteit  : light.label_op_entiteit  labels={'verlichting_wekker'}
   (b) apparaat  : light.label_op_apparaat  labels=set() (leeg!)
   (c) gebied    : light.label_op_gebied  labels=set() (leeg!)

3. DIRECT LEZEN van entity_registry.labels — vindt alleen (a) en (d)
   ['light.label_op_entiteit', 'light.verborgen']
```

De entiteit onder een gelabeld apparaat heeft dus **zelf een leeg labels-veld**.
Wie alleen `entity_entry.labels` leest, mist hem.

De helper die het wél goed doet is
`async_extract_referenced_entity_ids` (`helpers/target.py:158-294`). Die
behandelt alle drie de plaatsen:

```python
# helpers/target.py:223-237
if target_selection.label_ids:
    label_reg = lr.async_get(hass)
    for label_id in target_selection.label_ids:
        if label_id not in label_reg.labels:
            selected.missing_labels.add(label_id)

        for entity_entry in entities.get_entries_for_label(label_id):
            if entity_entry.hidden_by is None:
                selected.indirectly_referenced.add(entity_entry.entity_id)

        for device_entry in dev_reg.devices.get_devices_for_label(label_id):
            selected.referenced_devices.add(device_entry.id)

        for area_entry in area_reg.areas.get_areas_for_label(label_id):
            selected.referenced_areas.add(area_entry.id)
```

waarna regel 258-292 de apparaten en gebieden naar entiteiten uitrolt. Gemeten
resultaat:

```
4. EXPANSIE via helpers/target.py — label_id als target
   primary_entities_only=True
     indirectly_referenced: ['light.label_op_apparaat', 'light.label_op_entiteit', 'light.label_op_gebied']
   primary_entities_only=False
     indirectly_referenced: ['light.label_op_apparaat', 'light.label_op_entiteit', 'light.label_op_gebied', 'sensor.diagnostiek_op_apparaat']
```

Drie dingen die daaruit volgen en die makkelijk fout gaan:

1. **`primary_entities_only=True` (de default) laat config- en
   diagnostiek-entiteiten weg** bij expansie via apparaat en gebied
   (`helpers/target.py:163-173, 252-256`). Dat is precies wat je wil: een
   gelabeld apparaat levert zijn lamp op, niet zijn signaalsterkte-sensor. Zet
   het niet op `False`.
2. **Verborgen entiteiten vallen af** (`helpers/target.py:230`). In de meting
   zat `light.verborgen` wél in de directe uitlezing en **niet** in de expansie.
3. **Alles komt in `indirectly_referenced` terecht, niet in `referenced`.** Dat
   is exact de reden dat een offline speaker via een label geen waarschuwing
   oplevert (E2.6). Dezelfde eigenschap die het filteren fijn maakt, maakt het
   falen stil.

**Let op de deprecation.** De meting is gedaan met `TargetSelectorData`, en die
gaf: *"The deprecated class TargetSelectorData was instantiated. It will be
removed in HA Core 2026.12.0. Use TargetSelection instead"*. Gebruik in
productiecode **`TargetSelection`**.

### E4.3 — Hoe reageert de kaart als een label niet bestaat?

Dat is de situatie bij een nieuwe klant. **Er komt geen exceptie; je krijgt een
lege selectie plus een expliciet signaal dat het label niet bestond.** Gemeten:

```
5. LABEL BESTAAT NIET (nieuwe klant) — target op 'wekker_bestaat_niet'
   referenced           : []
   indirectly_referenced: []
   missing_labels       : {'wekker_bestaat_niet'}
   -> geen exceptie, lege selectie
```

Dat `missing_labels` is de bruikbare kant hiervan: de integratie kan
**onderscheiden** tussen "het label bestaat niet" en "het label bestaat maar er
zit niets in". Dat zijn twee verschillende meldingen aan de klant:

- label bestaat niet → *"Maak eerst een label 'Verlichting Wekker' aan en zet het
  op de lampen die mee moeten doen."*
- label bestaat, leeg → *"Er zijn nog geen lampen met het label 'Verlichting
  Wekker'."*

Zonder dat onderscheid wordt het één vage melding. Het onderscheid is er, dus
gebruik het.

### E4.4 — Hernoemen en verwijderen van een label

Beide gemeten.

**Hernoemen verandert de `label_id` niet:**

```
6. LABEL HERNOEMEN — verandert de label_id?
   naam 'Verlichting Wekker' -> 'Wekkerlampen'
   label_id voor: 'verlichting_wekker'   na: 'verlichting_wekker'   gelijk: True
   entiteit houdt label: {'verlichting_wekker'}
```

`async_update` (`helpers/label_registry.py:182-213`) zet alleen `name`, `color`,
`icon`, `description` en `modified_at` — nooit `label_id`.

**Dus: sla nooit de labelnaam op, sla de `label_id` op.** Doe de opzoeking op
naam één keer, en bewaar het resultaat.

**Verwijderen ruimt alle verwijzingen op:**

```
7. LABEL VERWIJDEREN — wat blijft er staan?
   entiteit labels na verwijderen : set()
   apparaat labels na verwijderen : set()
   gebied  labels na verwijderen  : set()
```

Alle drie de registries luisteren op `EVENT_LABEL_REGISTRY_UPDATED` met een
filter op `action == "remove"` en wissen dan hun verwijzing —
`helpers/entity_registry.py:2593-2602`, `helpers/device_registry.py:3317`,
`helpers/area_registry.py:544`.

Er blijft dus **geen** verweesde verwijzing achter. Voor de kaart is een
verwijderd label niet te onderscheiden van een label dat nooit bestond, en dat is
prima: beide leveren `missing_labels`.

---

## Taak F — Wat dit betekent

### Welke van de vier is het grootste risico?

**E2, Music Assistant — en niet om de reden die je zou verwachten.**

De vier onbekenden zijn niet gelijk in risico:

| | Risico | Waarom |
|---|---|---|
| **E1** planning | **middel** | Alle mechanismen zijn er en gemeten. Het werk is bekend en af te bakenen: zelf herplannen, zelf een gemist moment inhalen, zelf op tijdzonewijziging herplannen. Geen verrassingen meer te verwachten. |
| **E2** Music Assistant | **hoog** | Twee onafhankelijke problemen, waarvan één stil. Zie hieronder. |
| **E3** person | **laag** | Werkt zoals bij DomotiApp Scene. Eén verificatie op de instance in fase 1 en het is klaar. |
| **E4** labels | **laag** | Volledig gemeten, het gedrag is beter dan gehoopt (`missing_labels` is een cadeautje), en de enige actie is: gebruik `TargetSelection` en sla `label_id` op. |

E2 is het grootste risico om drie redenen die bij elkaar optellen:

1. **De stille faalmodus is precies de faalmodus van dit product.** Een
   offline speaker + targeting op label = de wekker slaagt, maakt geen geluid, en
   laat **geen enkel spoor** achter. Bij een wekkerkaart is dat de ergste
   mogelijke fout: de klant ontdekt hem doordat hij zich verslaapt, en er is niets
   in het log om achteraf vast te stellen wat er gebeurd is. Alle andere
   bevindingen van deze fase zijn hooguit hinderlijk; deze is dat niet.

2. **Het oplopende volume bestaat niet en moet gebouwd worden.** De eis "van stil
   naar het ingestelde volume in 20 seconden" leest als een instelling. Het is
   een component: een lus, een afbreekvoorwaarde als de gebruiker zelf aan het
   volume draait, een herstelstap na de wekker, en een gelezen beginwaarde die je
   *vóór* het wijzigen moet vastleggen omdat je hem later misschien niet meer kunt
   lezen. Dat is een eigen testronde waard.

3. **Het is het enige onderdeel dat niet empirisch geverifieerd is.** E1, E3 en
   E4 zijn gemeten of uit de broncode hard vast te stellen. E2 is uit de broncode
   gelezen zonder MA-server erbij. De onbekenden die overblijven — de
   volumeresolutie van echte speakers, of `display`/`visualizer`-players als
   HA-entiteit opduiken, welke media-soorten bij deze klant resultaten opleveren —
   zijn alle drie pas te beantwoorden tegen een echte MA-server.

### Moet het productontwerp anders dan de eigenaar voor ogen heeft?

**Vier punten. Twee zijn een echte koerswijziging, twee zijn een waarschuwing.**

**1. Een wekker mag niet alleen op Music Assistant leunen. (koerswijziging)**

De opdracht zegt: *"Music Assistant draait bij alle klanten; de kaart hoeft niet
zonder te werken."* Dat is als **installatie**-eis redelijk. Maar E2.6 laat zien
dat het als **runtime**-eis niet houdbaar is: MA kan aanwezig zijn en de speaker
kan om 06:45 offline zijn, en dan is er geen geluid en geen melding. Een speaker
die 's nachts in standby gaat, een wifi-hikje, een MA-server die na een
HA-herstart nog aan het opstarten is — alle drie realistisch op precies dat
moment.

Wat er moet bijkomen:

- **een beschikbaarheidscontrole vóór het afspelen**, in de integratie, niet
  vertrouwend op HA's service-dispatch;
- **een expliciet gedrag als de speaker weg is**: een andere gelabelde speaker,
  of de verlichtingswekker alleen;
- **een terugmelding die de eigenaar 's ochtends ziet** — een repair issue of een
  persistent notification. Dit is geen nice-to-have. Zonder terugmelding is de
  enige manier waarop de klant het ontdekt, dat hij te laat is.

Dat betekent ook dat de **verlichtingswekker de betrouwbare helft** van dit
product is en het geluid de onbetrouwbare. Dat is de omgekeerde verhouding van
wat een wekker suggereert, en het hoort in `SPEC.md` te staan.

**2. "Oplopend volume in 20 seconden" is een component, geen instelling.
(koerswijziging)**

Zie hierboven onder punt 2. De eigenaar mag dit als één regel in de eisen zien;
in de planning is het een eigen ronde met eigen tests. Als er geknepen moet
worden, is dit de kandidaat: een wekker die op het ingestelde volume begint,
werkt. Een wekker die geen geluid maakt, niet.

**3. Wekkertijden tussen 02:00 en 03:00 hebben drie mogelijke uitkomsten.
(waarschuwing)**

Twee nachten per jaar, en het gaat om precies die twee nachten waarin niemand
eraan denkt. `SPEC.md` moet kiezen wat er gebeurt en dat opschrijven —
overslaan, één keer, of twee keer. Ik zou de kaart in de editor een **melding**
laten geven bij een tijd in dat uur, in plaats van het stil te laten gebeuren.
Praktisch is dit klein: 06:45 heeft er geen last van. Maar het is een
klantmelding die niet te reproduceren is als je niet weet dat hij bestaat.

**4. De opslag hangt aan de person, en dat werkt — met dezelfde prijs als bij
DomotiApp Scene. (waarschuwing)**

Een verwijderde en opnieuw aangemaakte person begint met lege wekkers, en de oude
wekkers blijven aan een dood ID hangen. Dat is bedoeld gedrag, maar het moet in
de klantdocumentatie staan en het vraagt een opruimoverzicht. Dat is precies wat
fase 5 van DomotiApp Scene opleverde, dus de vorm is bekend.

### Wat ik in fase 1 zou meenemen

Niet gevraagd, maar het volgt uit het bovenstaande en uit `AANPAK.md`:

1. **Neem de rooktest van DomotiApp Scene over** — `build.mjs`,
   `check-registratie.mjs`, `registreer.js`, de CI-workflow, `.gitattributes`.
   Dat is de hele buildketen, en `.gitattributes` is nu al nodig: bij de eerste
   commit gaf git "LF will be replaced by CRLF" op vier bestanden.
2. **Sluit de rooktest af op een instance die je nooit hard herlaadt, met een
   browser die die HA al kende.** Dat is de stap die in DomotiApp Scene ontbrak en
   daar fase 7, 8 en 9 heeft gekost.
3. **Meet E3 na op de instance** zodra er ge-onboard is: person aanmaken,
   registry-entry uitlezen, hernoemen, opnieuw uitlezen.
4. **Zet een MA-server op, of stel vast dat dat niet gaat.** Zolang die er niet
   is, blijft het grootste risico van dit product ongemeten. Als een echte
   MA-server niet haalbaar is in de testopstelling, dan is dát een bevinding die
   het ontwerp raakt: dan moet elk MA-gedrag defensief geschreven worden, want het
   is nooit geverifieerd.
