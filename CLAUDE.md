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
  Config in `.ha-dev-config/` (gitignored).
- **De poorten 8123, 8124, 8125, 8126 en 8127 zijn bezet door andere projecten
  en mogen nooit gebruikt worden.**
- **De productie-HA wordt nooit aangeraakt, ook niet gelezen.**
- **Minimum HA-versie: 2026.8.**
- `name:` staat expliciet in `docker-compose.yml`. Zonder die regel ziet Docker
  Compose meerdere compose-bestanden in dezelfde mapstructuur als één project en
  vervangt het de verkeerde container.
- **`custom_components/domotiapp_alarm/` moet in git bestaan vóór de container
  start**, anders maakt Docker er zelf een lege root-owned map van.

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

5. **De browsertool schrijft geen screenshotbestanden weg.** Vijf rondes op rij
   in DomotiApp Scene. Reken daarop: het bewijs is een DOM-uitlezing, een lijst
   service-aanroepen, een bytegrootte of een gemeten positie in pixels.

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
    **Staat er in dit project nog niet in** — bij de eerste commit gaf git al
    "LF will be replaced by CRLF" op vier bestanden. Regelen in fase 1, vóór er
    een bundel in de repo staat.

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

26. **Music Assistant heeft geen oplopend volume dat je kunt aanroepen.** MA
    kent wel `fade_in`, maar dat is een **boolean** op `play_index`/`resume`
    (`music_assistant_client/player_queues.py:101, 193`) en de HA-integratie
    roept het **nergens** aan. Vanuit HA is er alleen `volume_set` (absoluut) en
    `volume_up`/`volume_down` (stap). Een oploop van stil naar het ingestelde
    volume in 20 seconden moet de integratie zelf maken, met herhaalde
    `volume_set`-aanroepen.

---

## Releaseprocedure

Nog niet van toepassing: er is nog geen manifest, geen bundel en geen CI. Wat er
uit DomotiApp Scene overgenomen moet worden zodra die er zijn — het is daar drie
keer bijna misgegaan en één keer echt:

Het versienummer uit `manifest.json` hoort in de bundel geïnjecteerd te worden.
Een versieverhoging verandert dan de bytes van de bundel, ook als er in `src/`
niets is gewijzigd. In DomotiApp Scene is bij 1.0.1 de versie opgehoogd zonder
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
