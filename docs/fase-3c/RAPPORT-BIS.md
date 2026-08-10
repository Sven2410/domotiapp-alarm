# Fase 3c-bis — De URI-controle vervalt

Eén beslissing uitgevoerd: de controle die het geluid vóór het afspelen verifieerde is
weg. Dit is een ronde waarin `SPEC.md` op verzoek gewijzigd is.

**Het bewijs in één regel:** dezelfde wekker die in taak I van fase 3c niet afging —
SomaFM: Beat Blender, op een URI die de zoekopdracht *nog steeds* niet vindt — ging nu
af, met geluid dat 87 seconden lang onafgebroken uit de speaker kwam.

---

## Samenvatting

| | |
|---|---|
| SPEC gewijzigd | 11.2 (herschreven), 11.2.1 (vervallen), 11.2.2 (criterium bijgewerkt), 8.2, 8.2.1, 8.3.1, 11.3, 15.6, 20.1 |
| Code | `noodrem.py` −77 regels, `afvuren.py`: één controle eruit, één melding gewijzigd |
| Tests | **212 geslaagd**; 5 verwijderd, 4 nieuw. Alle 5 gewijzigde/nieuwe tests falen op de oude code |
| Mutaties | 5 op de gewijzigde paden, **alle 5 gevangen** |
| Livecontrole | de SomaFM-wekker gaat af; afwijking **+2,565 s**; audio **0 van 87 s** stil |
| Taak C | nagelopen, **niets gebouwd** — beide uitwegen afgewezen, met vindplaats |

### Taak A — wat er in SPEC veranderd is

**11.2 heet nu "De URI wordt NIET vooraf gecontroleerd"** en legt uit waarom, met de
meting uit taak I als onderbouwing: de opgeslagen naam `"SomaFM: Beat Blender"` geeft
nul treffers in MA's zoekindex, `"Beat Blender"` geeft er drie. De sectie zegt met
zoveel woorden dat dit **geen versoepeling** is, met een tabel die het faalgeval
verschuift in plaats van weghaalt:

| | met de controle | zonder de controle |
|---|---|---|
| URI is dood | wekker gaat **niet** af | wekker gaat af, stil, melding via 11.3 |
| URI leeft, naam niet vindbaar | **wekker gaat niet af** — vals alarm | wekker gaat af en klinkt |
| URI leeft, naam vindbaar | wekker gaat af en klinkt | wekker gaat af en klinkt |

De middelste rij is de reden; de bovenste is de prijs. En er staat expliciet bij dat
11.1, 11.3, 11.4 en 11.6 **onaangeroerd** blijven — wat wegvalt is één hulpaanroep die
iets probeerde vast te stellen over een derde partij en daarbij aantoonbaar vaker
ongelijk had dan gelijk.

**11.2.1 is vervallen** in plaats van geschrapt. De subsectie blijft bestaan met de kop
"VERVALLEN" en legt uit dat de omkering (mislukte controle → wél afgaan) alleen bestond
*voor* die controle, en dat de afweging zelf nog op één plek leeft: bij `radio_mode`
(8.3.1), waar twijfel de **andere** kant op valt. Schrappen zou die verwijzing dood
maken; iemand die zich over 8.3.1 verwondert vindt hier het antwoord.

**11.2.2 heeft een nieuw overstapcriterium**, en dat is de kern van de wijziging daar:

| | vóór 3c-bis | vanaf 3c-bis |
|---|---|---|
| zoekroute | de vastgelegde route | **vervallen**, aantoonbaar zelf-verslaand |
| `music/item_by_uri` | betere alternatief | **de enige mogelijke route** |
| als geen van beide kan | — | **geen voorafgaande controle** |

Er is dus geen terugvaloptie meer. De sectie zegt ook waarom deze route het probleem van
11.2 **per constructie** niet heeft: hij vraagt naar de URI en niet naar de naam, dus er
is geen zoekindex met een providerprefix bij betrokken.

**8.2: de aanbeveling blijft, expliciet.** `name`, `media_type` en `image` worden nog
steeds naast de `uri` opgeslagen — er staat nu bij dat ze bestaan om te **tonen** wat de
klant koos en niet om iets te controleren, en dat juist die opgeslagen naam het verschil
maakt tussen een leesbare melding en een regel machinetaal.

**Vier plekken die naar de vervallen controle verwezen zijn gecorrigeerd**, en dat is
meer dan opruimwerk: elk van de vier had een argument dat nu ergens anders vandaan komt.

- **8.2.1** noemde de twee gelijknamige `"Ghost Stories"`-albums als reden dat de
  controle niet op naam mocht leunen. Die reden is er niet meer; de meting blijft staan
  omdat ze óók voor de **editor** geldt.
- **8.3.1** verwees voor "geen HA-service beschikbaar" naar 11.2 en voor de omkering naar
  11.2.1. Nu staat er dat dit de **enige** plek in het product is waar twijfel tot
  weglaten leidt.
- **15.6** verantwoordde het maximum van 50 met de URI-controle. Dat maximum blijft, nu
  met de reden waarvoor de sectie zelf bestaat.
- **11.3** heeft er een alinea bij: deze controle **draagt meer dan hij deed** en is nu
  het enige net onder een dood geluid. Wie hem ooit wil verlengen of weghalen, haalt meer
  weg dan een tweede blik op de speaker.

**20.1 punt 8 is herschreven** naar de nieuwe beperking: een geluid dat niet meer bestaat
wordt **pas achteraf** opgemerkt, via 11.3, en de melding zegt dan *"mogelijk niet
hoorbaar geweest"* — niet dat het geluid weg is, want dat is op dat moment niet vast te
stellen. Met erbij dat een URI die MA wél met een fout afwijst niet stil faalt, en dat
er geen garantie is dat het zo gaat (schema 31 accepteert elke URI met `://`).

### Taak B — de code

`noodrem.py` verliest `async_controleer_uri` en daarmee 77 regels, plus vier imports die
alleen daarvoor bestonden. `SEARCH_LIMIT_MAX` en `SEARCH_TIMEOUT_SECONDEN` **blijven**:
die worden ook door `websocket.py` gebruikt voor de zoekopdracht van de editor, en dat is
een andere zaak.

**`Uitkomst.ONBEKEND` is weg**, en dat is de interessante consequentie. Die derde
enum-waarde bestond precies voor de URI-controle: dat was de enige controle die kon
mislukken zonder iets over het geluid te zeggen. `controleer_speaker` kan dat niet — een
`hass.states.get` faalt niet. Met één consumer minder gaf niemand hem nog terug, en dan
is het dode documentatie (valkuil 34). Er staat een comment op de plek waar hij stond,
met de reden en de aantekening dat hij **terug moet** zodra 11.2.2 in werking treedt:
`music/item_by_uri` heeft drie uitkomsten, en `ProviderUnavailableError` hoort niet in
een `bool` geperst te worden.

**Wat er nog van de controle afhing, en wat ermee gebeurd is.** Nagelopen op alle vijf
de dingen die de opdracht noemde:

| Wat | Uitkomst |
|---|---|
| time-outs | `SEARCH_TIMEOUT_SECONDEN` blijft, alleen nog voor `sound/search` (SPEC 15.6) |
| limieten | `SEARCH_LIMIT_MAX` blijft, idem; SPEC 15.6 heeft een nieuwe verantwoording |
| foutcodes | geen; de controle gaf geen WebSocket-fouten |
| het onderscheid "URI bestaat niet" / "controle mislukt" | **weg**, met `ONBEKEND` |
| meldingsteksten | `KIND_SOUND_GONE` **blijft bestaan**, met een andere afzender — zie hieronder |

### De melding `sound_gone` verhuist naar een sterkere afzender

`KIND_SOUND_GONE` werd uitsluitend door de URI-controle gestuurd. Zonder ingrijpen zou
die soort onbereikbaar worden en zou SPEC 11.7 een dode rij in zijn tabel hebben. Dat is
niet gebeurd, en de reden is niet verlegenheid:

**een mislukt `play_media` meldt nu `sound_gone` in plaats van `speaker_unavailable`.**
Dat is op twee manieren beter dan wat er stond:

1. `speaker_unavailable` was **onwaar** geworden. De speaker is een paar milliseconden
   eerder nog beschikbaar bevonden (stap 1 van de afvuurvolgorde), dus "de speaker was
   niet bereikbaar" is een mededeling waarvan we weten dat ze niet klopt.
2. De aanroep die het geluid werkelijk zou starten heeft geweigerd. Dat is een **sterker**
   signaal dan een zoekopdracht ooit was — het is de directe uitspraak van de partij die
   het geluid moet leveren, in plaats van een gevolgtrekking uit een zoekindex.

**Wat er niet klopt en niet door mij gerepareerd is:** de tekst van SPEC 11.7 stelt het
zekerder dan we het weten. *"het gekozen geluid 'X' bestaat niet meer"* terwijl we alleen
weten dat het niet startte. Dat is een woordkeuze in een bindende sectie die deze ronde
niet mocht wijzigen, dus hij staat er nog. Als de eigenaar hem wil bijstellen, is
*"kon niet gestart worden"* nauwkeuriger en behoudt het de handeling die helpt
("Kies een nieuw geluid"). Er staat een comment in `afvuren.py` dat hiernaar verwijst.

### Taak D — de tests

**5 tests verwijderd, 4 nieuwe.** De keuze was: weghalen of herschrijven naar een
regressiewacht. **Herschrijven**, en om een concrete reden: de aanroep terugzetten is één
regel code, en het zou opnieuw dezelfde stille storing opleveren. Wat nu vastligt:

| Test | Wat hij vasthoudt |
|---|---|
| `test_er_wordt_geen_uri_controle_meer_gedaan` | er zit **geen** `music_assistant.search` in het afvuurpad |
| `test_een_somafm_wekker_gaat_af` | het geval uit taak I: naam onvindbaar, wekker gaat tóch af |
| `test_een_traag_antwoord_van_ma_houdt_de_wekker_niet_meer_op` | een ontploffende zoekopdracht heeft geen enkel effect meer |
| `test_een_mislukt_afspelen_meldt_het_geluid_en_niet_de_speaker` | `sound_gone` in plaats van `speaker_unavailable` |

**Alle vijf falen op de code van vóór deze ronde.** De URI-controle is daarvoor tijdelijk
teruggezet — inclusief de oude `speaker_unavailable`-melding — en de tests zijn ertegen
gedraaid:

```
FAILED tests/test_afvuren.py::test_de_acht_stappen_gebeuren_in_de_voorgeschreven_volgorde
FAILED tests/test_afvuren.py::test_er_wordt_geen_uri_controle_meer_gedaan
FAILED tests/test_afvuren.py::test_een_somafm_wekker_gaat_af - KeyError: 'mus...
FAILED tests/test_afvuren.py::test_een_traag_antwoord_van_ma_houdt_de_wekker_niet_meer_op
FAILED tests/test_afvuren.py::test_een_mislukt_afspelen_meldt_het_geluid_en_niet_de_speaker
5 failed, 34 deselected in 1.10s
```

Dat `test_een_somafm_wekker_gaat_af` faalt met `KeyError: 'music_assistant.play_media'`
is precies de juiste faalwijze: op de oude code werd er niets afgespeeld, dus die aanroep
staat niet in de lijst.

**Vijf mutaties op de gewijzigde paden, alle vijf gevangen** — waaronder de belangrijkste,
"de URI-controle komt terug" (5 tests falen) en "een mislukt afspelen meldt weer
`speaker_unavailable`" (2 tests falen).

---

## Taak C — De vertraging van `play_media`

**Nagelopen, niets gebouwd.** Beide uitwegen zijn afgewezen, en de eerste op een harde
vindplaats.

### Niet-blokkerend aanroepen kan niet — het kost de foutdetectie

`homeassistant/core.py:2953-2959`:

```python
if not blocking:
    self._hass.async_create_task_internal(
        self._run_service_call_catch_exceptions(coro, service_call),
        f"service call background {service_call.domain}.{service_call.service}",
        eager_start=True,
    )
    return None
```

Met `blocking=False` verpakt HA de aanroep in `_run_service_call_catch_exceptions` en
geeft `None` terug. **De exceptie wordt binnen HA afgevangen en bereikt de integratie
nooit.** Twee dingen die daarop staan, en beide zijn een SPEC-eis:

- de **terugval zonder `radio_mode`** (SPEC 8.3.1, als eis gesteld in fase 3a-bis) — die
  bestaat alleen omdat de HTTP 500 opgevangen kan worden;
- de **foutmelding bij een mislukt afspelen** (SPEC 11.6), die na deze ronde nog
  belangrijker is: het is de plek waar een dood geluid boven komt nu de voorafgaande
  controle weg is.

Niet-blokkerend aanroepen zou dus de twee dingen weghalen die de vervallen URI-controle
moesten opvangen. Dat is geen verbetering maar een ruil in de verkeerde richting.

### De oploop eerder starten kan wél, maar is een ontwerpwijziging

De tweede uitweg: `play_media` als taak starten, de oploop meteen laten beginnen, en de
taak later `await`en om fouten alsnog te zien. Dat werkt technisch, en het zou de oploop
op de wandklok houden — 40 % bereikt op +20 s in plaats van +22,7 s.

Wat het kost, en waarom ik het niet gebouwd heb:

1. **De stappenorde van SPEC 9.1 verandert.** Stap 6 (oploop) zou vóór of gelijk met
   stap 5 (geluid) komen. Dat is de volgorde die SPEC vastlegt.
2. **Het `started`-event verandert van betekenis.** Nu gaat het uit nadat het afspelen
   geslaagd is. Zou de oploop eerder starten, dan moet het event ofwel eerder uit —
   waarna een mislukt afspelen een *"gestarte"* wekker moet terugtrekken — ofwel later,
   waarna de kaart een oplopend volume heeft zonder stopknop.
3. **De eerste hoorbare seconde is niet meer stil.** Het geluid begint dan op 4–6 % in
   plaats van op 0 %. Dat is nog steeds zacht, maar "van stil naar het ingestelde niveau"
   (SPEC 9.3) is dan niet meer letterlijk waar.

Punt 1 en 2 zijn SPEC-wijzigingen, en de opdracht zei: dan stoppen en rapporteren. **Mijn
aanbeveling als de eigenaar het wil aanpakken:** doe het niet met een taak, maar door de
oploop bij te laten **inhalen** — bereken bij de eerste stap hoeveel seconden er sinds de
wektijd verstreken zijn en begin op de bijbehorende stap. Dan blijft de stappenorde
intact, blijft het `started`-event waar het is, en is de oploop op +20 s klaar. Het kost
alleen de eerste paar treden, en die zijn onhoorbaar.

### De meting ligt vast in SPEC 20.1

Toegevoegd als punt 9, met **twee** metingen op twee providers:

| Provider | wektijd → volume 0 | `play_media` blokkeert | totale afwijking |
|---|---|---|---|
| `radiobrowser://` (fase 3c, taak I) | 17 ms | **2131 ms** | **+2153 ms** |
| `somafm://` (fase 3c-bis, taak E) | 10 ms | **2550 ms** | **+2565 ms** |

Tussen 2,1 en 2,6 seconden, en **het verschil zit niet in de provider** maar in MA die de
stream opzet. Er is dus geen provider te kiezen die dit wegneemt — dat was de open vraag
van fase 3c, en die is hiermee beantwoord.

De eerste kolom bevat de bijvangst van deze ronde: van 17 naar 10 ms, want de URI-controle
kostte 5 ms.

---

## Taak E — De livecontrole

Dezelfde wekker als in taak I: `somafm://radio/beatblender`, naam
`"SomaFM: Beat Blender"`, speaker `wekker_slaapkamer`, volume 40 %, lamp op 60 %.

**Eerst nagegaan dat de opzet nog steeds de opzet is** die toen faalde — anders zou de
toets om de verkeerde reden slagen:

```
sound/search op "SomaFM: Beat Blender"  ->  0 treffers, URI niet gevonden
```

Nog steeds onvindbaar. Toen hield dat de wekker tegen; nu niet.

### De wekker gaat af

Server-side tijdstempels, wektijd 00:31:00 (= 22:31:00 UTC):

```
22:31:00.010  media_player.volume_set -> 0.0        +10 ms
22:31:00.015  light.turn_on                         +15 ms
22:31:00.015  music_assistant.play_media            +15 ms
22:31:02.565  >>> afgegaan voor moment 2026-08-11T00:31:00+02:00, oploop naar 40%
22:31:03.566  media_player.volume_set -> 0.02
…
22:31:22.675  media_player.volume_set -> 0.4
22:31:22.679  >>> Oploop klaar op 40% in 20 stappen
```

**Er staat geen `music_assistant.search` meer in.** Dat is de wijziging, live: de eerste
aanroep van het afvuurpad is nu de `volume_set` naar 0.

**Totale afwijking: +2,565 s**, waarvan 2,550 s `play_media`. De noodrem kost nu 10 ms
in plaats van 17.

### De oploop, aan de speakerkant

Uit het log van de snapclient in de MA-container — dus niet HA's boekhouding maar wat de
speaker werkelijk kreeg:

```
00-31-00.012  volume 0
00-31-03.567  volume 2
00-31-04.574  volume 4
…
00-31-21.671  volume 38
00-31-22.676  volume 40
```

Twintig stappen, cadans 1,005–1,007 s, eindvolume exact 40.

### En er kwam geluid uit — herhaalbaar

De audiometing uit taak I is herhaald, en dit is het beste bewijs in dit project:

| Venster | Duur | `No chunks available` | Uitkomst |
|---|---|---|---|
| vóór het afgaan (00:30:00–00:31:03) | 63 s | **64** | stil |
| **tijdens de wekker (00:31:03–00:32:30)** | **87 s** | **0** | **AUDIO LIEP** |

Nul van 87 seconden stilte. In taak I was het nul van 97 — op een andere provider en met
een andere URI. De meting is dus herhaalbaar, en ze doet wat SPEC 11.5 zegt dat de
integratie zelf nooit kan: aantonen dat er geluid uit de speaker komt.

### Stoppen

| | |
|---|---|
| vóór de stop | volume 0,40, state `playing` |
| ná de stop | volume **0,55**, state `idle` |
| gelijk aan de stand vóór de wekker | **ja** |
| `ringing` | leeg |
| `last_message` | **`null`** — geen vals alarm, en dat is het punt van deze ronde |
| lamp | blijft aan (SPEC 9.4) |
| events | `started`, dan `stopped/user` |

Dat `last_message` `null` is, is de kortste samenvatting van de hele ronde: dezelfde
wekker die in taak I een `sound_gone`-fout en een `persistent_notification` achterliet,
laat nu niets achter omdat er niets mis was.

---

## Wat niet lukte

### De vertraging van `play_media` is niet weggenomen

Zie [taak C](#taak-c--de-vertraging-van-play_media). Niet-blokkerend aanroepen kan niet
zonder de foutdetectie te verliezen, en de oploop eerder starten is een SPEC-wijziging.
De meting ligt vast; de keuze ligt bij de eigenaar. Mijn aanbeveling — de oploop laten
inhalen in plaats van eerder starten — is niet gebouwd en niet getoetst.

### SPEC 11.7's tekst voor `sound_gone` stelt het te zeker

*"het gekozen geluid bestaat niet meer"* terwijl de code alleen weet dat het niet
startte. De soort is de juiste, de tekst claimt meer dan we kunnen zien. Niet gewijzigd:
11.7 stond niet in de opdracht en is bindend.

### Eén onnauwkeurigheid in de opdracht, voor de volledigheid

De opdracht zegt "Spotify en podcasts zijn zelf-vindbaar". Gemeten is dat voor
**`radiobrowser://`** en iTunes-podcasts; Spotify is op deze instance niet te toetsen
omdat de OAuth-callback niet terugkomt (fase 0b). Voor de beslissing maakt het niets uit —
één zelf-vindbare provider is al genoeg om te weten dat het providerspecifiek is — maar
het staat hier zodat de vindplaats klopt.

### De cadans is nog steeds niet als "vloeiend" beoordeeld

Onveranderd sinds fase 3c: 1,005–1,007 s per stap is gemeten aan twee kanten, maar of het
vloeiend *klinkt* vraagt een oor.

---

## Aannames

1. **Een mislukt `play_media` meldt `sound_gone`.** SPEC schrijft geen soort voor bij een
   mislukt afspelen; `speaker_unavailable` was onwaar geworden en `sound_gone` is de
   soort die het dichtst bij de oorzaak zit en de juiste handeling geeft. Zie de
   verantwoording hierboven. Dit houdt de rij in SPEC 11.7 in gebruik.

2. **`Uitkomst.ONBEKEND` is verwijderd in plaats van bewaard.** Een enum-waarde die
   niemand teruggeeft is dode documentatie (valkuil 34). De reden staat als comment op de
   plek, met de instructie hem terug te zetten zodra SPEC 11.2.2 in werking treedt.

3. **11.2.1 blijft als "VERVALLEN"-subsectie bestaan** in plaats van geschrapt te worden.
   Er verwijst nog een sectie naar (8.3.1, voor de omgekeerde afweging bij `radio_mode`),
   en een dode verwijzing zou die uitleg onvindbaar maken.

4. **`SEARCH_LIMIT_MAX` en `SEARCH_TIMEOUT_SECONDEN` blijven op 50 en 10.** Hun
   oorspronkelijke verantwoording (het valse negatief van de URI-controle) is vervallen,
   maar ze worden nog gebruikt door `sound/search` en er is geen reden ze te veranderen.
   SPEC 15.6 heeft een nieuwe verantwoording voor het maximum gekregen.

5. **De vier tests die de controle toetsten zijn vervangen, niet weggehaald.** De opdracht
   liet de keuze; de reden voor herschrijven is dat de aanroep terugzetten één regel is.

---

## `git status --porcelain`

```
M  CLAUDE.md
M  SPEC.md
M  custom_components/domotiapp_alarm/afvuren.py
M  custom_components/domotiapp_alarm/noodrem.py
A  docs/fase-3c/RAPPORT-BIS.md
M  tests/test_afvuren.py
```
