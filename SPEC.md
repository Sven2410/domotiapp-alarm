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

### 3.2 Met wekkers

Een lijst, één rij per wekker, in de volgorde uit
[sectie 3.4](#34-sorteervolgorde). Per rij:

| Onderdeel | Inhoud |
|---|---|
| Tijd | `06:45`, groot en als eerste — dat is waar de gebruiker naar kijkt |
| Naam | de naam van de wekker, onder of naast de tijd |
| Herhaaldagen | `ma di wo do vr` — of **"Eenmalig"** als er geen dag is aangevinkt |
| Schakelaar | aan/uit, accentkleur `#026FA1` als hij aan staat |

Onderaan de kaart, één regel: **wanneer de eerstvolgende wekker afgaat**, in de
vorm **"Morgen 06:45"**. Zie [sectie 3.3](#33-de-regel-eerstvolgende-wekker).

Een wekker is per rij:

- **te verwijderen** — [sectie 15.4](#154-domotiapp_alarmalarmsdelete);
- **eenmalig over te slaan** — [sectie 15.5](#155-domotiapp_alarmalarmsskip_next).
  Een overgeslagen wekker blijft in de lijst staan, met de tekst
  **"Morgen overgeslagen"** in plaats van de herhaaldagen, en met de schakelaar
  nog aan.

**VOORSTEL** voor hoe verwijderen en overslaan bereikbaar zijn: een
overloopmenu (drie puntjes) per rij met twee items, **"Overslaan"** en
**"Verwijderen"**. Verwijderen vraagt een bevestiging; overslaan niet, want dat
is omkeerbaar met dezelfde knop.

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
| Geen enkele wekker aan | `Geen wekker actief` |

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
[sectie 15.9](#159-domotiapp_alarmringingsubscribe).

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

| Situatie | Wat de editor toont |
|---|---|
| Label bestaat **niet** | **"Het label 'Music Assistant Wekker' bestaat nog niet. De beheerder moet dat label aanmaken en op de speakers zetten die als wekker mogen dienen."** |
| Label bestaat, **geen** entiteiten | **"Er zijn nog geen speakers met het label 'Music Assistant Wekker'."** |
| Label bestaat, entiteiten vallen af op [7.2](#72-vaststellen-dát-het-een-ma-speaker-is) | **"De gelabelde speakers zijn geen Music Assistant-speakers, of ze kunnen geen volume instellen."** |

In alle drie de gevallen:

- de plusknop **blijft werken** — de gebruiker mag de editor openen en zien
  waarom het niet gaat;
- **Opslaan is uitgeschakeld**, met de melding erbij, want speaker en geluid zijn
  verplicht;
- de melding is **geen** foutkleur maar `--secondary-text-color`: dit is een
  installatiestap die nog moet gebeuren, geen storing.

Voor de wake-up light geldt hetzelfde, met één verschil: die is **optioneel**, dus
een ontbrekend label `Verlichting Wekker` blokkeert niets. De keuze wordt dan
niet aangeboden en er staat één regel bij waarom.

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
  werkt;
- de noodrem controleert de URI vóór het afspelen
  ([sectie 11.2](#112-de-uri-wordt-vooraf-gecontroleerd));
- faalt hij, dan is de melding **"Het gekozen geluid bestaat niet meer"** met de
  opgeslagen naam erin, en niet een kale URI.

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
artiesten** terug. Een naam identificeert een item dus **niet** uniek. Dat is de
reden dat de URI-controle in
[sectie 11.2](#112-de-uri-wordt-vooraf-gecontroleerd) niet op naam mag leunen.

### 8.3 Afspelen

`music_assistant.play_media` op de gekozen speaker, met `media_id` = de
opgeslagen `uri`.

**Radio en afspeellijst zijn de soorten die bij een wekker passen**, want die
hebben een onbepaalde duur. Een los nummer van drie minuten stopt van zichzelf en
dan is de wekker stil terwijl niemand wakker is.

#### 8.3.1 `radio_mode` wordt in fase 3 uitgezocht

`music_assistant.play_media` heeft een veld **`radio_mode`**
(`components/music_assistant/services.yaml:48-50`). Werkt dat, dan speelt MA na
het gekozen item eindeloos door in dezelfde stijl, en is een los nummer wél een
bruikbare wekker.

**Fase 3 stelt vast of dat werkt**, door `radio_mode: true` mee te sturen bij een
`track` en te meten of er na het einde van het nummer nog geluid is. Twee
uitkomsten, beide hier vastgelegd zodat fase 3 niet hoeft te improviseren:

**Tak A — `radio_mode` werkt.** Dan stuurt de integratie `radio_mode: true` mee
bij elk geluid met een eindige duur (`track`, `podcast`, `audiobook`), en
**vervalt de waarschuwing hieronder**. De editor zegt dan niets bijzonders over
de soort; alle soorten zijn gelijkwaardig. De wekker stopt dan alleen door de
gebruiker of door de 30-minutentimer
([9.4](#94-de-wekker-stopt-na-30-minuten)).

**Tak B — `radio_mode` werkt niet, of niet betrouwbaar.** Dan blijft de
waarschuwing staan en wordt hij bindend: de editor **waarschuwt** bij `track`,
`podcast` en `audiobook`, niet blokkerend:

> **Dit geluid stopt van zichzelf.** Een los nummer is na een paar minuten
> voorbij; daarna is het stil. Kies een afspeellijst of een radiostation als de
> wekker moet blijven spelen tot je hem uitzet.

Fase 3 legt de uitkomst vast in het faserapport en **werkt deze subsectie bij**
naar de tak die het geworden is — dat is een SPEC-correctie waar bij voorbaat om
gevraagd is, dus melden en doorgaan is hier voldoende.

---

## 9. Afgaan

### 9.1 De volgorde

Op de wektijd, in deze volgorde:

1. **Noodrem vooraf** ([sectie 11.1](#111-vóór-het-afspelen-available)) — is de
   speaker beschikbaar, en is de URI geldig?
2. **Volume op 0** zetten op de speaker.
3. **Wake-up light aan**, als die is ingesteld ([sectie 12](#12-de-wake-up-light)).
4. **Geluid starten** via `music_assistant.play_media`.
5. **Volume-oploop** starten: van 0 naar het ingestelde niveau in 20 seconden.
6. **Noodrem achteraf** ([sectie 11.3](#113-een-paar-seconden-ná-het-starten)) —
   een paar seconden later opnieuw controleren.
7. **Stoptimer** van 30 minuten zetten.

Stap 2 vóór stap 4 is essentieel: start je het geluid op het oude volume en zet
je het daarna op 0, dan is er één harde uitbarsting voordat de oploop begint.

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

### 11.2 De URI wordt vooraf gecontroleerd

**GEMETEN** in fase 0b: de MA-server op **schema 31** valideert de URI **niet**
vóór het afspelen — `verify_item_uri` bestaat pas vanaf schema 33, en op 31 wordt
een URI die `://` bevat direct geaccepteerd
(`components/music_assistant/media_player.py:494-498`). Een verouderde URI faalt
daardoor stil.

De integratie controleert dus zelf dat het opgeslagen geluid nog bestaat. **Hoe
dat gebeurt, wordt in fase 3 uitgezocht.**

**Fase 3 zoekt eerst naar een directe controle.** In de
`music_assistant_client`-bibliotheek staat het volledige commando-oppervlak van de
MA-server; fase 3 gaat daar na of er een aanroep is die van één URI zegt of hij
nog bestaat — bijvoorbeeld een `get_item`-achtige aanroep op URI, of
`verify_item_uri` dat op een nieuwere schemaversie wél bestaat. De testinstance
draaide schema 31; een klant kan een nieuwere server hebben, dus de controle mag
**per schemaversie verschillen** zolang het gedrag hetzelfde is.

**Tak A — er is een directe controle.** Die wordt gebruikt. Eén aanroep, één
antwoord, geen naamvergelijking.

**Tak B — er is niets beters.** Dan is de terugval een `music_assistant.search`
op de opgeslagen `name`, beperkt tot het opgeslagen `media_type`, waarbij gekeken
wordt of de opgeslagen `uri` **letterlijk** in de treffers voorkomt.

> **Tak B is niet waterdicht, en dat moet in de code staan.** De meting uit
> [8.2.1](#821-welke-soorten-getoetst-zijn) laat zien waarom: op
> `"Ghost Stories"` kwamen **twee albums met dezelfde naam van verschillende
> artiesten** terug. Een naam identificeert een item dus niet uniek.
>
> Concrete gevolgen van tak B, die als bekende beperking gelden:
>
> - **Vals positief:** staat er een gelijknamig item in de bibliotheek waarvan de
>   URI wél bestaat, dan kan de controle "geldig" zeggen over een URI die dood
>   is — als de vergelijking op naam in plaats van op URI zou gebeuren. Daarom is
>   de vergelijking **op de URI-string** en niet op de naam; de naam dient alleen
>   om de zoekopdracht te richten.
> - **Vals negatief:** is het item er nog maar geeft de zoekopdracht het niet
>   terug — een andere sorteervolgorde, een `limit` die te laag is, een
>   wisselvallige provider zoals RadioBrowser in fase 0b — dan meldt de controle
>   onterecht dat het geluid weg is en gaat de wekker niet af. **Dat is het
>   ergste faalgeval van tak B**, want het maakt van een werkende wekker een
>   stille.
> - Om dat te beperken gebruikt tak B een ruime `limit` (**50**, het maximum uit
>   [15.6](#156-domotiapp_alarmsoundsearch)) en faalt hij **niet** op een
>   time-out of een fout van de zoekopdracht: kan de controle niet worden
>   uitgevoerd, dan wordt de wekker **wél** gestart. Liever een wekker die
>   misschien niets speelt dan een wekker die zeker niets speelt.

Fase 3 legt vast welke tak het geworden is en **werkt deze subsectie bij**. Dat is
een SPEC-correctie waar bij voorbaat om gevraagd is.

### 11.3 Een paar seconden ná het starten

**Opnieuw** controleren dat de speaker niet `unavailable` is. Dat vangt de
speaker die tijdens het starten wegvalt — het geval waarin de aanroep slaagde en
er tóch geen geluid is.

**VOORSTEL: 5 seconden ná stap 5** van [9.1](#91-de-volgorde). Lang genoeg dat
MA de stream heeft opgezet, kort genoeg dat de klant nog niet is doorgeslapen.

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

Teksten bij `severity: "error"`:

| `kind` | Tekst op de kaart |
|---|---|
| `speaker_unavailable` | **"De wekker van 06:45 is niet afgegaan: de speaker 'Slaapkamer' was niet bereikbaar."** |
| `ma_unavailable` | **"De wekker van 06:45 is niet afgegaan: Music Assistant was niet bereikbaar."** |
| `sound_gone` | **"De wekker van 06:45 is niet afgegaan: het gekozen geluid 'Beat Blender' bestaat niet meer. Kies een nieuw geluid."** |
| `speaker_lost_during_play` | **"De wekker van 06:45 is mogelijk niet hoorbaar geweest: de speaker 'Slaapkamer' viel weg tijdens het spelen."** |
| `light_failed` | **"De wekker is afgegaan, maar de lamp 'Bedlamp' kon niet aangezet worden."** |
| `volume_ramp_unavailable` | **"De wekker is afgegaan op het ingestelde volume; het oplopende volume was op deze speaker niet mogelijk."** |

Teksten bij `severity: "notice"`:

| `kind` | Tekst op de kaart |
|---|---|
| `skipped_grace_window` | **"Je wekker van 06:45 is niet afgegaan omdat Home Assistant uit stond."** |
| `skipped_by_user` | **"De wekker van 06:45 is overgeslagen, zoals je had ingesteld."** |

De eerste is de tekst die de eigenaar heeft vastgelegd, en de reden dat deze hele
categorie bestaat: dat is precies wat iemand wil weten die zich heeft
verslapen. Het is geen storing en het moet er ook niet als een storing uitzien.

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
4. Is `skip_next` gezet voor dat moment, dan wordt hij overgeslagen en wordt
   `skip_next` gewist.
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

Voor een wekker die door `skip_next` is overgeslagen (stap 4) geldt hetzelfde
mechanisme met `kind: "skipped_by_user"` — óók een mededeling, want de klant heeft
het zelf ingesteld en hoeft er niets aan te doen.

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
| `skip_next` | bool | ja | eenmalig overslaan |
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
Is een wekker gisteren mislukt en vandaag overgeslagen, dan ziet de klant alleen
het overslaan. Dat is aanvaard — de klant wil weten wat er vanochtend gebeurde,
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
| `skip_next` | `false` |
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
            "skip_next": false,
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
            "skip_next": true,
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
            "skip_next": false,
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
- Migraties zijn **puur en zonder verlies**: kan een migratie een veld niet
  omzetten, dan faalt ze in plaats van het veld weg te laten.
- **Migratie slaat kapotte personen over.** Een persoon die niet valideert
  ([sectie 19.2](#192-onleesbare-of-ongeldige-opslag)) wordt niet gemigreerd; hij
  blijft in het oude formaat staan en blijft gemarkeerd. Je kunt niet
  betrouwbaar omzetten wat je niet kunt lezen.

In v1 bestaat er nog geen oudere versie, dus `_async_migrate_func` hoeft alleen
te bestaan en `NotImplementedError` te gooien voor onbekende versies.

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

De server beheert zelf en accepteert **niet** van de kaart: `skip_next`,
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

**VOORSTEL:** een wekker uitzetten **wist `skip_next`**. Uit-en-weer-aan is de
manier waarop iemand "vergeet het maar" intrekt.

### 15.4 `domotiapp_alarm/alarms/delete`

**Invoer:** `person`, `alarm_id`.
**Uitvoer:** als `alarms/get`.
**Fouten:** `not_found`.

Verwijdert de wekker uit de opslag en zegt zijn planning op. Loopt de wekker op
dat moment, dan wordt hij eerst gestopt volgens
[9.4](#94-de-wekker-stopt-na-30-minuten) — inclusief het terugzetten van het
volume. Anders blijft er geluid draaien voor een wekker die niet meer bestaat.

### 15.5 `domotiapp_alarm/alarms/skip_next`

Eenmalig overslaan, en het terugdraaien daarvan.

**Invoer:** `person`, `alarm_id`, `skip` (bool).
**Uitvoer:** als `alarms/get`.

`skip_next` wordt gewist zodra het overgeslagen moment voorbij is, of wanneer de
wekker wordt uitgezet ([15.3](#153-domotiapp_alarmalarmsset_enabled)).

### 15.6 `domotiapp_alarm/sound/search`

Proxy naar `music_assistant.search`. De kaart praat niet rechtstreeks met Music
Assistant: dan zou de kaart de MA-config-entry moeten opzoeken en zou de
filtering in twee talen bestaan.

**Invoer**

| Veld | Type | Verplicht |
|---|---|---|
| `query` | string | ja |
| `media_types` | array van string | nee — weglaten = alle soorten |
| `limit` | int | nee — **VOORSTEL** standaard 10, maximum 50 |

**Uitvoer**

```json
{
  "results": [
    { "name": "SomaFM: Beat Blender", "uri": "somafm://radio/beatblender",
      "media_type": "radio", "image": null,
      "artists": null, "album": null }
  ]
}
```

**Één platte lijst**, niet de acht lijsten van MA. De kaart toont een
zoekresultaat en niet acht koppen; `media_type` per treffer houdt het onderscheid
vast. **VOORSTEL** voor de volgorde: afspeellijsten en radio eerst, want dat zijn
de soorten die bij een wekker passen ([8.3](#83-afspelen)), daarna de rest in de
volgorde waarin MA ze gaf.

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
    "entities": [ { "entity_id": "media_player.slaapkamer", "name": "Slaapkamer" } ]
  },
  "lights": {
    "label_exists": false,
    "entities": []
  }
}
```

`label_exists` maakt het onderscheid uit
[sectie 7.4](#74-wat-de-kaart-toont-als-het-label-nog-niet-bestaat) mogelijk en
komt uit `missing_labels` van `helpers/target.py`.

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

### 15.9 `domotiapp_alarm/ringing/subscribe`

Een abonnement, zodat de kaart weet dat hij een stopknop moet worden zonder te
pollen.

**Invoer:** `type`, en **VOORSTEL** een optionele `person` om alleen de wekkers
van één persoon te ontvangen.

**Berichten**

```json
{ "event": "started", "person": "person.sven", "alarm_id": "a1f4…", "name": "Werk", "time": "06:45" }
{ "event": "stopped", "person": "person.sven", "alarm_id": "a1f4…", "reason": "user" }
{ "event": "failed",  "person": "person.sven", "alarm_id": "f0e3…",
  "reason": "speaker_unavailable",
  "text": "De wekker van 05:20 is niet afgegaan: …" }
```

`reason` bij `stopped` is `"user"`, `"timeout"` (de 30 minuten) of `"deleted"`.

**Dit is een abonnement en geen entiteit.** Vastgelegd.

Het alternatief was een `binary_sensor` per persoon. Dat is afgewezen om twee
redenen: het zou **de entiteitenkiezer van de klant vullen** met entiteiten die hij
nergens voor nodig heeft, en het zou de integratie van `integration_type: service`
in een entiteitenleverancier veranderen. Dit product levert bewust **geen**
entiteiten. Een abonnement houdt de toestand binnen de kaart, waar hij hoort.

De prijs staat er ook bij: de afgaan-toestand is daarmee **niet** beschikbaar voor
automatiseringen van de klant. Dat is aanvaard.

### 15.10 Wat er bewust géén commando is

| Niet | Waarom |
|---|---|
| Een wekker aanmaken zonder speaker of geluid | Ze zijn verplicht; een half opgeslagen wekker is een wekker die stil faalt |
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
| Wekker aanmaken, wijzigen, verwijderen, aan/uit, overslaan | **iedere ingelogde gebruiker** |
| Wekker stoppen | **iedere ingelogde gebruiker** |
| Geluid zoeken, voorbeeld spelen | iedere ingelogde gebruiker |
| `entities/list`, `ringing/subscribe` | iedere ingelogde gebruiker |
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
| `INFO` | een wekker overgeslagen wegens het respijtvenster ([13.4](#134-het-respijtvenster-30-minuten)) |
| `DEBUG` | registraties, hashberekening, elke planningsronde, elke opslagronde, welke MA-config-entry gekozen is |

`INFO` staat er voor precies één geval, en dat is met opzet: een overgeslagen
wekker is een gebeurtenis die de klant raakt zonder dat er iets stuk is. Verder
geen `INFO` bij normaal gebruik — een integratie die bij elke druk op de knop
logt, vervuilt de logs van de klant.

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
8. **`audiobook` is niet getoetst.** Zes van de zeven mediasoorten zijn gemeten
   ([8.2.1](#821-welke-soorten-getoetst-zijn)); voor luisterboeken was er geen
   provider. Werkt het niet, dan is dat één regel in de soortenlijst.
9. **Er is één melding per wekker.** Een nieuwe overschrijft de vorige, dus een
   wekker die gisteren mislukte en vandaag werd overgeslagen toont alleen het
   overslaan ([14.2.1](#1421-één-veld-voor-fouten-én-mededelingen)).
10. **De afgaan-toestand is niet beschikbaar voor automatiseringen.** Het is een
    abonnement en geen entiteit
    ([15.9](#159-domotiapp_alarmringingsubscribe)).
