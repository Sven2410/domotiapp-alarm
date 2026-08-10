# CLAUDE.md — DomotiApp Alarm

Dit bestand gaat over **hoe** we werken. Wat we bouwen komt later in `SPEC.md`;
zodra dat bestaat, is het bindend en wint het van een opdracht die ervan afwijkt.

Dit is het tweede product in deze reeks. Het eerste, **DomotiApp Scene**
(`C:\dev\domotiapp-scene`, in productie op 1.0.2), heeft een werkwijze en een
valkuilenlijst opgeleverd. Wat hieronder staat is daaruit overgenomen voor zover
het hier ook geldt, plus wat fase 0 zelf heeft gemeten.

`C:\dev\domotiapp-scene` is **uitsluitend leesmateriaal**. Nooit in schrijven.

---

## Werkafspraken

- **Fases met een duidelijk stoppunt.** Elke ronde eindigt met een PR waarin het
  bewijs in de beschrijving staat. **De eigenaar merget zelf; Claude Code merget
  nooit.** `main` is altijd de laatste geverifieerde staat.
- **Branch per ronde:** `fase-<N>/<korte-naam>`, één PR naar `main`.
- **Een test telt pas als hij aantoonbaar faalt op de code van vóór de fix.**
  Toon dat ook — draai de nieuwe test tegen de oude code en plak de uitvoer.
  Regressiewachten mógen op oude code slagen, maar worden dan expliciet als
  **REGRESSIEWACHT** gelabeld; nieuw gedrag als **NIEUW GEDRAG**.
  Bijbehorende valkuil: **"de setup faalt niet"-tests slagen ook op de oude
  code.** Dat is triviaal waar in code die het betreffende ding niet doet. Zet er
  een positieve controle vóór, anders is het label NIEUW GEDRAG onterecht.
- **Frontendwijzigingen worden in een echte browser met echte kliks
  geverifieerd** via `claude-in-chrome`. Een synthetisch event bewijst de
  handler, niet de control. **Toon `isTrusted`.**
- **Tekstvelden worden met échte toetsaanslagen geverifieerd**, nooit met
  `.value =` of een programmatisch `input`-event, en **in elk tekstveld wordt
  expliciet een spatie getypt**. Toon `isTrusted` op de keydown van die spatie.
  In DomotiApp Scene accepteerde een naamveld een hele fase lang geen spatie,
  en de meting die dat had moeten vangen gebruikte één woord zonder spatie.
- **Uitlijning en verdeling worden met gemeten posities aangetoond**, niet op het
  oog: lees de `getBoundingClientRect()` uit en toon de afstanden.
- **Bewijs eerst dat je verse code meet.** De service worker wissen is niet
  genoeg. Gebruik `fetch(url, {cache:'reload'})` en vergelijk hash of lengte met
  het bestand op schijf. Toon beide getallen.
- **Geen jsdom-tests die een browser nabootsen.** jsdom stubt HA-componenten
  volledig en beoordeelt de CSS-cascade niet. Pure logica mag wél in een gewone
  Node-test — en juist daarom wordt beslislogica van renderen afgesplitst
  **zodra er een tweede beslissing bijkomt**, niet zodra er een fout is. Het
  criterium: kan ik dit gedrag in een gewone Node-test opschrijven? Zo nee, dan
  staat het op de verkeerde plek.
- **Toon nooit een terugvalwaarde die je niet zou opslaan.** In DomotiApp Scene
  is dit twee keer misgegaan: de editor toonde een waarde uit de levende
  entiteit die bij Opslaan nergens terechtkwam. Rust in de weergave is dat nooit
  waard. Geldt naast de regel dat de opslag nooit stil op een default terugvalt.
- **Elk rapport eindigt met**, in deze volgorde: samenvatting, wat niet lukte,
  aannames (of letterlijk "geen aannames gedaan"), en `git status --porcelain`.
- **Elk rapport gaat óók naar `docs/fase-<N>/RAPPORT.md`** en wordt meegecommit.
  De terminaluitvoer is bij de eigenaar niet betrouwbaar over te nemen.
- **Een valkuil en de projectstand gaan mee in de PR van de fase die ze vond.**
  In DomotiApp Scene is `CLAUDE.md` als losse fase geschreven en liep het daarna
  zeven fases achter. Niet herhalen.
- **Kleuren lopen via HA-themavariabelen, nooit hardcoded.** Uitzondering:
  iconen mogen vaste kleuren en gradients dragen.
- **Alle zichtbare teksten zijn Nederlands.**
- **Tags en releases maakt de eigenaar zelf, zonder `v`-prefix.** Claude Code
  maakt ze nooit, en merget geen PR's.

---

## Omgeving

- Windows 11, PowerShell, `C:\dev\domotiapp-alarm`.
- **Testinstance:** container `ha-alarm`, compose-project `domotiapp-alarm-dev`,
  **poort 8129**, image gepind op `2026.8` (draait 2026.8.1).
  Config in `.ha-dev-config/` (gitignored). **`default_config:` staat daar
  uiteengelegd, minus `my`** — zie valkuil 32; met `my` erin is geen enkele
  externe-stap-config-flow af te maken.
- **De poorten 8123, 8124, 8125, 8126 en 8127 zijn bezet door andere projecten
  en mogen nooit gebruikt worden.**
- **De productie-HA wordt nooit aangeraakt, ook niet gelezen.**
- **Minimum HA-versie: 2026.8.**
- `name:` staat expliciet in `docker-compose.yml`. Zonder die regel ziet Docker
  Compose meerdere compose-bestanden in dezelfde mapstructuur als één project en
  vervangt het de verkeerde container.
- **`custom_components/domotiapp_alarm/` moet in git bestaan vóór de container
  start**, anders maakt Docker er zelf een lege root-owned map van.

### Music Assistant-testserver (fase 0b)

- `docker-compose.music-assistant.yml`, project **`domotiapp-alarm-ma`**,
  container **`ma-alarm`**, poorten **8095** (web-UI/API) en **8097**
  (audiostream). Config in `.ma-dev-config/` (gitignored).
- **HA bereikt MA op `http://host.docker.internal:8095`.** Binnen de
  HA-container wijst `localhost` naar HA zelf. De **browser** moet juist
  `localhost:8095` gebruiken, want die kent `host.docker.internal` niet — gemeten
  in fase 3c: `ping host.docker.internal` op de host geeft "could not find host".
  **Voor de config flow gebruik je geen van beide maar het LAN-IP van de host**
  (`http://192.168.1.212:8095`, gemeten bereikbaar van *beide* kanten): de flow
  bouwt zijn login-URL uit de URL die je HA geeft, dus met `host.docker.internal`
  opent de browser een adres dat hij niet kan vinden. Dat IP komt van DHCP en kan
  veranderen.
- **MA vereist authenticatie** (schema 31, min 28). Er is geen optie om dat uit
  te zetten — gezocht op `DISABLE_AUTH|no_auth|allow_anonymous`, nul treffers.
  De eerste admin maakt de **eigenaar** aan via `http://localhost:8095/setup`;
  Claude Code maakt geen accounts en typt geen wachtwoorden.
- **MA's API is JSON-RPC over `POST /api`**, met `{"command": ..., "args": {...}}`
  en een bearer-token. Vanuit de browser: token uit `localStorage.ma_access_token`,
  fetch binnen de pagina, alleen het resultaat teruggeven.
- **Speakers zonder hardware:** de MA-image bevat `snapserver` **en**
  `snapclient`. MA start zijn eigen snapserver (controlepoort 1705). Een
  headless speaker met echte volumeregeling start je met:
  ```
  docker exec -d ma-alarm sh -c 'snapclient tcp://127.0.0.1:1704 \
    --hostID wekker-slaapkamer --instance 1 \
    --player file:filename=/dev/null --mixer software \
    --logsink file:/tmp/snap1.log'
  ```
  Er loopt dan een echte stream: het log toont `Codec: flac, sampleformat:
  48000:16:2`.
- **Muziekbron zonder account:** **SomaFM** werkt (zoeken op kanaalnaam,
  browsen via `somafm://`) en **iTunes Podcast Search** werkt.
  **RadioBrowser is wisselvallig** (1 van 6 zoekopdrachten lukte; netwerk, DNS-SRV
  en de `radios`-bibliotheek zijn uitgesloten). **Spotify werkt niet** achter
  Docker Desktop: de OAuth-callback komt niet terug.
- **Album, artiest en los nummer zijn op deze instance niet te toetsen** — die
  komen bij een klant uit een streamingprovider. De toetslijst daarvoor staat in
  `docs/fase-0b/RAPPORT.md` onder "Wat de eigenaar moet toetsen".

---

## Valkuilen

De eerste groep is overgenomen uit DomotiApp Scene omdat ze
productonafhankelijk zijn. Elke valkuil heeft een **vindplaats** — zonder
vindplaats wordt zo'n lijst binnen twee maanden folklore.

### Overgenomen uit DomotiApp Scene

1. **Registreren van custom elements gaat altijd via `src/registreer.js`.**
   HA 2026.8 draait `@webcomponents/scoped-custom-element-registry`; de
   gepatchte `get` leest alleen de eigen Map, zonder fallback naar de native
   registry. Registreer je op modulescope, dan win je soms de race met HA's
   eigen `import()` en is je element daarna onzichtbaar — zonder fout, zonder
   log, met "Configuratiefout" op elke kaart en een kaartkiezer die eindeloos
   laadt. Wacht op het bestaan van `home-assistant` als **signaal**, lees
   `customElements` bij elke poging **opnieuw**, en houd een harde bovengrens.
   Bewaak het met een script dat controleert dat alléén `registreer.js` in
   `src/` `customElements.define` aanroept, én dat de markernaam nog in de
   **gebouwde** bundel staat.

2. **De `?v=` op de frontend-URL is de hash van het bundelbestand**, niet het
   versienummer. Die hash wordt berekend bij setup van de config entry. Dus:
   **na elke `npm run build` de config entry herladen**, daarna pas hard
   herladen in de browser. Sla je het herladen over, dan meet je de oude bundel.

3. **HA serveert `index.html` zonder cache-validatie-headers** (geen
   `Cache-Control`, geen `ETag`, geen `Last-Modified`) en zijn service worker
   beantwoordt de wortel-URL met `StaleWhileRevalidate`. Een browser die HA al
   gebruikte vóór de installatie houdt daardoor een `index.html` van vóór die
   installatie vast, en elk dashboard toont "Configuratiefout". DomotiApp Scene
   registreert de kaart daarom óók als **Lovelace-resource** naast
   `add_extra_js_url`. Reken op **twee laadroutes** tot HA het bovenstrooms
   oplost (`home-assistant/epics#113`).

4. **Een `fetch('/')` om te controleren of de service-workercache vervuild is,
   repareert die cache zélf.** Die fetch gaat door de service worker en
   `StaleWhileRevalidate` schrijft de verse index meteen terug. Lees **alleen
   uit de cache** (`cache.match`, buiten de service worker om) en navigeer
   daarna meteen.

5. **~~De browsertool schrijft geen screenshotbestanden weg.~~ ACHTERHAALD in
   fase 1.** In DomotiApp Scene lukte dat vijf rondes op rij niet; met
   `save_to_disk: true` schrijft de tool het bestand nu wél weg en geeft hij het
   pad terug. Twee screenshots van fase 1 staan in `docs/fase-1/RAPPORT.md`
   genoemd.
   **Wat blijft gelden:** een screenshot is zwakker bewijs dan een meting. "33 px
   overloop, de tegels schoven van 208 naar 241" is controleerbaar, "het ziet er
   scheef uit" niet. Gebruik plaatjes ter illustratie, en DOM-uitlezingen,
   bytegroottes en gemeten posities als bewijs.

6. **`docker exec` met `/`-paden vanuit Git Bash** vereist `MSYS_NO_PATHCONV=1`,
   anders mangelt Git Bash het pad naar `C:/Program Files/...`. In fase 0 ook
   gebruikt voor `docker cp`.

7. **De browsertool blokkeert uitvoer met query strings** ("Cookie/query string
   data"). Stel het vraagteken samen met `String.fromCharCode(63)` en vergelijk
   op gelijkheid in plaats van de string terug te geven.

8. **Wacht tot de MDI-iconen geladen zijn voordat je klikt.** `ha-icon` laadt
   asynchroon; een klik op een knop die nog geen oppervlak heeft, mist. Doe een
   hit-test met `elementFromPoint` op het klikpunt.

9. **Eén `subscribeEvents`-abonnement per meting.** Twee tegelijk levert elke
   service-aanroep dubbel op, wat makkelijk voor een gedragsverandering wordt
   aangezien.

10. **Zoek kaartelementen niet met een eigen deep-query door shadow roots.** Dat
    heeft in DomotiApp Scene drie keer ten onrechte "0 kaarten" opgeleverd.
    Gebruik een capture-listener op `window` en lees `event.composedPath()`. Eén
    gewone `querySelector` op de shadow root daaruit is wél stabiel.

11. **De dialoog is met de browsertool niet met het muiswiel te scrollen**, en
    Tab werkt niet altijd door. `scrollIntoView()` gevolgd door een échte klik
    is de uitweg — maar zeg dan ook dat het scrollen programmatisch was en de
    klik niet.

12. **`getGridOptions` moet `rows: "auto"` teruggeven, geen getal.** Een getal
    geeft de kaart in HA's sections-grid een vaste hoogte; wordt de kaart hoger,
    dan loopt hij over zijn vak en over de "+"-knop eronder heen. Een wekkerkaart
    verandert van hoogte (meerdere wekkers, meldingen), dus dit geldt hier zeker.

13. **Attributen van HA-componenten heten in het lit-template anders dan in JS.**
    `headerTitle` als letterlijk attribuut doet niets; het attribuut heet
    `header-title`. Gebruik property-binding (`.headerTitle=`).

14. **`.trim()` in een controlled input eet de spatie op.** Trim bij het
    **opslaan**, niet bij het typen.

15. **Draai hassfest op een schone uitcheck, niet op de werkmap.** Op de werkmap
    loopt hij `.venv/` in en keurt daar de kernintegraties van Home Assistant af
    omdat die geen `version` in hun manifest hebben.

16. **Een dropdown in HA herschikt zich rond de huidige selectie.** Een
    y-coördinaat uit een oudere screenshot wijst na het openen naar een ander
    item. Neem vlak vóór elke klik een verse screenshot en lees het veld daarna
    zelf uit vóór Verzenden.

17. **`.gitattributes` met `* text=auto eol=lf` en `npm ci` in plaats van
    `npm install`.** Zonder de eerste zet `core.autocrlf` op Windows de bundel
    om naar CRLF terwijl esbuild LF schrijft, en faalt de bytevergelijking
    zonder dat er iets mis is. Zonder de tweede kan de esbuild-versie afwijken.
    **Sinds fase 1 geregeld**: `.gitattributes` staat in de repo en CI gebruikt
    `npm ci`.

### Nieuw in fase 0, uit de broncode van 2026.8.1

Alle regel- en bestandsverwijzingen hieronder zijn na te lezen in
`docs/fase-0/ONDERZOEK.md`.

18. **Extra state attributes verdwijnen zodra een entiteit `unavailable` is.**
    `helpers/entity.py:1118-1124` voegt `state_attributes` én
    `extra_state_attributes` alleen toe wanneer `available` waar is. Wat wél
    blijft staan: `supported_features` (regel 1169-1170), `device_class`
    (1135-1139) en `friendly_name` (1166-1167).
    **Gevolg voor dit product:** `mass_player_type` en `volume_level` van een
    Music Assistant-speaker zijn onleesbaar zodra die speaker wegvalt. Filter
    speakers dus op `supported_features`, niet op `mass_player_type`. Gemeten in
    fase 0: bij een onbeschikbare entiteit bleven precies `friendly_name` en
    `supported_features` over.

19. **Een service-aanroep op een `unavailable` entiteit slaagt en doet niets.**
    `helpers/service.py` filtert onbeschikbare entiteiten weg
    (`entity_candidates = [e for e in entity_candidates if e.available]`) zonder
    exceptie. Erger: bij targeting **op entity_id** komt er nog één
    `WARNING` in het log, maar bij targeting **op label_id** staat de entiteit
    in `indirectly_referenced` en niet in `referenced`, en dan komt er
    **helemaal geen log** (`helpers/target.py:136-155`). Gemeten in fase 0:
    label-targeting met één offline speaker → nul waarschuwingen.
    **Dit is de stilste faalmodus in dit product.** De wekker "slaagt" en er
    komt geen geluid. De integratie moet zelf vóór het afspelen controleren of
    de speaker beschikbaar is en zelf een hoorbaar alternatief kiezen.

20. **Er is geen ingebouwde inhaalslag na een herstart.** Tijdplanners zijn
    puur `loop.call_at`-timers in het geheugen
    (`helpers/event.py:1461-1466`) en overleven een herstart niet. HA's eigen
    tijdtrigger plant een absoluut moment **alleen als het in de toekomst
    ligt** (`components/homeassistant/triggers/time.py:190-191`) en slaat een
    gemist moment dus stil over. De integratie moet zelf herplannen bij setup
    én zelf beslissen wat er met een gemiste wekker gebeurt.

21. **Een wekker op een wandkloktijd die niet bestaat wordt een dag
    overgeslagen; een die twee keer bestaat vuurt twee keer.** Gemeten met
    `find_next_time_expression_time` (`util/dt.py:436-555`) op
    Europe/Amsterdam: patroon 02:30 op 29 maart 2026 → eerstvolgende vuurmoment
    **30 maart** 02:30. Patroon 02:30 op 25 oktober 2026 → **twee** keer
    (00:30 UTC en 01:30 UTC). Een naieve lokale 02:30 door
    `async_track_point_in_time` schuift juist stil naar 03:30. Drie
    verschillende uitkomsten voor dezelfde wens; kies expliciet.

22. **Een tijdzonewijziging herplant bestaande tijdplanners niet.** Alleen
    `SunListener` luistert op `EVENT_CORE_CONFIG_UPDATE`
    (`helpers/event.py:1672`); `_TrackUTCTimeChange` (regel 1750) doet dat niet.
    De integratie moet daar zelf op luisteren en herplannen.

23. **`async_track_time_change` vuurt 50–500 ms ná de seconde**, door een
    opzettelijke random jitter tegen een thundering herd
    (`helpers/event.py:83-88, 1835`). Gemeten: +0,289 s. Ruim binnen de eis, maar
    reken er niet op dat een meting op de milliseconde reproduceerbaar is.

24. **`async_track_point_in_time` op een moment in het verleden vuurt
    onmiddellijk.** Gemeten: +0,0002 s. Dat is bruikbaar als inhaalmechanisme,
    maar ook een valkuil: een wekker van 06:45 knalt om 14:00 aan als je hem
    zonder controle herplant na een herstart. Altijd zelf een
    respijtvenster afwegen.

25. **`TargetSelectorData` verdwijnt in HA 2026.12.** De deprecation-melding
    zegt: gebruik `TargetSelection`. Fase 0 heeft de meting nog met de oude
    klasse gedaan; gebruik in productiecode meteen `TargetSelection`.

27. **`playback_state` van een MA-speaker bewijst niets.** Gemeten: nadat het
    afspeelproces van een spelende speaker was gedood, meldde MA nog steeds
    `playback_state: "playing"` met een **doorlopende** `elapsed_time` (220,3 s),
    terwijl `available` op `false` stond. De queue weet niet of er iemand
    luistert. **Gebruik `available` als noodrem, nooit `playing`.**

28. **Een offline speaker faalt aan de MA-kant luid, maar niet overal.**
    `player_queues/play_media` geeft HTTP 500 met
    `PlayerUnavailableError`; `players/cmd/volume_set` geeft **HTTP 200** en
    logt alleen `Ignoring command cmd_volume_set for unavailable player`. Dus:
    afspelen klaagt, volume zetten slaagt stil. En omdat HA onbeschikbare
    entiteiten al wegfiltert vóór de integratie (valkuil 19), komt die
    500 nooit boven water.

29. **Groepsvolume in MA werkt relatief, niet absoluut.** Een sync-groep meldt
    zelf `volume_level: null` — de waarde zit in `group_volume`. Groepsvolume op
    60 zetten bij leden op 40 en 25 gaf **60 en 50**, niet 60 en 60. Een oploop
    naar een vast eindvolume moet dus **per speaker** gezet worden, nooit op de
    groep. Bijkomend: `power_control` was bij alle geteste players `"none"`, dus
    een MA-speaker heeft geen `TURN_ON`/`TURN_OFF`.

30. **`volume_set` kapt buiten bereik stil af.** Gemeten: `-5` → 0, `150` → 100,
    `12.5` → 12, `33.7` → 33 (afkappen, niet afronden), alle met HTTP 200. Een
    rekenfout in de volume-oploop geeft dus geen exceptie, alleen een verkeerd
    volume.

31. **Meet een tijdgestuurde lus niet vanuit een achtergrondtabblad.** Chrome
    knijpt `setTimeout` af: een oploop van 20 stappen van 1 s liep in paren van
    2 stappen per 2 s (t=1.995/2.001, 3.995/4.000, …). De **totaalduur** klopte
    op 20,004 s, dus wie alleen die rapporteert, meldt een vloeiende oploop die
    in werkelijkheid 10 sprongen was. Meet cadans in Python, of toon per stap de
    werkelijke tijdstempel.

32. **HA's externe-stap-config-flows redirecten via `my.home-assistant.io`, en
    `external_url` verandert dat niet.** Na het zetten van `external_url` én
    `internal_url` op `http://localhost:8129` plus herstart — waarna
    `hass.config.external_url` de nieuwe waarde had — bleef de `return_url` van
    de MA-flow naar `/redirect/oauth` wijzen. Achter Docker Desktop komt de
    callback dan niet aan.

    **OORZAAK GEVONDEN in fase 3c, en het is niet de URL.**
    `helpers/config_entry_oauth2_flow.py:74-85`:

    ```python
    def async_get_redirect_uri(hass) -> str:
        if "my" in hass.config.components:
            return MY_AUTH_CALLBACK_PATH       # my.home-assistant.io
        if (req := http.current_request.get()) is None:
            raise RuntimeError("No current request in context")
        if (ha_host := req.headers.get(HEADER_FRONTEND_BASE)) is None:
            raise RuntimeError("No header in request")
        return f"{ha_host}{AUTH_CALLBACK_PATH}"
    ```

    Die **eerste regel gaat vóór alles**. Zolang de `my`-integratie geladen is,
    wordt `external_url` in dit pad *nooit gelezen* — het was dus geen
    configuratiefout maar een controlevraag die er niet aan te pas komt.
    `my` zit in `default_config`.

    **De uitweg** (gedaan in fase 3c, staat in `.ha-dev-config/configuration.yaml`):
    `default_config:` uiteenleggen in zijn 22 dependencies **minus `my`**. Dan valt
    HA terug op de header `HA-Frontend-Base` die de frontend zelf meestuurt, en
    blijft de hele flow op `http://localhost:8129`. `my` levert alleen
    /redirect-koppelingen naar documentatie.

    **Twee dingen die daarbij horen.** Ten eerste: een flow die je **niet** vanuit
    de echte frontend start (een `fetch` naar `/api/config/config_entries/flow`)
    heeft die header niet, en dan valt de MA-flow terug op zijn
    `auth_manual`-stap — die om een long-lived token vraagt. Ten tweede: de
    login-URL wordt gebouwd uit de URL die je HA geeft, dus met
    `host.docker.internal:8095` opent de browser een adres dat hij niet kent.
    **Gebruik het LAN-IP van de host** (`http://192.168.1.212:8095`): dat is
    bereikbaar vanuit de HA-container én vanuit de browser, en dan hoeft er in de
    adresbalk niets herschreven te worden. Let op dat dat IP van DHCP komt.

33. **`ps` bestaat niet in de MA-container.** Processen zoeken gaat via
    `/proc/*/cmdline`. En de browsertool blokkeert tokens in zijn uitvoer, wat
    prettig is maar betekent dat MA's API alleen ván binnen de pagina
    aanroepbaar is (token uit `localStorage`, resultaat terug, token niet).

26. **Music Assistant heeft geen oplopend volume dat je kunt aanroepen.** MA
    kent wel `fade_in`, maar dat is een **boolean** op `play_index`/`resume`
    (`music_assistant_client/player_queues.py:101, 193`) en de HA-integratie
    roept het **nergens** aan. Vanuit HA is er alleen `volume_set` (absoluut) en
    `volume_up`/`volume_down` (stap). Een oploop van stil naar het ingestelde
    volume in 20 seconden moet de integratie zelf maken, met herhaalde
    `volume_set`-aanroepen. Fase 0b heeft dat gebouwd en gemeten: 20 aanroepen,
    elk 3–6 ms, eindvolume exact. Het werkt.

### Nieuw in fase 0b, live gemeten tegen MA 2.9.11

Vindplaatsen in `docs/fase-0b/RAPPORT.md`.

### Nieuw in fase 3c

Vindplaatsen in `docs/fase-3c/RAPPORT.md`.

34. **Een mutatie die niet gevangen wordt heeft drie mogelijke oorzaken, en ze
    vragen drie verschillende dingen.** Fase 3a, 3b en 3c hebben ze alle drie
    gezien, en ze verwarren is de manier waarop deze oefening waardeloos wordt:

    | Oorzaak | Hoe je het vaststelt | Wat je doet |
    |---|---|---|
    | **testgat** | de regel is bereikbaar en doet iets waarneembaars | test erbij (fase 3c, A37) |
    | **redundante maar bereikbare verdediging** | een ánder pad komt er wél langs | test op dát pad (fase 3b P3, fase 3c A19) |
    | **onbereikbare code** | narekenen: er is geen invoer waarbij de regel iets verandert | **regel eruit**, meting in een comment (fase 3c A14) |

    De verleiding bij de tweede is hem voor dood te verklaren; bij de derde is het
    een test te verzinnen. Beide zijn fout. Een test op onbereikbare code bewijst
    niets en suggereert dekking die er niet is.

35. **Een test die de juiste uitkomst om de verkeerde reden krijgt, is geen test.**
    Fase 3c's eerste poging om A19 te vangen (de register-controle in de oploop)
    slaagde ogenschijnlijk, maar wat er werkelijk afbrak was `wijkt_af`: na een
    volledige stop staat het volume weer op de oude waarde terwijl de oploop 0 had
    gezet, en dat is een afwijking van 50 procentpunt. De mutatie bleef ongevangen.
    Bij een test op één voorwaarde moeten de andere voorwaarden **expliciet
    onschadelijk** gemaakt worden — hier door de oploop eerst één stap te laten
    zetten, zodat het gelezen volume gelijk is aan wat de oploop zelf zette.

37. **Een vastgehouden `hass` leest een BEVROREN states-snapshot.** HA's frontend
    **vervangt** `hass.states` bij elke statuswijziging in plaats van het te muteren,
    dus `const hass = ...` aan het begin van een script en daarna `hass.states[x]`
    lezen levert de stand van vóór je handeling op. In fase 3c leverde dat een
    "mislukte" toets op die niets mankeerde: `alarms/stop` had het volume netjes op 0,55
    teruggezet en de meting zei 0,40. **Haal `document.querySelector('home-assistant').hass`
    opnieuw op na elke handeling die de state verandert**, of lees de waarde uit het
    server-side log.

38. **Meet de cadans van een tijdgestuurde lus aan de ONTVANGENDE kant.** Fase 3c mat de
    volume-oploop in twee onafhankelijke logs: HA's `call_service`-regels én het log van
    de snapclient in de MA-container (`ServerSettings … volume: 2/4/6…`). Beide gaven
    1,004–1,007 s per stap. Eén bron zou niet hebben uitgesloten dat HA netjes plant en
    de speaker het samenvoegt. Dit is het antwoord op valkuil 31: niet in de browser
    meten, en niet op totaalduur.

39. **`sound/search` geeft meer velden terug dan `alarms/save` accepteert.** Een
    zoekresultaat draagt `album` en `artists`; het `sound`-object in de opslag mag
    alleen `uri`, `name`, `media_type` en `image` (SPEC 8.2). Letterlijk doorgeven geeft
    `invalid_format — onbekende velden: ['album', 'artists']`. De kaart moet het
    resultaat dus uitkleden vóór het opslaan.

40. **De weergavenaam van een MA-item is niet altijd een zoekterm.** `somafm://` geeft
    `"SomaFM: Beat Blender"` terug, en zoeken op die string in MA levert **nul**
    treffers; `"Beat Blender"` levert er drie. Providerspecifiek: `radiobrowser://` en
    iTunes-podcasts zijn zelf-vindbaar, SomaFM niet.

    **Dit heeft de URI-controle van SPEC 11.2 gekost** (fase 3c-bis): de opgeslagen naam
    komt van MA, dus een controle die op die naam zoekt kan per definitie zijn eigen
    geluid niet terugvinden. De les die breder geldt: **een identificator die je van een
    dienst terugkrijgt is niet automatisch een identificator die je aan die dienst kunt
    teruggeven.** Voordat je iets opslaat om er later mee te zoeken, toets of het
    **zelf-vindbaar** is — zoek op wat je opslaat en kijk of je het terugvindt.

41. **Een controle die vals alarm slaat is erger dan geen controle.** De afweging die
    fase 3c-bis maakte, in één regel: het faalgeval verschuift van "de wekker gaat niet
    af" naar "de wekker ging af maar was stil", en het tweede wordt achteraf opgemerkt
    terwijl het eerste onherstelbaar is. Weeg bij elke noodrem niet alleen wat hij vangt
    maar ook **hoe vaak hij onterecht afgaat** — en meet dat, want hier was het 100 %
    voor een hele provider terwijl de SPEC-tekst het als zeldzaam risico beschreef.

42. **`blocking=False` verbergt de fout, het versnelt niets wat je mag weten.**
    `core.py:2953-2959`: HA verpakt een niet-blokkerende service-aanroep in
    `_run_service_call_catch_exceptions` en geeft `None` terug — de exceptie bereikt de
    integratie **nooit**. Elke terugval of foutmelding die op die aanroep staat, vervalt
    daarmee stil. Nagelopen in fase 3c-bis voor `play_media`, dat 2,1–2,6 s blokkeert;
    die twee seconden zijn de prijs van weten dát het lukte.

36. **Positieve controles vangen de mutaties die een functie volledig
    uitschakelen.** Een test die alleen op falen let, komt door een implementatie
    die *altijd* faalt. In fase 3c wordt een groot deel van de 39 mutaties gevangen
    door precies zo'n paar: "een kleine afwijking breekt de oploop **niet** af",
    "een speaker die blijft staan levert **geen** melding op", "afspelen faalt ook
    zonder `radio_mode`". Dit staat al als werkafspraak in dit bestand; A37 laat
    zien dat het in de praktijk alsnog misgaat.

---

## Commando's

```bash
npm install                # eenmalig
npm run build              # bundelt src/ -> custom_components/.../frontend/
npm run verify             # faalt als de gecommitte bundel afwijkt van de bron
npm run check:registratie  # bewaakt de registratieregel (valkuil 1)
npm test                   # JS-unittests (node --test), geen jsdom
```

**Python-tests draaien niet op Windows** — Home Assistant importeert `fcntl`.
Draai ze in Linux:

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "C:/dev/domotiapp-alarm:/app" -w /app \
  python:3.14-slim sh -c "pip install -q -r requirements-test.txt && python -m pytest -q"
```

CI draait vier jobs: bundelvergelijking + registratieregel, hassfest op het
manifest, JS-tests, Python-tests.

**Na elke `npm run build` de config entry herladen**, daarna pas hard herladen in
de browser. De `?v=` is de bundelhash en die wordt bij setup berekend (valkuil 2).

---

## Releaseprocedure

Nog geen release gemaakt; de eerste versie is `0.1.0`. De procedure staat er al
omdat hij in DomotiApp Scene drie keer bijna misging en één keer echt.

Het versienummer uit `manifest.json` wordt in de bundel geïnjecteerd
(`scripts/build.mjs`, `define: __CARD_VERSION__`). Een versieverhoging verandert
dus de bytes van de bundel, ook als er in `src/` niets is gewijzigd. In DomotiApp Scene is bij 1.0.1 de versie opgehoogd zonder
opnieuw te bouwen; de CI-job "Bundel komt overeen met de bron" ving dat, `main`
stond rood en er moest een 1.0.2 aan te pas komen.

De vaste volgorde. Claude Code mag dit tot en met de commit voorbereiden, op een
branch en alleen als daar om gevraagd is; **de tag en de release maakt de
eigenaar**.

```powershell
$v = "1.0.1"
cd C:\dev\domotiapp-alarm
# versienummer in custom_components\domotiapp_alarm\manifest.json zetten
npm run build     # <-- MAG NIET WEGVALLEN
npm run verify
git add custom_components/domotiapp_alarm/manifest.json custom_components/domotiapp_alarm/frontend/domotiapp-alarm-card.js
git commit -m "Versie $v"
git push
gh run watch
# daarna maakt de EIGENAAR: gh release create $v --title $v --notes "..."
```

Drie dingen die hierin niet mogen wegvallen:

1. **`npm run build` staat tussen het versienummer en de commit.** Sla je hem
   over, dan draagt de bundel nog de oude versie en faalt CI.
   `npm run verify` erna is de plaatselijke controle die hetzelfde zegt als CI,
   vóórdat je pusht.
2. **Beide bestanden gaan in dezelfde commit**: het manifest *en* de bundel. De
   bundel wordt meegecommit omdat HACS levert wat er in de repo staat.
3. **Een tag alleen is niet genoeg.** HACS leest de laatste **release**, niet de
   laatste tag. Geen `v`-prefix: de tag is `1.0.1`, en HACS vergelijkt hem met
   `version` in het manifest.

`gh run watch` staat er niet voor de netheid: het is het moment om te zien dat
CI groen is vóórdat er een release aan de tag hangt die een klant binnenhaalt.

---

## Projectstand

| Fase | Wat het opleverde | Status |
|---|---|---|
| 0 | Repo-opzet, testinstance op 8129, en architectuurverificatie van vier onbekenden: `docs/fase-0/ONDERZOEK.md` | gemerged |
| 0b | Music Assistant live geverifieerd (`docs/fase-0b/RAPPORT.md`): `playback_state` bewijst niets, groepsvolume werkt relatief, volumeresolutie is 1 %. HA↔MA-koppeling niet gelukt | gemerged |
| 1 | Rooktest: buildketen (lit + esbuild), CI met vier jobs, de integratie serveert en registreert haar eigen kaart langs beide routes, 8 JS- en 10 Python-tests, verificatie op de dev-instance én op een verse instance | gemerged |
| 2 | `SPEC.md` als bron van waarheid: 20 secties met opslagschema, negen WebSocket-commando's, foutgedrag, wat niet in v1 zit, en tien open vragen | in PR #4 |
| 2b | De tien open vragen gesloten en sectie 21 verwijderd. `last_failure` hernoemd naar `last_message` met een `severity`. `radio_mode` en de URI-controle doorgeschoven naar fase 3, met beide takken uitgeschreven | gemerged |
| 3a | De server-side laag zonder klok: `store.py` met de kapotte-data-scheiding, `validatie.py` en `volgende.py` (beide puur), `entiteiten.py` met de labelfiltering, en de negen WebSocket-commando's. 112 Python-tests, 13 mutaties nagelopen | gemerged |
| 3b | De planner: `planner.py` (plannen, inhaalslag, respijtvenster, herplannen), `afvuren.py` als naad met 3c, `meldingen.py` met de drie kanalen en de repair issues die 3a openliet. 137 Python-tests, 17 mutaties nagelopen, live gemeten afwijking 12 ms | gemerged |
| 3c | Het afvuren: de acht stappen van SPEC 9.1, `noodrem.py` (available + URI-controle met de omkering van 11.2.1), `oploop.py` en `radiomodus.py` (beide puur), de wake-up light en de stoptimer. 213 Python-tests, 39 mutaties nagelopen (drie gaten gevonden en gedicht). Valkuil 32 opgelost (oorzaak: de `my`-integratie, niet `external_url`) en de livecontrole live gedaan: **+2,153 s afwijking, oploop 1,006 s per stap, audio bewezen aan de speakerkant. En één blokkerende bevinding: de URI-controle van SPEC 11.2 houdt een werkende SomaFM-wekker tegen | in PR #8 |
| **3c-bis** | **De URI-controle vervalt (SPEC 11.2 herschreven, 11.2.1 vervallen, 11.2.2 met een nieuw criterium). De SomaFM-wekker die in 3c niet afging, gaat nu af met 0 van 87 s stilte. 212 tests, 5 mutaties. `play_media` blokkeert 2,1–2,6 s en dat is niet weg te nemen zonder de foutdetectie te verliezen (`core.py:2953-2959`)** | **deze ronde, PR #8** |

**Wat er staat na fase 1:** een integratie die haar eigen bundel serveert op
`/domotiapp_alarm/domotiapp-alarm-card.js?v=<bundelhash>`, die URL langs twee
routes registreert (index-import én Lovelace-resource), een lege config flow, en
een kaart die één regel tekst rendert. Versie `0.1.0`, bundel 16.713 bytes.

**Wat er staat na fase 2b:** `SPEC.md` is **bindend** en heeft geen open vragen
meer. Wat er nog niet gebouwd is: wekkerlogica, opslag, WebSocket-commando's,
editor, planning, Music Assistant.

**Wat er staat na fase 3a:** de volledige server-side laag **zonder klok**. Opslag
met validatie en het foutgedrag uit SPEC 19.2, de labelfiltering, en de negen
WebSocket-commando's. `volgende.py` bevat de rekenkunde voor "wanneer gaat deze
wekker af" en is **puur** — fase 3b hergebruikt hem in plaats van hem opnieuw te
schrijven.

**Wat er staat na fase 3b:** de klok erbij. Een wekker gaat op tijd af (live
gemeten: **12 ms** na het bedoelde moment), een gemiste wekker wordt binnen 30
minuten ingehaald en daarbuiten overgeslagen met een mededeling, en elke wijziging
bouwt de planning van nul opnieuw op zodat er geen listener achterblijft. Er wordt
nog **niets afgespeeld**: `afvuren.py` doet de boekhouding (`last_fired`, `ringing`,
het `started`-event) en documenteert per regel wat fase 3c waar invult.

**De drie regels van de planner die je niet mag omdraaien** (zie
`docs/fase-3b/RAPPORT.md`):

1. **`last_fired` gaat vóór het geluid, nooit erna.** Crasht HA tussen die twee, dan
   is de ergste uitkomst een wekker die niet klonk — andersom een wekker die na elke
   herstart opnieuw afgaat.
2. **`last_fired` houdt het *bedoelde* moment vast, niet "nu".** `async_track_time_change`
   vuurt met 50–500 ms jitter, en bij een inhaalslag liggen die tot 30 minuten uit
   elkaar. Op "nu" zetten laat de vergelijking elke herstart meeschuiven.
3. **De vergelijking gaat op een absoluut moment, niet op wandtijd.** Precies daarom
   gaat een wekker van 02:30 in de najaarsnacht **twee keer** af (`02:30+02:00`, dan
   `02:30+01:00`), zoals SPEC 13.1 eist.

Verder: `_TrackUTCTimeChange` (`helpers/event.py:1750`) luistert **zelf niet** op
`EVENT_CORE_CONFIG_UPDATE` — alleen `SunListener` doet dat. De planner luistert er
daarom zelf op, anders gaat een wekker na een tijdzonewijziging op de oude
UTC-offset af.

**Wat er staat na fase 3c:** de server-side laag is **compleet**. Een wekker gaat af
volgens de acht stappen van SPEC 9.1, met de noodrem ervoor en erna, een volume-oploop
van 20 stappen, de wake-up light en een stoptimer van 30 minuten. Fase 4 kan de kaart
bouwen; er is geen server-side werk meer dat de kaart nodig heeft.

**De drie regels van het afvuren die je niet mag omdraaien** (zie
`docs/fase-3c/RAPPORT.md`):

1. **Volume op 0 gaat vóór het geluid.** Andersom is er één harde uitbarsting op de
   stand van gisteravond voordat de oploop begint — het verschil tussen wakker worden
   en wakker schrikken. En het volume wordt **gelezen** vóór het op 0 gaat, anders zet
   het terugzetten bij het stoppen de speaker op stil.
2. **Twijfel valt niet altijd dezelfde kant op.** Bij de speakercontrole en bij
   `radio_mode` betekent twijfel *niet doen*; bij de URI-controle betekent twijfel
   *wél afgaan* (SPEC 11.2.1). Dat is geen inconsistentie maar dezelfde afweging op
   andere feiten, en de twee zien er in code op elkaar lijken — daarom staan ze in
   verschillende modules, met een `Uitkomst`-enum van **drie** waarden in plaats van
   een `bool`.
3. **De terugval is de garantie, niet de lijst.** `SIMILAR_TRACKS_PROVIDERS` kan stil
   verouderen; daarom vangt `afvuren.py` de HTTP 500 van `play_media` op en probeert
   het opnieuw **zonder** `radio_mode`. Vertrouwen op de lijst zou betekenen dat een
   MA-wijziging een wekker volkomen stil stukmaakt.

Verder: `async_call_later` en geen `asyncio.sleep` voor de oploop, de tweede
noodremcontrole en de stoptimer. Dat levert een afzegbare unsub op **en** het loopt op
HA's klok, dus een test van 20 stappen kost geen 20 seconden.

**Wat de livecontrole van 3c live heeft aangetoond** (`docs/fase-3c/RAPPORT.md`):

- de acht stappen in de voorgeschreven volgorde, met `volume_set` naar 0 op **+17 ms**
  en `play_media` op **+22 ms** — volume nul komt aantoonbaar vóór het geluid;
- de oploop `[0, 2, 4, … 40]` met **1,004–1,007 s** per stap, in twee onafhankelijke
  logs (HA én de snapclient in de MA-container);
- er kwam **werkelijk geluid** uit: 0 van 97 s `No chunks available` tijdens de wekker,
  63/63 s en 74/74 s stilte ervoor en erna;
- `alarms/stop` zet het volume terug (0,40 → 0,55), ná `media_stop`, 8 ms ertussen;
- een onbereikbare speaker levert **nul** service-aanroepen op, met melding, event én
  de wake-up light aan (SPEC 11.6 punt 2);
- valkuil 18 live bevestigd: op `unavailable` blijven precies `device_class`, `icon`,
  `friendly_name`, `supported_features` en `entity_picture` over — dus filteren op
  `supported_features` is de juiste keuze, en `alarms/save` accepteert de speaker nog.

**De totale afwijking is +2,153 s**, en dat is **niet** de noodrem: de URI-controle kost
**5 ms**. 2,131 s van de 2,153 zit in `music_assistant.play_media`, die blokkeert tot MA
de stream heeft opgezet. Gevolg: de oploop begint op +3,1 s en is klaar op +22,3 s. Bij
een langzamere provider loopt dat verder uit.

**Openstaand uit 3b, en in 3c gesloten:** de lezing van SPEC 13.4 stap 4. De eigenaar
koos de letterlijke lezing — een gemist moment buiten het respijtvenster **verbruikt**
de overslag — en die verduidelijking staat nu in SPEC 13.4 stap 4 zelf, zodat de
tweede lezing niet opnieuw opduikt.

**CI:** de eerste run (op de PR van fase 1) was **alle vier groen**, hassfest
inbegrepen.

**De twee vragen uit fase 3a zijn beslist en in SPEC verwerkt** (fase 3a-bis; zie
`docs/fase-3a/RAPPORT.md` voor de metingen en `RAPPORT-BIS.md` voor de
verwerking):

- **`radio_mode` wordt VOORWAARDELIJK meegestuurd** (SPEC 8.3.1): alleen als de
  provider van het gekozen geluid `SIMILAR_TRACKS` ondersteunt. Zonder zo'n provider
  geeft MA `UnsupportedFeaturedException` — HTTP 500 en er speelt **niets**. Faalt de
  controle zélf, dan wordt `radio_mode` **weggelaten**: hinderlijk is beter dan stil.
- **De directe URI-controle wordt NIET gebruikt** (SPEC 11.2): `music/item_by_uri`
  bestaat en geeft drie uitkomsten, maar vereist `entry.runtime_data.mass` — de
  binnenkant van een andere integratie, en dat breekt bij een update stilletjes. De
  zoekroute is de vastgelegde route; de directe controle staat als **voorkeursoptie**
  in SPEC 11.2.2 zodra MA hem als service publiceert.

**Openstaande punten met een fase erbij** — zodat ze niet blijven liggen:

| Punt | Waar | Fase |
|---|---|---|
| **`music/item_by_uri` als voorkeursroute** zodra MA hem via een gepubliceerde service beschikbaar stelt (SPEC 11.2.2) | `websocket.py` / noodrem | na een MA-release; iemand moet dit volgen |
| **De lijst providerdomeinen met `SIMILAR_TRACKS`** (SPEC 8.3.1) is een constante die uit MA's broncode is afgeleid en die **stil** kan verouderen. De HTTP 500 van `play_media` wordt sinds fase 3c opgevangen met een terugval zonder `radio_mode`, dus het ergste geval is nu hinderlijk in plaats van stil. Nalopen blijft nodig: staat een provider er onterecht *niet* in, dan stopt het geluid na het item en vangt geen terugval dat op | `const.py` | nalopen bij elke MA-release |
| **De volume-oploop begint 2,1–2,6 s te laat** doordat `play_media` blokkeert tot MA de stream heeft opgezet. Niet-blokkerend aanroepen kan niet: `core.py:2953-2959` vangt de exceptie binnen HA af, en dan vervallen de `radio_mode`-terugval én de foutmelding. De oploop eerder starten verandert SPEC 9.1 en de betekenis van het `started`-event. **Aanbeveling die niet gebouwd is:** de oploop laten *inhalen* — begin op de stap die bij de verstreken tijd hoort. Meting ligt vast in SPEC 20.1 punt 9 | `afvuren.py` / SPEC 9.1, 9.3 | **beslissing van de eigenaar** |
| **De tekst van SPEC 11.7 bij `sound_gone` stelt het zekerder dan de code weet**: "het gekozen geluid bestaat niet meer" terwijl er alleen vaststaat dat het niet startte. De soort is juist, de formulering claimt te veel. `"kon niet gestart worden"` zou nauwkeuriger zijn | SPEC 11.7 | **eigenaar**, woordkeuze |
| `getCardSize()` ontbreekt; masonry niet gemeten | de kaart | 4 |
| `panel: true` niet aangeraakt | de kaart | 4 of later |

Bij de twee kaartpunten in die tabel: `panel: true` staat in DomotiApp Scene als
openstaand punt (`frontend#52570`) en raakt juist kiosk-opstellingen. Voor de
stoptoestand is het inmiddels een vastgelegde beperking (SPEC 20.1, punt 2): de
kaart hoort op een eigen Lovelace-dashboard in sections-weergave, niet op een
ingebouwd paneel.

---

## Meetvalkuilen in de browser

Samengevat, omdat ze in DomotiApp Scene bij elkaar meer tijd hebben gekost dan
welke bug ook. Uitgeschreven staan ze hierboven als valkuil 2 tot en met 11.

- Meet nooit zonder eerst te bewijzen dat je **verse code** meet (2, 4).
- Bewijs met **getallen uit de DOM**, niet met plaatjes — de tool schrijft geen
  screenshots weg (5).
- Een **synthetisch event** bewijst de handler, niet de control. Echte kliks,
  echte toetsaanslagen, en toon `isTrusted` (werkafspraken).
- **Verse coördinaten vlak vóór elke klik**, want dropdowns en dialogen
  herschikken zich (16), en iconen laden asynchroon (8).
- **Eén abonnement per meting**, anders tel je dubbel (9).
- Zeg **welk deel van de handeling programmatisch was** als scrollen niet met
  het muiswiel lukte (11).
- En de les onder al deze: **een testomgeving die je zorgvuldig onderhoudt,
  wijkt op precies de punten af waar de zorgvuldigheid zit.** In DomotiApp Scene
  had het voorschrift "bewijs dat je verse code meet" de service-workercache tien
  fases lang bij toeval gerepareerd, waardoor een bevinding die bij vrijwel elke
  klant speelde pas in fase 7 boven kwam. Vraag bij elke werkafspraak wat hij
  verbergt.
