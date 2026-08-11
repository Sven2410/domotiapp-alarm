# Fase 4b — De editor en een algemeen abonnement

De plusknop opent nu een echte editor, en het abonnement uit fase 4a is verbreed
zodat een kaart die openstaat meebeweegt met wijzigingen van elders. Twee
SPEC-wijzigingen, beide op verzoek van de eigenaar: taak A (het abonnement) en
taak D (het voorbeeld).

---

## Taak A — het abonnement verbreed

### De naam

`ringing/subscribe` heet nu **`domotiapp_alarm/updates/subscribe`**.

De verantwoording: het abonnement gaat niet meer over afgaan maar over **alles
wat een open kaart nodig heeft om actueel te blijven**, waarvan afgaan er één
soort is. "Updates" dekt dat en blijft in dezelfde vorm als de andere
commando's (`alarms/get`, `sound/search`, `entities/list`). Er waren nog geen
klanten, dus hernoemen kostte niets.

De module `ringing.py` heet daarmee **`abonnement.py`**. Dat is geen cosmetiek:
een bestand dat `ringing` heet en berichten over opslagwijzigingen verstuurt, is
precies de soort naamdrift die dit project elders expliciet bestrijdt.

### Het vierde bericht

```json
{ "event": "changed", "person": "person.sven" }
```

**Het is een sein, geen toestand.** Er staat alleen `person` in; de ontvanger
haalt zelf `alarms/get` op. Twee redenen, beide vastgelegd in SPEC 15.9:

- een abonnee **zonder** `person`-filter zou anders bij elke wijziging de
  wekkerlijst van élke persoon in huis toegestuurd krijgen;
- `alarms/get` blijft de **enige** plek die de toestand samenstelt — dezelfde
  reden dat de kaart `next_fire` niet zelf berekent.

De prijs is één extra aanroep per wijziging, en die is bewust betaald.

### Waar het bericht vandaan komt, en waarom dat het interessante deel is

**Uit de opslaglaag, niet uit de vijf muterende commando's.**

De voor de hand liggende implementatie is een regel aan het eind van `save`,
`set_enabled`, `delete`, `skip_next` en `clear_message`. Die zou werken en toch
een gat laten, want er schrijven méér dingen in de opslag:

| Wie schrijft | Wat | Is het een commando? |
|---|---|---|
| de vijf commando's | de wekker zelf | ja |
| `planner.py` | `last_fired` na elke wekker | **nee** |
| `planner.py` | `skip_next` en `last_message` bij de inhaalslag (SPEC 13.4) | **nee** |
| `meldingen.py` | `last_message` bij elke fout of mededeling (SPEC 11.7) | **nee** |

Dat zijn precies de wijzigingen die de klant **niet zelf heeft aangevraagd** — en
dus de wijzigingen waarvan hij het meest heeft dat zijn kaart ze uit zichzelf
laat zien. `AlarmStore._async_schrijf` is het enige punt waar ze allemaal
langskomen, dus daar staat het bericht. Er is een test per route.

Het bericht gaat er **ná** het wegschrijven uit: faalt het schrijven, dan is er
niets gemeld, want een kaart die dan `alarms/get` doet zou een toestand ophalen
die niet op schijf staat. Mutatie Q11 (bericht vóór de schrijfactie) wordt
gevangen.

---

## Taak D — de voorbeeldknop

### De vorm: een abonnement, geen start/stop-paar

`domotiapp_alarm/preview/start` is een **abonnement**. Zolang het abonnement
loopt, speelt het voorbeeld; afmelden stopt het geluid en zet het volume terug.
**Er is geen `preview/stop`.**

Dat volgt rechtstreeks uit SPEC 5.4: *elke manier van de editor sluiten stopt het
voorbeeld*. "Elke manier" is meer dan de kaart kan afvangen:

| Manier van sluiten | Met een stopcommando | Met een abonnement |
|---|---|---|
| Opslaan, Annuleren, Escape | af te vangen | af te vangen |
| de kaart verdwijnt uit de DOM | af te vangen | af te vangen |
| **tabblad weggeklikt** | **muziek speelt door** | stopt |
| **browser gecrasht** | **muziek speelt door** | stopt |
| **wandtablet verliest wifi** | **muziek speelt door** | stopt |

In de onderste drie gevallen blijft met een stopcommando niet alleen de muziek
draaien, maar staat het volume van de speaker ook nog op het voorbeeldniveau. Dat
is de lege woning uit SPEC 9.4, alleen dan zonder stoptimer. Home Assistant roept
de opruimcallback van een abonnement aan zodra de client zich afmeldt **of de
verbinding wegvalt** — één codepad, en het geval dat je niet kunt afvangen wordt
gratis meegenomen.

Dat is niet alleen beredeneerd maar **gemeten**; zie punt 7 hieronder.

### De tweede rem

Een abonnement leeft zolang de verbinding leeft, en een tabblad dat op een editor
blijft staan kan dagen leven. Een voorbeeld stopt daarom hoe dan ook na **5
minuten** (`VOORBEELD_MAX_MINUTEN`, een VOORSTEL).

### Wat het voorbeeld niet doet

Geen volume-oploop (SPEC 5.4), geen `radio_mode` (dat haalt er de HTTP 500 van
SPEC 8.3.1 bij, en dan lijkt de knop stuk terwijl het geluid deugt), geen
wake-up light (die hoort bij de wekker, niet bij het beoordelen van een geluid).

### Een wekker gaat vóór

Gaat er op de gekozen speaker een **wekker** af, dan wordt het voorbeeld geweigerd
met `not_allowed`. Anders neemt het voorbeeld de queue over en zet het bij het
stoppen het volume terug naar wat de oploop op dat moment toevallig had gezet.
De wekker is het product; het voorbeeld is een hulpmiddel.

---

## Taak B, C en E — de editor

Achter de plusknop (nieuwe wekker) en achter een tik op een rij (bestaande). Een
eigen formulier in de kaart, geen pop-up.

Toetsbare logica staat in **`src/editorlogica.js`** zonder DOM: de standaarden
van SPEC 14.3, het uitkleden van een zoekresultaat, de opslaanbaarheid, de
zomertijdwaarschuwing, de SPEC 7.4-meldingen en de vertaling naar een
`alarms/save`-payload.

### Waarom hier gewone HTML-controls staan

Valkuil 44, en deze fase heeft hem gemeten in plaats van aangenomen. Op het
dashboard waar de kaart staat:

| Component | Gedefinieerd? |
|---|---|
| `ha-card` | ja |
| `ha-select` | ja |
| **`ha-time-input`** | **nee** |
| **`ha-textfield`** | **nee** |

`ha-time-input` is het VOORSTEL van SPEC 5.2 en is er dus niet. Een
ongedefinieerd custom element rendert als een leeg inline-element, zonder fout in
de console — de tijdkiezer zou onzichtbaar zijn geweest. SPEC 5.2 noemt
`<input type="time">` als terugval "die door alle drie de besturingssystemen
native wordt opgelost", en dat is wat de editor gebruikt. Dat `ha-select` er
toevallig wél is, maakt het punt alleen maar scherper: welke component geladen is
hangt af van wat er verder op het dashboard staat.

### Twee plekken waar SPEC nauwkeuriger is dan de kaart kan zijn

Beide gemeld, geen van beide zelf opgelost, want ze vragen een wijziging in
SPEC 15 die buiten de toestemming van deze ronde valt.

**1. De waarschuwing bij een geluid met een eindige duur (SPEC 8.3.1).** SPEC
beperkt die tot geluiden waarvan de provider `SIMILAR_TRACKS` **niet** ondersteunt
— kan hij het wél, dan gaat `radio_mode` mee en blijft het geluid doorspelen, en
dan is de waarschuwing onwaar. De kaart kan dat onderscheid niet maken: de lijst
providerdomeinen staat server-side in `const.py` (en hem kopiëren is precies de
dubbele implementatie die dit product overal vermijdt), en `sound/search` geeft
niet terug of `radio_mode` meegestuurd zou worden.

Wat er nu gebeurt: er wordt gewaarschuwd bij **elke** soort met een eindige duur
(`track`, `podcast`, `audiobook`). Dat is een superset van wat SPEC vraagt — dus
hinderlijk waar het onnodig is, en dat is de goede kant om fout te zitten
(SPEC 8.3.1 kiest bij twijfel zelf ook voor hinderlijk boven stil). Op deze
instance is er geen streamingprovider, dus elke waarschuwing die je hier ziet is
terecht; bij een klant met Spotify zou een los nummer onterecht waarschuwen.

**De oplossing is één veld**: `sound/search` geeft per treffer terug of
`radio_mode` meegestuurd zou worden. Dat is een wijziging van SPEC 15.6.

**2. Twee van de drie meldingen uit SPEC 7.4 zijn niet te onderscheiden.**
`entities/list` geeft `label_exists` plus de overgebleven entiteiten. "Het label
bestaat maar er hangt niets aan" en "er hing wel iets aan maar het viel af op de
eisen van 7.2" leveren allebei een **lege lijst** op. De editor toont daarom één
tekst die beide dekt in plaats van er één te kiezen en in de helft van de gevallen
iets onwaars te beweren:

> "Er zijn nog geen bruikbare speakers met het label 'Music Assistant Wekker'.
> Gelabelde speakers vallen af als het geen Music Assistant-speakers zijn of als
> ze geen volume kunnen instellen."

Het geval dat SPEC wél onderscheidt — het label bestaat niet — heeft zijn eigen
tekst, letterlijk uit SPEC 7.4. Ook hier is de oplossing één veld extra
(bijvoorbeeld een `filtered_out`-telling).

---

## Taak F — tests

| | vóór 4b | na 4b |
|---|---|---|
| JS (`node --test`, geen jsdom) | 40 | **69** |
| Python | 216 | **238** |

Alle nieuwe tests zijn **NIEUW GEDRAG**; er zitten geen regressiewachten in.

### Falen op de oude code

**De `changed`-tests zijn het interessante geval.** Op de code van fase 4a falen
ze triviaal met `ImportError` (de module heet daar nog `ringing`). Om te laten
zien dat het **gedrag** het probleem is en niet de naam, is de hernoeming in de
oude uitcheck weggedacht — `import ringing as abonnement`, en de oude
commandonaam:

```
E       AssertionError: een save hoort een changed-bericht op te leveren
E       assert []
E       AssertionError: save heeft geen changed-bericht gestuurd
E       AssertionError: set_enabled heeft geen changed-bericht gestuurd
E       AssertionError: skip_next heeft geen changed-bericht gestuurd
E       AssertionError: clear_message heeft geen changed-bericht gestuurd
```

Dat is de bevinding van fase 4a, nu als falende test.

`test_voorbeeld.py` faalt op de oude code met een collectiefout (`voorbeeld`
bestaat niet) en `editorlogica.test.mjs` met `ERR_MODULE_NOT_FOUND` — beide
triviaal, en dat staat hier zo in plaats van als bewijs opgevoerd.

### De mutatie-oefening: 31 mutaties, twee rondes

**Ronde 1 ving 22 van de 22.** Dat is precies het patroon waar valkuil 46 voor
waarschuwt — in fase 4a gebeurde hetzelfde — dus er kwam een tweede ronde die
gericht naar gaten zocht in plaats van dekking te bevestigen. Die vond er twee.

| | Mutatie | Uitkomst |
|---|---|---|
| E1–E14 | `editorlogica.js`: standaarden, uitkleden, trimmen, `id`, zomertijdgrens, eindige soorten, labelmeldingen, tijdvalidatie | gevangen |
| Q1–Q8 | `changed` niet sturen, bericht zonder persoon, volume niet lezen, noodrem eruit, wekkercontrole eruit, vorig voorbeeld niet stoppen, abonnement niet registreren, maximumtimer eruit | gevangen |
| E16–E18, E20, Q9–Q11 | tweede ronde: tijdvalidatie, `uri`-controle, lege lijst, volume-type, volume niet terugzetten, bericht vóór de schrijfactie | gevangen |
| **E15** | `conceptVan`: `wekker.enabled !== false` → `=== true` | **NIET GEVANGEN** |
| **E19** | `naarAlarm`: de vangnetlus die niet-gebruikersvelden verwijdert | **NIET GEVANGEN** |

**E15 is een testgat** (valkuil 34, eerste rij). De twee uitdrukkingen zijn gelijk
voor elke waarde die de server kan leveren, maar niet voor een **ontbrekend**
veld — en dan zou een wekker die je opent en opslaat **stil uit** gaan. Dat is
precies het soort stille fout dat SPEC 19.1 verbiedt. Test erbij, met een
positieve controle dat een expliciete `false` wél uit blijft.

**E19 is onbereikbare code** (valkuil 34, derde rij), en dat is nagerekend in
plaats van vermoed: `alarm` wordt als **letterlijk object** opgebouwd uit precies
de negen velden van `GEBRUIKERSVELDEN`, dus die lus kan nooit iets verwijderen.
**De regel is eruit en de meting staat in een comment.** De test die de
eigenschap vastlegt — er gaat nooit een serverveld mee — blijft staan, met de
kanttekening dat hij slaagt door de opbouw en niet door de lus (valkuil 35).

---

## Taak G — browserverificatie

Op de dev-instance (poort 8129), eigen Lovelace-dashboard in sections-weergave.

**Verse code bewezen vóór er iets gemeten is:** service worker afgemeld (1),
vier caches gewist, één harde herlaadbeurt. Bundel op schijf en door HA
geserveerd byte-identiek — **51.276 bytes**, sha256 `024e9369…c699e3`, en
`?v=024e9369b4bf` is de prefix van diezelfde hash. Alle drie de custom elements
geregistreerd (kaart, wekker-editor, config-editor).

### De tien punten

**1. De editor openen** — via de plusknop (`isTrusted: true`, kop "Nieuwe wekker")
en via een rij (kop "Wekker bewerken", met de **opgeslagen** waarden ingevuld:
tijd 06:45, dagen [1,5], naam, geluid, speaker, lamp 60 %). Screenshots
`02-editor-nieuwe-wekker.jpg` en `04-editor-volledig-ingevuld.jpg`.

Het nieuwe formulier opent met precies de standaarden uit SPEC 14.3 —
`time: "07:00"`, `volume_pct: 40`, `days: []`, `enabled: true`, `light: null` —
en met `name`, `speaker` en `sound` **leeg**. Dat laatste is de duurste les uit
DomotiApp Scene: een voorgevulde speaker zou een keuze zijn die de klant niet
heeft gemaakt en die bij Opslaan wél wordt vastgelegd.

**2. Een tijd kiezen, met toetsen én met kliks.**

- Toetsaanslagen: klik op het uur-segment, dan `0`, `6`, `3`, `0` — alle vier
  `isTrusted: true` → veld en concept op **06:30**.
- Kliks: een echte klik op het **minuten**-segment, dan 15 × `ArrowUp` (alle
  `isTrusted`) → **06:45**.

Dat `<input type="time">` beide routes aankan is meteen het antwoord op SPEC 5.2;
zie de meting over `ha-time-input` hierboven.

**3. Herhaaldagen.** Vier echte kliks: `ma`, `di`, `vr`, en `di` opnieuw. Uitkomst
`days: [1, 5]`, aangevinkte dagen in `rgb(2, 111, 161)` = **#026FA1**,
uitgevinkte transparant. De uitleg eronder wisselde van "Geen dag aangevinkt…"
naar "Deze wekker herhaalt zich op de aangevinkte dagen."

**4. De naam MET een spatie** — het punt waar DomotiApp Scene een hele fase op
verloor:

```
T|r|e|i|n|SPATIE|n|a|a|r|SPATIE|U|t|r|e|c|h|t
spatie-keydowns: isTrusted true, true
veldwaarde: "Trein naar Utrecht"   (2 spaties)
concept:    "Trein naar Utrecht"
cursor staat achteraan: ja
```

De cursorpositie staat erbij omdat dát de faalmodus van valkuil 14 is: een
`.trim()` in een controlled input eet de spatie op én laat de cursor terugspringen.
Trimmen gebeurt pas in `naarAlarm`.

**5. Zoeken in Music Assistant.** "Beat Blender" + Enter → **23 treffers**, in de
volgorde `radio, radio, radio, podcast × 20` — afspeellijsten en radio eerst
(SPEC 15.6). Drie afbeeldingen daadwerkelijk geladen
(`naturalWidth > 0`). Screenshot `03-zoeken-in-music-assistant.jpg`.

**En wat er wordt opgeslagen**, valkuil 39 in werking:

| | velden |
|---|---|
| wat `sound/search` teruggeeft | `album`, `artists`, `image`, `media_type`, `name`, `uri` |
| wat de kaart opslaat | `image`, `media_type`, `name`, `uri` |

`album` en `artists` zijn weg. Zonder dat had `alarms/save` de hele opslag
geweigerd met `invalid_format`.

**6. Speaker en lamp.** Beide uit `entities/list`: één speaker
(`media_player.wekker_slaapkamer`, label `Music Assistant Wekker`) en één lamp
(`light.bed_light`, label `Verlichting Wekker`). Na het kiezen van de lamp
verscheen de helderheidsregelaar op de standaard **60 %**, en werd Opslaan
beschikbaar.

**Programmatisch deel, expliciet gemeld:** de twee `<select>`-velden zijn
programmatisch gefocust (`.focus()`) en daarna met een **echte** `ArrowDown`
bediend (`isTrusted: true`). Een klik op een native `<select>` opent een
OS-popup, en die kan de browsertool blokkeren — dezelfde soort beperking als
valkuil 11 beschrijft voor scrollen.

**7. De voorbeeldknop.** Echte klik → speaker `playing`, volume **0,40** (het
ingestelde niveau, niet 0: geen oploop), knop wordt "Voorbeeld stoppen". Aan de
**ontvangende** kant in het snapclient-log (valkuil 38):

```
13-31-18.746  volume: 40    <- het voorbeeld
13-31-58.394  volume: 55    <- na op "Voorbeeld stoppen" klikken
```

**0 regels `No chunks available`** tussen die twee momenten — er kwam werkelijk
geluid uit. HA's log: `Voorbeeld op media_player.wekker_slaapkamer gestopt
(afgemeld)` — de stopknop is dus werkelijk een **afmelding** en geen apart
commando.

**En het geval waarvoor het ontwerp bestaat**, apart gemeten: een voorbeeld
gestart in een tweede tabblad, en dat tabblad daarna **weggeklikt** — geen
afmelding, geen opruimcode, niets:

```
13:36:53.814  Voorbeeld gestart: … volume 35%, maximaal 5 minuten
13-36-51.905  snapclient: volume: 35
   [tabblad gesloten]
13:37:00.757  Voorbeeld op media_player.wekker_slaapkamer gestopt (afgemeld)
13-37-00.754  snapclient: volume: 55
```

**8,8 seconden** tussen het sluiten van het tabblad en het teruggezette volume —
dat is Chrome die de WebSocket afbreekt en HA die de opruimcallback aanroept. Met
een `preview/stop`-commando was hier niets gebeurd.

**8. Opslaan.** Editor dicht, en de opslag bevat exact wat er in het formulier
stond: naam mét spaties, `days: [1,5]`, geluid uitgekleed tot vier velden, lamp
met `brightness_pct: 60`, `volume_pct: 40`, `time: "06:45"`. De lijst stond meteen
gesorteerd met de nieuwe wekker vooraan, en de voetregel op **"Vrijdag 06:45"** —
vandaag is dinsdag 11 augustus en de wekker herhaalt op ma en vr.

**9. De zomertijdwaarschuwing.** Tijd op 02:30 → de waarschuwing verschijnt,
**letterlijk gelijk aan SPEC 5.3** (string-vergelijking: `true`), in
`rgb(155, 155, 155)` (secondary, geen foutkleur) en **niet blokkerend**: de tijd
werd aanvaard en Opslaan bleef beschikbaar. Screenshot
`05-zomertijdwaarschuwing.jpg`.

Daarna Escape — een echte toetsaanslag (`isTrusted: true`) — waarop de editor
sloot en de wijziging **weg** was: op de server stond nog steeds 06:45.

**10. Het abonnement over twee tabbladen.** Dit is de kern van taak A en het gat
dat fase 4a vond.

Tabblad 1 (het "wandtablet") kreeg een `MutationObserver` en tellers op nul.
Tabblad 2 (de "telefoon") zette met een echte klik de schakelaar van
"Trein naar Utrecht" om. Wat tabblad 1 daarvan zag:

| klok | tabblad 1 toont |
|---|---|
| 13:35:42 | … `Zaterdag 09:00` |
| **13:35:48** | … **`Vrijdag 06:45`**, schakelaar weer aan |

En de harde randvoorwaarden bij die meting:

| | |
|---|---|
| kliks in tabblad 1 sinds 13:35:42 | **0** |
| toetsaanslagen in tabblad 1 | **0** |
| tabblad 1 geladen om | **13:20:41** (`performance.timeOrigin`) — dus niet herladen |

Zes seconden na de klik in het andere tabblad bewoog de kaart mee, zonder
herlaadbeurt en zonder dat er in dat tabblad iets is aangeraakt.

Screenshot `06-tweede-tab-meebewogen.jpg`.

**Console:** na een herlaadbeurt met de consolelezer actief geen enkel bericht.

---

## Wat niet lukte

**1. De eerste audiometing van het voorbeeld was onbruikbaar door de
testomgeving.** Het voorbeeld startte correct (HA-log, speaker `playing`, volume
0,40) maar het snapclient-log toonde onafgebroken `No chunks available`. Oorzaak:
**negen snapclient-processen** in de MA-container, meerdere met dezelfde
`hostID`. Die vechten om dezelfde stream en dan krijgt geen van allen chunks.

Na opruimen tot precies één snapclient was de meting meteen schoon: 0 stilte
tijdens het voorbeeld. Dit is een rig-probleem en geen productprobleem, maar het
kostte tijd en het staat nu als valkuil in `CLAUDE.md` — met de bijbehorende les
dat `rm` op een logbestand dat een draaiend proces open heeft, geen nieuw
logbestand oplevert.

**2. De twee SPEC-nauwkeurigheden hierboven** (de `radio_mode`-waarschuwing en
twee van de drie SPEC 7.4-meldingen) zijn **niet** opgelost. Beide vragen één
veld extra in het antwoord van een bestaand commando, en dat is een wijziging van
SPEC 15.6 respectievelijk 15.7 — buiten de toestemming van deze ronde, die alleen
taak A en taak D dekt. Ze staan als openstaand punt in `CLAUDE.md`.

**3. De editor is niet op iOS of Android getoetst.** SPEC 5.2 eist dat de
tijdkiezer op alle drie de platformen werkt. Wat hier is aangetoond is dat
`<input type="time">` op **desktop Chrome** met toetsen én kliks werkt, en dat
het element native is en dus geen lui geladen HA-component nodig heeft. Dat het
op iOS en Android het systeemwiel opent is de reden dat SPEC het als terugval
noemt, maar het is in deze ronde niet gemeten — daar is een echt apparaat voor
nodig.

**4. `sound/search` is niet met een time-out getoetst.** De tekst uit SPEC 15.6
("Zoeken duurt te lang. Probeer het opnieuw.") wordt server-side gezet en door de
editor getoond, maar er is geen meting waarin die time-out werkelijk optrad —
RadioBrowser was deze ronde snel genoeg. De weg ernaartoe is wel gedekt: elke
fout uit `sound/search` komt in dezelfde meldingsregel terecht.

---

## Aannames

1. **De naam `updates/subscribe`** is een keuze; de opdracht vroeg een naam en een
   verantwoording, niet een specifieke naam.
2. **`changed` draagt alleen `person`.** Het alternatief — de volledige toestand
   meesturen — scheelt een aanroep maar geeft elke abonnee de lijst van elke
   persoon en maakt `alarms/get` niet langer de enige bron.
3. **Het maximum van 5 minuten voor een voorbeeld** is een VOORSTEL; SPEC 5.4
   legt geen maximum vast.
4. **Een voorbeeld wordt geweigerd terwijl er op die speaker een wekker afgaat.**
   SPEC beschrijft dit geval niet; de keuze volgt uit "de wekker is het product".
5. **Een tweede voorbeeld op dezelfde speaker vervangt het eerste**, omdat MA één
   queue per player heeft (dezelfde redenering als SPEC 9.2).
6. **De waarschuwing bij een eindige duur wordt op `media_type` alleen gebaseerd**
   en is daarmee ruimer dan SPEC 8.3.1. Zie "Wat niet lukte", punt 2.
7. **De zoeklimiet in de editor is 20**; SPEC 15.6 legt alleen het maximum van 50
   vast en noemt 10 als standaard voor "het eerste beeld".
8. **Een ontbrekend `enabled`-veld telt als aan.** Vastgelegd na mutatie E15;
   de server kan dit niet produceren, maar de andere keuze zou een wekker stil
   uitzetten.

---

## `git status --porcelain`

```
```

(schoon; alles staat in de commits van `fase-4b/editor`)
