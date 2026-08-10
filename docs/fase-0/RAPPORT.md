# Fase 0 — Rapport

Repo-opzet, testinstance en architectuurverificatie voor **DomotiApp Alarm**.

Deze fase heeft niets functioneels gebouwd: geen tests, geen integratiecode. De
regel "een test telt pas als hij aantoonbaar faalt op de code van vóór de fix"
was hier niet van toepassing.

---

## Samenvatting

**Taak A — nieuwe repo.** `C:\dev\domotiapp-alarm` is een git-repo met één
commit rechtstreeks op `main`: `README.md`, `.gitignore`, `docker-compose.yml`,
`LICENSE` (MIT, Sven2410, 2026) en `custom_components/domotiapp_alarm/.gitkeep`.
Geen manifest, geen hacs.json, geen code. De GitHub-repo is **public**
aangemaakt en `origin` wijst erheen.

**Taak B — testinstance.** Container `ha-alarm` draait in compose-project
`domotiapp-alarm-dev` op **poort 8129**, image gepind op `2026.8` (feitelijk
2026.8.1). HTTP antwoordt. **Er is niet ge-onboard** — geen account, geen
wachtwoord, geen browser.

**Taak C — snelkoppeling.** `C:\Users\svenk\Desktop\DomotiApp Alarm.lnk` bestaat
en is niet gestart.

**Taak D — CLAUDE.md.** Geschreven op basis van
`C:\dev\domotiapp-scene\CLAUDE.md` en `docs\AANPAK.md`. Zeventien
productonafhankelijke valkuilen overgenomen (registratie via `registreer.js`, de
`?v=`-bundelhash met herladen van de config entry, de twee laadroutes, de
meetvalkuilen in de browser, de releaseprocedure met `npm run build` tussen
versienummer en commit). Negen valkuilen nieuw toegevoegd uit de metingen van
deze fase, waaronder dat extra state attributes verdwijnen bij `unavailable`.
Scene-specifieke zaken (lampsoorten, kelvinregelaars, light groups, de
SPEC-nummering van dat project) zijn weggelaten.

**Taak E — architectuurverificatie.** Alle vier de onbekenden zijn nagemeten in
de broncode van de draaiende container, met bestandspad en regelnummer, in
`docs/fase-0/ONDERZOEK.md`. Drie van de vier zijn ook **empirisch** gemeten met
draaiende Python-scripts in de container in plaats van alleen gelezen.

De vier belangrijkste uitkomsten:

1. **Er is geen inhaalmechanisme na een herstart.** Tijdplanners zijn
   `loop.call_at`-timers in het geheugen (`helpers/event.py:1461-1466`) en HA's
   eigen tijdtrigger plant een absoluut moment alleen als het in de toekomst
   ligt (`components/homeassistant/triggers/time.py:190-191`) — een gemist moment
   wordt stil overgeslagen. Wél bruikbaar: een `async_track_point_in_time` op een
   moment in het verleden vuurt onmiddellijk (gemeten +0,0002 s). Nauwkeurigheid
   is geen risico: `async_track_time_change` vuurde +0,289 s te laat, door een
   opzettelijke jitter van 50–500 ms.

2. **Een service-aanroep op een offline speaker slaagt en doet niets.** Gemeten
   met een echte entity service: bij targeting op `entity_id` komt er één
   `WARNING`, bij targeting op **`label_id` nul waarschuwingen**. Dit is de
   stilste faalmodus in dit product.

3. **Music Assistant heeft geen aanroepbaar oplopend volume.** `fade_in` bestaat,
   maar is een boolean op `play_index`/`resume`
   (`music_assistant_client/player_queues.py:101, 193`) en de HA-integratie roept
   het nergens aan. De oploop van stil naar het ingestelde volume in 20 seconden
   moet de integratie zelf maken met herhaalde `volume_set`-aanroepen.

4. **Person en labels werken zoals gehoopt.** Een person-entiteit heeft een
   `unique_id` (`components/person/__init__.py:448`) en dus een registry-entry met
   een stabiel `random_uuid_hex` (`helpers/entity_registry.py:234-235`); die
   overleeft hernoemen. Labels op entiteit, apparaat én gebied worden alle drie
   uitgerold door `helpers/target.py:223-292`, een niet-bestaand label geeft geen
   exceptie maar een expliciete `missing_labels`, en `label_id` verandert niet bij
   hernoemen.

**Taak F — beoordeling.** Het grootste risico is **E2, Music Assistant**: de
stille faalmodus bij een offline speaker is precies de faalmodus die een
wekkerkaart niet mag hebben, het oplopende volume is een te bouwen component in
plaats van een instelling, en E2 is het enige onderdeel dat niet empirisch
geverifieerd kon worden. Vier punten voor het productontwerp zijn gemeld, waarvan
twee een koerswijziging: een wekker mag niet alleen op Music Assistant leunen, en
het oplopende volume verdient een eigen ronde. Volledig uitgeschreven in
`docs/fase-0/ONDERZOEK.md`, taak F.

---

## Wat niet lukte

- **Music Assistant is niet live geverifieerd.** Er is geen MA-server in de
  testopstelling. Alles onder E2 komt uit de broncode van de integratie
  (`components/music_assistant/`) en de twee bibliotheken
  (`music-assistant-client==1.4.3`, `music-assistant-models==1.1.152`), niet uit
  waargenomen gedrag. Drie dingen blijven daardoor **ONBEKEND**: de
  volumeresolutie van echte speakers (en dus of een oploop hoorbaar trapsgewijs
  wordt), of `display`/`visualizer`/`light`-players als HA-mediaplayer opduiken,
  en welke media-soorten bij deze klant daadwerkelijk resultaten opleveren. Dit
  is de grootste openstaande post van deze fase.

- **E3 is niet op de draaiende instance nagemeten.** Zonder onboarding bestaat
  er geen gebruiker en geen person, en onboarden was expliciet buiten de
  opdracht. Het antwoord is uit de broncode hard vast te stellen, maar de
  bevestiging op een echte instance hoort in fase 1: person aanmaken,
  registry-entry uitlezen, hernoemen, opnieuw uitlezen.

- **Twee meetfouten die ik zelf heb gemaakt en gerepareerd.** Beide zijn
  leerzaam genoeg om op te schrijven:
  1. De eerste DST-meting gebruikte naieve `datetime`-rekenkunde om de
     herplanlus na te bootsen. Per PEP 495 verliest `fold` zijn waarde bij
     optellen, waardoor mijn lus "10 keer vuren" opleverde voor een wekker op
     02:30 in de najaarsnacht. Opnieuw gemeten vanuit echte UTC-instants, precies
     zoals `helpers/event.py:1780-1795` het doet: het is **2 keer**. De eerste
     uitkomst was een artefact van de meting, niet van HA.
  2. Mijn log-teller in de offline-speakermeting formatteerde het log-record
     dubbel (`record.getMessage() % record.args`) en gooide een `TypeError` die
     als "exceptie uit de service-aanroep" in de uitvoer verscheen. Na reparatie
     bleek de service-aanroep juist géén exceptie te geven — het tegenovergestelde
     van wat de kapotte meting suggereerde.

  Beide keren gold hetzelfde: de eerste meting gaf een antwoord dat plausibel
  genoeg was om te geloven. Dat is precies waarom de uitkomst hier met de
  meetmethode erbij staat.

- **Geen `.gitattributes` in de eerste commit.** Bij `git add` gaf git al "LF
  will be replaced by CRLF" op vier bestanden. Dat is nog onschadelijk — er is
  geen bundel — maar het is de valkuil die in DomotiApp Scene de
  bytevergelijking op Windows liet falen. De eerste commit was bewust beperkt tot
  de opgedragen bestanden, dus het is niet toegevoegd; het staat als valkuil 17 in
  `CLAUDE.md` met de opdracht het in fase 1 te regelen, vóór er een bundel in de
  repo staat.

- **De snelkoppeling heeft een andere `TargetPath` dan opgegeven.** Opgegeven
  was `wt.exe`; `WScript.Shell` heeft dat bij het opslaan tegen `PATH` opgelost
  naar `C:\Users\svenk\AppData\Local\Microsoft\WindowsApps\wt.exe`. Dat is
  normaal gedrag van de COM-interface, geen afwijking van de opdracht, maar het
  is wél wat er teruggelezen wordt en daarom staat het zo in het bewijs.

---

## Aannames

1. **`RegistryEntry.id` is de opslagsleutel, niet `unique_id`.** Beide zijn
   stabiel bij hernoemen. De keuze voor `RegistryEntry.id` is een aanbeveling met
   twee redenen (gelijkvormig met DomotiApp Scene, en `unique_id` is bij een
   person een slug van de naam die uitnodigt tot matchen), maar het is een
   **ontwerpkeuze die de eigenaar of `SPEC.md` maakt**, niet iets dat de meting
   dicteert. Beschreven in ONDERZOEK E3.2.

2. **De genoemde `WARNING`-regel is de enige terugmelding bij een offline
   speaker.** Gemeten is dat `helpers/service.py` geen exceptie geeft en dat
   `log_missing` bij label-targeting niets logt. Ik heb niet uitgesloten dat een
   andere HA-voorziening (recorder, logbook, een systeemmelding elders) er alsnog
   iets van vastlegt. Voor het ontwerp maakt dat niets uit — er is geen
   terugmelding die de klant 's ochtends ziet — maar de formulering "geen enkel
   spoor" is beperkt tot wat gemeten is.

3. **De nauwkeurigheidsmeting is op een onbelaste eventloop gedaan** in een
   los Python-proces met een `HomeAssistant`-object dat niet volledig is gestart.
   De planningsmachinerie is dezelfde, maar wat een druk bezette eventloop met de
   afwijking van +0,289 s doet, is niet gemeten. Bij een eis van een minuut is de
   marge zo groot dat dit het antwoord niet verandert.

4. **De DST-uitkomsten gelden voor Europe/Amsterdam in 2026** (overgangen 29
   maart en 25 oktober), expliciet gezet in het meetscript. Het mechanisme in
   `util/dt.py:436-555` is tijdzone-onafhankelijk, maar de getallen in de tabel
   zijn dat niet.

Geen andere aannames gedaan. Waar iets niet vastgesteld kon worden, staat in
`ONDERZOEK.md` letterlijk **ONBEKEND** in plaats van een gok.

---

## Bewijzen

### Taak A — `git remote -v` en zichtbaarheid

```
=== git remote -v ===
origin	https://github.com/Sven2410/domotiapp-alarm.git (fetch)
origin	https://github.com/Sven2410/domotiapp-alarm.git (push)

=== visibility ===
{"defaultBranchRef":{"name":"main"},"name":"domotiapp-alarm","url":"https://github.com/Sven2410/domotiapp-alarm","visibility":"PUBLIC"}
```

Eerste commit op `main`:

```
f7d05fb Scaffold: repo-opzet en testinstance voor DomotiApp Alarm
```

### Taak B — de container draait

```
=== docker compose ls ===
NAME                  STATUS              CONFIG FILES
domotiapp-alarm-dev   running(1)          C:\dev\domotiapp-alarm\docker-compose.yml
domotiapp-energy      running(1)          C:\dev\domotiapp-energy\docker-compose.dev.yml

=== docker ps ===
NAMES      IMAGE                                          STATUS          PORTS
ha-alarm   ghcr.io/home-assistant/home-assistant:2026.8   Up 40 seconds   0.0.0.0:8129->8123/tcp, [::]:8129->8123/tcp

=== docker compose logs (laatste 15) ===
ha-alarm  | s6-rc: info: service s6rc-oneshot-runner: starting
ha-alarm  | s6-rc: info: service s6rc-oneshot-runner successfully started
ha-alarm  | s6-rc: info: service fix-attrs: starting
ha-alarm  | s6-rc: info: service fix-attrs successfully started
ha-alarm  | s6-rc: info: service legacy-cont-init: starting
ha-alarm  | s6-rc: info: service legacy-cont-init successfully started
ha-alarm  | s6-rc: info: service legacy-services: starting
ha-alarm  | services-up: info: copying legacy longrun home-assistant (no readiness notification)
ha-alarm  | s6-rc: info: service legacy-services successfully started
ha-alarm  | 2026-08-10 11:28:56.011 WARNING (ImportExecutor_0) [py.warnings] /usr/local/lib/python3.14/site-packages/rich/segment.py:547: SyntaxWarning: 'return' in a 'finally' block
ha-alarm  |   return
```

HTTP-statuscode op `http://localhost:8129`:

```
=== HTTP http://localhost:8129 ===
StatusCode: 200

=== curl-controle ===
HTTP 302
```

Twee getallen, één toestand: PowerShell volgt de redirect en rapporteert **200**
op de onboardingpagina; `curl` zonder `-L` toont de **302** die daarheen wijst.
De instance draait en is **niet ge-onboard**.

### Taak C — de snelkoppeling

```
=== bestand ===
FullName      : C:\Users\svenk\Desktop\DomotiApp Alarm.lnk
Length        : 1198
LastWriteTime : 10-8-2026 13:29:54

=== teruggelezen uit het object ===
TargetPath       : C:\Users\svenk\AppData\Local\Microsoft\WindowsApps\wt.exe
Arguments        : -d "C:\dev\domotiapp-alarm" "C:\Users\svenk\.local\bin\claude.exe"
WorkingDirectory : C:\dev\domotiapp-alarm
```

Niet gestart.

---

## `git status --porcelain`

Op branch `fase-0/verificatie`, na het commiten van `CLAUDE.md` en
`docs/fase-0/`:

```
```

(leeg — geen niet-vastgelegde wijzigingen)
