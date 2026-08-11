# SPEC.md — DomotiApp Alarm

Dit document beschrijft **wat** we bouwen en is **bindend**. `CLAUDE.md`
beschrijft **hoe** we werken.

Wijkt een opdracht van dit document af, dan wint dit document en wordt dat
gemeld. Blijkt een sectie niet uitvoerbaar of feitelijk onjuist, dan wordt hij
**niet zelf gewijzigd**: melden en stoppen. Uitzondering is een ronde waarin de
eigenaar expliciet om een SPEC-correctie vraagt.

**Markeringen in dit document**

- **VOORSTEL** — niet vastgelegd door de eigenaar; door mij ingevuld om het
  document uitvoerbaar te maken. Mag zonder discussie omgegooid worden.
- **GEMETEN** — volgt uit fase 0, 0b of 1, met vindplaats.

---

## Inhoud

1. [Product en identiteit](#1-product-en-identiteit)
2. [Architectuur in één beeld](#2-architectuur-in-één-beeld)
3. [De kaart in rusttoestand](#3-de-kaart-in-rusttoestand)
4. [De kaart terwijl een wekker afgaat](#4-de-kaart-terwijl-een-wekker-afgaat)
5. [De editor: een wekker instellen](#5-de-editor-een-wekker-instellen)
6. [De person-entiteit als opslagsleutel](#6-de-person-entiteit-als-opslagsleutel)
7. [Entiteiten kiezen: labels en herkomst](#7-entiteiten-kiezen-labels-en-herkomst)
8. [Geluid kiezen](#8-geluid-kiezen)
9. [Afgaan](#9-afgaan)
10. [Hoe de wekker gestopt wordt](#10-hoe-de-wekker-gestopt-wordt)
11. [De noodrem](#11-de-noodrem)
12. [De wake-up light](#12-de-wake-up-light)
13. [Plannen](#13-plannen)
14. [Opslag](#14-opslag)
15. [WebSocket-API](#15-websocket-api)
16. [De kaart-config](#16-de-kaart-config)
17. [Rechten](#17-rechten)
18. [Entiteiten die verdwijnen of veranderen](#18-entiteiten-die-verdwijnen-of-veranderen)
19. [Foutgedrag](#19-foutgedrag)
20. [Wat NIET in v1 zit](#20-wat-niet-in-v1-zit)

---

## 1. Product en identiteit

| | |
|---|---|
| Naam | **DomotiApp Alarm** |
| Domein | `domotiapp_alarm` |
| Custom element | `domotiapp-alarm-card` |
| Minimum HA-versie | **2026.8** |
| Taal | Nederlands; `translations/en.json` alleen als fallback zodat een niet-Nederlandse installatie geen ruwe sleutels toont |

Het model is de **wekker-app op een telefoon**: een lijst wekkers, per wekker
een tijd, herhaaldagen en een schakelaar, en een editor achter een plusknop.

**Het wezenlijke verschil met DomotiApp Scene:** dat product was reactief — de
kaart deed iets omdat iemand erop drukte. Dit product is dat niet. De wekker moet
om 06:45 afgaan **ook als er geen browser openstaat en ook als Home Assistant
vannacht is herstart**. De integratie plant en vuurt af; de kaart is een editor
voor de opslag plus een stopknop.

### 1.1 Kleur

- **Accentkleur `#026FA1`** voor accenten: een actieve schakelaar, de stopknop,
  het geselecteerde tabblad.
- **Alles daarbuiten via HA-themavariabelen**: `--primary-text-color`,
  `--secondary-text-color`, `--card-background-color`, `--divider-color`. Zo
  beweegt de kaart mee met het thema van de klant.
- Iconen mogen vaste kleuren dragen (uitzondering uit `CLAUDE.md`).

### 1.2 Eén bron voor het versienummer

`version` in `custom_components/domotiapp_alarm/manifest.json`. Die waarde wordt
bij het bundelen in de kaart geïnjecteerd (`__CARD_VERSION__`). `package.json`
heeft bewust geen `version`. Zie `docs/fase-1/RAPPORT.md`, taak A.

---

## 2. Architectuur in één beeld

```
                     ┌─────────────────────────────────────────┐
                     │ integratie domotiapp_alarm              │
  Store              │                                         │
  .storage/          │  planner                                │
  domotiapp_alarm    │   - async_track_time_change (herhaald)  │
  .alarms  ◄────────►│   - async_track_point_in_time (eenmalig)│
                     │   - inhaalslag bij setup (30 min)       │
                     │                                         │
                     │  afvuren                                │
                     │   - noodrem: available?                 │
                     │   - MA: play_media                      │
                     │   - volume-oploop per speaker, 20 s     │
                     │   - wake-up light aan (optioneel)       │
                     │   - stop na 30 min                      │
                     │                                         │
                     │  WebSocket-commando's ◄──────────┐      │
                     │  frontend-registratie (2 routes) │      │
                     └──────────────────────────────────┼──────┘
                                                        │
                              ┌─────────────────────────┴──┐
                              │ domotiapp-alarm-card       │
                              │  - lijst wekkers           │
                              │  - editor                  │
                              │  - stopknop bij afgaan     │
                              └────────────────────────────┘
                                          │
                    ┌─────────────────────┴───────────────────┐
                    │ Music Assistant  +  light-entiteiten    │
                    └─────────────────────────────────────────┘
```

**De laadketen staat en verandert niet.** De integratie serveert haar bundel op
`/domotiapp_alarm/domotiapp-alarm-card.js?v=<bundelhash>` en registreert die URL
langs **twee** routes: `add_extra_js_url` (voor HA's ingebouwde panelen) en een
Lovelace-resource (voor een browser met een verouderde `index.html` in zijn
service-workercache). Eén URL, twee routes, één ophaling. Zie
`docs/fase-1/RAPPORT.md` taak G en H, en `resource.py`.

De tweede route is **tijdelijk bedoeld**. Landt `frontend#53208` of
`core#176912` in een HA-release, dan kan hij eruit en is `homeassistant` in
`hacs.json` het instrument om te bepalen vanaf welke versie dat mag.

---

## 3. De kaart in rusttoestand

### 3.1 Zonder wekkers

Eén regel **"Geen wekkers ingesteld"** in `--secondary-text-color`, en een
**plusknop**. Niets anders — geen uitleg, geen lege lijstkop.

Die ene regel ís de kopbalk uit [3.2](#32-met-wekkers): links de tekst, rechts de
plusknop. De kaart bestaat dan uit één rij.

**Waarom niet de kopbalk plus een aparte lege regel eronder.** Dan staan er twee
ontkenningen onder elkaar — "Geen wekker actief" boven "Geen wekkers ingesteld" —
en heeft de kaart twee plusknoppen, of één die verspringt zodra de eerste wekker
er is. De plusknop staat altijd op dezelfde plek.

*Verduidelijkt in fase 6b, toen de kopbalk naar boven verhuisde.*

### 3.2 Met wekkers

**Bovenaan een kopbalk**, met links de tekst uit
[3.3](#33-de-regel-eerstvolgende-wekker) — *"Morgen 06:45"* — en rechts de
**plusknop**. Daaronder de lijst.

De kopbalk stond tot fase 6b **onder** de lijst. Met tien wekkers moest je dan
scrollen om te zien wanneer je wekker gaat en om er een toe te voegen, en dat zijn
precies de twee dingen waarvoor je de kaart openslaat. Op een telefoon is dat het
verschil tussen wel en niet bruikbaar.

Daaronder de lijst, één rij per wekker, in de volgorde uit
[sectie 3.4](#34-sorteervolgorde). Per rij:

| Onderdeel | Inhoud |
|---|---|
| Tijd | `06:45`, groot en als eerste — dat is waar de gebruiker naar kijkt |
| Naam | de naam van de wekker, onder of naast de tijd |
| Herhaaldagen | `ma di wo do vr` — of **"Eenmalig"** als er geen dag is aangevinkt |
| Schakelaar | aan/uit, accentkleur `#026FA1` als hij aan staat |

Een wekker is per rij **te verwijderen** —
[sectie 15.4](#154-domotiapp_alarmalarmsdelete). Dat is de enige rij-actie naast
de schakelaar en het openen van de editor.

**Eén prullenbakknop per rij**, en geen overloopmenu. De knop vraagt een
bevestiging, want verwijderen is onomkeerbaar; **Annuleren doet niets**.

De bevestiging **noemt de naam én de tijd** van de wekker. Beide, want een lijst
met vier wekkers heeft er zo twee van "Werk", en de vraag moet te beantwoorden
zijn op precies het moment dat hij onomkeerbaar wordt.

*Tot fase 7 stond hier een overloopmenu met "Overslaan" en "Verwijderen". Het
overslaan is als functie vervallen (zie [15.5](#155-vervallen)), en het menu zelf
werkte niet — zie hieronder.*

**De bevestiging mag de kaart niet blokkeren.** Dat is een eis en geen
opmaakdetail, en hij komt uit de bevinding die fase 7 opende: het overloopmenu
werd afgesloten met een laag over het hele venster, en die laag ving **elke** klik
op de kaart weg. Wie tweemaal op de drie puntjes drukte, kreeg de eerste keer een
menu en de tweede keer niets, want de knop lag onder de laag. De eigenaar meldde
het als *"het menu opent maar heel af en toe"*.

De regel die daaruit volgt: **elke laag die klikken opvangt, hoort ook te
verbergen wat eronder ligt.** Een dialoog mag dat — dan is de rest van het scherm
zichtbaar dood. Een menu dat naast een klikbare knop staat, mag het niet.

**GEMETEN in fase 7** op HA 2026.8.1, verse pagina, zonder een enkele klik en nog
eens vijf seconden later: `ha-dialog`, `ha-alert`, `ha-button` en
`ha-icon-button` **zijn** gedefinieerd op een gewoon dashboard; `ha-md-dialog`
niet. De bevestiging gebruikt daarom `ha-dialog` — die heeft het scrim, de
focusval en Escape al opgelost.

**Met een terugval**, want "gedefinieerd op dit dashboard" is niet hetzelfde als
"gedefinieerd bij elke klant": fase 6b mat dat `ha-switch` in fase 4a nog niet
geladen was en in 6b wel. Ontbreekt een van de componenten, dan komt de
bevestiging als **regel binnen de kaart**, met dezelfde tekst en dezelfde twee
knoppen; die regel overlapt niets. Het faalgeval zonder terugval zou stil zijn:
een ongedefinieerd custom element rendert als een leeg inline-element, dus de
klant zou op de prullenbak drukken en niets zien gebeuren.

### 3.3 De regel "eerstvolgende wekker"

De tekst wordt **server-side** bepaald en meegeleverd door
[`alarms/get`](#151-domotiapp_alarmalarmsget) als `next_fire`. Dat is met opzet:
de kaart mag de planningslogica uit [sectie 13](#13-plannen) niet dupliceren,
want dan zijn er twee implementaties die uiteen kunnen lopen — de fout die
DomotiApp Scene met de helderheidsschaal maakte.

Vorm, **VOORSTEL**:

| Situatie | Tekst |
|---|---|
| Vandaag | `Vandaag 06:45` |
| Morgen | `Morgen 06:45` |
| Binnen 7 dagen | `Zaterdag 08:00` |
| Verder weg | `Za 17 aug 08:00` |
| Er zijn wekkers, maar geen enkele staat aan | `Geen wekker actief` |
| Er is geen enkele wekker | `Geen wekkers ingesteld` ([3.1](#31-zonder-wekkers)) |

De laatste twee zijn sinds fase 6b uit elkaar gehaald. Ze vragen iets anders van de
gebruiker: "maak er een" tegenover "zet er een aan".

### 3.4 Sorteervolgorde

**VOORSTEL:** op tijd, oplopend, en bij gelijke tijd op naam. Niet op
"eerstvolgende", want dan verspringt de lijst gedurende de dag en verliest de
gebruiker zijn plek.

### 3.5 Afmetingen

`getGridOptions()` geeft **`rows: "auto"`**, nooit een getal. Een getal geeft de
kaart in het sections-grid een vaste hoogte en dan loopt hij over zijn vak heen
zodra hij hoger wordt — en deze kaart verandert van hoogte, want er komen
wekkers bij. Zie `CLAUDE.md` valkuil 12.

`getCardSize()` hoort er ook te zijn, voor masonry-weergaven. Dat ontbreekt na
fase 1 en staat als openstaand punt in `CLAUDE.md`.

---

## 4. De kaart terwijl een wekker afgaat

**Er is geen pop-up.** Gaat een wekker af, dan **verandert de kaart zelf van
vorm**: de hele kaart wordt één grote stopknop, in accentkleur `#026FA1`, met de
naam en de tijd van de wekker erin en een duidelijk woord **"Stoppen"**.

Waarom geen pop-up: een `hass-more-info`- of dialoogvenster vergt dat er een
gebruiker is die hem kan wegklikken op het moment dat hij verschijnt, en het
werkt niet op een wandtablet die op een dashboard staat. Een kaart die van vorm
verandert werkt in beide gevallen hetzelfde.

**Dit is een instructie aan de eigenaar, geen eigenschap die de kaart
afdwingt.** De kaart kan alleen een stopknop worden op een dashboard dat op dat
moment openstaat. Staat de kaart nergens open, dan gaat de wekker wél af — de
integratie plant en vuurt onafhankelijk van de browser — maar is er geen
stopknop, en stopt hij pas na 30 minuten
([sectie 9.4](#94-de-wekker-stopt-na-30-minuten)). De klantdocumentatie moet
zeggen: **zet de kaart op het dashboard dat op het wandtablet en op de telefoon
openstaat.**

Hoe de kaart het weet: via een abonnement, niet door te pollen. Zie
[sectie 15.9](#159-domotiapp_alarmupdatessubscribe).

**Meerdere wekkers tegelijk.** Twee personen kunnen op dezelfde tijd een wekker
hebben. Elke kaart toont alleen de wekkers van **zijn eigen** person
([sectie 6](#6-de-person-entiteit-als-opslagsleutel)), dus een kaart wordt alleen
een stopknop voor een wekker van die persoon. Gaan er twee wekkers van dezelfde
persoon tegelijk af — mogelijk, want twee wekkers mogen dezelfde tijd hebben —
dan toont de kaart **één** stopknop die **beide** stopt. **VOORSTEL**, en de
eenvoudigste uitkomst die niet liegt.

---

## 5. De editor: een wekker instellen

De editor gaat open via de plusknop (nieuwe wekker) of door op een rij te tikken
(bestaande wekker). Hij is **geen** Lovelace-config-editor: het is een eigen
formulier in de kaart, dat de opslag van de integratie bewerkt.

### 5.1 Velden

| Veld | Verplicht | Toelichting |
|---|---|---|
| **Tijd** | ja | tijdkiezer, zie [5.2](#52-de-tijdkiezer) |
| **Herhaling** | nee | zeven dagen, elk aan te vinken. **Geen dag aangevinkt = eenmalige wekker** voor de eerstvolgende keer dat die tijd voorbijkomt |
| **Naam** | ja | vrije tekst |
| **Speaker** | **ja** | uit de gelabelde MA-speakers, [sectie 7](#7-entiteiten-kiezen-labels-en-herkomst) |
| **Geluid** | **ja** | via zoeken in Music Assistant, [sectie 8](#8-geluid-kiezen) |
| **Volume** | ja | het niveau waar de oploop op eindigt; [9.3](#93-de-volume-oploop) |
| **Wake-up light** | **nee** | optioneel: een lamp plus een helderheid, [sectie 12](#12-de-wake-up-light) |

**Speaker en geluid zijn verplicht.** Er is geen wekker zonder geluid. Dat heeft
een consequentie die in [sectie 7.4](#74-wat-de-kaart-toont-als-het-label-nog-niet-bestaat)
staat: zijn er geen gelabelde speakers, dan kan er geen wekker worden opgeslagen,
en dan moet de editor dat uitleggen in plaats van een onopslaanbaar formulier te
tonen.

**Naam verplicht** is een keuze — **VOORSTEL**. Alternatief was een
automatische naam ("Wekker 1"). Een verplichte naam is beter omdat de naam in de
stopknop staat en dan iets moet zeggen.

### 5.2 De tijdkiezer

Moet werken op **iOS, Android en desktop**. Dat is een eis, niet een
implementatiedetail: een eigen wieltje met `touchmove` doet het op één van de
drie niet.

**VOORSTEL:** HA's eigen `ha-time-input`, met 24-uursnotatie en zonder seconden.
Dat component wordt door HA zelf op alle drie de platformen gebruikt en heeft de
platformverschillen al opgelost. Blijkt het niet te bruiken, dan is de terugval
een `<input type="time">`, die door alle drie de besturingssystemen native wordt
opgelost.

**Seconden bestaan niet in dit product.** Een wekkertijd is `HH:MM`; de seconde
is altijd `00`.

### 5.3 De zomertijdwaarschuwing

Kiest de gebruiker een tijd **tussen 02:00 en 02:59**, dan toont de editor een
waarschuwing. Niet blokkerend — de tijd mag gekozen worden.

Reden, **GEMETEN** in fase 0 (`docs/fase-0/ONDERZOEK.md` E1.3): een wekker in dat
uur heeft drie mogelijke uitkomsten. Met `async_track_time_change` gaat 02:30 op
29 maart 2026 **niet af** en schuift naar 30 maart; op 25 oktober 2026 gaat hij
**twee keer** af (00:30 en 01:30 UTC). Met een naieve lokale tijd via
`async_track_point_in_time` schuift hij stil naar 03:30.

**De tekst** (VOORSTEL, letterlijk):

> **Let op: deze tijd bestaat twee nachten per jaar niet, of twee keer.**
> Bij de overgang naar zomertijd wordt het uur van 02:00 tot 03:00
> overgeslagen; die nacht gaat deze wekker niet af. Bij de overgang naar
> wintertijd komt dat uur twee keer voorbij; die nacht gaat hij twee keer af.
> Kies een tijd vóór 02:00 of ná 03:00 als dat een probleem is.

**Het gedrag** ligt vast en is niet instelbaar: de integratie gebruikt
`async_track_time_change`, dus het voorjaar slaat over en het najaar vuurt twee
keer. Dat is het gedrag van HA's eigen tijdtrigger en het is het enige van de
drie dat niet stil de tijd verandert.

### 5.4 De voorbeeldknop

Model: de Voorbeeldknop uit DomotiApp Scene (SPEC 9 daar) — **hij doet het echt**,
in plaats van te beloven wat er zou gebeuren.

Het gedrag dat vastligt:

- De knop **speelt het gekozen geluid op de gekozen speaker**, met de waarden
  zoals ze **nu in de editor staan** (nog niet opgeslagen).
- Er is een **stopknop** zolang het voorbeeld speelt.
- **Elke manier van de editor sluiten stopt het voorbeeld**: opslaan,
  annuleren, de X, Escape, wegklikken.
- Het voorbeeld gaat door de **noodrem** van [sectie 11](#11-de-noodrem). Is de
  speaker onbereikbaar, dan zegt de editor dat — dat is precies het moment
  waarop je dat wil weten.

**VOORSTEL, twee punten die niet vastliggen:**

1. **Het voorbeeld speelt op het ingestelde volume, zonder oploop.** De oploop
   duurt 20 seconden en het doel van de knop is het geluid en het niveau
   beoordelen; 20 seconden wachten voordat je hoort of het te hard is, maakt de
   knop onbruikbaar. Dat de oploop zelf werkt is in fase 0b gemeten.
2. **Het volume van de speaker wordt na het voorbeeld teruggezet** naar wat het
   was, volgens [sectie 9.5](#95-het-volume-wordt-teruggezet).

### 5.5 Wat de editor bij openen doet

1. `alarms/get` voor de gekoppelde person, zodat de lijst en de te bewerken
   wekker uit één bron komen.
2. `entities/list` voor de gelabelde speakers en lampen
   ([sectie 15.7](#157-domotiapp_alarmentitieslist)).
3. Bij een bestaande wekker: de opgeslagen waarden invullen.

**Nooit een terugvalwaarde tonen die niet opgeslagen zou worden.** Dat is de
duurste les uit DomotiApp Scene (`CLAUDE.md`, werkafspraken): daar toonde de
editor een helderheid die uit de levende lamp kwam en bij Opslaan nergens
terechtkwam. Concreet hier: staat er geen volume in de opslag, dan toont de
editor **geen** volume uit de speaker maar de expliciete standaard uit
[sectie 14.3](#143-standaardwaarden), en die wordt ook echt opgeslagen.

---

## 6. De person-entiteit als opslagsleutel

### 6.1 De koppeling

De kaart wordt aan **één `person.`-entiteit** gekoppeld, via de
Lovelace-config-editor ([sectie 16](#16-de-kaart-config)). Elke persoon heeft
zijn eigen wekkerlijst, zodat een huisgenoot de wekkers van een ander niet op
zijn kaart ziet.

### 6.2 De sleutel is het registry-entry-ID

**GEMETEN** in fase 0 (`docs/fase-0/ONDERZOEK.md` E3): een person-entiteit heeft
een `unique_id` (`components/person/__init__.py:448`) en krijgt daarmee een
entity registry entry met een stabiel `id` — een `random_uuid_hex`
(`helpers/entity_registry.py:234-235`). Dat ID overleeft hernoemen.

**De opslagsleutel is dat registry-entry-ID**, niet het entity-ID. Reden: een
person hernoemen verandert de weergavenaam en kán het entity-ID veranderen; het
registry-entry-ID niet. Zonder deze keuze verdwijnen de wekkers van iemand die
zijn naam wijzigt.

**De vertaling gebeurt server-side.** De kaart stuurt en ontvangt uitsluitend
`entity_id`; de integratie zoekt het registry-entry-ID erbij. De kaart kent het
registry-entry-ID niet en hoeft dat niet te kennen.

Waarom niet de `unique_id` van de person, die óók stabiel is: die is een slug van
de naam bij aanmaken (`sven`, en bij een tweede Sven `sven_2`, zie
`helpers/collection.py:96-106`). Dat ziet in de opslag uit als iets met
betekenis, en dat nodigt uit tot matchen. Het registry-entry-ID heeft die
verleiding niet en is bovendien dezelfde vorm als in DomotiApp Scene.

### 6.3 Dit is geen beveiliging

**Expliciet vastgelegd:** de scheiding per persoon is een **weergavekeuze**, geen
beveiliging.

- Een huisgenoot ziet de wekkers van een ander **niet op zijn kaart**.
- Maar hij **kan ze technisch opvragen**: elke ingelogde gebruiker mag
  `alarms/get` aanroepen met een willekeurige `person.`-entiteit
  ([sectie 17](#17-rechten)), en de opslag staat in `.storage/` waar elke admin
  bij kan.

Dat is een bewuste keuze en geen omissie. Wekkers zijn geen geheim, en een
rechtenlaag per persoon zou betekenen dat een klant zonder adminrechten zijn
eigen wekkers niet meer kan beheren — precies het faalgeval dat DomotiApp Scene
in SPEC 14 beschrijft. De klantdocumentatie moet dit zeggen, zodat niemand het
voor privacy aanziet.

---

## 7. Entiteiten kiezen: labels en herkomst

### 7.1 De twee labels

De eigenaar plakt twee labels:

| Label | Op | Waarvoor |
|---|---|---|
| `Music Assistant Wekker` | speakers | de speakerkiezer |
| `Verlichting Wekker` | lampen | de wake-up-lightkiezer |

De kaart toont **alleen** entiteiten met dat label.

**GEMETEN** in fase 0 (`docs/fase-0/ONDERZOEK.md` E4):

- Een label heeft een eigen `label_id`, een slug van de naam:
  `Music Assistant Wekker` → `music_assistant_wekker`. **Sla de `label_id` op,
  niet de naam** — hernoemen laat de `label_id` ongemoeid
  (`helpers/label_registry.py:182-213`).
- Labels werken op **entiteit, apparaat én gebied**. Rechtstreeks
  `entity_entry.labels` lezen vindt alleen de eerste; `helpers/target.py:223-292`
  rolt alle drie uit. **Gebruik die helper**, met `TargetSelection` en niet met
  het in HA 2026.12 verdwijnende `TargetSelectorData`.
- Gebruik `primary_entities_only=True` (de standaard), zodat een gelabeld
  apparaat zijn lamp oplevert en niet zijn signaalsterktesensor.
- Verborgen entiteiten vallen af. Dat is gewenst.

De filtering gebeurt **server-side** en wordt geleverd door
[`entities/list`](#157-domotiapp_alarmentitieslist). De kaart filtert niet zelf:
dan zou de label-expansie in twee talen bestaan.

### 7.2 Vaststellen dát het een MA-speaker is

Het label zegt wat de eigenaar **bedoelt**; het zegt niet dat de entiteit
werkelijk een Music Assistant-speaker is. De integratie controleert dat er
bovenop.

**Aanbevolen in fase 0b** (`docs/fase-0b/RAPPORT.md` C1), en hier bindend. Een
entiteit komt in de speakerkiezer als **alle** volgende dingen gelden:

1. het label `Music Assistant Wekker` bereikt hem (via entiteit, apparaat of
   gebied);
2. domein is **`media_player`**;
3. de entity registry entry heeft **`platform == "music_assistant"`**;
4. `supported_features` bevat **`PLAY_MEDIA`**;
5. `supported_features` bevat **`VOLUME_SET`** — anders is de volume-oploop niet
   uitvoerbaar en is de wekker een belofte die niet nagekomen wordt;
6. de speaker is **geen groep**: zie [7.3](#73-groepen-worden-uitgesloten).

**Waarom `supported_features` en niet `mass_player_type`:** extra state
attributes verdwijnen zodra een entiteit `unavailable` is
(`helpers/entity.py:1118-1124`, gemeten in fase 0b). `supported_features`
overleeft dat (regel 1169-1170), `mass_player_type` niet — en juist een
weggevallen speaker is het geval waarin je wil weten wat hij was.

**`device_class` filtert niets:** MA zet `MediaPlayerDeviceClass.SPEAKER` op
élke player (`components/music_assistant/media_player.py:140`).

**`TURN_ON`/`TURN_OFF` is NIET gegarandeerd.** Bij alle in fase 0b geteste
players was `power_control` gelijk aan `"none"`. **Een wekker kan een speaker dus
niet aanzetten.** Staat het apparaat fysiek uit, dan is er geen geluid en geen
manier om dat te verhelpen; dat valt onder [sectie 11](#11-de-noodrem).

**Waarom de platformcheck een vangnet is, niet een luxe:** bij een Sonos maken
zowel de Sonos-integratie als Music Assistant een entiteit aan voor dezelfde
fysieke speaker — `media_player.one_sl_sven` en `media_player.one_sl_sven_2`.
Het label onderscheidt ze als de eigenaar het goed plakt; de platformcheck vangt
het als hij het verkeerd plakt. Zonder die check zou de wekker de Sonos-entiteit
kunnen kiezen, waarop `music_assistant.play_media` niet werkt.

### 7.3 Groepen worden uitgesloten

Groepsplayers komen **niet** in de speakerkiezer.

**GEMETEN** in fase 0b (`docs/fase-0b/RAPPORT.md` C3): een sync-groep meldt zelf
`volume_level: null` — de waarde zit in `group_volume` — en groepsvolume werkt
**relatief**. Groepsvolume op 60 zetten bij leden op 40 en 25 gaf **60 en 50**,
niet 60 en 60. Een wekker die "begin stil, eindig op 40 %" belooft en dat op een
groep doet, levert een eindvolume dat afhangt van waar de speakers gisteravond
stonden.

Uitsluiten gebeurt op **`mass_player_type == "group"`** wanneer de entiteit
beschikbaar is. Is hij dat niet, dan is dat attribuut er niet — dan valt de
integratie terug op wat wél overleeft: een entiteit die in de opslag staat en
niet meer als niet-groep te herkennen is, wordt behandeld volgens
[sectie 18.3](#183-de-speaker-verdwijnt-of-is-onbereikbaar).

Wil de eigenaar meerdere speakers, dan is dat "meerdere speakers per wekker" en
dat zit **niet in v1** ([sectie 20](#20-wat-niet-in-v1-zit)).

### 7.4 Wat de kaart toont als het label nog niet bestaat

Dat is de situatie bij een **nieuwe klant**, en hij moet niet als een fout
voelen.

**GEMETEN** in fase 0 (E4.3): een niet-bestaand label geeft **geen exceptie**
maar een lege selectie, **plus** een expliciete `missing_labels`. Daarmee is
"het label bestaat niet" te onderscheiden van "het label bestaat maar is leeg",
en dat zijn twee verschillende meldingen. `entities/list` levert dat onderscheid
door als `label_exists`.

| Situatie | Signaal uit [15.7](#157-domotiapp_alarmentitieslist) | Wat de editor toont |
|---|---|---|
| Label bestaat **niet** | `label_exists: false` | **"Het label 'Music Assistant Wekker' bestaat nog niet. De beheerder moet dat label aanmaken en op de speakers zetten die als wekker mogen dienen."** |
| Label bestaat, **geen** entiteiten | leeg, `filtered_out: 0` | **"Er zijn nog geen speakers met het label 'Music Assistant Wekker'."** |
| Label bestaat, entiteiten vallen af op [7.2](#72-vaststellen-dát-het-een-ma-speaker-is) | leeg, `filtered_out > 0` | **"De gelabelde speakers zijn geen Music Assistant-speakers, of ze kunnen geen volume instellen."** |

**De middelste kolom is toegevoegd in fase 4c.** Tot dan leverde `entities/list`
alleen `label_exists` en de overgebleven entiteiten, en waren de onderste twee
situaties **van buiten niet te onderscheiden** — beide een lege lijst. De kaart
toonde er daarom één tekst voor die beide dekte. Dat is precies de verkeerde
uitkomst voor de eigenaar: het verschil tussen die twee is het verschil tussen
*"zet het label op je speakers"* en *"die speakers zijn geen Music
Assistant-speakers"*, en dat zijn twee verschillende handelingen. Zie
[15.7](#157-domotiapp_alarmentitieslist).

In alle drie de gevallen:

- de plusknop **blijft werken** — de gebruiker mag de editor openen en zien
  waarom het niet gaat;
- **Opslaan is uitgeschakeld**, met de melding erbij, want speaker en geluid zijn
  verplicht;
- de melding is **geen** foutkleur maar `--secondary-text-color`: dit is een
  installatiestap die nog moet gebeuren, geen storing.

Voor de wake-up light geldt hetzelfde, met één verschil: die is **optioneel**, dus
een ontbrekend label `Verlichting Wekker` blokkeert niets. De keuze wordt dan
niet aangeboden en er staat één regel bij waarom. De derde situatie luidt daar
**"De entiteiten met het label 'Verlichting Wekker' zijn geen lampen."**, want de
enige eis aan een lamp is het domein ([sectie 12](#12-de-wake-up-light)).

---

## 8. Geluid kiezen

### 8.1 Zoeken via Music Assistant

De integratie zoekt via de service **`music_assistant.search`**, die is
geregistreerd met `supports_response=SupportsResponse.ONLY`
(`components/music_assistant/services.py:90-107`). Aanroepen met
`blocking=True` en `return_response=True`.

`config_entry_id` is **verplicht**. Zoek de MA-config-entry op met
`hass.config_entries.async_loaded_entries("music_assistant")`
(`config_entries.py:2213`) — die geeft alleen de entries die daadwerkelijk
geladen zijn. Zijn er meerdere, dan **VOORSTEL**: neem de eerste en log op
`DEBUG` welke. Meerdere MA-servers in één huishouden is geen scenario dat dit
product ondersteunt.

`media_type` is **optioneel**: laat je hem weg, dan zoekt MA alle soorten. De
kaart laat de gebruiker een soort kiezen of "alles"; **VOORSTEL** is dat de
standaard "alles" is, omdat de klant meestal een naam intikt en niet weet of dat
een album of een afspeellijst is.

Het antwoord is **één object met acht lijsten**: `artists`, `albums`, `tracks`,
`playlists`, `radio`, `audiobooks`, `podcasts` — en `media_type` per treffer.

Per treffer komt terug: **`name`**, **`uri`**, **`image`**, **`media_type`**. Bij
een track zitten `album` en `artists` genest, inclusief afbeelding. Dat bepaalt
wat de editor kan tonen: **naam, soort en een afbeelding**, en bij een nummer ook
de artiest en het album. Er is **geen duur** en **geen numeriek ID**.

### 8.2 Sla de URI op, niet de naam

De `uri` is de sleutel. Afspelen met een URI is een verificatie in plaats van een
nieuwe zoekopdracht, en het resultaat verandert niet doordat de bibliotheek
wijzigt.

**Maar de URI is niet eeuwig.** Hij draagt een instantie-ID van de provider:

```
spotify--ZvzrFmgX://track/4uLU6hMCjMI75M1A2tKUQC
        ^^^^^^^^
```

Dat deel **verandert als de provider opnieuw gekoppeld wordt**. De opgeslagen URI
is dan onbruikbaar. Daarom:

- naast de `uri` worden **`name`, `media_type` en `image`** opgeslagen, zodat de
  kaart kan blijven tonen wat de klant had gekozen ook als de URI niet meer
  werkt. **Deze aanbeveling blijft onverkort staan**, ook nu de voorafgaande
  URI-controle is vervallen ([11.2](#112-de-uri-wordt-niet-vooraf-gecontroleerd)): die drie velden bestaan om te **tonen** wat
  de klant koos, niet om iets te controleren. Ze dragen de rij op de kaart, de
  afbeelding, en de naam in elke melding;
- faalt het afspelen, dan is de melding **"Het gekozen geluid bestaat niet meer"** met
  de opgeslagen `name` erin en niet een kale URI — dus juist die opgeslagen naam maakt
  het verschil tussen een leesbare melding en een regel machinetaal.

**Wat er NIET meer gebeurt:** eerdere versies lieten de noodrem de URI vóór het
afspelen controleren, met een zoekopdracht op de opgeslagen `name`. Die controle is in
fase 3c-bis vervallen omdat de opgeslagen naam voor een hele provider onvindbaar bleek
in MA's eigen zoekindex; zie [11.2](#112-de-uri-wordt-niet-vooraf-gecontroleerd). Een verouderde URI wordt daardoor **pas bij het
afspelen** opgemerkt.

### 8.2.1 Welke soorten getoetst zijn

| Soort | Status | Waar gemeten |
|---|---|---|
| `radio` | **zoeken én afspelen aangetoond** | fase 0b, SomaFM: `Beat Blender` → treffer, afgespeeld met echte FLAC-stream |
| `podcast` | **zoeken aangetoond** | fase 0b, iTunes Podcast Search; afspelen niet getoetst |
| `playlist` | zoeken via de bibliotheek aangetoond | fase 0b, `library://playlist/…` |
| `artist` | **zoeken aangetoond** | eigenaar, aug 2026 |
| `track` | **zoeken aangetoond** | eigenaar, aug 2026 |
| `album` | **zoeken aangetoond** | eigenaar, aug 2026 |
| `audiobook` | **niet getoetst** | geen provider die ze levert |

**GEMETEN door de eigenaar, augustus 2026**, op zijn eigen Home Assistant met een
gekoppelde Spotify-provider, via `music_assistant.search`. Deze getallen staan
niet in een faserapport; ze zijn hier vastgelegd zodat ze naspeurbaar zijn:

| Aanroep | Uitkomst |
|---|---|
| `media_type: [artist]`, `name: "Coldplay"` | **5 treffers**, elk met `name`, `uri`, `image` |
| `media_type: [track]`, `name: "Coldplay"` | **5 treffers**, elk met `name`, `uri`, `image`, plus genest `album` en `artists` inclusief afbeelding |
| `media_type: [album]`, `name: "Ghost Stories"` | **3 treffers**, elk met `name`, `uri`, `image`, plus genest `artists` |

Daarmee is de belofte van [sectie 8.1](#81-zoeken-via-music-assistant) — naam,
soort en afbeelding per treffer, en bij een nummer ook artiest en album — voor
zes van de zeven soorten gemeten in plaats van aangenomen. `audiobook` blijft
ongetoetst; er was geen provider die ze levert.

**Wat dezelfde meting óók liet zien, en wat elders doorwerkt:** bij
`"Ghost Stories"` kwamen **twee albums met dezelfde naam van verschillende
artiesten** terug. Een naam identificeert een item dus **niet** uniek.

Dat was oorspronkelijk het argument om de URI-controle niet op naam te laten leunen.
Fase 3c toonde dat het probleem een graad erger is: de opgeslagen naam is voor sommige
providers niet alleen niet-uniek maar **helemaal niet vindbaar**, en daarom is die
controle vervallen ([11.2](#112-de-uri-wordt-niet-vooraf-gecontroleerd)). De meting blijft hier staan omdat ze óók voor de
**editor** geldt: twee gelijknamige treffers betekent dat de klant iets moet kunnen
onderscheiden aan meer dan de naam, en dat is waarom `image` en `media_type` in de
zoekresultaten staan ([15.6](#156-domotiapp_alarmsoundsearch)).

### 8.3 Afspelen

`music_assistant.play_media` op de gekozen speaker, met `media_id` = de
opgeslagen `uri`.

**Radio en afspeellijst zijn de soorten die bij een wekker passen**, want die
hebben een onbepaalde duur. Een los nummer van drie minuten stopt van zichzelf en
dan is de wekker stil terwijl niemand wakker is.

#### 8.3.1 `radio_mode` wordt voorwaardelijk meegestuurd

`music_assistant.play_media` heeft een veld **`radio_mode`**
(`components/music_assistant/services.yaml:48-50`). Staat dat aan, dan speelt MA na
het gekozen item eindeloos door in dezelfde stijl, en is een los nummer wél een
bruikbare wekker.

**GEMETEN in fase 3a** (`docs/fase-3a/RAPPORT.md`, taak A1), en dit is de reden dat
het voorwaardelijk is en niet altijd:

Het veld is van begin tot eind doorverbonden — `services.py:141`,
`media_player.py:406` en `:556`, en de client op
`music_assistant_client/player_queues.py:209`. Maar **de server weigert het als
er geen provider is die vergelijkbare nummers kan aanleveren.** Dezelfde track,
twee keer afgespeeld op dezelfde speaker:

```
zonder radio_mode : HTTP 200, queue items=1
met    radio_mode : HTTP 500, queue items=0, state=idle
```

met als serverfout:

```
UnsupportedFeaturedException: No Music Provider found that supports requesting
similar tracks.
  music_assistant/controllers/player_queues.py:1484 in _handle_play_media
  music_assistant/controllers/player_queues.py:2773 in _get_radio_tracks
```

**Blind `radio_mode: true` meesturen is dus gevaarlijker dan het weglaten:** er
speelt dan *niets*. Een wekker die afgaat en na drie minuten stopt is hinderlijk;
een wekker die helemaal niet afgaat is stuk.

**De regel.** De integratie stuurt `radio_mode: true` mee **als en alleen als** de
provider van het gekozen geluid `SIMILAR_TRACKS` ondersteunt. In alle andere
gevallen wordt het veld **weggelaten** — niet op `false` gezet, maar weggelaten,
zodat MA zijn eigen standaard houdt.

**Hoe de integratie dat vaststelt.** De feature is opvraagbaar:

- `ProviderFeature.SIMILAR_TRACKS` (`music_assistant_models/enums.py:627`) is de
  feature waar het om gaat.
- De providerlijst van MA geeft per provider zijn `supported_features`. De provider
  van het gekozen geluid is af te leiden uit de opgeslagen `uri`: het deel vóór de
  `://` is het instantie-ID of het domein van de provider
  (`spotify--ZvzrFmgX://track/…`, `somafm://radio/…`).
- Providers die de feature hebben, uit hun eigen broncode: `spotify`, `tidal`,
  `apple_music`, `ytmusic`, `deezer`, `soundcloud`, `plex`, `jellyfin`, `emby`,
  `opensubsonic` en enkele andere — kortom de streamingproviders en de
  mediaservers. Geen van de gratis radio- en podcastproviders heeft hem.

**Hoe de integratie erbij komt.** Er is **geen HA-service** die de providerlijst van
Music Assistant blootgeeft — hetzelfde probleem dat de URI-controle van
[11.2](#112-de-uri-wordt-niet-vooraf-gecontroleerd) uiteindelijk fataal werd. Er zijn twee routes, en de tweede is
de vastgelegde:

| Route | Voordeel | Prijs |
|---|---|---|
| `entry.runtime_data.mass` van de MA-config-entry uitvragen | actueel en exact | de binnenkant van een andere integratie — **afgewezen**, zie [11.2.2](#1122-voorkeursoptie-zodra-ma-hem-publiceert) |
| **Een lijst providerdomeinen in onze eigen constanten**, afgeleid uit MA's broncode | alleen de opgeslagen `uri` nodig, geen afhankelijkheid van andermans binnenkant | de lijst kan verouderen als MA de feature aan een provider toevoegt of ontneemt |

**De vastgelegde route is de tweede:** een constante met de providerdomeinen die
`SIMILAR_TRACKS` ondersteunen, en de vergelijking op het deel vóór de `://` in de
opgeslagen `uri`. Dat is dezelfde constructie — en dezelfde prijs — als de
groep-constanten in DomotiApp Scene: het maakt ons onafhankelijk van de binnenkant
van een andere integratie, maar een wijziging bovenstrooms werkt **stil** door.

Het stille falen is hier echter goedaardig, en dat is de reden dat het aanvaardbaar
is:

- **Verdwijnt een provider uit de lijst** terwijl hij de feature nog heeft, dan
  wordt `radio_mode` niet meegestuurd en stopt het geluid na het item. Hinderlijk,
  niet stil.
- **Blijft een provider in de lijst** terwijl hij de feature verliest, dan geeft MA
  HTTP 500 en gaat de wekker **niet** af. Dat is het ergste geval, en het wordt
  opgevangen doordat de melding uit
  [11.7](#117-waar-de-melding-verschijnt-en-hoe-de-klant-hem-wegkrijgt) de klant
  vertelt dat de wekker niet is afgegaan. **Fase 3b moet die fout dus expliciet
  afvangen** en er niet op vertrouwen dat de lijst klopt.

De lijst hoort bij de openstaande punten in `CLAUDE.md`: hij moet worden nagelopen
bij een MA-release, net als de tweede laadroute.

**Faalt de controle zelf, dan géén `radio_mode`.** Kan de integratie niet
vaststellen of de provider de feature heeft — geen providerlijst beschikbaar, een
onbekend URI-schema, een fout of een time-out — dan wordt `radio_mode`
**weggelaten**.

Dat was bewust de omgekeerde keuze van de vervallen URI-controle, waar een mislukte
controle de wekker juist liet doorgaan ([11.2.1](#1121-vervallen--de-omkering-bestond-alleen-voor-de-controle)).
Sinds die controle weg is, is dit de **enige** plek in het product waar twijfel tot
weglaten leidt. Het verschil zit in wat de twijfel kost:

| | Bij twijfel meesturen | Bij twijfel weglaten |
|---|---|---|
| Provider kan het wél | eindeloos doorspelen | geluid stopt na het item — hinderlijk |
| Provider kan het **niet** | **HTTP 500, geen geluid** | geluid stopt na het item — hinderlijk |

De rechterkolom heeft geen enkel geval waarin er niets klinkt. Dat is de reden.

**De waarschuwing uit [8.3](#83-afspelen) blijft staan**, en geldt voor precies de
gevallen waarin `radio_mode` **niet** meegestuurd wordt: een geluid met een eindige
duur (`track`, `podcast`, `audiobook`, en ook `artist` of `album`) waarvan de
provider `SIMILAR_TRACKS` niet ondersteunt of waarvan dat niet vast te stellen is.
De editor **waarschuwt** dan, niet blokkerend:

> **Dit geluid stopt van zichzelf.** Een los nummer is na een paar minuten
> voorbij; daarna is het stil. Kies een afspeellijst of een radiostation als de
> wekker moet blijven spelen tot je hem uitzet.

Kan het wél, dan blijft de waarschuwing weg en stopt de wekker alleen door de
gebruiker of door de 30-minutentimer
([9.4](#94-de-wekker-stopt-na-30-minuten)).

**Hoe de editor dat weet: `sound/search` zegt het** — het veld `endless` per
treffer, [15.6](#156-domotiapp_alarmsoundsearch). **Toegevoegd in fase 4c**, en
het lost een gat op dat de waarschuwing onbetrouwbaar maakte: de kaart kan de
providerlijst niet raadplegen zonder hem te dupliceren, dus waarschuwde ze op de
**soort** alleen. Een los nummer van een streamingprovider kreeg dan een
waarschuwing dat het geluid van zichzelf stopt, terwijl `radio_mode` het juist
eindeloos maakt.

Dat is erger dan het klinkt. Een waarschuwing die soms onwaar is, is een
waarschuwing die mensen leren negeren — en dan werkt hij ook niet meer in de
gevallen waarvoor hij bedoeld is. De regel die daaruit volgt en breder geldt:
**laat de kant die het antwoord heeft het antwoord geven**, ook als dat een veld
in een bestaand commando kost.

---

## 9. Afgaan

### 9.1 De volgorde

Op de wektijd, in deze volgorde:

1. **Noodrem vooraf** ([sectie 11.1](#111-vóór-het-afspelen-available)) — is de
   speaker beschikbaar, en is de URI geldig?
2. **Volume op 0** zetten op de speaker.
3. **Wake-up light aan**, als die is ingesteld ([sectie 12](#12-de-wake-up-light)).
4. **Shuffle aanzetten**, als het geluid uit meerdere nummers bestaat
   ([9.6](#96-shuffle-bij-media-met-meerdere-nummers)).
5. **Geluid starten** via `music_assistant.play_media`.
6. **Volume-oploop** starten: van 0 naar het ingestelde niveau in 20 seconden.
7. **Noodrem achteraf** ([sectie 11.3](#113-een-paar-seconden-ná-het-starten)) —
   een paar seconden later opnieuw controleren.
8. **Stoptimer** van 30 minuten zetten.

Stap 2 vóór stap 5 is essentieel: start je het geluid op het oude volume en zet
je het daarna op 0, dan is er één harde uitbarsting voordat de oploop begint.

Stap 4 vóór stap 5 heeft dezelfde vorm en dezelfde reden: wat de queue bepaalt
moet er zijn vóórdat de queue bestaat. Zie [9.6](#96-shuffle-bij-media-met-meerdere-nummers).

**Transition-loos** — er is geen fade-in van het geluid zelf, alleen de
volume-oploop. MA's eigen `fade_in` is niet aanroepbaar; zie
[9.3](#93-de-volume-oploop).

### 9.2 Meerdere wekkers op hetzelfde moment

Elke wekker is onafhankelijk en heeft zijn eigen speaker, geluid, volume-oploop
en stoptimer. Twee wekkers op dezelfde speaker op dezelfde tijd is een
gebruikersfout die het product niet hoeft op te lossen; **VOORSTEL** is dat de
tweede de eerste overschrijft omdat MA één queue per player heeft, en dat er op
`WARNING` gelogd wordt.

### 9.3 De volume-oploop

**Van stil naar het ingestelde niveau in 20 seconden.**

**GEMETEN** in fase 0b: MA's eigen `fade_in` is **niet aanroepbaar** — het is een
boolean op `play_index`/`resume` (`music_assistant_client/player_queues.py:101,
193`) en de HA-integratie roept het **nergens** aan. De oploop moet dus met
herhaalde `media_player.volume_set`.

Dat dat werkt is gemeten: 20 aanroepen van elk 3–6 ms, totaal 20,004 s,
eindvolume exact.

De volumeresolutie is **1 %** over de hele schaal. **GEMETEN door de eigenaar,
augustus 2026**, op een Sonos, en exact gehonoreerd: `0.31` → `0.31`,
`0.32` → `0.32`, `0.33` → `0.33`. Andere merken zijn niet getoetst; dat is een
aanvaard risico en staat als beperking in
[sectie 20.1](#201-bekende-beperkingen).

**De oploop gaat PER SPEAKER**, nooit op een groep. Zie
[sectie 7.3](#73-groepen-worden-uitgesloten).

**Aantal stappen: 20, één per seconde.** Vastgelegd.

Dit is **niet gemeten als "vloeiend"** en dat blijft zo: fase 0b kon de cadans
niet halen doordat Chrome `setTimeout` in een achtergrondtabblad afknijpt, en er
zat geen oor bij de speaker.

**Het is één constante in de implementatie**, en dat is met opzet: klinkt de
oploop trapsgewijs, dan wordt die constante verhoogd en verandert er niets anders.
De techniek laat **100 stappen** toe — de volumeresolutie is 1 % en de
aanroepkosten zijn 3–6 ms per stap — dus de bovengrens wordt door het gehoor
bepaald en niet door Music Assistant.

**Buiten bereik wordt stil afgekapt.** Gemeten: `-5` → 0, `150` → 100, `33.7` →
33 (afkappen, niet afronden), alles met HTTP 200. Een rekenfout in de oploop
geeft dus **geen exceptie**, alleen een verkeerd volume. De implementatie
clampt daarom zelf en logt als er geclampt moest worden.

**De oploop stopt** zodra de wekker gestopt wordt, en ook als de gebruiker zelf
aan het volume draait: **VOORSTEL** is dat de oploop afbreekt wanneer het
gelezen volume meer dan 5 procentpunt afwijkt van wat de oploop zelf net heeft
gezet. Zonder die regel vecht de integratie met de gebruiker.

### 9.4 De wekker stopt na 30 minuten

De wekker stopt **niet vanzelf**, met één uitzondering: **na 30 minuten stopt hij
automatisch**. Dat voorkomt dat de muziek dagenlang doorspeelt in een lege
woning.

Stoppen is: geluid stoppen op de speaker, oploop afbreken, volume terugzetten
([9.5](#95-het-volume-wordt-teruggezet)). De **wake-up light blijft aan** —
[sectie 12](#12-de-wake-up-light).

Er is **geen snooze** in v1.

### 9.5 Het volume wordt teruggezet

Na het stoppen — door de gebruiker of door de 30-minutentimer — wordt het volume
van de speaker teruggezet naar wat het vóór de wekker was.

**VOORSTEL**, en het waarom: zonder dit staat de speaker de rest van de dag op
het wekvolume, en dat is een bijwerking die de klant niet heeft gevraagd.

Het volume wordt gelezen **vóór** stap 2 van [9.1](#91-de-volgorde). Lukt dat
niet — de speaker is onbereikbaar en dan is `volume_level` er niet, want state
attributes verdwijnen bij `unavailable` — dan wordt er **niets** teruggezet en
wordt dat op `DEBUG` gelogd. Nooit een verzonnen waarde terugzetten.

Sinds fase 6b geldt hetzelfde voor **shuffle**; zie
[9.6](#96-shuffle-bij-media-met-meerdere-nummers).

### 9.6 Shuffle bij media met meerdere nummers

**Shuffle staat altijd aan wanneer het gekozen geluid uit meerdere nummers
bestaat.** Er is geen instelling voor en geen veld in de opslag: het is gedrag,
net als de volume-oploop.

| `media_type` | meerdere nummers | shuffle |
|---|---|---|
| `playlist`, `album`, `artist` | ja | **aan** |
| `radio` | nee — één doorlopende stream | uit |
| `track`, `podcast`, `audiobook` | nee — één item | uit |

Bij een onbekende of ontbrekende soort: **niet** shuffelen.

**Waarom dit er is.** Een wekker met een afspeellijst begon elke ochtend met
hetzelfde nummer. Voor een wekker verliest dat zijn werking: het geluid dat je
moet wekken wordt het geluid dat je niet meer hoort. Gevonden in productie op
1.0.0.

**Waarom het vóór het afspelen gebeurt, en niet erna.** **GEMETEN** in de
broncode van Music Assistant 2.9.11 (`controllers/player_queues.py:1533`):

```python
shuffle = queue.shuffle_enabled and len(queue_items) > 1 and not radio_mode
```

MA past shuffle toe **op het moment dat de queue geladen wordt**, op basis van
`shuffle_enabled` zoals dat dán staat. Een `shuffle_set` ná `play_media` schudt
alleen de nummers ná het eerste — de wekker begint dan nog steeds elke ochtend
hetzelfde. Daarom staat het als stap 4 in [9.1](#91-de-volgorde).

**Hoe.** `media_player.shuffle_set` op de speaker.
`music_assistant.play_media` heeft geen shuffle-veld.

**Wat er gebeurt als die aanroep faalt:** niets bijzonders. Er wordt op `WARNING`
gelogd en de wekker gaat gewoon door. Shuffle is een verbetering van de wekker en
niet de wekker zelf; het faalgeval is "hij begon bij nummer 1", en dat is precies
de toestand van vóór deze regel. Een noodrem die een stille ochtend kan
veroorzaken zou hier niet in verhouding staan
([11.5](#115-volledige-zekerheid-bestaat-niet)).

**Het voorbeeld schudt mee** ([5.4](#54-de-voorbeeldknop)). Een voorbeeld dat
altijd met nummer 1 begint terwijl de wekker schudt, laat iets anders horen dan
wat er 's ochtends gebeurt.

**Shuffle wordt bij het stoppen teruggezet**, met precies dezelfde drie regels als
het volume in [9.5](#95-het-volume-wordt-teruggezet):

1. de stand wordt **gelezen vóór** hij gezet wordt — erna lees je je eigen waarde
   terug, en dan zet het stoppen de shuffle van iedereen aan;
2. was hij **niet te lezen**, dan wordt er **niets** teruggezet. Een speaker die
   geen `shuffle`-attribuut meldt is niet hetzelfde als een speaker waarvan shuffle
   uit staat, en `false` terugzetten zou een keuze maken die we niet kennen. Dit is
   [7.2](#72-vaststellen-dát-het-een-ma-speaker-is)'s valkuil: extra state
   attributes verdwijnen zodra een entiteit `unavailable` is, dus juist op het
   moment dat je de stand zou willen kennen is hij weg;
3. hebben we shuffle **niet aangezet** (radio, een los nummer), dan zetten we ook
   niets terug. De stand van de speaker is dan die van de klant — en had hij hem
   tijdens de wekker zelf omgezet, dan zou terugzetten zíjn wijziging ongedaan
   maken.

Het terugzetten gebeurt **ná** `media_stop`, net als het volume. Dat botst niet met
de regel dat shuffle vóór `play_media` moet: die gaat over het **laden** van een
queue, en er wordt op dat moment geen queue geladen.

*Terugzetten toegevoegd in fase 6b. De motivatie is letterlijk die van 9.5: geen
bijwerking die de klant niet vroeg.*

**Twee dingen die MA zelf al goed doet**, en die de integratie dus niet hoeft na
te bouwen: een queue met één item wordt nooit geschud (`len(queue_items) > 1`),
en een radio-queue laat MA met opzet ongeschud (`not radio_mode`). De tabel
hierboven is daarmee een verfijning en geen noodzaak — hij bestaat zodat er niet
onnodig een service wordt aangeroepen en zodat de bedoeling leesbaar is.

---

## 10. Hoe de wekker gestopt wordt

Zie [sectie 4](#4-de-kaart-terwijl-een-wekker-afgaat) voor de vorm. Technisch:

- De kaart roept [`alarms/stop`](#158-domotiapp_alarmalarmsstop) aan.
- Dat commando is beschikbaar voor **iedere ingelogde gebruiker**
  ([sectie 17](#17-rechten)) — een klant op een wandtablet is geen admin en moet
  zijn wekker kunnen uitzetten.
- Stoppen is **idempotent**: twee keer stoppen is geen fout. Een wandtablet en
  een telefoon kunnen tegelijk drukken.
- Stopt niemand, dan stopt de 30-minutentimer hem
  ([9.4](#94-de-wekker-stopt-na-30-minuten)).

**Buiten de kaart om stoppen** kan ook, en dat is met opzet niet geblokkeerd: wie
in de MA-app of via `media_player.media_stop` de speaker stilzet, heeft de muziek
gestopt. De integratie merkt dat **niet** en blijft denken dat de wekker loopt
tot de 30 minuten om zijn. Gevolg: het volume wordt pas dan teruggezet, en de
kaart blijft tot dat moment een stopknop. Dat is een **bekende beperking**;
oplossen zou vragen dat de integratie de speaker gaat pollen, en
`playback_state` is daar aantoonbaar niet betrouwbaar genoeg voor
([sectie 11.4](#114-playback_state-is-nooit-bewijs)).

---

## 11. De noodrem

De rode draad: **een wekker die niet afgaat moet luider falen dan een wekker die
afgaat.** Dit is de sectie die het bestaansrecht van het product beschermt.

### 11.1 Vóór het afspelen: `available`

Controleer dat de speaker **niet `unavailable`** is:

```python
state = hass.states.get(speaker_entity_id)
if state is None or state.state == "unavailable":
    ...falen...
```

**GEMETEN** in fase 0b: dit dekt **twee** storingen in één controle. MA's
`available` is `self.player.available and bool(self.mass.connection.connected)`
(`components/music_assistant/entity.py:72-74`), dus zowel een dode speaker als
een dode MA-server komt hier uit.

**Waarom dit niet aan HA's service-dispatch overgelaten mag worden:** HA filtert
onbeschikbare entiteiten weg vóórdat de integratie ze ziet
(`helpers/service.py`), **zonder exceptie**. Bij targeting op `entity_id` komt er
nog één `WARNING` in het log; bij targeting op een **label** komt er
**helemaal geen** logregel (`helpers/target.py:136-155`). Gemeten in fase 0:
label-targeting met één offline speaker gaf nul waarschuwingen. Een wekker die op
die manier faalt, faalt volkomen stil.

### 11.2 De URI wordt NIET vooraf gecontroleerd

**Vastgelegd in fase 3c-bis, en dit is een ontwerpcorrectie.** Eerdere versies van deze
sectie schreven een controle vóór het afspelen voor: een zoekopdracht op de opgeslagen
`name`, met de vergelijking op de `uri`. **Die controle vervalt.** Er is geen
voorafgaande controle op het geluid meer.

#### Waarom hij vervalt

De controle sloeg vals alarm, en niet bij uitzondering maar als normale uitkomst voor
een hele provider. **GEMETEN in fase 3c, taak I** (`docs/fase-3c/RAPPORT.md`, sectie
"BEVINDING"; herhaald in `RAPPORT-BIS.md`): de eerste wekker die op de dev-instance werd
gezet, op een SomaFM-kanaal, ging niet af:

```
23:23:00.245 WARNING [afvuren] Wekker 4a852fe9… gaat NIET af:
             het geluid 'somafm://radio/beatblender' bestaat niet meer
```

Het geluid bestond wél. Twee minuten eerder was het via
[15.6](#156-domotiapp_alarmsoundsearch) gevonden en opgeslagen. De meting:

| Zoekopdracht | Treffers | Bevat `somafm://radio/beatblender` |
|---|---|---|
| `"SomaFM: Beat Blender"` ← **de opgeslagen `name`** | **0** | **nee** |
| `"Beat Blender"` | 3 | ja |
| `"beatblender"` | 0 | nee |

**De naam die Music Assistant teruggeeft is een naam die Music Assistant zelf niet kan
vinden.** De weergavenaam draagt een providerprefix (`SomaFM: `) die niet in de
zoekindex zit. De voorgeschreven route was daarmee **zelf-verslaand**: hij kon per
definitie zijn eigen opgeslagen geluid niet terugvinden, omdat
[8.2](#82-sla-de-uri-op-niet-de-naam) voorschrijft dat de opgeslagen naam de naam is
die MA teruggaf.

Het is providerspecifiek, en dat maakt het erger in plaats van beter. Elke treffer
opnieuw op zijn eigen naam gezocht:

| Provider | Voorbeeldnaam | Zelf-vindbaar |
|---|---|---|
| `somafm://` | `SomaFM: Beat Blender` | **nee** |
| `radiobrowser://` | `SomaFM Beat Blender (128k AAC)` | ja |
| iTunes-podcasts | `Radiolab` | ja |

Juist de provider die zonder account betrouwbaar werkt is de provider die faalt. De
zelf-vindbare radioprovider is RadioBrowser, en die is **wisselvallig** (fase 0b: 1 van
6 zoekopdrachten lukte).

De vorige versie van deze sectie noemde het valse negatief al **"het ergste
faalgeval"**, want het maakt van een werkende wekker een stille. Het stond er als
risico. Het bleek de normale uitkomst.

#### Wat het faalgeval nu is, en waarom dat beter is

**Een controle die vals alarm slaat is erger dan geen controle.** Het faalgeval
verschuift:

| | met de controle | zonder de controle |
|---|---|---|
| URI is dood | wekker gaat **niet** af, melding `sound_gone` | wekker gaat af, geen geluid, melding via [11.3](#113-een-paar-seconden-ná-het-starten) |
| URI leeft, naam niet vindbaar | **wekker gaat niet af** — vals alarm | wekker gaat af en klinkt |
| URI leeft, naam vindbaar | wekker gaat af en klinkt | wekker gaat af en klinkt |

De middelste rij is de reden. De bovenste rij is de prijs, en die is aanvaardbaar: van
*"de wekker ging niet af"* naar *"de wekker ging af maar was stil"*, en dat tweede wordt
**wel** opgemerkt — door de controle van [11.3](#113-een-paar-seconden-ná-het-starten),
met de melding `speaker_lost_during_play` erbij. De klant weet 's ochtends nog steeds
waarom hij zich heeft verslapen.

#### Dit is geen versoepeling van de noodrem

**De noodrem blijft in beide richtingen onaangeroerd:**

- **[11.1](#111-vóór-het-afspelen-available) blijft** — de speaker moet beschikbaar
  zijn vóór het afspelen. Die controle stelt iets vast over de **kans op geluid** en
  faalt niet vals: `available` is `False` of hij is dat niet.
- **[11.3](#113-een-paar-seconden-ná-het-starten) blijft** — vijf seconden na het
  starten wordt opnieuw gecontroleerd. Deze controle wordt door het vervallen van 11.2
  **belangrijker**, want hij is nu het enige net onder een dood geluid.
- **[11.4](#114-playback_state-is-nooit-bewijs) blijft** — `playback_state` is nooit
  bewijs.
- **[11.6](#116-bij-falen) blijft** — faalt een controle, dan gaat de wekker niet af, er
  komt geen verzonnen alternatief, en er komt een melding.

Wat wegvalt is precies één ding: een **hulpaanroep** die iets probeerde vast te stellen
over een derde partij, en die daarbij aantoonbaar vaker ongelijk had dan gelijk. Het
verschil met 11.1 is dat 11.1 een eigenschap van de speaker leest en 11.2 een
zoekindex ondervroeg die de vraag niet kon beantwoorden.

#### Wat er met een dood geluid gebeurt

`music_assistant.play_media` wordt blokkerend aangeroepen
([8.3](#83-afspelen)). Faalt die aanroep, dan gaat de wekker **niet** af en volgt de
melding uit [11.6](#116-bij-falen) — dus een dood geluid dat MA met een fout afwijst
wordt nog steeds opgemerkt, alleen nu op het moment van afspelen in plaats van ervoor.
Levert de aanroep géén fout op terwijl er niets speelt, dan is
[11.3](#113-een-paar-seconden-ná-het-starten) het net.

**GEMETEN in fase 0b, en dit is waarom 11.3 nu draagt wat 11.2 droeg:** MA op schema 31
valideert de URI zelf **niet** vóór het afspelen — `verify_item_uri` bestaat pas vanaf
schema 33, en op 31 wordt een URI die `://` bevat direct geaccepteerd
(`components/music_assistant/media_player.py:494-498`). Er is dus geen garantie dat een
dood geluid een fout oplevert. Zie [20.1](#201-bekende-beperkingen), punt 8.

#### 11.2.1 VERVALLEN — de omkering bestond alleen voor de controle

Deze subsectie schreef voor dat een **mislukte** URI-controle de wekker juist wél liet
doorgaan: een trage zoekopdracht is geen reden om iemand niet te wekken. Dat was de
enige plek in [sectie 11](#11-de-noodrem) waar twijfel de andere kant op viel, en de
tekst waarschuwde uitdrukkelijk dat de twee gevallen — *"de URI bestaat niet"* tegen
*"de controle kon niet worden uitgevoerd"* — in code op elkaar lijken.

**Met het vervallen van de controle in [11.2](#112-de-uri-wordt-niet-vooraf-gecontroleerd)
vervalt de omkering.** Er is geen controle die kan mislukken, dus er is geen
onderscheid meer te maken en geen uitzondering meer nodig. De code hoeft dat verschil
niet langer te dragen — en dat is winst, want het was het subtielste onderscheid in het
hele product.

**Wat er van de gedachte overblijft**, en dat is de reden dat deze subsectie niet
zomaar geschrapt is maar hier staat: de afweging zelf blijft geldig en komt op één plek
terug. Bij [8.3.1](#831-radio_mode-wordt-voorwaardelijk-meegestuurd) valt twijfel de
**andere** kant op dan hier: `radio_mode` wordt bij twijfel **weggelaten**, want daar
kost twijfel een wekker die *zeker* niets speelt (HTTP 500, lege queue) in plaats van
een wekker die *misschien* niets speelt. Wie die sectie leest en zich afvraagt waarom de
keuze daar omgekeerd is dan hij hier ooit was: dit is het antwoord, en het is dezelfde
afweging op andere feiten.

#### 11.2.2 Voorkeursoptie zodra MA hem publiceert

**Zodra Music Assistant een URI-controle via een gepubliceerde service beschikbaar
stelt, komt een voorafgaande controle terug — en dan is dat de enige route.** Dit is
geen "misschien ooit": de controle bestaat al aan de MA-kant en is in fase 3a gemeten.
Alleen de service ontbreekt.

**Het overstapcriterium is veranderd, en dat is de kern van deze subsectie.** Tot fase
3c-bis luidde het: *de directe controle is beter dan de zoekroute, dus stap over zodra
hij te bereiken is.* Er was toen een werkende tweede keus. Nu niet meer:

| | vóór 3c-bis | vanaf 3c-bis |
|---|---|---|
| zoekroute | de vastgelegde route | **vervallen**, aantoonbaar zelf-verslaand |
| `music/item_by_uri` | betere alternatief | **de enige mogelijke route** |
| als geen van beide kan | — | **geen voorafgaande controle**, dat is de huidige toestand |

Er is dus geen terugvaloptie meer. Een voorafgaande controle op het geluid komt terug
óf niet, en tot die tijd draagt [11.3](#113-een-paar-seconden-ná-het-starten) het geval
alleen.

Wat er is, met vindplaats:

| Aanroep | Vindplaats | Schema | Uitkomst |
|---|---|---|---|
| `music/verify_item_uri` | `music_assistant_client/music.py:721-739` | **≥ 33** | `bool`; op schema 31 `HTTP 400 Invalid Command` |
| `music/item_by_uri` | `music_assistant_client/music.py:714-719` | geen eis | het media-item, of een exceptie |

`music/item_by_uri` geeft **drie** uitkomsten, en die drie zijn precies wat een
bruikbare controle nodig heeft — inclusief het her-gekoppelde-provider-geval uit
[8.2](#82-sla-de-uri-op-niet-de-naam):

| Uitkomst | Betekenis | Gedrag |
|---|---|---|
| het item komt terug | de URI bestaat | wekker gaat af |
| `MediaNotFoundError` | de URI bestaat **niet** | wekker gaat **niet** af, melding `sound_gone` |
| `ProviderUnavailableError` | de **provider** is er niet | dat de provider weg is bewijst niet dat het nummer weg is → wekker gaat **wél** af |

**Waarom dit het probleem van 11.2 niet heeft:** deze route vraagt naar de URI en niet
naar de naam. Er is geen zoekindex bij betrokken, dus er is geen providerprefix die niet
gevonden wordt. Het faalgeval dat de zoekroute onbruikbaar maakte, kan hier per
constructie niet optreden.

**Waarom hij nog niet gebruikt wordt:** hij is alleen te bereiken via
`entry.runtime_data.mass`, de **binnenkant** van de `music_assistant`-integratie. Dat is
precies het soort afhankelijkheid dat bij een update van die integratie stilletjes
breekt, en dit product mag niet stil breken. Die afweging staat nog steeds — maar de
weegschaal is wel gekanteld: het alternatief is nu *geen* controle in plaats van *een
andere* controle. Als de eigenaar de directe route alsnog wil, is dat een verdedigbare
keuze en geen ongelukje; het vraagt dan wel een expliciete afspraak over wat er gebeurt
als `runtime_data.mass` er niet is (behandelen als `ProviderUnavailableError`: wekker
gaat af).

**Het criterium om over te stappen** blijft: Music Assistant stelt de controle
beschikbaar als **service** in `components/music_assistant/services.yaml`, naast de zes
die er nu zijn (`play_media`, `play_announcement`, `transfer_queue`, `get_queue`,
`search`, `get_library`). Iemand moet dit blijven volgen; het is dezelfde soort
openstaande post als de tweede laadroute uit [sectie 2](#2-architectuur-in-één-beeld).

### 11.3 Een paar seconden ná het starten

**Opnieuw** controleren dat de speaker niet `unavailable` is. Dat vangt de
speaker die tijdens het starten wegvalt — het geval waarin de aanroep slaagde en
er tóch geen geluid is.

**VOORSTEL: 5 seconden ná stap 5** van [9.1](#91-de-volgorde). Lang genoeg dat
MA de stream heeft opgezet, kort genoeg dat de klant nog niet is doorgeslapen.

**Sinds fase 3c-bis draagt deze controle meer dan hij deed.** Met het vervallen van de
voorafgaande URI-controle ([11.2](%s)) is dit het **enige** net onder een geluid dat niet
meer bestaat: levert `play_media` geen fout op terwijl er niets speelt, dan is dit de
plek waar dat boven komt. Wie deze controle ooit wil weghalen of verlengen, haalt daarmee
dus meer weg dan alleen een tweede blik op de speaker.

### 11.4 `playback_state` is nooit bewijs

**Vastgelegde regel: gebruik `playback_state` of `"playing"` NOOIT als bewijs dat
de wekker geluid maakt.**

**GEMETEN** in fase 0b, en het is de belangrijkste bevinding van die ronde: nadat
het afspeelproces van een spelende speaker was gedood, meldde MA nog steeds
`playback_state: "playing"` met een **doorlopende** `elapsed_time` (220,3 s),
terwijl `available` op `false` stond. De queue weet niet of er iemand luistert.

De eigenaar heeft op zijn eigen HA bevestigd dat HA dit **maskeert** door de
entiteit op `unavailable` te zetten, waardoor de kaart de misleidende toestand
niet te zien krijgt. **De regel blijft desondanks staan:** `available` is het
signaal, `playing` niet. Twee redenen om dat niet te versoepelen: de maskering is
gedrag van HA en niet van ons, en `playing` is ook zonder die maskering geen
bewijs van geluid.

### 11.5 Volledige zekerheid bestaat niet

**Expliciet vastgelegd:** geen enkele controle in deze sectie bewijst dat er
geluid uit de speaker komt.

- Een speaker op **volume nul** meldt netjes dat hij speelt.
- Een speaker met de **versterker uit** meldt netjes dat hij speelt.
- Een speaker die **gedempt** is meldt netjes dat hij speelt.
- En omdat een MA-speaker geen `TURN_ON` heeft
  ([sectie 7.2](#72-vaststellen-dát-het-een-ma-speaker-is)), kan de integratie
  daar niets aan doen.

Dit is een grens van het systeem, niet een tekortkoming van het ontwerp. Het is
wel de reden dat de klantdocumentatie moet zeggen: **laat de wake-up light
meelopen als je een enkele storing wil overleven.**

### 11.6 Bij falen

Faalt een van de controles, dan:

1. **De wekker gaat niet af**, en dat is een gebeurtenis en geen stilte.
2. **Geen automatische wake-up light** als die niet was ingesteld. Vastgelegd:
   het product verzint geen alternatief dat de klant niet heeft gekozen. Was er
   wél een wake-up light ingesteld, dan gaat die **wel** aan — die had ook aan
   moeten gaan als het geluid het had gedaan.
3. **Een melding aan de klant** die uitlegt waarom de wekker niet is afgegaan.

### 11.7 Waar de melding verschijnt en hoe de klant hem wegkrijgt

**VOORSTEL** voor de twee kanalen, en beide zijn nodig omdat ze verschillende
mensen bereiken.

**Er zijn twee soorten meldingen**, en ze zien er verschillend uit. Dat verschil
is vastgelegd, niet cosmetisch: een fout vraagt een handeling, een mededeling
niet.

| Soort | `severity` | Toon | Kleur |
|---|---|---|---|
| **Fout** — de wekker is niet afgegaan door een storing | `"error"` | *"is niet afgegaan"*, met wat de klant eraan kan doen | foutkleur (`--error-color`) |
| **Mededeling** — de wekker is niet afgegaan door iets normaals | `"notice"` | *"is niet afgegaan omdat…"*, feitelijk, zonder oproep tot actie | `--secondary-text-color`, met een informatie-icoon |

**a) Op de kaart.** De rij van de betreffende wekker krijgt de melding, met een
**"Begrepen"**-knop die hem wegneemt. De kaart is waar de klant 's ochtends kijkt.

Die knop roept
[`alarms/clear_message`](#1510-domotiapp_alarmalarmsclear_message) aan en wist het
veld in de **opslag**. Lokaal verbergen is niet genoeg en dat volgt uit deze
sectie zelf: de melding staat in de opslag zodat hij een herstart overleeft en op
elk scherm zichtbaar is, dus wegklikken moet op dezelfde plek gebeuren. Anders
blijft hij staan op het wandtablet en komt hij terug na een herlaadbeurt.

Teksten bij `severity: "error"`:

| `kind` | Tekst op de kaart |
|---|---|
| `speaker_unavailable` | **"De wekker van 06:45 is niet afgegaan: de speaker 'Slaapkamer' was niet bereikbaar."** |
| `ma_unavailable` | **"De wekker van 06:45 is niet afgegaan: Music Assistant was niet bereikbaar."** |
| `sound_gone` | **"De wekker van 06:45 is niet afgegaan: het geluid 'Beat Blender' kon niet gestart worden. Music Assistant meldde: "No playable items found". Controleer het geluid in Music Assistant, of kies een ander."** — het middelste deel staat er alleen als MA een reden meegaf; zie hieronder |
| `speaker_lost_during_play` | **"De wekker van 06:45 is mogelijk niet hoorbaar geweest: de speaker 'Slaapkamer' viel weg tijdens het spelen."** |
| `light_failed` | **"De wekker is afgegaan, maar de lamp 'Bedlamp' kon niet aangezet worden."** |
| `volume_ramp_unavailable` | **"De wekker is afgegaan, maar het volume was op deze speaker niet in te stellen; het oplopende volume is overgeslagen."** |

Teksten bij `severity: "notice"`:

| `kind` | Tekst op de kaart |
|---|---|
| `skipped_grace_window` | **"Je wekker van 06:45 is niet afgegaan; Home Assistant heeft dat moment gemist."** |

De eerste is de tekst die de eigenaar heeft vastgelegd, en de reden dat deze hele
categorie bestaat: dat is precies wat iemand wil weten die zich heeft
verslapen. Het is geen storing en het moet er ook niet als een storing uitzien.

**Een melding zegt alleen wat er is vastgesteld.** Dat is een regel over álle
teksten hierboven en niet alleen over `sound_gone`. Een melding die de oorzaak
verzint stuurt de klant — of de eigenaar — de verkeerde kant op, en dat kost meer
tijd dan geen melding.

De tekst bij `sound_gone` is in fase 6 om die reden herschreven. Hij luidde *"het
gekozen geluid 'X' bestaat niet meer. Kies een nieuw geluid."*, en in productie
op 1.0.0 bestond het geluid gewoon: Spotify was in Music Assistant niet
geautoriseerd en gaf `"No playable items found"`. Wat de integratie op dat punt
weet, is dat `play_media` heeft geweigerd — meer niet. De naam `sound_gone`
blijft ongewijzigd, want die staat in de opslag van elke klant die 1.0.0 draaide
en de kaart vergelijkt erop ([14.2.1](#142-het-schema)); alleen de tekst is
veranderd.

**De reden van Music Assistant gaat mee als die er is.** Ontbreekt hij, dan
vervalt dat deel van de zin — geen leeg citaat en geen verzonnen oorzaak. Van de
teruggegeven fout wordt alleen de **eerste regel** gebruikt: MA zet de mededeling
daar, en wat erna komt is context voor een log en niet voor een kaart.

**In fase 6b zijn er nog twee herschreven**, en beide om dezelfde reden. Ze stonden
als openstaand punt genoteerd omdat de woordkeuze aan de eigenaar was; hij ging
akkoord met de voorstellen uit `docs/fase-6/RAPPORT.md`.

`volume_ramp_unavailable` zei *"De wekker is afgegaan **op het ingestelde
volume**"*. Deze melding ontstaat doordat `volume_set(0)` weigerde; daarna doet de
integratie één poging tot het ingestelde niveau — **met dezelfde service die net
weigerde** — en die uitkomst wordt niet gelezen. Wat de speaker werkelijk doet is
spelen op de stand van gisteravond, en die kan net zo goed onhoorbaar zijn als
oorverdovend. Wat vaststaat is dat het volume niet in te stellen was en dat de
oploop daardoor vervalt.

`skipped_grace_window` zei *"**omdat Home Assistant uit stond**"*. Wat de
inhaalslag vaststelt is smaller: dit moment is verstreken, er staat geen
`last_fired` op, en het ligt verder dan het respijtvenster terug. Een narekenbaar
tegenvoorbeeld waarin de oude tekst onwaar was:

> Iemand maakt om 12:00 een wekker voor 06:45 vandaag. Home Assistant draait de
> hele dag door. Bij de eerstvolgende herstart vindt de inhaalslag een verstreken
> 06:45 zonder `last_fired`, en meldt dat Home Assistant uit stond.

De **soort** klopte in beide gevallen; alleen de oorzaak was gegist. Dat is het
patroon: elke tekst die het waaróm invult in plaats van het wát, is een kandidaat.

**b) Een `persistent_notification`.** Die verschijnt in HA's eigen meldingenlijst
en overleeft dat niemand de kaart opent. De klant krijgt hem weg met HA's eigen
kruisje.

**VOORSTEL:** alleen bij `severity: "error"`. Een mededeling op de kaart is
genoeg; een `persistent_notification` bij elke overgeslagen wekker zou de
meldingenlijst vullen met dingen waar niets aan te doen is, en dan leest niemand
hem meer.

Waarom geen repair issue: repair issues zijn admin-only
(`components/repairs`), en de klant is geen admin
([sectie 17](#17-rechten)). Een melding die alleen de eigenaar ziet, bereikt de
persoon die zich verslaapt niet.

**De melding wordt vastgelegd in de opslag**, per wekker, zodat hij een herstart
overleeft en de kaart hem kan tonen ook als de browser pas uren later opengaat.
Zie het veld `last_message` in [sectie 14.2](#142-het-schema).

---

## 12. De wake-up light

- **Optioneel.** Een wekker zonder wake-up light is geldig.
- De klant kiest **één lamp** uit de entiteiten met label `Verlichting Wekker`,
  en **één helderheid** in procenten.
- De lamp gaat aan **OP de wektijd**, niet ervoor. **Geen opbouw** — geen
  langzaam oplopende helderheid, geen transition.
- De lamp **blijft aan** nadat de wekker gestopt is. De klant zet hem zelf uit.

Aanroep: `light.turn_on` met `entity_id` en `brightness_pct`. **VOORSTEL:** geen
`transition` meesturen, want "geen opbouw" is de eis en een expliciete
`transition: 0` is niet hetzelfde als hem weglaten bij lampen die de parameter
niet kennen.

Kleur en kleurtemperatuur zijn **niet** instelbaar in v1
([sectie 20](#20-wat-niet-in-v1-zit)).

Faalt `light.turn_on`, dan is dat **geen reden om de wekker te laten falen**: het
geluid is de wekker en het licht is een toevoeging. De fout wordt gelogd op
`WARNING` en verschijnt als melding op de kaart volgens
[sectie 11.7](#117-waar-de-melding-verschijnt-en-hoe-de-klant-hem-wegkrijgt),
met een eigen tekst: **"De wekker is afgegaan, maar de lamp 'Bedlamp' kon niet
aangezet worden."**

---

## 13. Plannen

### 13.1 Welke planner waarvoor

**GEMETEN** in fase 0 (`docs/fase-0/ONDERZOEK.md` E1.1), en het is de keuze die
HA's eigen tijdtrigger ook maakt:

| Geval | Planner | Vindplaats in HA |
|---|---|---|
| Wekker met herhaaldagen (terugkerende wandkloktijd) | **`async_track_time_change`** | `components/homeassistant/triggers/time.py:284-292` |
| Eenmalige wekker (één absoluut moment) | **`async_track_point_in_time`** | `triggers/time.py:176-200` |

`async_track_time_change` herplant zichzelf na elke vuurbeurt en rekent de
wandklok-naar-UTC-omzetting elke ronde opnieuw, inclusief zomertijd. Voor een
wekker die elke werkdag om 06:45 afgaat is dat de juiste.

**Filtering op dagen gebeurt in de callback, niet in de planner.**
`async_track_time_change` kent geen dagpatroon. De integratie plant op `hour` en
`minute` en controleert in de callback of vandaag een aangevinkte dag is. Dat is
eenvoudiger dan zeven listeners en het houdt de dagvergelijking op één plek.

**Nauwkeurigheid is geen risico.** Gemeten: **+0,289 s**, door een opzettelijke
random jitter van 50–500 ms tegen een thundering herd
(`helpers/event.py:83-88, 1835`). Tegen een eis van "een minuut te laat is stuk"
is dat twee ordes van grootte marge.

### 13.2 Bij een tijdzonewijziging herplannen

**GEMETEN** in fase 0 (E1.4): alleen `SunListener` luistert op
`EVENT_CORE_CONFIG_UPDATE` (`helpers/event.py:1672`); `_TrackUTCTimeChange`
(regel 1750) doet dat **niet**. Verandert de eigenaar de tijdzone van HA, dan
blijft een lopende listener op het al berekende moment staan.

De integratie luistert daarom zelf op `EVENT_CORE_CONFIG_UPDATE` en herplant
alles.

### 13.3 Er is geen inhaalmechanisme in HA

**GEMETEN** in fase 0 (E1.2). Twee onafhankelijke vaststellingen:

1. Tijdplanners zijn `loop.call_at`-timers in het geheugen
   (`helpers/event.py:1461-1466`). Een herstart gooit ze weg. Er is geen
   persistentie en geen herstelpad.
2. HA's eigen tijdtrigger plant een absoluut moment **alleen als het in de
   toekomst ligt** (`triggers/time.py:190-191`) en slaat een gemist moment dus
   **stil** over.

En het mechanisme dat wél bestaat is scherp: **een
`async_track_point_in_time` op een moment in het verleden vuurt onmiddellijk** —
gemeten +0,0002 s. Zonder rem zou een wekker van 06:45 om 14:00 afgaan als HA op
dat moment herstart.

### 13.4 Het respijtvenster: 30 minuten

**Vastgelegd:** een gemiste wekker gaat **alsnog af** als hij **minder dan 30
minuten** te laat is. Daarna wordt hij overgeslagen.

**Hoe de integratie dat bij setup vaststelt.** Bij elke setup van de config entry,
voor elke wekker die `enabled` is:

1. Bepaal de **laatst verstreken passende wandkloktijd** — het meest recente
   moment in het verleden dat aan de tijd én de herhaaldagen voldoet. Voor een
   eenmalige wekker is dat het opgeslagen `one_shot_at`.
2. Is er geen zo'n moment (een nieuwe wekker die nog nooit langsgekomen is), dan
   valt er niets in te halen.
3. Vergelijk met **`last_fired`** uit de opslag
   ([sectie 14.2](#142-het-schema)). Is `last_fired` gelijk aan of later dan dat
   moment, dan is de wekker al afgegaan en valt er niets in te halen. **Dit veld
   is de enige reden dat de inhaalslag niet dubbel kan vuren**, en het is ook de
   reden dat het bestaat.
4. **VERVALLEN in fase 7.** Hier stond de controle op `skip_next`. Het veld en de
   hele overslaanfunctie zijn weg; er is geen stap meer die een passend moment kan
   inslikken.

   De nummering blijft staan: doorschuiven zou elke verwijzing naar "stap 3" en
   "stap 5" in de code, de rapporten en de commitgeschiedenis stil naar een andere
   stap laten wijzen.
5. Ligt het moment **minder dan 30 minuten** in het verleden, dan **gaat de
   wekker nu af**, met de volledige procedure uit
   [sectie 9.1](#91-de-volgorde) inclusief noodrem.
6. Ligt het er langer in het verleden, dan wordt hij **overgeslagen**, wordt dat
   gelogd op `INFO`, én wordt er een **mededeling aan de klant** vastgelegd — zie
   hieronder.
7. Daarna wordt normaal vooruit gepland.

**Een overgeslagen wekker wordt aan de klant getoond.** Vastgelegd. `last_message`
krijgt `kind: "skipped_grace_window"` en `severity: "notice"`, met de tekst:

> **"Je wekker van 06:45 is niet afgegaan omdat Home Assistant uit stond."**

Dat is precies wat iemand wil weten die zich heeft verslapen, en het is de reden
dat de categorie "mededeling" bestaat naast "fout"
([11.7](#117-waar-de-melding-verschijnt-en-hoe-de-klant-hem-wegkrijgt)). Het is
**geen** storing en het ziet er ook niet als een storing uit: andere kleur, andere
formulering, en géén `persistent_notification`.

**Waarom 30 minuten en niet korter of langer** is de keuze van de eigenaar en
staat hier alleen vastgelegd. Het getal is hetzelfde als de automatische stop uit
[9.4](#94-de-wekker-stopt-na-30-minuten), maar dat is toeval en geen afhankelijkheid:
het zijn twee onafhankelijke constanten.

### 13.5 Wanneer er herpland wordt

Bij elk van deze gebeurtenissen wordt de planning volledig opnieuw opgebouwd:

- setup van de config entry (inclusief de inhaalslag uit 13.4);
- elke wijziging in de opslag via een WebSocket-commando;
- `EVENT_CORE_CONFIG_UPDATE` (tijdzone);
- unload van de config entry — dan worden alle listeners opgezegd.

**VOORSTEL:** volledig opnieuw opbouwen in plaats van incrementeel bijwerken. Een
wekkerlijst is klein en de kosten zijn verwaarloosbaar; incrementeel bijwerken is
de plek waar een verdwaalde listener ontstaat die op een verwijderde wekker
vuurt.

---

## 14. Opslag

### 14.1 Waar

- Één `Store` voor alle personen samen:
  **`.storage/domotiapp_alarm.alarms`**.
- `Store(hass, version=1, minor_version=1, key="domotiapp_alarm.alarms")`.
- Eén instantie voor alle config entries; er is er in de praktijk één.

### 14.2 Het schema

```
{
  "persons": {
    "<registry_entry_id van de person>": {
      "alarms": [ <wekker>, … ]
    }
  }
}
```

Per wekker:

| Veld | Type | Verplicht | Betekenis |
|---|---|---|---|
| `id` | string | ja | uniek binnen de persoon; `random_uuid_hex`. Nodig omdat namen niet uniek zijn |
| `name` | string | ja | niet leeg na `strip()` |
| `time` | string `"HH:MM"` | ja | 24-uurs, seconden bestaan niet |
| `days` | array van int | ja | ISO-weekdagen **1 = maandag … 7 = zondag**. **Lege array = eenmalige wekker** |
| `enabled` | bool | ja | de schakelaar op de kaart |
| `one_shot_at` | string of `null` | ja | ISO-8601 **met tijdzone**, alleen gevuld als `days` leeg is: het ene moment waarop deze wekker afgaat |
| `sound` | object | ja | `{ "uri", "name", "media_type", "image" }` — zie [8.2](#82-sla-de-uri-op-niet-de-naam) |
| `speaker` | string | ja | `entity_id` van de MA-speaker |
| `volume_pct` | int 1–100 | ja | het niveau waar de oploop op eindigt |
| `light` | object of `null` | ja | `{ "entity_id", "brightness_pct" }`, of `null` |
| `last_fired` | string of `null` | ja | ISO-8601 met tijdzone; het laatste moment waarop deze wekker daadwerkelijk is afgegaan. Draagt de inhaalslag uit [13.4](#134-het-respijtvenster-30-minuten) |
| `last_message` | object of `null` | ja | de melding uit [11.7](#117-waar-de-melding-verschijnt-en-hoe-de-klant-hem-wegkrijgt): `{ "at", "kind", "severity", "text" }`, of `null` als er niets te melden is. Zie [14.2.1](#1421-één-veld-voor-fouten-én-mededelingen) |

**Keuzes hierin die VOORSTEL zijn:** ISO-weekdagen 1–7 in plaats van namen of
0–6 (taalonafhankelijk en gelijk aan `datetime.isoweekday()`); `volume_pct` als
int 1–100 in plaats van HA's `0.0–1.0` (de gebruiker ziet procenten, dus de
opslag ook — omgekeerd aan DomotiApp Scene, waar de opslag HA's schaal hield
omdat HA's schaal daar de bron was); `image` in `sound` meeopslaan zodat de kaart
een afbeelding kan tonen zonder opnieuw te zoeken.

`volume_pct` ondergrens is **1** en niet 0: een wekker op volume 0 is geen
wekker.

#### 14.2.1 Één veld voor fouten én mededelingen

Een overgeslagen wekker moet aan de klant getoond worden
([11.7](#117-waar-de-melding-verschijnt-en-hoe-de-klant-hem-wegkrijgt)), en dat is
geen fout. Er waren twee manieren om dat in het schema te zetten: het bestaande
foutveld hergebruiken, of een tweede veld toevoegen.

**Gekozen: één veld, `last_message`, met een `severity`.** Het oorspronkelijk
voorgestelde `last_failure` is daarmee **hernoemd** — de naam zou liegen zodra er
mededelingen in staan.

De afweging:

- **Eén veld** betekent één code­pad, één "Begrepen"-knop, één plek in het schema,
  en één regel voor de kaart: *toon `last_message` als hij er is, en kies kleur en
  toon op `severity`.*
- **Twee velden** (`last_failure` plus `last_notice`) zou de vraag oproepen wat er
  gebeurt als ze **beide** gevuld zijn — welke laat de kaart dan zien, en in welke
  kleur? Dat is een toestand die niets toevoegt: de kaart heeft één regel per
  wekker en toont daar de meest recente gebeurtenis.

De prijs van één veld is expliciet: **een nieuwe melding overschrijft de vorige.**
Is een wekker gisteren mislukt en vanochtend gemist doordat Home Assistant uit
stond, dan ziet de klant alleen dat laatste. Dat is aanvaard — de klant wil weten wat er vanochtend gebeurde,
niet een logboek. Wie de geschiedenis wil, kijkt in het log
([19.5](#195-logniveaus)).

`kind` is de machineleesbare reden en is bedoeld om op te vergelijken; `text` is
de Nederlandse tekst die de kaart toont. De tekst staat in de opslag en wordt niet
in de kaart samengesteld, zodat een melding die op een herstart moet overleven
niet afhangt van de versie van de kaart die hem leest.

### 14.3 Standaardwaarden

Voor een **nieuwe** wekker vult de editor in, en slaat die waarden ook echt op —
nooit een terugvalwaarde tonen die niet opgeslagen wordt:

| Veld | Standaard |
|---|---|
| `time` | **VOORSTEL** `07:00` |
| `days` | leeg (eenmalig) |
| `enabled` | `true` |
| `volume_pct` | **VOORSTEL** `40` |
| `light` | `null` |

`name`, `sound` en `speaker` hebben **geen** standaard: ze zijn verplicht en de
gebruiker moet ze kiezen.

### 14.4 Letterlijk voorbeeld

Eén persoon met drie wekkers: een doordeweekse wekker **met** wake-up light, een
weekendwekker **zonder**, en een **eenmalige** wekker zonder herhaaldagen.

```json
{
  "version": 1,
  "minor_version": 1,
  "key": "domotiapp_alarm.alarms",
  "data": {
    "persons": {
      "3e91c7a54d2b48f6b8e0a1c93d7f2054": {
        "alarms": [
          {
            "id": "a1f4c9e27b8d4a3f9c1e6b2d7a5f8e30",
            "name": "Werk",
            "time": "06:45",
            "days": [1, 2, 3, 4, 5],
            "enabled": true,
            "one_shot_at": null,
            "sound": {
              "uri": "spotify--ZvzrFmgX://playlist/37i9dQZF1DX0UrRvztWcAU",
              "name": "Wake Up Happy",
              "media_type": "playlist",
              "image": "http://homeassistant.local:8095/imageproxy?path=abc123"
            },
            "speaker": "media_player.slaapkamer",
            "volume_pct": 40,
            "light": {
              "entity_id": "light.bedlamp_sven",
              "brightness_pct": 60
            },
            "last_fired": "2026-08-10T06:45:00.312000+02:00",
            "last_message": null
          },
          {
            "id": "7c2b5d81e6a94f0ab3d8c7e2d1a5b9d4",
            "name": "Weekend",
            "time": "09:00",
            "days": [6, 7],
            "enabled": true,
            "one_shot_at": null,
            "sound": {
              "uri": "somafm://radio/beatblender",
              "name": "SomaFM: Beat Blender",
              "media_type": "radio",
              "image": null
            },
            "speaker": "media_player.keuken",
            "volume_pct": 25,
            "light": null,
            "last_fired": "2026-08-09T09:00:00.208000+02:00",
            "last_message": null
          },
          {
            "id": "f0e3a7c15b2d48e9a6c4b8d1e7f2a903",
            "name": "Trein naar Utrecht",
            "time": "05:20",
            "days": [],
            "enabled": true,
            "one_shot_at": "2026-08-12T05:20:00+02:00",
            "sound": {
              "uri": "somafm://radio/groovesalad",
              "name": "SomaFM: Groove Salad",
              "media_type": "radio",
              "image": null
            },
            "speaker": "media_player.slaapkamer",
            "volume_pct": 55,
            "light": null,
            "last_fired": null,
            "last_message": {
              "at": "2026-08-05T05:20:00.191000+02:00",
              "kind": "speaker_unavailable",
              "severity": "error",
              "text": "De wekker van 05:20 is niet afgegaan: de speaker 'Slaapkamer' was niet bereikbaar."
            }
          }
        ]
      }
    }
  }
}
```

De buitenste drie velden (`version`, `minor_version`, `key`) zet HA's `Store`
zelf; alles onder `data` is van ons.

### 14.5 Wat er met een afgegane eenmalige wekker gebeurt

Na afgaan wordt `enabled` op `false` gezet en blijft de wekker in de lijst staan,
met `last_fired` gevuld. Hij wordt **niet** verwijderd. Vastgelegd.

Reden: de gebruiker ziet dan dat hij is afgegaan en kan hem opnieuw aanzetten
zonder alles opnieuw in te vullen. Automatisch verwijderen is een onomkeerbare
handeling die het product nergens anders heeft. De kaart toont zo'n wekker als
**"Eenmalig — afgelopen"**.

**"Na afgaan" is ruimer dan "na geluid".** Het moment is verbruikt zodra
`last_fired` erop staat, en dat gebeurt op drie manieren:

| Wat er gebeurde | `enabled` daarna |
|---|---|
| de wekker ging af | `false` |
| de noodrem hield hem tegen ([11.6](#116-bij-falen)) | `false` |
| het moment werd overgeslagen ([13.4](#134-het-respijtvenster-30-minuten)) | `false` |

Anders is de uitkomst dubbel onaangenaam: de wekker ging niet af én de
schakelaar suggereert dat hij dat morgen alsnog doet, terwijl `one_shot_at` in
het verleden ligt en de planner hem niet meer oppakt
([13.1](#131-welke-planner-waarvoor)).

**Opnieuw aanzetten geeft een nieuw moment.** Dat is geen eigenschap van de
opslag maar van het commando; zie
[15.3](#153-domotiapp_alarmalarmsset_enabled).

*Verduidelijkt in fase 6. Deze sectie stond er sinds fase 2, maar de implementatie
zette `enabled` nooit om — gevonden in productie op 1.0.0.*

### 14.6 Schemaversie en migratie

- **`minor_version` omhoog** bij een wijziging die oude data zonder aanpassing
  kan lezen (een nieuw optioneel veld). **`version` omhoog** bij een wijziging
  die dat niet kan (een veld hernoemd, een eenheid veranderd — bijvoorbeeld
  `volume_pct` naar HA's 0.0–1.0).
- Migreren in een subklasse van `Store` met
  `_async_migrate_func(old_major_version, old_minor_version, old_data)`. HA kiest
  die driearguments-vorm zelf op basis van de signatuur
  (`helpers/storage.py:449-455`) en schrijft direct na een geslaagde migratie weg
  (regel 460).
- **Een oudere codeversie leest nooit nieuwere data.** Staat er een hogere
  `version` in het bestand dan de code aankan, dan gooit HA zelf
  `UnsupportedStorageVersionError` (`helpers/storage.py:437-440`). Dat is gewenst:
  liever falen dan een nieuw formaat half interpreteren.
- Migraties zijn **puur**, en verliezen alleen wat hier bij naam genoemd staat.
  Kan een migratie een veld niet omzetten, dan **faalt** ze in plaats van het veld
  stil weg te laten. Een veld dat met opzet vervalt is iets anders dan een veld
  dat niet om te zetten is; dat eerste hoort in de lijst hieronder te staan.
- **Een migratie raakt alleen wat ze kent.** Alles wat niet in de lijst van
  vervallen velden staat, gaat ongewijzigd door naar de validatie — ook onbekende
  velden, ook kapotte structuren. Een migratie die de data "opschoont" naar wat de
  code van vandaag verwacht, zou een schrijffout onzichtbaar maken en de scheiding
  uit [19.2](#192-onleesbare-of-ongeldige-opslag) van zijn werk beroven.

**Correctie, fase 7.** Hier stond: *"Migratie slaat kapotte personen over. Een
persoon die niet valideert wordt niet gemigreerd."* Dat is niet uitvoerbaar en het
was nooit waar. Home Assistant draait `_async_migrate_func` **binnen**
`Store.async_load`, dus vóórdat onze code ook maar één persoon heeft gezien — de
scheiding tussen gezond en kapot bestaat op dat moment nog niet. Wat er in de
plaats komt is de regel hierboven: de migratie raakt alleen de vervallen velden en
laat de rest letterlijk staan, zodat een kapotte persoon daarna nog steeds als
kapot herkend wordt en zijn onbewerkte waarde nog steeds terugkomt bij het
schrijven.

**Bijkomend, en het is geen keuze van ons:** een geslaagde migratie **schrijft**,
ook als de opslag daarna onbruikbaar blijkt (geval C uit 19.2). HA doet dat zelf,
direct na de migratie. De inhoud blijft daarbij ongemoeid; alleen het versienummer
in het bestand gaat omhoog.

#### Versiegeschiedenis

| Van | Naar | Wat er gebeurt | Waarom een major |
|---|---|---|---|
| 1.1 | **2.1** | het veld `skip_next` wordt uit elke wekker verwijderd (fase 7, [15.5](#155-vervallen)) | de nieuwe code kan oude data **niet** zonder aanpassing lezen: `validatie.py` weigert onbekende velden en zet de hele persoon op onleesbaar ([19.2](#192-onleesbare-of-ongeldige-opslag) geval B). Zonder migratie verliest een bestaande klant al zijn wekkers, en hij ziet dat pas de eerste ochtend dat er niets afgaat |

`minor_version` gaat bij een majorsprong terug naar 1: hij telt binnen een
majorversie.

---

## 15. WebSocket-API

Alle commando's beginnen met `domotiapp_alarm/`. Alle commando's zijn voor
**iedere ingelogde gebruiker** tenzij anders vermeld; zie
[sectie 17](#17-rechten).

Overal waar een person wordt aangeduid, gebeurt dat met **`entity_id`**. De
vertaling naar het registry-entry-ID is server-side
([sectie 6.2](#62-de-sleutel-is-het-registry-entry-id)).

**Gemeenschappelijke fouten**, die bij elk commando met een `person`-veld kunnen
optreden:

| Code | Wanneer |
|---|---|
| `invalid_format` | een veld ontbreekt of heeft het verkeerde type |
| `not_found` | de entiteit bestaat niet, zit niet in het `person`-domein, of heeft geen entity registry entry |
| `home_assistant_error` | de opgeslagen data van deze persoon is onleesbaar ([sectie 19.2](#192-onleesbare-of-ongeldige-opslag)) |

### 15.1 `domotiapp_alarm/alarms/get`

Haalt de wekkers van één persoon op.

**Invoer**

| Veld | Type | Verplicht |
|---|---|---|
| `type` | `"domotiapp_alarm/alarms/get"` | ja |
| `person` | string, `person.`-entity-ID | ja |

**Uitvoer**

```json
{
  "alarms": [ { … zoals sectie 14.2, zonder wijzigingen … } ],
  "next_fire": { "at": "2026-08-11T06:45:00+02:00", "text": "Morgen 06:45", "alarm_id": "a1f4…" },
  "ringing": [ "a1f4c9e27b8d4a3f9c1e6b2d7a5f8e30" ],
  "stored": true
}
```

- `alarms` — gesorteerd volgens [sectie 3.4](#34-sorteervolgorde). Leeg als er
  niets is.
- `next_fire` — server-side berekend, inclusief de kant-en-klare tekst uit
  [sectie 3.3](#33-de-regel-eerstvolgende-wekker). `null` als er geen wekker aan
  staat.
- `ringing` — de ID's van de wekkers van deze persoon die **nu afgaan**. Zo weet
  een kaart die net opengaat meteen dat hij een stopknop moet zijn, zonder op een
  event te wachten.
- `stored` — `false` betekent "deze persoon heeft nog nooit opgeslagen".

### 15.2 `domotiapp_alarm/alarms/save`

Maakt een wekker aan of werkt hem bij. Eén wekker per aanroep.

**Invoer**

| Veld | Type | Verplicht |
|---|---|---|
| `person` | string | ja |
| `alarm` | object | ja |

`alarm` bevat de velden uit [14.2](#142-het-schema) die de gebruiker beheert:
`name`, `time`, `days`, `enabled`, `sound`, `speaker`, `volume_pct`, `light`, en
optioneel `id`. **Ontbreekt `id`, dan is het een nieuwe wekker** en genereert de
server er een.

De server beheert zelf en accepteert **niet** van de kaart:
`one_shot_at`, `last_fired`, `last_message`. Die worden bij een update
overgenomen uit de bestaande wekker. Reden: het zijn geen gebruikerskeuzes maar
boekhouding, en een kaart die ze mag zetten kan de inhaalslag uit
[13.4](#134-het-respijtvenster-30-minuten) om de tuin leiden.

`one_shot_at` wordt **server-side** berekend wanneer `days` leeg is: de
eerstvolgende keer dat `time` voorbijkomt.

**Uitvoer:** hetzelfde als `alarms/get`, zodat de kaart met één antwoord de hele
nieuwe toestand heeft en er geen tweede aanroep nodig is.

**Fouten**

| Code | Wanneer |
|---|---|
| `invalid_format` | `time` niet `HH:MM`; `days` geen deelverzameling van 1–7; `volume_pct` buiten 1–100; `name` leeg na `strip()`; `brightness_pct` buiten 1–100 |
| `not_found` | `id` opgegeven maar bestaat niet bij deze persoon |
| `not_allowed` | `speaker` haalt de controle uit [7.2](#72-vaststellen-dát-het-een-ma-speaker-is) niet, of is een groep; `light.entity_id` heeft het label niet |
| `home_assistant_error` | opslag onleesbaar, of wegschrijven mislukt |

**Validatie gebeurt server-side, ook al doet de kaart het al.** De kaart is niet
de enige aanroeper die je kunt bedenken en een kaart is te omzeilen.

### 15.3 `domotiapp_alarm/alarms/set_enabled`

De schakelaar op de kaart. Apart commando en niet via `save`, omdat de schakelaar
één veld zet en geen heel formulier hoeft te versturen — en omdat `save` een
volledig geldige wekker eist, wat een half ingevulde rij niet is.

**Invoer:** `person`, `alarm_id`, `enabled` (bool).
**Uitvoer:** als `alarms/get`.
**Fouten:** `not_found` als de wekker niet bestaat; verder de gemeenschappelijke.

**Een verlopen eenmalige wekker aanzetten geeft hem een nieuw moment.** Zet
`enabled` op `true` bij een wekker met lege `days` waarvan de `one_shot_at` is
verstreken, dan berekent de server een nieuwe `one_shot_at`: **de eerstvolgende
keer dat de ingestelde `time` voorbijkomt**, met dezelfde rekenkunde als
[15.2](#152-domotiapp_alarmalarmssave).

Zonder dit is de schakelaar een knop die niets doet. Sinds
[14.5](#145-wat-er-met-een-afgegane-eenmalige-wekker-gebeurt) zet een eenmalige
wekker zichzelf uit zodra zijn moment op is, en dan is deze schakelaar de enige
manier om hem terug te halen — terwijl `one_shot_at` in het verleden ligt, de
planner hem niet plant ([13.1](#131-welke-planner-waarvoor)) en de kaart "geen
volgende keer" toont bij een wekker die aan staat.

**Alleen als het moment verstreken is**, en dat is geen voorzichtigheid maar
noodzaak. Opnieuw rekenen terwijl het moment nog in de toekomst ligt kan de wekker
naar **vroeger** halen: staat een wekker van 06:45 op morgen en zet de klant hem
om 05:00 uit en weer aan, dan is de eerstvolgende 06:45 vandaag. Een wekker die
anderhalf uur later afgaat dan de klant zag, is erger dan de knop die hiermee
gerepareerd wordt.

Een **herhalende** wekker raakt dit niet: die heeft geen `one_shot_at`
([14.2](#142-het-schema)) en pakt zijn volgende dag vanzelf op.

*Toegevoegd in fase 6, op verzoek van de eigenaar.*

### 15.4 `domotiapp_alarm/alarms/delete`

**Invoer:** `person`, `alarm_id`.
**Uitvoer:** als `alarms/get`.
**Fouten:** `not_found`.

Verwijdert de wekker uit de opslag en zegt zijn planning op. Loopt de wekker op
dat moment, dan wordt hij eerst gestopt volgens
[9.4](#94-de-wekker-stopt-na-30-minuten) — inclusief het terugzetten van het
volume. Anders blijft er geluid draaien voor een wekker die niet meer bestaat.

### 15.5 VERVALLEN

Hier stond `domotiapp_alarm/alarms/skip_next`: een wekker eenmalig overslaan. De
eigenaar gebruikte het niet, en in fase 7 is de hele functie verwijderd — het
commando, het veld `skip_next` uit het schema, de stap in het respijtvenster, de
regel in [15.3](#153-domotiapp_alarmalarmsset_enabled), de weergave
*"Morgen overgeslagen"* en de meldingssoort `skipped_by_user`.

**Het commando bestaat niet meer**, en dat is aan het antwoord te zien: HA geeft
`unknown_command`. Dat is met opzet luider dan een handler die stil niets doet —
een oude kaart die het nog aanroept, krijgt een fout in plaats van de indruk dat
het gelukt is.

**De nummering van 15.6 en verder blijft staan.** Doorschuiven zou elke verwijzing
in de code, de rapporten en de commitgeschiedenis stil naar een ander commando
laten wijzen, en het zijn er tientallen.

Wat er met de bestaande opslag gebeurt, staat in
[14.6](#146-schemaversie-en-migratie): schemaversie **2**, met een migratie die
het veld verwijdert.

### 15.6 `domotiapp_alarm/sound/search`

Proxy naar `music_assistant.search`. De kaart praat niet rechtstreeks met Music
Assistant: dan zou de kaart de MA-config-entry moeten opzoeken en zou de
filtering in twee talen bestaan.

**Invoer**

| Veld | Type | Verplicht |
|---|---|---|
| `query` | string | ja |
| `media_types` | array van string | nee — weglaten = alle soorten |
| `limit` | int | nee — standaard **VOORSTEL** 10; **maximum 50 ligt vast** |

**Uitvoer**

```json
{
  "results": [
    { "name": "SomaFM: Beat Blender", "uri": "somafm://radio/beatblender",
      "media_type": "radio", "image": null,
      "artists": null, "album": null, "endless": true }
  ]
}
```

**Één platte lijst**, niet de acht lijsten van MA. De kaart toont een
zoekresultaat en niet acht koppen; `media_type` per treffer houdt het onderscheid
vast.

#### `endless` — blijft dit geluid doorspelen?

**Toegevoegd in fase 4c.** Een boolean per treffer die zegt of het geluid
eindeloos doorspeelt. De editor toont de waarschuwing uit
[8.3](#83-afspelen) wanneer hij `false` is, en anders niet.

**Dit wordt server-side bepaald en de kaart interpreteert niets.** Dat is de hele
reden dat het veld bestaat. Het antwoord hangt af van
`SIMILAR_TRACKS_PROVIDERS` — dezelfde constante waarmee
[8.3.1](#831-radio_mode-wordt-voorwaardelijk-meegestuurd) beslist of `radio_mode`
meegaat. Zou de kaart die lijst óók hebben, dan bestaat hij twee keer en kan de
editor *"dit speelt door"* beloven terwijl het afvuren `radio_mode` weglaat. Eén
lijst betekent dat hij ook maar op één plek fout kan staan — en fase 3a-bis legde
vast dat die lijst **stil** kan verouderen.

`true` bij **een** van deze twee, in deze volgorde:

| Reden | Voorbeeld |
|---|---|
| de **soort** houdt uit zichzelf niet op: `radio` of `playlist` ([8.3](#83-afspelen)) | `somafm://radio/…` van een provider zonder `SIMILAR_TRACKS` |
| **`radio_mode`** gaat mee, dus MA speelt na het item door in dezelfde stijl | `spotify--…://track/…` |

Bij twijfel — een onbekend URI-schema, een lege URI, een soort die er niet in
staat — is het `false`. Dat is de goede kant om fout te zitten: een waarschuwing
te veel is hinderlijk, een belofte dat het geluid doorspeelt terwijl het na drie
minuten stopt is een wekker die stil valt.

**Waarom er geen `endless` in de opslag staat:** het is een eigenschap van de
**provider** en niet van de keuze, en het kan veranderen zonder dat de klant iets
doet. `sound` houdt de vier velden van [8.2](#82-sla-de-uri-op-niet-de-naam).
Gevolg, en dat is aanvaard: opent de klant een **bestaande** wekker, dan weet de
editor het niet en waarschuwt hij niet. De waarschuwing hoort bij het **kiezen**
van een geluid, en daar is het veld er wel.

**De volgorde: afspeellijsten en radio eerst**, daarna de rest in de volgorde
waarin MA ze gaf. Vastgelegd.

De reden is wat mensen in de praktijk voor een wekker kiezen, en **niet** dat de
andere soorten technisch tekort zouden schieten. Die onderbouwing is met opzet
losgekoppeld van [8.3.1](#831-radio_mode-wordt-voorwaardelijk-meegestuurd): wat fase 3
over `radio_mode` vindt, verandert niets aan deze volgorde. Wordt een los nummer
een even bruikbare wekker, dan blijft het nog steeds zo dat iemand die een wekker
instelt meestal een afspeellijst of een radiostation wil.

**Het maximum van 50 ligt vast.** De oorspronkelijke reden was de URI-controle, die
deze bovengrens gebruikte om het valse negatief te beperken; die controle is in fase
3c-bis vervallen ([11.2](#112-de-uri-wordt-niet-vooraf-gecontroleerd)). Het maximum blijft staan, nu met alleen nog de reden
waarvoor deze sectie bestaat: een klant die een aflevering of een station zoekt moet het
kunnen vinden zonder zijn zoekterm te hoeven verfijnen. De standaard van 10 is wél een
voorstel: die geldt alleen voor het eerste beeld in de editor.

**Time-out: 10 seconden.** Vastgelegd. Duurt de zoekopdracht langer, dan breekt de
integratie af en geeft `home_assistant_error`, en de editor toont letterlijk:

> **"Zoeken duurt te lang. Probeer het opnieuw."**

Waarom er een time-out moet zijn: MA's eigen zoekopdracht ging in fase 0b in
tientallen milliseconden, maar RadioBrowser was **wisselvallig** en gaf
minutenlang fouten op elke zoekopdracht op één na. Een editor die dan blijft
wachten, lijkt stuk.

**Fouten**

| Code | Wanneer |
|---|---|
| `not_found` | er is geen geladen `music_assistant`-config-entry |
| `home_assistant_error` | de MA-service gaf een fout, of duurde langer dan 10 seconden |

### 15.7 `domotiapp_alarm/entities/list`

De gelabelde speakers en lampen, server-side gefilterd.

**Invoer:** alleen `type`.

**Uitvoer**

```json
{
  "speakers": {
    "label_exists": true,
    "entities": [ { "entity_id": "media_player.slaapkamer", "name": "Slaapkamer" } ],
    "filtered_out": 0
  },
  "lights": {
    "label_exists": false,
    "entities": [],
    "filtered_out": 0
  }
}
```

`label_exists` komt uit `missing_labels` van `helpers/target.py`.

#### `filtered_out` — hoeveel gelabelde entiteiten zijn afgevallen

**Toegevoegd in fase 4c**, om de drie situaties van
[7.4](#74-wat-de-kaart-toont-als-het-label-nog-niet-bestaat) uit elkaar te kunnen
houden. Met alleen `label_exists` en `entities` zijn er drie situaties en twee
signalen:

| Situatie ([7.4](#74-wat-de-kaart-toont-als-het-label-nog-niet-bestaat)) | `label_exists` | `entities` | `filtered_out` |
|---|---|---|---|
| het label bestaat niet | `false` | leeg | 0 |
| het label bestaat, er hangt niets aan | `true` | leeg | **0** |
| er hing wél iets aan, maar het viel af op [7.2](#72-vaststellen-dát-het-een-ma-speaker-is) | `true` | leeg | **> 0** |

De onderste twee zien er zonder deze teller identiek uit, en het zijn voor de
eigenaar twee heel verschillende boodschappen: *"zet het label op je speakers"*
tegenover *"die speakers zijn geen Music Assistant-speakers"*. Tot fase 4c toonde
de kaart één tekst die beide dekte, en dat is een zin die je twee keer moet lezen
om te weten wat je moet doen.

**Het is een getal en geen lijst met redenen.** De melding van
[7.4](#74-wat-de-kaart-toont-als-het-label-nog-niet-bestaat) is één zin die alle
afvalredenen samenvat, en de reden per entiteit staat al op `DEBUG` in het log.
Een lijst zou de kaart uitnodigen er zelf zinnen van te maken, en dan staat de
uitleg op twee plekken.

**Ook bij de lampen**, waar de enige eis het domein is
([sectie 12](#12-de-wake-up-light)): een `Verlichting Wekker`-label op iets dat
geen lamp is, telt mee.

**VOORSTEL:** `name` is de weergavenaam van de entiteit
(`friendly_name`), die een `unavailable` entiteit overleeft
(`helpers/entity.py:1166-1167`) — anders zou een weggevallen speaker in de lijst
als kaal entity-ID verschijnen.

**VOORSTEL:** `name` is de weergavenaam van de entiteit
(`friendly_name`), die een `unavailable` entiteit overleeft
(`helpers/entity.py:1166-1167`) — anders zou een weggevallen speaker in de lijst
als kaal entity-ID verschijnen.

### 15.8 `domotiapp_alarm/alarms/stop`

Stopt een lopende wekker.

**Invoer:** `person`, `alarm_id`.
**Uitvoer:** als `alarms/get`.

**Idempotent:** een wekker stoppen die niet loopt is **geen fout** en geeft
gewoon de huidige toestand terug. Een wandtablet en een telefoon kunnen tegelijk
drukken.

### 15.9 `domotiapp_alarm/updates/subscribe`

Eén abonnement op alles wat een open kaart nodig heeft om actueel te blijven.

**Tot fase 4b heette dit `ringing/subscribe`** en ging het alleen over afgaan.
Fase 4a mat wat daaraan ontbrak: een wekker die op de telefoon wordt gewijzigd
verscheen op het wandtablet **pas na een herlaadbeurt**, want er was geen
abonnement op opslagwijzigingen. Met de editor uit
[sectie 5](#5-de-editor-een-wekker-instellen) is dat zichtbaar gedrag.

De naam volgt de bredere betekenis: het abonnement gaat over **updates** voor de
kaart, waarvan afgaan er één soort is. Er waren nog geen klanten, dus hernoemen
kostte niets — en één abonnement is beter dan twee, omdat de kaart dan één
codepad heeft: *elk bericht betekent "haal de toestand opnieuw op"*, en alleen
`started` en `stopped` doen daarnaast nog iets met de stopknop.

**Invoer:** `type`, en **VOORSTEL** een optionele `person` om alleen de berichten
van één persoon te ontvangen.

**Berichten**

```json
{ "event": "started", "person": "person.sven", "alarm_id": "a1f4…", "name": "Werk", "time": "06:45" }
{ "event": "stopped", "person": "person.sven", "alarm_id": "a1f4…", "reason": "user" }
{ "event": "failed",  "person": "person.sven", "alarm_id": "f0e3…",
  "reason": "speaker_unavailable",
  "text": "De wekker van 05:20 is niet afgegaan: …" }
{ "event": "changed", "person": "person.sven" }
```

`reason` bij `stopped` is `"user"`, `"timeout"` (de 30 minuten) of `"deleted"`.

#### `changed` is een sein, geen toestand

Het bericht draagt **alleen** `person`. De ontvanger haalt daarna zelf
[`alarms/get`](#151-domotiapp_alarmalarmsget) op. Twee redenen:

- een abonnee **zonder** `person`-filter zou anders bij elke wijziging de
  wekkerlijst van élke persoon in huis toegestuurd krijgen. Dat is geen
  beveiligingslek ([6.3](#63-dit-is-geen-beveiliging)) maar het is wel de
  scheiding uit [sectie 6](#6-de-person-entiteit-als-opslagsleutel) gratis
  weggeven;
- `alarms/get` blijft de **enige** plek die de toestand samenstelt. Twee plekken
  die hetzelfde antwoord opbouwen lopen uiteen — dezelfde reden dat de kaart
  `next_fire` niet zelf berekent ([3.3](#33-de-regel-eerstvolgende-wekker)).

De prijs is één extra aanroep per wijziging, en die wordt bewust betaald.

#### `changed` komt uit de opslaglaag, niet uit de commando's

**Vastgelegd**, want het is het verschil tussen een abonnement dat werkt en een
dat gaten heeft. Het bericht gaat uit na elke geslaagde schrijfronde in de
opslag, niet aan het eind van de vijf muterende commando's.

Behalve die commando's schrijven namelijk ook de **planner** (`last_fired`, en de
inhaalslag uit [13.4](#134-het-respijtvenster-30-minuten) die
`last_message` zet) en **[11.7](#117-waar-de-melding-verschijnt-en-hoe-de-klant-hem-wegkrijgt)**
(`last_message`) in de opslag. Dat zijn precies de wijzigingen die de klant niet
zelf heeft aangevraagd — en dus de wijzigingen waarvan hij het meest heeft dat
zijn kaart ze uit zichzelf laat zien.

Het bericht gaat er **ná** het wegschrijven uit. Faalt het schrijven, dan is er
niets gemeld: een kaart die dan `alarms/get` zou doen, zou een toestand ophalen
die niet op schijf staat.

**Een wijziging voor een persoon die niet meer bestaat levert geen bericht op.**
De wekkers van een verwijderde persoon blijven in de opslag staan
([18.1](#181-de-person-entiteit-wordt-hernoemd-of-verwijderd)), maar er is dan
geen `person.`-entiteit om in het bericht te zetten en geen kaart die zich erop
kan abonneren.

**Dit is een abonnement en geen entiteit.** Vastgelegd.

Het alternatief was een `binary_sensor` per persoon. Dat is afgewezen om twee
redenen: het zou **de entiteitenkiezer van de klant vullen** met entiteiten die hij
nergens voor nodig heeft, en het zou de integratie van `integration_type: service`
in een entiteitenleverancier veranderen. Dit product levert bewust **geen**
entiteiten. Een abonnement houdt de toestand binnen de kaart, waar hij hoort.

De prijs staat er ook bij: de afgaan-toestand is daarmee **niet** beschikbaar voor
automatiseringen van de klant. Dat is aanvaard.

### 15.10 `domotiapp_alarm/alarms/clear_message`

De **"Begrepen"**-knop uit
[11.7](#117-waar-de-melding-verschijnt-en-hoe-de-klant-hem-wegkrijgt). Wist
`last_message` van één wekker.

**Invoer**

| Veld | Type | Verplicht |
|---|---|---|
| `type` | `"domotiapp_alarm/alarms/clear_message"` | ja |
| `person` | string, `person.`-entity-ID | ja |
| `alarm_id` | string | ja |

**Uitvoer:** als [`alarms/get`](#151-domotiapp_alarmalarmsget).

**Fouten**

| Code | Wanneer |
|---|---|
| `invalid_format` | een veld ontbreekt of heeft het verkeerde type |
| `not_found` | de persoon bestaat niet, of de wekker bestaat niet bij deze persoon |
| `home_assistant_error` | opslag onleesbaar, of wegschrijven mislukt |

**Rechten:** iedere ingelogde gebruiker, net als alle andere commando's
([sectie 17](#17-rechten)). Wie zijn wekker mag stoppen, mag de melding daarover
wegklikken.

**Waarom dit commando bestaat.** `last_message` staat **in de opslag** en niet in
de kaart, met opzet: een melding moet een herstart overleven en zichtbaar zijn als
de browser pas uren later opengaat
([11.7](#117-waar-de-melding-verschijnt-en-hoe-de-klant-hem-wegkrijgt),
[14.2](#142-het-schema)). Precies daardoor kán de kaart hem niet zelf wegnemen.
Zonder dit commando is de "Begrepen"-knop **een knop die liegt**: hij verbergt de
melding in één browser, laat hem staan op het wandtablet, en zet hem terug bij de
eerstvolgende herlaadbeurt.

**Dit is geen omweg naar de servervelden.** [15.2](#152-domotiapp_alarmalarmssave)
legt vast dat `one_shot_at`, `last_fired` en `last_message` **nooit
met een waarde van de kaart komen**, omdat een kaart die ze mag zetten de
inhaalslag uit [13.4](#134-het-respijtvenster-30-minuten) om de tuin kan leiden.
Die regel blijft onaangetast, en de vorm van dit commando is de reden:

- het neemt **geen waarde** aan — er is geen veld voor een `text`, een `kind`, een
  `severity` of een `at`;
- het zet `last_message` **onvoorwaardelijk** op `null`. Er is precies één
  uitkomst, en die is niet door de aanroeper te sturen;
- het raakt de andere drie servervelden **niet** aan.

De kaart kan met dit commando dus maar één ding: wegnemen wat de server zelf heeft
geschreven. Een tweede commando dat een melding zou kúnnen zetten is er bewust
niet — zie [15.12](#1512-wat-er-bewust-géén-commando-is).

**Idempotent:** een melding wissen die er niet is, is geen fout en geeft gewoon de
huidige toestand terug. Twee schermen kunnen tegelijk op "Begrepen" drukken.

### 15.11 `domotiapp_alarm/preview/start`

De **voorbeeldknop** uit [5.4](#54-de-voorbeeldknop). Speelt het gekozen geluid op
de gekozen speaker, met de waarden zoals ze **nu in de editor staan** — dus nog
niet opgeslagen.

**Invoer**

| Veld | Type | Verplicht |
|---|---|---|
| `type` | `"domotiapp_alarm/preview/start"` | ja |
| `speaker` | string, `media_player.`-entity-ID | ja |
| `sound` | object, zoals in [14.2](#142-het-schema) | ja |
| `volume_pct` | int 1–100 | ja |

**Uitvoer:** een leeg resultaat zodra het geluid **daadwerkelijk speelt**. Alles
wat kan mislukken gebeurt vóór dat resultaat, zodat een mislukt voorbeeld een
gewone fout is en geen abonnement dat meteen weer stukgaat.

**Fouten**

| Code | Wanneer |
|---|---|
| `invalid_format` | een veld ontbreekt, heeft het verkeerde type, of er is geen `uri` in `sound` |
| `not_allowed` | `speaker` haalt de controle uit [7.2](#72-vaststellen-dát-het-een-ma-speaker-is) niet, of er gaat op die speaker een **wekker** af |
| `speaker_unavailable` | de noodrem uit [11.1](#111-vóór-het-afspelen-available): de speaker is niet bereikbaar |
| `sound_gone` | `music_assistant.play_media` weigerde het geluid |

#### Dit is een abonnement, en dat is de hele truc

**Het voorbeeld loopt zolang dit abonnement loopt.** Afmelden stopt het geluid en
zet het volume terug; er is **geen los `preview/stop`-commando**.

Dat volgt rechtstreeks uit [5.4](#54-de-voorbeeldknop): *elke manier van de editor
sluiten stopt het voorbeeld*. "Elke manier" is meer dan de kaart kan afvangen. De
X, Escape, Annuleren en Opslaan zijn af te vangen; een tabblad dat wordt
weggeklikt, een browser die crasht, een wandtablet dat zijn wifi verliest of een
telefoon die in slaap valt niet.

Met een stopcommando speelt de muziek in al die gevallen **door**, op een speaker
waarvan het volume ook nog op het voorbeeldniveau blijft staan. Dat is de lege
woning uit [9.4](#94-de-wekker-stopt-na-30-minuten), alleen dan zonder stoptimer.

Home Assistant roept de opruimcallback van een abonnement aan zodra de client zich
afmeldt **of de verbinding wegvalt**. De stopknop in de editor is dus een
afmelding, en een weggevallen tabblad is dezelfde afmelding — één codepad, en het
geval dat je niet kunt afvangen wordt gratis meegenomen.

#### De tweede rem: een maximum

Een abonnement leeft zolang de verbinding leeft, en een tabblad dat op een editor
blijft staan kan dagen leven. Een voorbeeld stopt daarom hoe dan ook na **5
minuten**. **VOORSTEL**; dezelfde gedachte als
[9.4](#94-de-wekker-stopt-na-30-minuten), en het getal mag anders.

#### Wat het voorbeeld niet doet, en waarom

| Niet | Reden |
|---|---|
| **Geen volume-oploop** | Vastgelegd in [5.4](#54-de-voorbeeldknop): het doel is het geluid en het niveau beoordelen, en twintig seconden wachten voordat je hoort of het te hard staat maakt de knop onbruikbaar |
| **Geen `radio_mode`** | Het voorbeeld duurt kort en wat er ná het item gebeurt is niet wat de klant beoordeelt. Meesturen haalt er wél een risico bij: bij een provider zonder `SIMILAR_TRACKS` geeft MA HTTP 500 en speelt er niets ([8.3.1](#831-radio_mode-wordt-voorwaardelijk-meegestuurd)) — dan lijkt de voorbeeldknop stuk terwijl het geluid deugt |
| **Geen wake-up light** | De lamp hoort bij de wekker, niet bij het beoordelen van een geluid. Hem aanzetten zou een handeling zijn die de klant niet heeft gevraagd |

#### Een wekker gaat vóór

Gaat er op de gekozen speaker een **wekker** af, dan wordt het voorbeeld geweigerd
met `not_allowed`. Het voorbeeld zou de queue overnemen en bij het stoppen het
volume terugzetten naar wat de oploop op dat moment toevallig had gezet, waarna de
wekker zachtjes of helemaal niet verder speelt. De wekker is het product; het
voorbeeld is een hulpmiddel.

**Een tweede voorbeeld op dezelfde speaker vervangt het eerste** — Music Assistant
heeft één queue per player, dus naast elkaar bestaan ze toch niet.

**Rechten:** iedere ingelogde gebruiker ([sectie 17](#17-rechten)).

### 15.12 Wat er bewust géén commando is

| Niet | Waarom |
|---|---|
| Een wekker aanmaken zonder speaker of geluid | Ze zijn verplicht; een half opgeslagen wekker is een wekker die stil faalt |
| Een melding **zetten** of wijzigen | [15.10](#1510-domotiapp_alarmalarmsclear_message) wist alleen. Meldingen komen uit de integratie zelf ([11.7](#117-waar-de-melding-verschijnt-en-hoe-de-klant-hem-wegkrijgt)); een aanroeper die er een kan schrijven, kan de klant vertellen dat zijn wekker is afgegaan terwijl dat niet zo is |
| **`preview/stop`** | Afmelden van [15.11](#1511-domotiapp_alarmpreviewstart) **is** het stoppen. Een apart stopcommando zou het geval dat er het meest toe doet — een tabblad dat verdwijnt — juist niet dekken |
| De wekkerlijst van álle personen ophalen | De kaart is per persoon; een overzichtscommando zou de scheiding uit [sectie 6](#6-de-person-entiteit-als-opslagsleutel) tot niets maken zonder er functionaliteit voor terug te geven |
| Opslag verwijderen per persoon | v1 heeft geen opruimoverzicht; zie [sectie 18.1](#181-de-person-entiteit-wordt-hernoemd-of-verwijderd) en [sectie 20](#20-wat-niet-in-v1-zit) |
| Het volume van een speaker rechtstreeks zetten | Dat is `media_player.volume_set` en dat bestaat al |

---

## 16. De kaart-config

### 16.1 Sleutels

| Sleutel | Type | Verplicht | Betekenis |
|---|---|---|---|
| `type` | string | ja | `custom:domotiapp-alarm-card` |
| `person` | string | **ja** | `person.`-entity-ID; de opslagsleutel |

Meer niet. Er is geen `name`, geen `title`, geen `theme`: de kaart toont de
wekkers van één persoon en heeft geen kop nodig.

Lovelace hangt zelf sleutels aan een kaartconfig die de kaart moet **doorlaten en
bewaren** zonder ze te interpreteren: `grid_options`, `layout_options`,
`view_layout`, `visibility`. Die worden bij het opslaan van de config
meegenomen; ze horen niet in de validatie.

### 16.2 Wat de editor toont

De Lovelace-config-editor (`getConfigElement`) toont **één veld**: een
entiteitenkiezer beperkt tot het `person`-domein.

**VOORSTEL:** via `ha-form` met een `entity`-selector en
`domain: "person"`. Dat is HA's eigen component en lost de zoek- en
toetsenbordafhandeling al op.

`getStubConfig` levert `{ type: "custom:domotiapp-alarm-card" }` **zonder**
`person`, zodat de kaart via de kaartkiezer toe te voegen is en de gebruiker de
persoon daarna kiest.

### 16.3 Wat de kaart doet zonder geldige `person`

- **`person` ontbreekt** — de kaart toont **"Kies een persoon in de
  kaartinstellingen."** Geen fout, geen rode tekst: dit is de toestand direct na
  toevoegen.
- **`person` verwijst naar een niet-bestaande entiteit** — de kaart toont
  **"De gekozen persoon bestaat niet meer."** in foutkleur. Zie
  [sectie 18.1](#181-de-person-entiteit-wordt-hernoemd-of-verwijderd).
- **`person` zit niet in het `person`-domein** — `setConfig` gooit, zoals
  Lovelace verwacht bij een ongeldige config. Dit is de enige plek waar de kaart
  mag gooien, en het is wat Lovelace als "Configuratiefout" toont.

---

## 17. Rechten

| Handeling | Wie |
|---|---|
| Kaart zien, wekkerlijst lezen | iedere ingelogde gebruiker |
| Wekker aanmaken, wijzigen, verwijderen, aan/uit | **iedere ingelogde gebruiker** |
| Wekker stoppen | **iedere ingelogde gebruiker** |
| Een melding wegklikken ("Begrepen") | **iedere ingelogde gebruiker** |
| Geluid zoeken, voorbeeld spelen ([15.11](#1511-domotiapp_alarmpreviewstart)) | iedere ingelogde gebruiker |
| `entities/list`, `updates/subscribe` | iedere ingelogde gebruiker |
| Labels aanmaken en op entiteiten zetten | admin (dat regelt HA zelf) |
| Kaart aan een dashboard toevoegen of configureren | admin (dat regelt HA zelf) |

**Geen enkel commando is admin-only.** Dat is een bewuste keuze en de reden staat
in DomotiApp Scene SPEC 14: klanten draaien Fully Kiosk met een **niet-admin**
account, en juist zij moeten hun wekkers kunnen beheren. Een implementatie die
`require_admin` op `alarms/save` of `alarms/stop` zet, breekt het product voor de
doelgroep — en bij `alarms/stop` betekent het dat de klant zijn eigen wekker niet
kan uitzetten.

Dat dit geen beveiliging is, staat in
[sectie 6.3](#63-dit-is-geen-beveiliging).

Buiten scope voor v1: HA's eigen per-gebruiker entity-policies. Heeft een
gebruiker geen rechten op een speaker, dan faalt de `media_player`-service en
komt dat via de noodrem terug als een mislukte wekker.

---

## 18. Entiteiten die verdwijnen of veranderen

### 18.1 De person-entiteit wordt hernoemd of verwijderd

**Hernoemen: niets gebeurt.** De opslagsleutel is het registry-entry-ID en dat
overleeft hernoemen ([sectie 6.2](#62-de-sleutel-is-het-registry-entry-id)). De
kaart blijft werken, ook als het entity-ID meeverandert, want de kaart-config
verwijst naar het entity-ID en de kaart zoekt de entiteit op — verandert het
entity-ID, dan moet de klant de kaart-config bijwerken. **VOORSTEL:** de kaart
toont dan de melding uit [16.3](#163-wat-de-kaart-doet-zonder-geldige-person),
want het onderscheid tussen "hernoemd" en "verwijderd" is van buiten niet te
zien.

**Verwijderen:**

1. De wekkers van die persoon **blijven in de opslag staan**. Ze worden niet
   automatisch verwijderd: dat zou "person even weghalen" onomkeerbaar maken.
2. De planning van die wekkers wordt **opgezegd** — een wekker voor een
   niet-bestaande persoon gaat niet af. De integratie luistert daarvoor op
   `EVENT_ENTITY_REGISTRY_UPDATED` met `action == "remove"`.
3. De kaart toont **"De gekozen persoon bestaat niet meer."**
4. Wordt de persoon opnieuw aangemaakt, dan krijgt hij een **nieuw**
   registry-entry-ID en begint hij met een lege wekkerlijst. De oude regels
   blijven staan. Dat is hetzelfde gedrag als bij DomotiApp Scene en het moet in
   de klantdocumentatie staan.
5. Er is in v1 **geen opruimoverzicht** om die verweesde regels weg te halen.
   Zie [sectie 20](#20-wat-niet-in-v1-zit).

### 18.2 De person bestaat, maar heeft geen registry-entry

Kan alleen bij een `person` die via YAML is aangemaakt zonder dat HA hem in het
registry heeft gezet — in de praktijk niet, want `PERSON_SCHEMA` eist `CONF_ID`
(`components/person/__init__.py:74-84`) en daarmee komt er een `unique_id`. Toch
vastgelegd: `alarms/get` geeft dan `not_found`, en de kaart toont dat de persoon
niet bruikbaar is. **Nooit terugvallen op het entity-ID als sleutel** — dan zou
één YAML-wijziging de wekkers van iemand stil laten verdwijnen.

### 18.3 De speaker verdwijnt of is onbereikbaar

| Situatie | Gedrag |
|---|---|
| Speaker is `unavailable` op de wektijd | De wekker gaat **niet** af; noodrem [11.1](#111-vóór-het-afspelen-available) en melding [11.7](#117-waar-de-melding-verschijnt-en-hoe-de-klant-hem-wegkrijgt) |
| Speaker bestaat niet meer (uit het registry verwijderd) | Zelfde, met een eigen reden: **"de speaker bestaat niet meer"** |
| Speaker verliest zijn label | De wekker blijft werken. Het label bepaalt wat je **kunt kiezen**, niet wat blijft werken — anders zou een label weghalen stil alle wekkers slopen |
| Speaker verliest `VOLUME_SET` | De wekker gaat af **zonder oploop**, op het ingestelde volume, en er komt een melding dat de oploop niet mogelijk was. **VOORSTEL**: geluid is belangrijker dan de oploop |
| Speaker blijkt een groep te zijn geworden | De wekker gaat af; de oploop wordt overgeslagen met dezelfde melding als hierboven, want het eindvolume is niet voorspelbaar ([7.3](#73-groepen-worden-uitgesloten)) |

In de editor wordt een opgeslagen speaker die niet meer aan de eisen voldoet
**wel getoond**, met een melding erbij, en niet stil op de eerste beschikbare
speaker gezet. Dat is [sectie 19.1](#191-nooit-stil-terugvallen-op-een-default).

### 18.4 De lamp verdwijnt

De wake-up light is optioneel, dus dit mag de wekker niet breken.

- Lamp `unavailable` of verdwenen op de wektijd: het **geluid gaat gewoon af**,
  de lamp niet, en er komt een melding volgens
  [sectie 12](#12-de-wake-up-light).
- Lamp verliest zijn label: blijft werken, zelfde redenering als bij de speaker.
- In de editor: de opgeslagen lamp wordt getoond met een melding dat hij niet
  meer bestaat, en de gebruiker kan hem wissen of vervangen.

### 18.5 Music Assistant is weg

| Situatie | Gedrag |
|---|---|
| Geen geladen MA-config-entry bij het **zoeken** | `sound/search` geeft `not_found`; de editor toont **"Music Assistant is niet beschikbaar. Zonder Music Assistant kan er geen geluid gekozen worden."** |
| Geen geladen MA-config-entry op de **wektijd** | De speaker is dan `unavailable` (MA's `available` bevat `connection.connected`), dus de noodrem vangt het en de melding zegt dat Music Assistant niet bereikbaar was |
| MA aanwezig maar de speaker is verdwenen uit MA | Entiteit wordt `unavailable`; zelfde route |
| `entities/list` zonder MA | `speakers.entities` is leeg. `label_exists` blijft zeggen of het label bestaat, want dat is een labelvraag en geen MA-vraag |

**Music Assistant is een harde afhankelijkheid van dit product.** Speaker en
geluid zijn verplicht, dus zonder MA is er geen wekker aan te maken. Dat is een
productbeslissing van de eigenaar en geen technische noodzaak; de gevolgen staan
hier zodat niemand verrast is.

---

## 19. Foutgedrag

De rode draad: **stil doorgaan is de ergste uitkomst.** Bij dit product nog
sterker dan bij DomotiApp Scene, want een stille fout hier betekent dat iemand
zich verslaapt.

### 19.1 Nooit stil terugvallen op een default

Een waarde die niet valideert **is geen waarde**. Er wordt nooit een default
ingevuld en stil doorgegaan.

Concreet:

- Een `volume_pct` die niet valideert wordt **niet** 40 en niet 100. De wekker
  geldt als onbruikbaar en wordt gemeld.
- Een `time` die niet `HH:MM` is wordt niet naar iets in de buurt geraden.
- Een `speaker` die niet meer aan de eisen voldoet wordt **niet** vervangen door
  de eerste beschikbare speaker.
- De editor toont nooit een waarde uit een levende entiteit als terugval. Dat is
  de fout die DomotiApp Scene twee keer maakte
  ([sectie 5.5](#55-wat-de-editor-bij-openen-doet)).

### 19.2 Onleesbare of ongeldige opslag

Drie gevallen, zoals in DomotiApp Scene SPEC 18.2, en om dezelfde redenen.

**Geval A — het hele bestand is geen geldige JSON.**

Dat handelt HA zelf al af zoals wij het willen
(`helpers/storage.py:369-421`): het bestand wordt hernoemd naar
`<pad>.corrupt.<isotime>`, er wordt `ERROR` gelogd, er komt een **repair issue
met severity CRITICAL**, en `async_load` geeft `None`. Wij voegen daar niets aan
toe en doen er niets aan af. Het origineel is bewaard, dus "niet overschrijven"
is al voldaan.

De klantdocumentatie moet zeggen dat dit zich als reparatiemelding aandient en
dat de data uit het `.corrupt.`-bestand of uit een backup terug te halen is.

**Geval B — het bestand parseert, maar de data van één persoon klopt niet.**

Bijvoorbeeld een `alarms` die geen lijst is, een `time` van `"kwart voor zeven"`,
een `days` met een 9 erin.

1. **Per persoon, niet per bestand.** Eén kapotte persoon maakt de wekkers van
   de huisgenoten niet onbruikbaar.
2. Die persoon wordt gemarkeerd. `alarms/get` geeft `home_assistant_error`; de
   kaart toont **"De opgeslagen wekkers van deze persoon zijn onleesbaar."** en
   biedt **geen** editor aan.
3. **`alarms/save` wordt voor die persoon geweigerd** zolang de markering staat,
   zodat de kapotte data niet per ongeluk overschreven wordt.
4. Er komt een **repair issue** met de naam van de persoon erin, zodat een admin
   het ziet zonder in logs te kijken.
5. **De kapotte data wordt ongewijzigd bewaard en bij elke opslagronde letterlijk
   teruggeschreven.** Gezonde personen kunnen gewoon opslaan.
6. **Er wordt niets gepland voor die persoon.** Een wekker die je niet kunt lezen
   kun je niet betrouwbaar plannen, en gokken is hier het slechtste antwoord.

Waarom regel 5 en niet "helemaal niet schrijven": er is **één Store voor alle
personen samen** ([14.1](#141-waar)). Een schrijfverbod op bestandsniveau zou het
hele huishouden blokkeren om één kapotte persoon, en dan drukt een klant op
Opslaan en gebeurt er niets, om een reden die alleen in een repair issue staat
waar hij niet bij kan. Regel 5 haalt beide eisen tegelijk: niet overschrijven, en
niet blokkeren wat gezond is.

**Wat dat betekent voor de Store-laag.** Dezelfde constructie als DomotiApp
Scene SPEC 18.2.2: valideren is niet hetzelfde als parsen, en de laag bewaart het
onbewerkte materiaal naast het bewerkte.

```python
# schets, geen definitieve code
self._persons: dict[str, PersonData] = {}          # gevalideerd
self._corrupt: dict[str, tuple[Any, str]] = {}     # onbewerkt + reden
```

Bij het wegschrijven worden beide samengevoegd; de kapotte waarde gaat er
**letterlijk** weer in, niet opnieuw opgebouwd, niet genormaliseerd, niet door
een dataclass heen. Geen sleutel komt in beide dicts voor.

**Geval C — het bestand parseert, maar `data.persons` is geen object.**

Zeldzaam en in de praktijk alleen na handmatig bewerken. Er is dan **geen enkele
sleutel**, dus niets om per persoon te markeren en niets om bij een schrijfronde
terug te zetten.

1. **De hele opslag geldt als onbruikbaar.**
2. `ERROR` gelogd, met de opslagsleutel en wat er is aangetroffen.
3. Een **repair issue**.
4. **Er wordt niet geschreven.** In deze toestand helemaal niet.
5. Alle commando's die de opslag lezen of schrijven geven
   `home_assistant_error`.
6. **Er wordt niets gepland.** Geen enkele wekker gaat af.

Regel 4 wijkt bewust af van geval B: daar was "niet schrijven" fout omdat het
gezonde personen zou blokkeren; hier zijn er geen gezonde personen. Dan wint
[19.1](#191-nooit-stil-terugvallen-op-een-default).

**Hoe een admin eruit komt:** `.storage/domotiapp_alarm.alarms` uit een backup
terugzetten of verwijderen, HA herstarten of de integratie herladen, en de
wekkers opnieuw instellen. Dat is handwerk en dat is hier verdedigbaar: deze
toestand ontstaat niet vanzelf. De reparatiemelding zegt dit ook.

### 19.3 Falende service-aanroepen

Elke aanroep naar `music_assistant.play_media`, `media_player.volume_set` en
`light.turn_on` wordt **afgevangen**, niet genegeerd, en de uitkomst wordt
gebruikt. Een mislukte aanroep leidt tot de melding uit
[11.7](#117-waar-de-melding-verschijnt-en-hoe-de-klant-hem-wegkrijgt).

Let op de asymmetrie die in fase 0b gemeten is: aan de MA-kant geeft afspelen op
een offline speaker een fout (`PlayerUnavailableError`), maar **`volume_set`
geeft HTTP 200 en wordt stil genegeerd**. Op het niveau van HA's
service-dispatch komt geen van beide door. De noodrem uit
[sectie 11](#11-de-noodrem) is daarom de enige betrouwbare controle, en het
afvangen van excepties is een aanvulling en geen vervanging.

### 19.4 Nooit gooien op modulescope

Alles wat de kaartbundel bij het laden uitvoert, mag nooit gooien: die code
draait op élke pagina van élke gebruiker. Registreren gaat via
`src/registreer.js` met de wachtlus op HA's registry, en `window.customCards`
wordt met een guard gevuld. Zie `CLAUDE.md` valkuil 1 en
`docs/fase-1/RAPPORT.md` taak D.

### 19.5 Logniveaus

**VOORSTEL**

| Niveau | Waarvoor |
|---|---|
| `ERROR` | onleesbare opslag, mislukte schrijfactie, een wekker die niet is afgegaan |
| `WARNING` | lamp kon niet aan; speaker verloor `VOLUME_SET`; oploop moest clampen; twee wekkers op dezelfde speaker |
| `INFO` | een wekker overgeslagen wegens het respijtvenster — `kind: "skipped_grace_window"` ([13.4](#134-het-respijtvenster-30-minuten)) |
| `DEBUG` | registraties, hashberekening, elke planningsronde, elke opslagronde, welke MA-config-entry gekozen is |

`INFO` staat er voor **precies één geval**, en het onderscheid met `DEBUG` is
precies waar het om gaat: het respijtvenster is een gebeurtenis waar de klant
**niets aan kon doen** — Home Assistant stond uit — en dat hoort in een log dat
een beheerder zonder debugniveau leest. Een wekker die de klant **zelf** heeft
overgeslagen is verwacht gedrag: dat is exact wat hij vroeg, en dus `DEBUG`.

Beide gevallen leveren wél een mededeling op de kaart op
([11.7](#117-waar-de-melding-verschijnt-en-hoe-de-klant-hem-wegkrijgt)); het
logniveau gaat over de beheerder, de mededeling over de klant.

Verder geen `INFO` bij normaal gebruik — een integratie die bij elke druk op de
knop logt, vervuilt de logs van de klant.

---

## 20. Wat NIET in v1 zit

Elk punt met één regel waarom.

| Niet in v1 | Waarom |
|---|---|
| **Snooze** | Vergt een tweede planningsvorm, een eigen knop in de stoptoestand en een besluit over hoe vaak; eigen ontwerpronde. |
| **Meerdere speakers per wekker** | Groepen zijn uitgesloten omdat groepsvolume relatief is ([7.3](#73-groepen-worden-uitgesloten)); per speaker afzonderlijk oplopen vergt N oplopen met N faalgevallen. |
| **Gesproken berichten** (tijd, weer, agenda) | Dat is TTS met een eigen contract, eigen faalgevallen en een eigen plek in de editor; niets ervan raakt de laadketen of de opslag zoals die nu is. |
| **Wekkers gekoppeld aan aanwezigheid** | "Alleen als ik thuis ben" vergt een tweede voorwaarde in de planner en een besluit over wat er gebeurt als de persoon halverwege thuiskomt. |
| Wake-up light met opbouw | Vastgelegd is "aan op de wektijd, geen opbouw"; opbouw is een tweede oploop met eigen stappen en eigen afbreekvoorwaarden. |
| Kleur of kleurtemperatuur voor de wake-up light | Helderheid dekt het geval; kleur vergt de hele `supported_color_modes`-machinerie uit DomotiApp Scene. |
| Meerdere lampen per wekker | Zelfde reden als meerdere speakers, zonder de volumeproblematiek maar met dezelfde uitbreiding van het schema. |
| Automatisch stoppen op beweging of aanwezigheid | Zou de stopknop overbodig moeten maken en is precies het soort mechanisme dat stil faalt. |
| Een opruimoverzicht voor verweesde opslag | v1 heeft geen options flow; de opslag van een verwijderde person blijft staan ([18.1](#181-de-person-entiteit-wordt-hernoemd-of-verwijderd)) en dat is terug te draaien, wat automatisch opruimen niet is. |
| Meerdere personen op één kaart | De kaart is per persoon; meerdere personen maakt de opslagsleutel meerledig en de stoptoestand ambigu. |
| Wekkers importeren of exporteren | Geen vraag naar; de opslag zit in HA's backup. |
| Een pop-up bij afgaan | Vastgelegd: de kaart verandert zelf van vorm ([sectie 4](#4-de-kaart-terwijl-een-wekker-afgaat)). |
| Rechten per persoon | Het is geen beveiliging ([6.3](#63-dit-is-geen-beveiliging)) en admin-only zou de doelgroep uitsluiten ([sectie 17](#17-rechten)). |
| Meertaligheid buiten NL en EN | Het product is Nederlandstalig; `en.json` is er alleen zodat een niet-Nederlandse installatie geen ruwe sleutels toont. |
| Instellingen op de integratie | De config flow is bewust leeg; alles wat instelbaar is, is per wekker. |

### 20.1 Bekende beperkingen

1. **Buiten de kaart om stoppen wordt niet gemerkt.** Zie
   [sectie 10](#10-hoe-de-wekker-gestopt-wordt).
2. **De kaart moet openstaan om als stopknop te dienen, en de stoptoestand werkt
   niet op HA's ingebouwde panelen.** Vastgelegd als beperking, niet als iets dat
   opgelost wordt.

   Reden: op ingebouwde panelen zoals `/home/overview` worden
   Lovelace-resources niet geladen, dus de kaart komt daar alleen binnen via
   `add_extra_js_url` — en dat werkt alleen met een verse `index.html`. Fase 1
   heeft aangetoond dat een browser die HA al kende vóór de installatie een
   verouderde `index.html` uit zijn service-workercache haalt, waardoor de kaart
   op zo'n paneel helemaal niet laadt (`docs/fase-1/RAPPORT.md`, taak H).

   **De instructie in de klantdocumentatie is daarom:** zet de kaart op een
   **eigen Lovelace-dashboard in sections-weergave**, en zet dát dashboard open op
   het wandtablet en op de telefoon. Niet op een ingebouwd paneel.

   De consequentie als de eigenaar dat niet doet: de wekker gaat wél af — de
   integratie plant en vuurt onafhankelijk van de browser — maar er is geen
   stopknop en hij stopt pas na 30 minuten
   ([9.4](#94-de-wekker-stopt-na-30-minuten)).
3. **De volumeresolutie is alleen op Sonos gemeten.** `0.31` → `0.31`,
   `0.32` → `0.32`, `0.33` → `0.33`, exact — gemeten door de eigenaar, augustus
   2026. **Chromecast, WiiM en Bluesound zijn niet getoetst.**

   Dit geldt als **aanvaard risico**. HA rekent `int(volume * 100)`
   (`components/music_assistant/media_player.py:315-318`) en geeft dus 100 stappen
   door; wat het apparaat daarmee doet, is aan het apparaat. Rondt een speaker af
   naar stappen van 5 of 10, dan klinkt de oploop op dat merk trapsgewijs. De
   uitweg is dan de stapconstante uit
   [9.3](#93-de-volume-oploop) verlagen naar wat dat apparaat aankan; het product
   hoeft er niets aan te veranderen.
4. **Volledige zekerheid dat er geluid is bestaat niet.** Zie
   [sectie 11.5](#115-volledige-zekerheid-bestaat-niet).
5. **Een wekker tussen 02:00 en 02:59 gaat twee nachten per jaar mis.** De editor
   waarschuwt ([5.3](#53-de-zomertijdwaarschuwing)); het gedrag wordt niet
   gerepareerd.
6. **Een MA-speaker kan niet aangezet worden.** `power_control` was bij alle
   geteste players `"none"` ([7.2](#72-vaststellen-dát-het-een-ma-speaker-is)).
7. **De opgeslagen URI kan verouderen** als de provider opnieuw gekoppeld wordt
   ([8.2](#82-sla-de-uri-op-niet-de-naam)).
8. **Een geluid dat niet meer bestaat wordt pas ACHTERAF opgemerkt.** Er is geen
   voorafgaande controle op de URI meer; die is in fase 3c-bis vervallen omdat ze vals
   alarm sloeg voor een hele provider ([11.2](#112-de-uri-wordt-niet-vooraf-gecontroleerd)). Gevolg: een verouderde URI leidt tot
   een wekker die **wel afgaat maar stil blijft**. Dat wordt opgemerkt door de controle
   vijf seconden ná het starten ([11.3](#113-een-paar-seconden-ná-het-starten)), en de
   melding zegt dan dat de wekker **"mogelijk niet hoorbaar is geweest"** — niet dat het
   geluid weg is, want dat is op dat moment niet vast te stellen. De klant weet dus wél
   dat er iets mis was, maar niet meteen wát; hij moet zelf een nieuw geluid kiezen om
   het uit te sluiten. De directe controle die dit zou oplossen bestaat aan de MA-kant
   maar is niet via een gepubliceerde service bereikbaar
   ([11.2.2](#1122-voorkeursoptie-zodra-ma-hem-publiceert)); komt die service er, dan
   verdwijnt deze beperking.

   **En als MA de URI wél met een fout afwijst**, gaat de wekker niet af en volgt de
   gewone foutmelding — dat geval is dus niet stil. Er is alleen geen garantie dat het
   zo gaat: MA op schema 31 accepteert elke URI met `://` zonder validatie (gemeten in
   fase 0b).
9. **De volume-oploop begint pas nadat het afspelen bevestigd is, en dat kost tijd.**
   `music_assistant.play_media` wordt **blokkerend** aangeroepen, want anders is er geen
   fout om op te vangen — de terugval zonder `radio_mode`
   ([8.3.1](#831-radio_mode-wordt-voorwaardelijk-meegestuurd)) en de foutmelding uit
   [11.6](#116-bij-falen) hangen er beide aan.

   **Dat blokkerend nodig is, is niet te omzeilen.** `core.py:2953-2959`: met
   `blocking=False` verpakt Home Assistant de aanroep in
   `_run_service_call_catch_exceptions` als achtergrondtaak en geeft `None` terug — de
   exceptie wordt **binnen HA afgevangen** en bereikt de integratie nooit. Niet
   blokkerend aanroepen betekent dus: geen terugval op `radio_mode` en geen foutmelding
   bij een mislukt afspelen. Nagelopen in fase 3c-bis, taak C.

   **GEMETEN, twee keer, op twee providers:**

   | Provider | wektijd → volume 0 | `play_media` blokkeert | totale afwijking |
   |---|---|---|---|
   | `radiobrowser://` (fase 3c, taak I) | 17 ms | **2131 ms** | **+2153 ms** |
   | `somafm://` (fase 3c-bis, taak E) | 10 ms | **2550 ms** | **+2565 ms** |

   Tussen 2,1 en 2,6 seconden, en het verschil zit niet in de provider maar in MA die de
   stream opzet. Er is dus geen provider te kiezen die dit wegneemt. (Het verschil van
   17 naar 10 ms in de eerste kolom is het vervallen van de URI-controle uit
   [11.2](#112-de-uri-wordt-niet-vooraf-gecontroleerd): die kostte 5 ms.)

   De oploop begon daardoor op +3,1 s respectievelijk +3,6 s, en bereikte het ingestelde
   niveau op **+22,3 s** en **+22,7 s** in plaats van +20 s.

   **Dit is onschadelijk zolang het volume op 0 staat** — en dat doet het, want dat is
   stap 2 van [9.1](#91-de-volgorde) — dus die aanloop is stil in plaats van hard. Maar
   het betekent dat *"van stil naar het ingestelde niveau in 20 seconden"*
   ([9.3](#93-de-volume-oploop)) in de praktijk **20 seconden ná het starten van het
   geluid** is en niet 20 seconden na de wektijd. Bij een trager antwoord van de
   provider loopt de hele oploop mee naar achteren. Er is geen bovengrens gemeten en dus
   ook geen bovengrens vastgelegd.

   **Twee uitwegen zijn nagelopen in fase 3c-bis en beide afgewezen**, zie
   `docs/fase-3c/RAPPORT-BIS.md`: niet-blokkerend aanroepen kost de foutdetectie (zie
   hierboven), en de oploop laten starten vóórdat het afspelen bevestigd is verandert de
   stappenorde van [9.1](#91-de-volgorde) én de betekenis van het `started`-event. Dat
   tweede is een reële optie, maar het is een ontwerpwijziging en geen reparatie.

10. **`radio_mode` kan alleen met een streamingprovider.** Zonder een provider met
   `SIMILAR_TRACKS` stopt een los nummer na een paar minuten; het veld wordt dan
   weggelaten en de editor waarschuwt
   ([8.3.1](#831-radio_mode-wordt-voorwaardelijk-meegestuurd)).
11. **`audiobook` is niet getoetst.** Zes van de zeven mediasoorten zijn gemeten
    ([8.2.1](#821-welke-soorten-getoetst-zijn)); voor luisterboeken was er geen
    provider. Werkt het niet, dan is dat één regel in de soortenlijst.
12. **Er is één melding per wekker.** Een nieuwe overschrijft de vorige, dus een
    wekker die gisteren mislukte en vanochtend gemist werd toont alleen dat
    laatste ([14.2.1](#1421-één-veld-voor-fouten-én-mededelingen)).
13. **De afgaan-toestand is niet beschikbaar voor automatiseringen.** Het is een
    abonnement en geen entiteit
    ([15.9](#159-domotiapp_alarmupdatessubscribe)).
