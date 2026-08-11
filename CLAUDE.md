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
  **Wat er sinds fase 3c op de instance klaarstaat** (labels, een lamp via `demo:`,
  de MA-koppeling): zie "Waar fase 4 begint" onder Projectstand.
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

### Nieuw in fase 0b, live gemeten tegen MA 2.9.11

Vindplaatsen in `docs/fase-0b/RAPPORT.md`.


26. **Music Assistant heeft geen oplopend volume dat je kunt aanroepen.** MA
    kent wel `fade_in`, maar dat is een **boolean** op `play_index`/`resume`
    (`music_assistant_client/player_queues.py:101, 193`) en de HA-integratie
    roept het **nergens** aan. Vanuit HA is er alleen `volume_set` (absoluut) en
    `volume_up`/`volume_down` (stap). Een oploop van stil naar het ingestelde
    volume in 20 seconden moet de integratie zelf maken, met herhaalde
    `volume_set`-aanroepen. Fase 0b heeft dat gebouwd en gemeten: 20 aanroepen,
    elk 3–6 ms, eindvolume exact. Het werkt.

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

### Nieuw in fase 3c en 3c-bis

Vindplaatsen in `docs/fase-3c/RAPPORT.md` (34–40) en `RAPPORT-BIS.md` (41–42).

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

    **Fase 4c vond een vierde uitkomst die hier niet in stond: de equivalente
    mutant.** De regel is bereikbaar en nodig, maar de *mutatie* verandert het
    gedrag voor geen enkele bereikbare invoer — twee schrijfwijzen van dezelfde
    controle. Voorbeeld: `isinstance(x, str) and x.lower() in S` tegenover
    `x is not None and str(x).lower() in S`, waar alle invoer óf een `str` óf
    `None` is. Wat je dan doet is **niets**: geen test (die zou dekking
    suggereren die er niet is) en niets weghalen (de controle zelf is wél nodig —
    de mutatie die hem hélemaal weghaalt wordt gevangen). Je noteert dat je het
    hebt nagerekend. Het onderscheid met de derde rij: daar is de **regel**
    overbodig, hier alleen de **vorm** ervan.

35. **Een test die de juiste uitkomst om de verkeerde reden krijgt, is geen test.**
    Fase 3c's eerste poging om A19 te vangen (de register-controle in de oploop)
    slaagde ogenschijnlijk, maar wat er werkelijk afbrak was `wijkt_af`: na een
    volledige stop staat het volume weer op de oude waarde terwijl de oploop 0 had
    gezet, en dat is een afwijking van 50 procentpunt. De mutatie bleef ongevangen.
    Bij een test op één voorwaarde moeten de andere voorwaarden **expliciet
    onschadelijk** gemaakt worden — hier door de oploop eerst één stap te laten
    zetten, zodat het gelezen volume gelijk is aan wat de oploop zelf zette.

36. **Positieve controles vangen de mutaties die een functie volledig
    uitschakelen.** Een test die alleen op falen let, komt door een implementatie
    die *altijd* faalt. In fase 3c wordt een groot deel van de 39 mutaties gevangen
    door precies zo'n paar: "een kleine afwijking breekt de oploop **niet** af",
    "een speaker die blijft staan levert **geen** melding op", "afspelen faalt ook
    zonder `radio_mode`". Dit staat al als werkafspraak in dit bestand; A37 laat
    zien dat het in de praktijk alsnog misgaat.

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

### Nieuw in fase 4a

Vindplaatsen in `docs/fase-4a/RAPPORT.md`.

43. **De browsertool klikt in SCREENSHOTCOÖRDINATEN, `getBoundingClientRect` geeft
    CSS-pixels.** Gemeten in fase 4a: de screenshot is 1568 px breed terwijl
    `window.innerWidth` 1920 was — een factor **0,8167**. Een coördinaat uit een
    `getBoundingClientRect` rechtstreeks aan `computer.left_click` geven, klikt dus
    ~19 % te ver naar rechts en naar beneden. Andersom klopte een coördinaat die uit
    een screenshot was afgelezen wél, wat het verraderlijk maakt: het gaat pas mis
    zodra je gaat rekenen. **Reken elke klikcoördinaat om**
    (`css * 1568 / innerWidth`) en doe er een hit-test met `elementFromPoint`
    achteraan. Dit komt bovenop valkuil 16 (verse coördinaten) — hier was de coördinaat
    vers en tóch fout.

44. **Een HA-component die lui geladen wordt, rendert als niets — zonder fout.**
    Een custom element dat niet gedefinieerd is, is een geldig HTML-element met
    `display: inline` en geen inhoud. Zet je `ha-switch` of `ha-button-menu` op een
    dashboard waar niets anders ze binnenhaalt, dan is je schakelaar **onzichtbaar**
    en staat er niets in de console. Fase 4a gebruikt daarom eigen knoppen met inline
    SVG en alleen `ha-card` (die de dashboardchrome hoe dan ook laadt) en `ha-form`
    (die alleen in HA's eigen kaarteditor-dialoog voorkomt, waar hij gegarandeerd is).
    Bijvangst: eigen knoppen hebben hun oppervlak uit CSS in plaats van uit een
    asynchroon icoon, en dat maakt valkuil 8 hier onschadelijk.

45. **`overflow: hidden` op de `ha-card` knipt elk uitklapmenu af.** Nodig om kinderen
    binnen de hoekafronding te houden, fataal voor een overloopmenu op de onderste
    rij. Fase 4a laat de kaart overlopen en geeft de stopknop zelf
    `var(--ha-card-border-radius)`. Gemeten: het menu steekt 5 px onder de kaart uit
    en is zichtbaar.

46. **Een mutatie-oefening die 100 % vangt, heeft de verkeerde mutaties.** Fase 4a's
    eerste ronde van 22 mutaties werd volledig gevangen — en dat was geen goed teken,
    want de oefening vond in fase 1, 3a, 3b en 3c elke keer iets. Een tweede ronde met
    mutaties die **naar gaten zochten in plaats van dekking te bevestigen** vond er
    meteen twee, waarvan één een echte fout in de implementatie blootlegde
    (`typeof [] === "object"`, dus een lijst kwam door een objectcontrole heen).
    Vuistregel: schrijf de tweede ronde pas nadat de eerste groen is, en richt hem op
    de regels waarvan je zou moeten toegeven dat je ze niet toetst.

### Nieuw in fase 4b

Vindplaatsen in `docs/fase-4b/RAPPORT.md`.

47. **Meerdere snapclients met dezelfde `hostID` leveren NUL geluid op, en het
    ziet eruit als een productfout.** Fase 4b vond negen snapclient-processen in
    de MA-container, meerdere met `--hostID wekker-slaapkamer`. Ze vechten om
    dezelfde stream en dan logt élke client onafgebroken `No chunks available` —
    terwijl HA netjes `playing` meldt en het volume klopt. De diagnose kostte
    tijd omdat alle server-side signalen goed stonden.
    **Tel de processen vóór je een audiometing gelooft:** `docker exec ma-alarm`
    met een lus over `/proc/*/cmdline` (valkuil 33 — `ps` bestaat er niet).
    `docker start` op een draaiende container laat oude `docker exec -d`-processen
    staan, dus ze stapelen zich per sessie op.

48. **`rm` op een logbestand dat een draaiend proces openhoudt, geeft geen nieuw
    logbestand.** Het proces schrijft door naar de verwijderde inode en de
    volgende `grep` zegt "No such file or directory". Wil je een schone meting:
    **eerst het proces stoppen, dan het bestand weg, dan opnieuw starten** — in
    die volgorde.

49. **Een native `<select>` is met de browsertool niet te openen zonder risico.**
    Een klik erop opent een OS-popup die dezelfde blokkade kan geven als een
    dialoogvenster. De uitweg in fase 4b: het element **programmatisch focussen**
    en daarna met een **echte** `ArrowDown` bedienen — dat verandert de waarde en
    stuurt `change`, zonder popup. Meld dan wel welk deel programmatisch was, net
    als bij valkuil 11.

50. **Welke HA-component geladen is, hangt af van wat er verder op het dashboard
    staat — en dat is per component verschillend.** Fase 4b mat op hetzelfde
    dashboard: `ha-card` en `ha-select` bestaan, `ha-time-input` en `ha-textfield`
    **niet**. Dat is valkuil 44 met een scherpere rand: je kunt niet uit "die ene
    HA-component werkt" afleiden dat de volgende er ook is. Meet per component
    met `customElements.get(...)` vóór je erop bouwt.

### Nieuw in fase 6, uit drie bevindingen in productie

Vindplaatsen in `docs/fase-6/RAPPORT.md`.

51. **Music Assistant past shuffle toe op het moment dat de QUEUE GELADEN wordt.**
    `controllers/player_queues.py:1533` in 2.9.11:
    `shuffle = queue.shuffle_enabled and len(queue_items) > 1 and not radio_mode`.
    Een `media_player.shuffle_set` **ná** `play_media` schudt alleen de nummers ná
    het eerste, en dan begint de wekker nog steeds elke ochtend hetzelfde — precies
    de klacht die je dacht op te lossen. `music_assistant.play_media` heeft géén
    shuffle-veld. Gemeten: zonder shuffle 3× hetzelfde eerste nummer, met shuffle 4×
    vier verschillende. **De algemene vorm:** wat de queue bepaalt moet er zijn
    vóórdat de queue bestaat — dezelfde regel als "volume op 0 vóór het geluid".

52. **Een eis die in SPEC staat is geen eis die in de code staat.** SPEC 14.5
    ("na afgaan wordt `enabled` op `false` gezet") stond er sinds fase 2 en er was
    **nergens** code die het deed. Drie fases met livemetingen liepen er langs, en
    de reden is banaal: alle metingen gebruikten **herhalende** wekkers, want die
    zijn makkelijker te herhalen. De klant gebruikte een eenmalige.
    **Wat dit vraagt:** bij een SPEC-sectie die gedrag voorschrijft, zoek de test
    die hem noemt. Vind je er geen, dan is er geen — hoe zorgvuldig de sectie ook
    geschreven is. En kijk welk pad je metingen structureel vermijden.

53. **Een melding mag alleen zeggen wat er is vastgesteld.** `sound_gone` beweerde
    *"het gekozen geluid bestaat niet meer"* terwijl er alleen vaststond dat
    `play_media` had geweigerd; in productie bestond het geluid en was Spotify niet
    geautoriseerd. De klant — of de eigenaar — kijkt dan een half uur de verkeerde
    kant op, en dat is duurder dan geen melding. **Neem de reden van de dienst
    over** als die er is: die wijst wél naar de oorzaak.

    **Fase 6b vond er nog twee en daarmee het patroon**, en dat is bruikbaarder dan
    de drie gevallen apart. Alle drie zijn ze geschreven **bij de SPEC-sectie en
    niet bij de regel code die ze verstuurt**. SPEC beschrijft een *situatie* ("de
    speaker kan geen volume aan", "Home Assistant stond uit"); de code stelt iets
    veel smallers vast — één aanroep weigerde, één moment verstreek. Het gat
    daartussen ís de leugen. Twee gevolgen:

    - **De grammaticale toets werkt.** Elke tekst met een *"omdat"*, een *"want"* of
      een bewering over de buitenwereld ("bestaat niet meer", "op het ingestelde
      volume") is verdacht: die woorden vullen het *waarom* in, en de code kent
      alleen het *wat*.
    - **Het is een vindplaatsprobleem.** De reparatie was alle drie de keren: kijk
      naar de regel die de melding *stuurt*, en schrijf op wat daar bekend is.
      `meldingen.py` draagt daarom per herschreven tekst een comment met de
      vindplaats in de **code**, niet in SPEC.

54. **MA heeft een ingebouwde `test`-muziekprovider, en die maakt album en
    afspeellijst toetsbaar zonder streamingprovider.** 5 artiesten, 25 albums, 500
    tracks, gestreamd als een lang stiltebestand — genoeg om een queue te laden en
    de volgorde te meten. Hij stond op deze instance al aan.
    **Zijn grens:** `get_album_tracks` is niet geïmplementeerd, dus een **album**
    afspelen geeft `NotImplementedError`. Een **afspeellijst** (`library://playlist/6`,
    "Recently added tracks") speelt wél. Dat album is daarmee overigens het perfecte
    materiaal voor valkuil 53: een geluid dat aantoonbaar bestaat en toch niet start.

55. **Reken na vóór je een regel onbereikbaar noemt — en reken dan door.** De rem
    "bereken `one_shot_at` alleen opnieuw als hij verstreken is" was met geen enkele
    test via de gewone API te vangen, en dat is narekenbaar: `one_shot_at` is altijd
    "de eerstvolgende wektijd ná toen", dus zolang hij in de toekomst ligt is
    opnieuw rekenen per definitie een no-op. De verleiding is dan de regel te
    schrappen (valkuil 34, derde rij). Fout: er is één toestand waarin hij wél iets
    doet — na een **tijdzonewijziging** is `one_shot_at` een absoluut moment dat
    niet meer op de wandkloktijd valt. Het narekenen moet dus tot het einde: niet
    "geen test vangt hem" maar "er is geen invoer waarbij hij iets verandert".

56. **De state loopt achter op het log.** `play_media` blokkeert 2,1–2,6 s en de
    entiteit verandert daarna pas. Lees je `media_title` op het moment dat het
    HA-log "afgegaan" meldt, dan krijg je de waarde van de **vorige** meting — en
    dat ziet eruit als "shuffle werkt niet". Dit is valkuil 37 in een variant: niet
    een bevroren `hass`, maar een verse `hass` die de nieuwe waarde nog niet heeft.
    Wacht een paar seconden, of vergelijk op **verandering** in plaats van op
    waarde.

### Nieuw in fase 6b

Vindplaatsen in `docs/fase-6b/RAPPORT.md`.

57. **HA heeft géén menu-component die je op een dashboard mag gebruiken.** Gemeten
    op 2026.8.1, verse pagina plus vier seconden: `ha-md-menu`, `ha-md-menu-item`,
    `ha-button-menu`, `ha-md-button-menu` en `ha-menu` zijn **geen van alle**
    gedefinieerd. Wél: `ha-card`, `ha-form`, `ha-select`, `ha-switch`,
    `ha-list-item`, `ha-icon`, `ha-icon-button`, `ha-tooltip`. Dat is valkuil 44 en
    50 op hun scherpst — een `<ha-button-menu>` rendert dan als een leeg
    inline-element, dus een **onzichtbaar menu zonder fout in de console**.
    Bijvangst: `ha-switch` is inmiddels wél gedefinieerd waar fase 4a hem nog
    vermeed. Welke component geladen is verschilt dus **per component, per
    dashboard én per HA-versie**; meet het opnieuw in plaats van dit lijstje te
    geloven.

58. **Een zwevend menu hoort binnen de kaart te blijven, en dat is een meetbare
    eis.** Een `position: absolute` menu dat altijd onder de knop hangt, steekt bij
    de onderste rij onder de kaart uit — gemeten: **71 px**, over wat er op het
    dashboard onder stond. De uitweg is `position: fixed` plus een berekening die
    omhoog klapt zodra het er onder niet past, met het **venster** als laatste grens
    (een menu dat half buiten beeld valt is erger dan een menu dat een randje
    overlapt). En: **meet de hoogte van het menu**, leid hem niet uit de CSS af. De
    tekst verschilt ("Overslaan" tegenover "Toch niet overslaan") en de
    lettergrootte komt uit het thema van de gebruiker; een geraden hoogte duwt het
    menu bij een grote letter alsnog over de rand. Render het daarom eerst
    `visibility: hidden` — een element zonder layout heeft geen hoogte om te meten.

    **Het menu zelf is in fase 7 vervallen** (valkuil 60), dus `plaatsMenu` bestaat
    niet meer. Wat blijft gelden is de meetregel: leid de afmeting van iets dat je
    plaatst nooit uit de CSS af als de gebruiker aan de lettergrootte kan draaien.

59. **Een verdediging tegen data van een ánder wordt door geen enkele test
    geraakt.** De mutatieproef van 6b vond twee gaten, allebei in dezelfde functie:
    de `isinstance(..., bool)`-controle en de `STATE_UNAVAILABLE`-controle op een
    attribuut van een `media_player` die niet van ons is. Reden: alle tests gebruiken
    ons eigen testdubbel, en dat gedraagt zich netjes. HA's statemachine dwingt
    niets af, dus een integratie die `"true"` in `shuffle` zet houdt niemand tegen.
    **Wat je doet:** bouw in de test expliciet de combinatie die HA in de praktijk
    niet maakt maar wel toestaat (`unavailable` mét attributen, een string waar een
    bool hoort). Dit is valkuil 34 tweede rij, met een nieuw soort "ander pad": niet
    een ander codepad van onszelf, maar invoer die alleen van buiten kan komen.


### Nieuw in fase 7

Vindplaatsen in `docs/fase-7/RAPPORT.md`.

60. **Een laag die klikken opvangt, hoort ook te verbergen wat eronder ligt.** Het
    overloopmenu werd afgesloten met `position: fixed; inset: 0; z-index: 2`. Dat is
    het **hele venster**, boven elke knop in de kaart, en zolang het menu openstond
    ving die laag élke klik. Gemeten met een echte klik op de ⋮ van een andere rij:
    `elementFromPoint` gaf `div.sluiter`, de klik landde daarop, en het menu ging
    alleen dicht. Voor de klant: ongeveer de helft van de tikken doet zichtbaar
    niets — hij meldde het als *"het opent maar heel af en toe"*.
    **De regel:** een modale dialoog mag het scherm doodleggen, want dan zie je dat
    ook. Een menu dat naast een zichtbaar klikbare knop staat, mag dat niet. En de
    goedkoopste uitweg is geen laag: een bevestiging die de rijen **uit elkaar
    duwt** overlapt per constructie niets.

61. **Een klikvolgorde die alleen het gelukkige pad afloopt, vindt nooit de
    toestand die vastloopt.** Valkuil 60 zat er sinds fase 4a in en overleefde de
    browserverificaties van 4a, 4b, 6b en de mutatieproeven. Reden: élke meting
    opende het menu vanuit gesloten toestand en klikte daarna op een menu-item —
    ⋮, item, ⋮, item. Dat is precies de ene volgorde waarin de fout zich niet
    voordoet. **Klik in een UI-verificatie minstens één keer twee keer achter
    elkaar op dezelfde knop, en één keer op de gelijksoortige knop van een andere
    rij.** Fase 7 doet zes openingen over vier rijen en telt ze.

62. **De `?v=` op de kaart-URL is GEEN cache-buster tegen HA's service worker.**
    Gemeten: `cache.match('…card.js?v=<nieuw>', {ignoreSearch: true})` gaf de
    bundel van een versie eerder terug. En `fetch(url, {cache: 'reload'})` gaat
    door de service worker heen — die vervalt de HTTP-cache, niet de SW-cache; twee
    keer achter elkaar leverde hij de oude bundel terwijl `curl` van buiten de
    browser de nieuwe gaf.
    **Gevolg dat verder gaat dan meten:** de kaart wordt langs twee routes geladen
    (valkuil 3). Komt de index uit de cache met een oude `?v=`, dan wint de **oude**
    module de registratierace en draait de klant een oude kaart achter een nieuwe
    URL — de pagina toonde de vorige versie terwijl het `<script>`-element de
    nieuwe `?v=` droeg.
    **Wat wél werkt:** alle `file-cache`-entries van de kaart én de gecachte index
    verwijderen, `navigator.serviceWorker.getRegistrations()` afmelden, en dan pas
    navigeren. Verifieer daarna met een **cache-lezing** (`cache.match`, nooit een
    `fetch`, valkuil 4) tegen de hash op schijf.


### Nieuw in fase 8

Vindplaatsen in `docs/fase-8/RAPPORT.md`.

63. **`scrollWidth > clientWidth` vindt maar de helft van het afsnijden.** De
    methode uit fase 4c meet overloop naar **rechts**. Een flexrij met
    `justify-content: flex-end` spilt naar **links**, en dan meldt de rij netjes
    `clientWidth 244, scrollWidth 244` terwijl er een knop 67 px buiten de kaart
    ligt. En een veld dat wordt **platgeknepen** in plaats van afgesneden (een leeg
    zoekveld van 27 px) heeft niets om over te lopen, dus daar meet hij ook niets.
    **Wat wél werkt:** vergelijk per element de `getBoundingClientRect` met die van
    de kaart, aan **beide** kanten, en loop álle elementen af in plaats van de twee
    die gemeld zijn. In fase 8 leverde dat een derde probleem op dat niemand had
    genoemd.

64. **`container-type` doet niets op een inline element — en dat faalt stil.**
    Gemeten: HA geeft de kaarthost `display: inline`. `container-type: inline-size`
    heeft daar geen effect, de host wordt geen query-container, en elke
    `@container`-regel eronder komt nooit aan bod. Geen fout, geen waarschuwing,
    alleen opmaak die niet verandert. `display: block` erbij is dus een voorwaarde
    en geen smaak.
    En: **geef de container een naam.** Een naamloze `@container` pakt de
    dichtstbijzijnde container-voorouder, en dat kan er een van HA zelf zijn — dan
    hangt onze opmaak af van de afmeting van iets waar wij niet over gaan.
    Container queries zijn hier het juiste gereedschap en een media query het
    verkeerde: in een bubble pop-up is de **kaart** smal terwijl het **venster**
    breed is.

65. **Een kaart in een bubble card is smaller dan elke conditie die je tot nu toe
    meet.** `/fase-4a/smal` staat op 373 px (telefoonbreedte); een bubble pop-up zit
    daar onder. Er is nu een view `/fase-4a/bubble` met `grid_options: {columns: 6}`
    → **244 px**. Dat is strenger dan de werkelijkheid en dat is met opzet: wat daar
    past, past overal. Let op dat het **niet** dezelfde component is — een echte
    bubble card brengt eigen CSS mee.

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

**`1.0.0` is uitgebracht** (tag en release door de eigenaar, na fase 5) en draait
bij hem in productie. De procedure hieronder staat er al sinds fase 0, omdat hij in
DomotiApp Scene drie keer bijna misging en één keer echt — hij geldt nu voor elke
volgende versie.

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

### Wat er vóór de eerste release klaar moet zijn

Nagelopen in fase 5, tegen de broncode van HACS. Alles wat hieronder **niet**
staat, is er al.

| | Blokkeert installatie? |
|---|---|
| `version` in `manifest.json` op het releasenummer zetten | ja — HACS vergelijkt de tag met deze waarde |
| Beschrijving en topics op de GitHub-repo | nee (alleen de HACS-action) |
| De HACS-action in CI zetten | nee — pas zinvol bij aanvraag voor de HACS-winkel |

De repo is **nu** installeerbaar als custom repository: HACS' overige controles
(licentie, brands, beschrijving, topics) draaien uitsluitend in hun eigen action,
en die draait alleen bij opname in de standaardwinkel. Zie
`docs/fase-5/RAPPORT.md` voor de vindplaatsen.

---

## Projectstand

| Fase | Wat het opleverde | Status |
|---|---|---|
| 0 | Repo-opzet, testinstance op 8129, en architectuurverificatie van vier onbekenden: `docs/fase-0/ONDERZOEK.md` | gemerged |
| 0b | Music Assistant live geverifieerd (`docs/fase-0b/RAPPORT.md`): `playback_state` bewijst niets, groepsvolume werkt relatief, volumeresolutie is 1 %. HA↔MA-koppeling niet gelukt | gemerged |
| 1 | Rooktest: buildketen (lit + esbuild), CI met vier jobs, de integratie serveert en registreert haar eigen kaart langs beide routes, 8 JS- en 10 Python-tests, verificatie op de dev-instance én op een verse instance | gemerged |
| 2 | `SPEC.md` als bron van waarheid: 20 secties met opslagschema, negen WebSocket-commando's, foutgedrag, wat niet in v1 zit, en tien open vragen | gemerged |
| 2b | De tien open vragen gesloten en sectie 21 verwijderd. `last_failure` hernoemd naar `last_message` met een `severity`. `radio_mode` en de URI-controle doorgeschoven naar fase 3, met beide takken uitgeschreven | gemerged |
| 3a | De server-side laag zonder klok: `store.py` met de kapotte-data-scheiding, `validatie.py` en `volgende.py` (beide puur), `entiteiten.py` met de labelfiltering, en de negen WebSocket-commando's. 112 Python-tests, 13 mutaties nagelopen | gemerged |
| 3b | De planner: `planner.py` (plannen, inhaalslag, respijtvenster, herplannen), `afvuren.py` als naad met 3c, `meldingen.py` met de drie kanalen en de repair issues die 3a openliet. 137 Python-tests, 17 mutaties nagelopen, live gemeten afwijking 12 ms | gemerged |
| 3c | Het afvuren: de acht stappen van SPEC 9.1, `noodrem.py`, `oploop.py` en `radiomodus.py` (beide puur), de wake-up light en de stoptimer. 39 mutaties nagelopen (drie gaten gevonden en gedicht). Valkuil 32 opgelost — oorzaak was de `my`-integratie, niet `external_url`. Live: +2,153 s afwijking, oploop 1,006 s per stap, audio bewezen aan de speakerkant. Eén blokkerende bevinding, opgelost in 3c-bis | in PR #8 |
| 3c-bis | De URI-controle vervalt (SPEC 11.2 herschreven, 11.2.1 vervallen, 11.2.2 met een nieuw criterium). De SomaFM-wekker die in 3c niet afging, gaat nu af met 0 van 87 s stilte. 212 tests, 5 mutaties. `play_media` blokkeert 2,1–2,6 s en dat is niet weg te nemen zonder de foutdetectie te verliezen (`core.py:2953-2959`) | gemerged |
| 4a | De kaart in rusttoestand en de stoptoestand: lijst, schakelaar, overloopmenu, bevestiging bij verwijderen, melding met "Begrepen", en de kaart die één stopknop wordt. Twee pure modules (`weergave.js`, `kaartconfig.js`), de config-editor met `ha-form`. Een **tiende commando** `alarms/clear_message` erbij, want SPEC 11.7 vroeg een knop die SPEC 15 niet kon bedienen; SPEC 15.10/15.11 bijgewerkt met toestemming van de eigenaar. 40 JS- en 216 Python-tests, 28 mutaties (2 gaten gevonden) | gemerged |
| 4b | De editor (SPEC 5) achter de plusknop en achter een tik op een rij, met zoeken in MA, de zomertijdwaarschuwing en de voorbeeldknop. `ringing/subscribe` verbreed tot `updates/subscribe` met een `changed`-bericht uit de opslaglaag — daarmee is het openstaande punt van 4a gesloten. `preview/start` als abonnement, zodat een weggeklikt tabblad het geluid stopt (gemeten: 8,8 s). 69 JS- en 238 Python-tests, 31 mutaties in twee rondes | gemerged |
| 4c | De twee openstaande SPEC-punten van 4b gedicht: `sound/search` geeft per treffer `endless` (op dezelfde providerlijst als het afvuren) en `entities/list` geeft `filtered_out`, waarmee de drie situaties van SPEC 7.4 onderscheidbaar zijn. Het zoekveld past nu op een telefoon: placeholder "Zoek media", knop een vergrootglas. 77 JS- en 264 Python-tests, 23 mutaties in twee rondes | gemerged |
| 5 | HACS-klaar: `manifest.json` en `hacs.json` geverifieerd tegen hassfest én HACS' eigen schema's (beide echt gedraaid, met negatieve controle), README herschreven voor de klant, en de installatie bewezen op een verse HA op 8130 waar de integratie als **kopie** in staat zoals HACS hem levert. Geen functionele wijziging | gemerged, 1.0.0 |
| 6 | Drie bevindingen uit productie op 1.0.0. (1) Shuffle staat nu altijd aan bij afspeellijst, album en artiest — `media_player.shuffle_set` vóór `play_media`, want MA schudt bij het laden van de queue (SPEC 9.6, nieuw). (2) De melding `sound_gone` zei "bestaat niet meer" terwijl het geluid bestond; hij zegt nu "kon niet gestart worden" mét de reden van MA (SPEC 11.7 herschreven — buiten de gestelde grens, gemeld). (3) Een afgelopen eenmalige wekker zette zichzelf nooit uit terwijl SPEC 14.5 dat sinds fase 2 eist; dat is nu op alle drie de routes gerepareerd, en opnieuw aanzetten geeft een nieuwe `one_shot_at` (SPEC 15.3). 297 Python-tests, 22 mutaties in twee rondes (3 gaten gedicht). Audit van SPEC 11.7: nog twee teksten claimen te veel | gemerged |
| 6b | Vier bevindingen. (1) Het overloopmenu bleef onder de kaart hangen — HA heeft géén bruikbare menu-component (gemeten), dus een eigen `position: fixed` menu dat omhoog klapt en binnen de kaart blijft; gemeten op 373 px: was 71 px buiten de kaart, is nu 57 px erbinnen. (2) De kopbalk met de eerstvolgende wektijd en de plusknop staat nu **boven** de lijst; de lege staat ís die kopbalk (SPEC 3.1–3.3). (3) De laatste twee liegende teksten herschreven, mét het patroon erachter (SPEC 11.7). (4) Shuffle gaat na de wekker terug naar wat het was, met de drie regels van SPEC 9.5; live `false → true → false`. 308 Python- en 91 JS-tests, 23 mutaties in twee rondes (2 gaten gedicht) | gemerged, 1.0.1 |
| 7 | De prullenbak, en overslaan eruit. De bevinding eerst uitgezocht: het menu opende maar half, en de oorzaak was een `position: fixed; inset: 0`-laag die sinds fase 4a élke klik op de kaart opving (valkuil 60). Het menu is vervangen door één prullenbakknop per rij met een bevestiging die naam en tijd noemt — geen `ha-dialog`, want die is in 2026.8 van mwc naar Web Awesome gegaan en zijn knoppen kwamen als 0 x 0 uit de verf (gemeten). `skip_next` is volledig verwijderd, met een migratie van schemaversie 1 naar 2; live bewezen op een echte oude `.storage`: 4 wekkers, 0 onleesbaar. 314 Python- en 85 JS-tests, 15 mutaties in twee rondes (2 gaten gedicht, 1 mutatie was zelf fout) | gemerged |
| **8** | **Twee bevindingen uit een bubble card op de telefoon. (1) Afsnijden: de knoppenrij liep 67 px buiten de kaart en het zoekveld werd tot 27 px platgeknepen — `scrollWidth` vond geen van beide (valkuil 63). Voetregel en zoekrij wikkelen nu, en kaart én editor passen zich met een **benoemde** container query aan hun eigen breedte aan (valkuil 64). Gemeten bij 244 px: 0 van de 57 elementen valt nog buiten de kaart. (2) Het voorbeeld zet nu ook de wake-up light aan en zet hem bij het stoppen terug, met dezelfde drie regels als het volume (SPEC 5.4 en 12). Live: `uit → 100 % → uit` en `128 → 255 → 128`. 327 Python- en 85 JS-tests, 14 mutaties in twee rondes (2 gaten gedicht, 1 regel geschrapt als onbereikbaar)** | **deze ronde, PR #16** |

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
2. **Een controle die vals alarm slaat is erger dan geen controle.** Dit was in fase 3c
   nog "twijfel valt niet altijd dezelfde kant op", met de URI-controle als voorbeeld.
   Die controle is in 3c-bis **vervallen** omdat hij voor een hele provider onterecht
   afging. Wat overblijft: `radio_mode` is de énige plek waar twijfel tot *weglaten*
   leidt (SPEC 8.3.1), en de speakercontrole is de enige plek waar twijfel niet kan
   optreden. Zie valkuil 41.
3. **De terugval is de garantie, niet de lijst.** `SIMILAR_TRACKS_PROVIDERS` kan stil
   verouderen; daarom vangt `afvuren.py` de HTTP 500 van `play_media` op en probeert
   het opnieuw **zonder** `radio_mode`. Vertrouwen op de lijst zou betekenen dat een
   MA-wijziging een wekker volkomen stil stukmaakt.

Verder: `async_call_later` en geen `asyncio.sleep` voor de oploop, de tweede
noodremcontrole en de stoptimer. Dat levert een afzegbare unsub op **en** het loopt op
HA's klok, dus een test van 20 stappen kost geen 20 seconden.

**Wat er staat na fase 3c-bis:** hetzelfde, minus één ding. De **voorafgaande
URI-controle is vervallen** (SPEC 11.2), omdat de opgeslagen naam voor een hele provider
onvindbaar bleek in MA's eigen zoekindex en de controle daardoor werkende wekkers
tegenhield. Gevolgen die je moet weten:

- er is **geen** controle op het geluid vóór het afspelen. Een dood geluid komt boven bij
  `play_media` (dan gaat de wekker niet af, met melding `sound_gone`) of bij de tweede
  noodremcontrole vijf seconden later (dan is de wekker wél afgegaan en luidt de melding
  `speaker_lost_during_play`, "mogelijk niet hoorbaar geweest");
- **SPEC 11.3 draagt daardoor meer dan het deed** en is het enige net onder een dood
  geluid. Niet verlengen of weghalen zonder dat te beseffen;
- `Uitkomst.ONBEKEND` is uit `noodrem.py` verdwenen, met een comment dat hij terug moet
  zodra SPEC 11.2.2 in werking treedt.

Live bevestigd: dezelfde SomaFM-wekker die in 3c niet afging, gaat af met **0 van 87
seconden** stilte aan de speakerkant.

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

**De totale afwijking is +2,153 s** (fase 3c) en **+2,565 s** (fase 3c-bis, andere
provider), en dat is **niet** de noodrem: die kost 10 ms sinds de URI-controle vervallen
is, en kostte er 17 mét die controle. Vrijwel alles zit in
`music_assistant.play_media`, die 2,1–2,6 s blokkeert tot MA de stream heeft opgezet —
**en het verschil zit niet in de provider**, dus er is er geen te kiezen die dit wegneemt.
Gevolg: de oploop begint op +3,1 à +3,6 s en is klaar op +22,3 à +22,7 s in plaats van
+20 s. Zie het openstaande punt hieronder; niet-blokkerend aanroepen kan niet.

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
  binnenkant van een andere integratie, en dat breekt bij een update stilletjes.
  **ACHTERHAALD DOOR 3c-bis**, en het is nuttig te weten hoe: de zoekroute die toen als
  alternatief werd gekozen bleek voor een hele provider onbruikbaar en is vervallen. Er
  is nu **geen** voorafgaande controle, en `music/item_by_uri` is daarmee niet langer het
  betere alternatief maar de **enige** route — zie SPEC 11.2.2. De afweging over
  `runtime_data.mass` staat nog, maar de weegschaal is gekanteld.

**Wat er staat na fase 4a:** de kaart in rusttoestand en de stoptoestand. Wekkers zijn
te zien, aan en uit te zetten, over te slaan en te verwijderen; een melding is te lezen
en weg te klikken; en gaat er een wekker af, dan wordt de hele kaart één stopknop —
zowel terwijl hij openstaat (via `updates/subscribe`) als bij het openen (via het veld
`ringing` van `alarms/get`).

**De drie regels van de kaart die je niet mag omdraaien** (zie
`docs/fase-4a/RAPPORT.md`):

1. **De kaart rekent niets uit wat de server al weet.** `next_fire.text` komt
   kant-en-klaar mee (SPEC 3.3) en `alarms/get` levert de lijst gesorteerd (SPEC 3.4).
   Twee implementaties van dezelfde planning lopen uiteen — dat is de fout die
   DomotiApp Scene met de helderheidsschaal maakte.
2. **De stopknop blijft staan bij een onbekend alarm-ID.** Tussen het `started`-event
   en het antwoord van `alarms/get` kent de kaart het ID wel en de wekker nog niet.
   Verdwijnt de knop dan, dan krijgt de klant het geluid pas na 30 minuten uit
   (SPEC 9.4). Er staat dan een neutrale naam in plaats van een verzonnen naam — en dit
   is **live gezien**, niet bedacht: fase 4a mat precies dat venster.
3. **"Begrepen" wist server-side, nooit lokaal.** `last_message` staat in de opslag
   zodat hij een herstart overleeft en op elk scherm zichtbaar is (SPEC 11.7). Lokaal
   verbergen laat hem staan op het wandtablet en zet hem terug na een herlaadbeurt.
   Daarvoor bestaat `alarms/clear_message` (SPEC 15.10).

**Wat er staat na fase 4c:** hetzelfde als na 4b, met twee meldingen die niet meer
kunnen liegen. De editor waarschuwt alleen nog over een geluid dat werkelijk
ophoudt, en de drie situaties van SPEC 7.4 hebben elk hun eigen tekst. Het zoekveld
past op een telefoon.

**Wat er staat na fase 4b: het product is functioneel compleet.** De editor zit achter
de plusknop en achter een tik op een rij, met de tijdkiezer, de herhaaldagen, het zoeken
in Music Assistant, de speaker- en lampkiezer, de zomertijdwaarschuwing en de
voorbeeldknop. Wat er niet meer op de lijst staat: niets uit SPEC 1 t/m 20 dat gebouwd
moest worden. Wat er nog wél is: de openstaande punten hieronder. *(Ten tijde van 4b
stond de versie op `0.1.0` en was er nog geen release; die kwam na fase 5.)*

**De twee regels van fase 4b die je niet mag omdraaien** (zie
`docs/fase-4b/RAPPORT.md`):

1. **Het `changed`-bericht komt uit de OPSLAGLAAG, niet uit de commando's.** De vijf
   muterende commando's zijn niet de enige schrijvers: de planner schrijft `last_fired`
   en de inhaalslag, en `meldingen.py` schrijft `last_message`. Dat zijn juist de
   wijzigingen die de klant niet zelf heeft aangevraagd — en dus de wijzigingen waarvan
   hij het meest heeft dat zijn kaart ze uit zichzelf laat zien. Zet het bericht in
   `websocket.py` en je mist precies die.
2. **Het voorbeeld is een abonnement, en afmelden ís het stoppen.** SPEC 5.4 eist dat
   elke manier van sluiten het voorbeeld stopt, en "elke manier" is meer dan de kaart
   kan afvangen: een weggeklikt tabblad, een gecrashte browser, een wandtablet dat zijn
   wifi verliest. Met een `preview/stop`-commando speelt de muziek in al die gevallen
   door op een speaker waarvan het volume ook nog verzet is. Gemeten in fase 4b: tabblad
   dicht → **8,8 s later** stond het volume terug.

**Wat er staat na fase 6:** het product draait bij de eigenaar en heeft zijn eerste
drie productiebevindingen achter de rug. Een afspeellijst begint niet meer elke
ochtend hetzelfde (SPEC 9.6), de melding bij een mislukt afspelen zegt wat er is
vastgesteld in plaats van wat we vermoeden (SPEC 11.7), en een afgelopen eenmalige
wekker zet zichzelf uit en is met de schakelaar weer tot leven te wekken (SPEC 14.5
en 15.3).

**De drie regels van fase 6 die je niet mag omdraaien** (zie
`docs/fase-6/RAPPORT.md`):

1. **Shuffle gaat vóór het geluid**, om precies dezelfde reden als volume nul: MA
   past shuffle toe bij het **laden** van de queue, dus erna schud je alleen de rest
   (valkuil 51).
2. **Een melding zegt alleen wat is vastgesteld.** De reden van de dienst gaat mee
   als die er is; ontbreekt hij, dan staat er niets in plaats van een gok
   (valkuil 53).
3. **Een verbruikt moment zet een eenmalige wekker uit — op alle drie de routes.**
   Afgegaan, tegengehouden door de noodrem, of overgeslagen: het staat in één
   functie (`afvuren.velden_bij_verbruikt_moment`) juist omdat het anders per route
   uiteenloopt.

**Wat er staat na fase 6b:** de kaart is op een telefoon doorgelopen en de twee
dingen die daar opvielen zijn weg. De kopbalk met de eerstvolgende wektijd en de
plusknop staat **boven** de lijst, en het overloopmenu blijft binnen de kaart in
plaats van eronder te hangen. Verder zegt geen enkele meldingstekst uit SPEC 11.7
nog iets dat de code niet vaststelt, en laat de wekker geen shuffle meer aan staan.

**De twee regels van fase 6b die je niet mag omdraaien** (zie
`docs/fase-6b/RAPPORT.md`):

1. **Meet welke HA-component bestaat vóór je erop bouwt** — en verwacht dat het
   antwoord "geen" is. Er is geen bruikbare menu-component (valkuil 57), en wat er
   wél is verschilt per HA-versie.
2. **Wat wij aanzetten, zetten wij terug — en niets anders.** Volume en shuffle
   volgen dezelfde drie regels: lezen vóór zetten, niets terugzetten wat niet te
   lezen was, en niets terugzetten wat we niet hebben aangezet. Dat laatste is geen
   zuinigheid: het voorkomt dat we een wijziging van de klant zelf ongedaan maken.

**Wat er staat na fase 7:** de kaart heeft één handeling per rij die het altijd
doet. Het overloopmenu is weg en daarmee de laag die er sinds fase 4a onder lag en
elke klik opving; er zweeft **niets** meer boven de kaart. Het overslaan bestaat
niet meer — niet als knop, niet als commando, niet als veld — en de opslag staat op
**schemaversie 2** met een migratie die het oude veld verwijdert.

**De drie regels van fase 7 die je niet mag omdraaien** (zie
`docs/fase-7/RAPPORT.md`):

1. **Geen laag boven de kaart die klikken opvangt.** Een bevestiging die de rijen
   uit elkaar duwt kan de bevinding per constructie niet herhalen (valkuil 60).
2. **Klik in een UI-verificatie twee keer achter elkaar, en op de knop van een
   andere rij.** Vier browserrondes liepen langs deze fout omdat ze alleen
   ⋮ → item → ⋮ → item deden (valkuil 61).
3. **De migratie raakt alleen wat bij naam in SPEC staat.** Al het andere gaat
   letterlijk door naar de validatie, ook rommel — anders verliest de admin het
   bewijs dat hem vertelt wat er stuk is (SPEC 14.6 en 19.2).

En één ding om te weten vóór de volgende meting: **de `?v=` verslaat HA's service
worker niet** (valkuil 62). Ruim de cache en de service worker op, en vergelijk met
een `cache.match` tegen de hash op schijf.

**Wat er staat na fase 8:** de kaart en de editor passen in een bubble card. De
voetregel en de zoekrij wikkelen, en beide surfaces meten zich aan hun **eigen**
breedte in plaats van aan het venster. En het voorbeeld laat zien wat er
's ochtends gebeurt: geluid, volume, shuffle **en** de wake-up light — met de lamp
terug op zijn oude stand zodra je stopt.

**De twee regels van fase 8 die je niet mag omdraaien** (zie
`docs/fase-8/RAPPORT.md`):

1. **Meet afsnijden aan beide kanten, over álle elementen.** `scrollWidth` meet
   alleen naar rechts en ziet een platgeknepen veld helemaal niet (valkuil 63).
2. **Wat wij aanzetten, zetten wij terug — en niets anders.** Volume, shuffle en nu
   ook de lamp volgen dezelfde drie regels: lezen vóór zetten, niets terugzetten
   wat niet te lezen was, en niets terugzetten wat we niet hebben aangezet. Bij de
   lamp komt daar één uitzondering bij die in SPEC staat: een **wekker** laat hem
   aan, een **voorbeeld** zet hem terug.

### Waar de volgende fase begint

`SPEC.md` is bindend en volledig. SPEC 15 beschrijft de **tien** commando's die de
kaart mag gebruiken (15.5 is in fase 7 vervallen; de nummering schuift niet door); dat is de bron, niet dit bestand. Wat hieronder staat is wat je
uit SPEC *niet* kunt lezen omdat het gemeten is.

**Vier dingen die de kaart doet en waar je anders tegenaan loopt:**

1. **Kleed een zoekresultaat uit vóór het opslaan.** `sound/search` geeft `album` en
   `artists` mee; `alarms/save` weigert die met `invalid_format` (valkuil 39). Het
   `sound`-object mag alleen `uri`, `name`, `media_type` en `image` bevatten.
2. **Reken op vier soorten gebeurtenissen uit `updates/subscribe`**: `started`, `stopped`
   (met `reason` `user`/`timeout`/`deleted`) en `failed` (met `reason` = de meldingssoort
   en een `text`). Alle drie zijn live gezien in fase 3c.
3. **Toon `last_message` op kleur en toon van `severity`**, niet op `kind`. `error` en
   `notice` zien er verschillend uit (SPEC 11.7); `kind` is om op te vergelijken.
4. **`getGridOptions` moet `rows: "auto"` teruggeven** (valkuil 12). Een wekkerkaart
   verandert van hoogte, dus een vast getal laat hem over de "+"-knop lopen.

Alle vier zijn in fase 4a en 4b gebouwd en gemeten. Punt 2 telt sinds 4b **vier**
soorten: `changed` is erbij gekomen, en de kaart behandelt elk bericht hetzelfde —
haal de toestand opnieuw op.

**En sinds 4c geldt er een vijfde, die breder is dan de kaart:** *laat de kant die
het antwoord heeft het antwoord geven.* Twee keer bleek de kaart iets te moeten
raden wat de server wist — of `radio_mode` meegaat (`endless`), en waarom een
entiteitenlijst leeg is (`filtered_out`). Beide keren was het gevolg een melding
die soms onwaar was, en dat is het soort dat mensen leren negeren. Eén veld in een
bestaand commando is bijna altijd goedkoper dan een tweede implementatie in de
kaart.

**Vier dashboards om in te meten staan klaar:** `/fase-4a/0` (sections-weergave, de
kaart op `person.dev`), `/fase-4a/spec163` met de drie gevallen van SPEC 16.3 naast
elkaar, en `/fase-4a/smal` — dezelfde kaart op `grid_options: {columns: 9}`, wat
**373 px** oplevert. Dat is telefoonbreedte (Galaxy S8 360, iPhone SE 375, Pixel 7
412) en het is de manier om afkappende teksten te meten zonder het browservenster te
verkleinen, wat op een gemaximaliseerd venster niet lukt (fase 4c). En sinds fase 8
`/fase-4a/bubble` — `grid_options: {columns: 6}`, wat **244 px** oplevert. Dat is
smaller dan een echte bubble pop-up en dus strenger dan de werkelijkheid
(valkuil 65).

**En let op de testrig**: tel de snapclients vóór je een audiometing gelooft
(valkuil 47). Er hoort er **één per hostID** te draaien.

**En bij het meten in de browser:** valkuil 37 (een vastgehouden `hass` leest een bevroren
`states`-snapshot) heeft in fase 3c een geslaagde toets als mislukt laten lijken. Haal
`document.querySelector('home-assistant').hass` opnieuw op na elke handeling.

**De dev-instance is klaar om in te meten**, en dat was niet triviaal:

| | |
|---|---|
| Music Assistant | gekoppeld; drie players (`wekker_slaapkamer`, `wekker_keuken`, `wekkergroep`) |
| Labels | `Music Assistant Wekker` op `media_player.wekker_slaapkamer`, `Verlichting Wekker` op `light.bed_light` |
| Lamp | via `demo:` in `configuration.yaml`; er stond geen enkele `light`-entiteit |
| Speakers | twee snapclients in de MA-container; herstarten met het commando bij "Music Assistant-testserver" |
| Geluid dat werkt | zoek op `Beat Blender`, kies de `radiobrowser://`- of de `somafm://`-treffer |
| Afspeellijst die werkt | `library://playlist/6` — "Recently added tracks", 500 tracks uit MA's `test`-provider. De enige manier om shuffle te meten op deze instance (valkuil 54) |
| Geluid dat aantoonbaar bestaat en tóch niet start | `library://album/1` — een album uit dezelfde provider; `get_album_tracks` ontbreekt en MA geeft `NotImplementedError`. Precies het geval van bevinding 2 |
| Persoon | `person.dev` |

Staat de MA-koppeling na een herstart niet meer: opnieuw toevoegen met URL
**`http://192.168.1.212:8095`** (het LAN-IP — zie valkuil 32 en de MA-sectie).

**Openstaande punten met een fase erbij** — zodat ze niet blijven liggen:

| Punt | Waar | Fase |
|---|---|---|
| **`music/item_by_uri` als voorkeursroute** zodra MA hem via een gepubliceerde service beschikbaar stelt (SPEC 11.2.2) | `websocket.py` / noodrem | na een MA-release; iemand moet dit volgen |
| **De lijst providerdomeinen met `SIMILAR_TRACKS`** (SPEC 8.3.1) is een constante die uit MA's broncode is afgeleid en die **stil** kan verouderen. De HTTP 500 van `play_media` wordt sinds fase 3c opgevangen met een terugval zonder `radio_mode`, dus het ergste geval is nu hinderlijk in plaats van stil. Nalopen blijft nodig: staat een provider er onterecht *niet* in, dan stopt het geluid na het item en vangt geen terugval dat op | `const.py` | nalopen bij elke MA-release |
| **De volume-oploop begint 2,1–2,6 s te laat** doordat `play_media` blokkeert tot MA de stream heeft opgezet. Niet-blokkerend aanroepen kan niet: `core.py:2953-2959` vangt de exceptie binnen HA af, en dan vervallen de `radio_mode`-terugval én de foutmelding. De oploop eerder starten verandert SPEC 9.1 en de betekenis van het `started`-event. **Aanbeveling die niet gebouwd is:** de oploop laten *inhalen* — begin op de stap die bij de verstreken tijd hoort. Meting ligt vast in SPEC 20.1 punt 9 | `afvuren.py` / SPEC 9.1, 9.3 | **beslissing van de eigenaar** |
| ~~De tekst bij `sound_gone` claimt te veel~~ **OPGELOST in fase 6**: hij zegt nu "kon niet gestart worden" met de reden van MA erbij | SPEC 11.7 | gedaan |
| ~~`volume_ramp_unavailable` en `skipped_grace_window` claimen te veel~~ **OPGELOST in fase 6b**, met de voorstellen die de eigenaar heeft goedgekeurd. Het patroon erachter staat nu in valkuil 53 | SPEC 11.7 | gedaan |
| ~~Shuffle wordt na de wekker niet teruggezet~~ **OPGELOST in fase 6b**: hij gaat terug met dezelfde drie regels als het volume (SPEC 9.6) | `afvuren.py` / SPEC 9.5, 9.6 | gedaan |
| **Het tijdveld in de editor is niet op een telefoon getoetst.** De eigenaar meldde dat de tijd tegen de rand loopt; bij 244 px houdt "05:20" nog 130 px over binnen zijn veld, dus het is hier niet te reproduceren. De wijziging van fase 8 (meer padding, kleinere cijfers onder 300 px) is voorzorg. De native tijdweergave is precies wat een telefoon anders tekent | de editor | **eigenaar toetst dit op zijn telefoon** |
| **De verwijderbevestiging heeft geen focusval en geen Escape.** Het zijn twee gewone knoppen in een rij, dus Tab en Enter werken; wat ontbreekt is wat een echte dialoog zou meebrengen. `ha-dialog` bestaat wél op een dashboard, maar zijn sloten zijn in 2026.8 van mwc naar Web Awesome gegaan (`headerTitle`, `footer` in plaats van `primaryAction`/`secondaryAction`) en met de oude namen komen de knoppen als 0 x 0 uit de verf — gemeten in fase 7. Wie dit alsnog wil: gebruik `footer`, en weet dat de kaart zich dan aan de binnenkant van een net verbouwde HA-component bindt | de kaart | bij gelegenheid |
| **De waarschuwing bij een eindig geluid blijft weg bij een BESTAANDE wekker.** `endless` komt uit `sound/search` en staat niet in de opslag — het is een eigenschap van de provider, niet van de keuze (SPEC 15.6). Wie hem ook wil zien bij het openen van een oude wekker, moet `endless` in de opslag zetten of `alarms/get` het laten meesturen. Aanvaard in fase 4c | SPEC 8.2 / 15.1 | **eigenaar**, als hij het mist |
| **De provider-as van `endless` is niet live aangetoond**, alleen de soort-as: er is geen streamingprovider op deze instance (fase 0b). Unittests dekken het paar `spotify`/`somafm` op dezelfde soort | `radiomodus.py` | de eigenaar toetst het op zijn eigen HA |
| **De tijdkiezer is niet op iOS of Android getoetst.** SPEC 5.2 eist alle drie de platformen. Gemeten is dat `<input type="time">` op desktop met toetsen én kliks werkt en dat `ha-time-input` op het dashboard **niet geladen** is (valkuil 50). Een echt apparaat is nodig | de editor | **eigenaar toetst dit op zijn telefoon** |
| **De time-out van `sound/search` is nooit opgetreden in een meting.** De tekst uit SPEC 15.6 wordt server-side gezet en door de editor getoond, maar RadioBrowser was deze ronde snel | `websocket.py` / de editor | bij gelegenheid |
| `getCardSize()` bestaat sinds 4a (1 per rij + 1, en 3 in de stoptoestand) maar is **niet in een masonry-weergave nagemeten**; het dashboard staat in sections-weergave zoals SPEC 20.1 punt 2 voorschrijft | de kaart | 4b of later |
| `panel: true` niet aangeraakt (`frontend#52570`); voor de stoptoestand inmiddels een vastgelegde beperking (SPEC 20.1 punt 2) | de kaart | 4b of later |
| **De kaart moet een zoekresultaat uitkleden** vóór `alarms/save`: `album` en `artists` worden geweigerd (valkuil 39) | de editor | **4b** |
| **Album, artiest en los nummer zijn nooit live AFGESPEELD.** Sinds fase 6 zijn ze wél te **kiezen** en te **zoeken** via MA's `test`-provider (valkuil 54), maar `get_album_tracks` is daar niet geïmplementeerd, dus een album geeft `NotImplementedError`. `playlist` speelt wél en is de basis van de shuffle-meting. Artiest is alleen in Node-tests afgedekt | de editor / `shuffle.py` | de eigenaar toetst het op zijn eigen HA |

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
