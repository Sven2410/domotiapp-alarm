# Fase 3c — Het afvuren

Van noodrem tot stoptimer. Hierna is de server-side laag **compleet**: fase 4 kan de
kaart bouwen zonder dat er nog iets aan de serverkant bij moet.

**SPEC.md is gewijzigd op precies één plek**, en dat is de plek waar deze ronde om
vroeg: de verduidelijking bij SPEC 13.4 stap 4. Zie [Taak A](#taak-a--de-verduidelijking-in-spec-134-stap-4).

**De livecontrole (taak I) is gedaan**, in een tweede ronde nadat de eigenaar op Music
Assistant had ingelogd. Alle vijf de toetsen zijn uitgevoerd, en ze leverden **één
bevinding op die zwaarder weegt dan de rest van deze fase**: de URI-controle van SPEC
11.2 maakt van een werkende SomaFM-wekker een stille. Zie
[Taak I](#taak-i--de-livecontrole-in-twee-rondes).

**Er is één ding dat de eigenaar moet beslissen voordat dit product bij een klant komt.**
Dat staat onder [BEVINDING](#bevinding--de-uri-controle-van-spec-112-maakt-van-een-werkende-wekker-een-stille).
SPEC en code zijn daarvoor **niet** gewijzigd: de implementatie doet wat SPEC
voorschrijft, het defect zit in het voorgeschreven ontwerp, en dan is de afspraak melden
en stoppen.

---

## Taak A — De verduidelijking in SPEC 13.4 stap 4

Toegevoegd, letterlijk als clausule onder stap 4: een gemist moment dat **buiten het
respijtvenster** viel verbruikt `skip_next` óók, ook al is er niets afgegaan. Met de
reden erbij, want dat is wat een clausule ervan weerhoudt over twee jaar opnieuw als
open vraag op te duiken:

> `skip_next` betekent *"de eerstvolgende keer niet"*, en die keer is voorbij — of hij
> nu gemist werd door een herstart of bewust is overgeslagen. Bij de andere lezing zou
> een overslag **dagenlang blijven hangen** als Home Assistant een paar keer uit is
> geweest, en dan gaat de wekker niet af terwijl niemand nog weet waarom.

Plus de asymmetrie die de keuze draagt: een overslag die te lang meegaat is een
**stille wekker**; een overslag die één ochtend te vroeg opgaat is een wekker die
afgaat terwijl je hem uit had willen hebben — en dát merk je meteen.

En de consequentie voor de code staat er expliciet bij: de `skip_next`-controle staat
**vóór** de venstertoets van stap 5 en 6. Dat is hoe fase 3b het al bouwde; er is
geen code veranderd.

---

## Samenvatting

### Wat er nieuw is

| Bestand | Wat het doet |
|---|---|
| `afvuren.py` | **Herschreven.** Was in 3b de naad met een boekhoudkundige inhoud; is nu de acht stappen van SPEC 9.1, de oploop, de stoptimer en het stoppen. |
| `noodrem.py` | **Nieuw.** `available` en de URI-controle, met een `Uitkomst`-enum van drie waarden. |
| `oploop.py` | **Nieuw en puur.** De rekenkunde van de volume-oploop: stappen, clamp, afbreekmarge. |
| `radiomodus.py` | **Nieuw en puur.** De voorwaardelijke `radio_mode` en het providerdomein uit een URI. |
| `const.py` | `OPLOOP_STAPPEN`, `OPLOOP_STAP_SECONDEN`, `OPLOOP_AFBREEK_MARGE_PCT`, `NOODREM_NA_SECONDEN`, `STOP_NA_MINUTEN`, `SIMILAR_TRACKS_PROVIDERS`. |
| `__init__.py` | Bij unload worden afgaande wekkers gestopt, ná de planner en vóór de opslag. |
| `SPEC.md` | Alleen de clausule van taak A. |

**Tests: 213 geslaagd** (137 uit fase 3b, 76 nieuw), 8 JS-tests, bundel onveranderd,
registratieregel intact. **39 mutaties nagelopen**, drie gaten gevonden en gedicht.

### De volgorde is de kern, en één stap is de essentie

De acht stappen (taak B) zijn precies SPEC 9.1 met het volumelezen uit SPEC 9.5 als
eigen stap erbij — SPEC 9.5 plaatst dat lezen uitdrukkelijk **vóór** stap 2 van 9.1,
dus de acht van de opdracht en de zeven van SPEC zijn dezelfde volgorde.

**Stap 3 vóór stap 5 is het punt waar het om gaat.** Start je het geluid op het oude
volume en zet je het daarna op 0, dan knalt de wekker één keer hard op de stand van
gisteravond voordat de oploop begint. Dat is het verschil tussen wakker worden en
wakker schrikken.

De test daarop assert daarom niet dat er ooit een 0 gezet is, maar de **index**:

```python
assert namen[:4] == [
    "music_assistant.search",     # stap 1, de noodrem
    "media_player.volume_set",    # stap 3, op 0
    "light.turn_on",              # stap 4
    "music_assistant.play_media", # stap 5
]
assert huis.volumes()[0] == 0
assert namen.index("media_player.volume_set") < namen.index("music_assistant.play_media")
```

En stap 2 heeft zijn eigen test, want hem ná stap 3 doen levert altijd 0 op — en dan
zet het terugzetten bij het stoppen de speaker **op stil**, een bijwerking die niemand
merkt tot hij 's avonds muziek wil.

### Twijfel valt niet altijd dezelfde kant op, en dat is opzet

Dit is de subtielste eis van de fase, en de twee gevallen zien er in code op elkaar
lijken:

| Controle | Uitkomst "ik weet het niet" | Gedrag |
|---|---|---|
| speaker `available` | — (kan niet twijfelen) | **niet afgaan** |
| URI bestaat nog | zoekopdracht faalde of liep in de time-out | **wél afgaan** (SPEC 11.2.1) |
| `radio_mode`-provider | onbekend schema, provider niet in de lijst | **weglaten** (SPEC 8.3.1) |

Geen inconsistentie, maar dezelfde afweging op andere feiten:

- bij de URI-controle kost twijfel een wekker die **misschien** niets speelt — en een
  trage zoekopdracht is geen reden om iemand niet te wekken. RadioBrowser lukte in
  fase 0b bij 1 van 6 zoekopdrachten;
- bij `radio_mode` kost twijfel een wekker die **zeker** niets speelt: MA geeft
  HTTP 500 en de queue blijft leeg.

Om te voorkomen dat "onbekend" ooit stil als "goed" of "fout" door het leven gaat,
geeft `noodrem.py` geen `bool` terug maar een enum met **drie** waarden:

```python
class Uitkomst(Enum):
    GOED = "goed"
    FOUT = "fout"          # vastgesteld negatief -> niet afgaan
    ONBEKEND = "onbekend"  # controle kon niet worden uitgevoerd
```

De omkering heeft een eigen test met **drie** foutsoorten
(`HomeAssistantError`, `TimeoutError`, `RuntimeError`), want ze moeten alle drie
dezelfde kant op vallen, en één van de drie vergeten is precies hoe dit stukgaat.

### De terugval is de garantie, niet de lijst

`SIMILAR_TRACKS_PROVIDERS` is uit MA's broncode afgeleid en kan **stil** verouderen.
Fase 3a-bis stelde daarom als eis dat de HTTP 500 wordt opgevangen, en dat is hoe het
gebouwd is: mislukt `play_media` mét `radio_mode`, dan wordt het **opnieuw geprobeerd
zonder**, met een `WARNING` waarin het providerdomein staat zodat de lijst nagelopen
kan worden.

Dat maakt het ergste geval hinderlijk in plaats van stil:

| | provider kan het wél | provider kan het **niet** |
|---|---|---|
| lijst klopt | eindeloos doorspelen | geluid stopt na het item |
| lijst is verouderd | geluid stopt na het item | HTTP 500 → **terugval** → geluid stopt na het item |

Er is geen vakje meer waarin er niets klinkt. Wat de terugval **niet** dekt: staat een
provider er onterecht *niet* in, dan stopt het geluid na het item en merkt niemand dat
er iets te winnen was. Dat blijft een openstaand punt bij elke MA-release.

Het veld wordt bovendien **weggelaten** en niet op `False` gezet, zodat MA zijn eigen
standaard houdt. De test daarop is `assert "radio_mode" not in data` en niet
`assert data["radio_mode"] is False` — een detail dat makkelijk verkeerd getest wordt
en dan het verkeerde vastlegt.

### De oploop loopt op HA's klok, niet op `asyncio.sleep`

Twee redenen, en de tweede is de belangrijkste:

1. Een `async_call_later` levert een **unsub** op, dus afbreken is één aanroep en er
   blijft nooit een taak hangen die nog één keer het volume zet nadat de klant op stop
   heeft gedrukt.
2. Hij loopt op HA's klok en is dus met `async_fire_time_changed` vooruit te zetten.
   Met `asyncio.sleep` zou elke oplooptest 20 echte seconden kosten, en dan gebeurt wat
   fase 0b overkwam: dan meet niemand hem nog per stap. Chrome kneep daar de cadans af
   tot sprongen van 2, de **totaalduur** klopte (20,004 s), en wie alleen die
   rapporteert meldt een vloeiende oploop die in werkelijkheid tien sprongen was
   (valkuil 31).

De oplooptest assert daarom niet het eindvolume maar **elke stap, in volgorde**:

```python
assert huis.volumes() == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18,
                          20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40]
```

De eerste 0 is stap 3 van de afvuurvolgorde; daarna 20 stappen naar 40.

De oploop breekt af op drie dingen: de wekker is gestopt, de speaker is weggevallen, of
**de gebruiker draait zelf aan de knop** (meer dan 5 procentpunt afwijking van wat de
oploop net zette). Bij elk van de drie staat een **positieve controle** naast de
negatieve — een afwijking van 3 procentpunt mag níet afbreken, want een implementatie
die altijd afbreekt zou anders door de afbreektest komen en nooit verder komen dan
stap 1.

### Wat er clampt, en waarom dat gemeld wordt

Fase 0b mat dat MA buiten bereik **stil** afkapt met HTTP 200: `-5` → 0, `150` → 100,
`33.7` → 33 (afkappen, niet afronden). Een rekenfout in de oploop geeft dus geen
exceptie, alleen een verkeerd volume — het soort fout dat maanden blijft zitten.

`oploop.clamp()` geeft daarom `(waarde, is_geclampt)` terug, en `afvuren.py` logt op
`WARNING` als die tweede waar is, met erbij dat dit niet hoort voor te komen. Zonder
dat verschil is ons clampen net zo stil als dat van MA en is er niets gewonnen.

De **laatste stap wordt hard op het doel gezet** in plaats van op de uitkomst van de
deling. Bij 20 stappen en een geheel doel is dat hetzelfde getal; bij een ander aantal
stappen scheelt afronding er soms één, en dan is wat de klant instelde belangrijker
dan de formule. Er is een test met `aantal=100` die dat vasthoudt, want SPEC 9.3 zegt
uitdrukkelijk dat het aantal stappen één constante is die verhoogd mag worden.

### Wat er bij falen wél gebeurt

SPEC 11.6 punt 2 is een regel die makkelijk omvalt: bij een noodremfout gaat een
**ingestelde** wake-up light wél aan. Hij had ook aan moeten gaan als het geluid het
had gedaan. Wat het product niet doet, is een lamp verzinnen die de klant niet heeft
gekozen.

Daaronder zit een ordeningsprobleem dat een eigen test heeft. Er is **één** veld
`last_message` (SPEC 14.2.1), dus de laatste schrijver wint:

- **de lamp gaat eerst, de melding daarna.** Faalt de lamp tíjdens een noodremfout,
  dan moet `last_message` de reden zijn dat de wekker niet afging — niet de lamp.
  Waarom de wekker stil was, is het belangrijkste dat de klant 's ochtends kan lezen;
- **de oude `persistent_notification` wordt gewist zodra de noodrem gehaald is**, niet
  aan het eind. Aan het eind zou het de melding wegwissen die de lamp of de tweede
  noodremcontrole net had gemaakt.

Beide zijn met een mutatie getoetst (A34, A35, A36).

### `last_fired` wordt óók bij een noodremfout gezet

Een keuze met een prijs, dus hier expliciet. Fase 3b legde vast: `last_fired` gaat vóór
het geluid. Fase 3c zet een noodrem daartussen, en dan is de vraag of `last_fired`
meeschuift. Nee:

- **nu:** een noodremfout **verbruikt** het moment. Eén melding, en geen nieuwe poging
  bij de volgende herstart binnen het respijtvenster;
- **andersom:** elke herstart binnen 30 minuten herhaalt de mislukking — nieuwe melding,
  nieuwe `persistent_notification` — en als de speaker inmiddels terug is, gaat de
  wekker alsnog af op een moment dat de klant niet verwacht.

Het weegpunt: een mislukte noodrem maakt **geen geluid**, dus opnieuw proberen kan
nooit "twee keer afgaan" opleveren, en dat is de enige uitkomst die echt erg is. Het
sluit ook aan bij hoe fase 3b het overslaan behandelt — dat zet `last_fired` ook. En
het is dezelfde lezing als de clausule van taak A, één laag lager.

### Wat de mutatietests opleverden

39 mutaties op `afvuren.py`, `noodrem.py`, `oploop.py`, `radiomodus.py` en
`__init__.py`. **36 werden meteen gevangen, drie niet** — en die drie waren elk iets
anders, wat de oefening opnieuw zijn geld waard maakte.

#### A37 — het `failed`-event was helemaal niet gedekt

Het weghalen van `register.stuur({"event": "failed", …})` in `_async_faal` veranderde
niets. Puur een testgat, en een pijnlijk gemakkelijk gat: de noodremtests keken naar
`last_message`, en de énige test die wél een `failed`-event verwachtte liep door een
**ander** stuk code — `_maak_noodrem_achteraf` stuurt zijn eigen event. Ik had dus een
test die "het failed-event werkt" leek te zeggen over een pad dat het niet was.

Gevolg als het echt fout was gegaan: een open kaart zou een mislukte wekker pas na een
herlaadactie zien. Nu gedekt door `test_een_mislukte_wekker_stuurt_het_failed_event`,
met een positieve controle ernaast
(`test_een_geslaagde_wekker_stuurt_geen_failed_event`), want anders zou "er komt een
`failed`-event" ook waar kunnen zijn omdat er altijd één komt.

#### A19 — dezelfde vorm als P3 uit fase 3b, en dus wél nodig

Het weghalen van de `is_afgaand`-controle in `_Oploop._async_tik` veranderde ook niets,
want `async_stop_afgaan` zegt de `async_call_later` toch al af. De verleiding is dan om
de regel dood te verklaren — precies zoals in fase 3b bij P3 — en het antwoord is
hetzelfde: **dubbele verdediging op de ene weg, enige verdediging op de andere.**

De weg waarop hij de enige is: `_async_tik` zet `self._unsub = None` en gaat dan
`await`en. Komt de stop precies daartussen, dan is er geen unsub meer om af te zeggen,
en is deze controle het enige dat voorkomt dat er ná de stop nog één keer het volume
omhoog gaat — op een speaker waarvan het volume net is teruggezet.

Deze test kostte twee pogingen, en dat is zelf een les. Mijn eerste versie leek te
werken maar toetste de verkeerde regel: na een volledige stop staat het volume weer op
50 terwijl de oploop 0 had gezet, en dan breekt `wijkt_af` de oploop al af. De mutatie
bleef daardoor ongevangen. De test moest de oploop éérst één stap laten zetten, zodat
het gelezen volume gelijk is aan wat de oploop zelf zette — pas dan is de
register-controle geïsoleerd. **Een test die de juiste uitkomst om de verkeerde reden
krijgt, is geen test.**

#### A14 — de regel was niet redundant maar onbereikbaar

`waarden[-1] = doel` — de regel die de laatste stap hard op het doel zette — was niet
te vangen, en na narekenen bleek waarom: de laatste term is `doel * aantal / aantal`,
en dat is voor elk geheel doel en elk aantal stappen **exact** het doel. Nagerekend
voor `aantal ∈ {1, 2, 3, 7, 20, 100, 999}` en `doel` 0–100: **nul** afwijkingen.

Dit is de andere uitkomst dan bij A19, en het verschil is de moeite waard: A19 was
redundant-maar-bereikbaar, A14 was onbereikbaar. Voor het eerste hoort een test; voor
het tweede hoort **de regel eruit**. Een test op onbereikbare code bewijst niets en
suggereert dekking die er niet is. De regel is weg, met de meting in een comment zodat
niemand hem "voor de zekerheid" terugzet.

Dat de laatste stap exact het doel is blijft wél een eis — die wordt bewaakt door
`test_de_oploop_daalt_nooit`, voor elk doel van 1 tot 100. En de mutatie is vervangen
door een die de eis wél raakt (de oploop een stap te vroeg laten eindigen); die wordt
door acht tests gevangen.

#### Na het dichten

**Alle 39 gevangen**, met 213 tests. Wat verder opvalt: een groot deel van de 39 wordt
gevangen door een test die er expliciet als **positieve controle** naast staat — de
"kleine afwijking breekt niet af", de "speaker die blijft staan levert geen melding
op", de "afspelen faalt ook zonder radio_mode". Zonder die zou een implementatie die
*altijd* faalt door de bijbehorende negatieve test komen. Dat is de valkuil uit
CLAUDE.md, en A37 laat zien dat hij in deze fase daadwerkelijk was opgetreden.

De volledige uitvoer staat onder [Bijlage: de 39 mutaties](#bijlage-de-39-mutaties).

### De verplichte gevallen

| # | Geval | Test |
|---|---|---|
| 1 | de acht stappen in volgorde, volume 0 vóór het geluid | `test_de_acht_stappen_gebeuren_in_de_voorgeschreven_volgorde` |
| 2 | onbereikbare speaker: geen enkele aanroep | `test_een_onbereikbare_speaker_laat_de_wekker_niet_afgaan` |
| 3 | ongeldige URI: idem | `test_een_verdwenen_uri_laat_de_wekker_niet_afgaan` |
| 4 | URI-controle faalt → wekker gaat **wél** af | `test_een_mislukte_uri_controle_laat_de_wekker_wel_afgaan` |
| 5 | speaker valt weg tussen stap 5 en 7 | `test_een_speaker_die_wegvalt_na_het_starten_wordt_gemeld` |
| 6 | oploop bereikt exact het niveau in 20 stappen | `test_de_oploop_bereikt_het_ingestelde_niveau_in_twintig_stappen` |
| 7 | gebruiker draait aan het volume → afbreken | `test_de_oploop_breekt_af_als_de_gebruiker_aan_het_volume_draait` |
| 8 | `radio_mode` wel en niet, per provider | `test_radio_mode_gaat_mee_bij_een_ondersteunende_provider`, `test_radio_mode_gaat_niet_mee_bij_een_gratis_radioprovider` |
| 9 | mét `radio_mode` faalt → opnieuw zonder | `test_een_mislukte_radio_mode_wordt_opnieuw_geprobeerd_zonder` |
| 10 | stoppen zet het volume terug; onleesbaar → niets | `test_stoppen_zet_het_volume_terug`, `test_een_onleesbaar_oud_volume_zet_niets_terug` |
| 11 | stoptimer stopt na 30 minuten | `test_de_stoptimer_stopt_de_wekker_na_dertig_minuten` |
| 12 | falende lamp laat de wekker afgaan | `test_een_falende_lamp_laat_de_wekker_gewoon_afgaan` |

Alle 76 nieuwe tests zijn **NIEUW GEDRAG**: er was in fase 3b niets dat afspeelde,
`afvuren.py` deed alleen de boekhouding. De regressiewacht op wat 3a en 3b bouwden
staat in `test_store.py`, `test_websocket.py`, `test_volgende.py` en `test_planner.py`
en is ongewijzigd geslaagd — met één uitzondering die hieronder staat.

### Twee tests zijn verhuisd, en één fixture verdient uitleg

`test_planner.py` vervangt sinds deze fase `afvuren.async_laat_afgaan` door een
boekhouder die alleen `last_fired` schrijft. Dat was nodig omdat de planner-tests de
klok over **dagen** verzetten, en dan vuurt de stoptimer van 30 minuten mee — waarna
het ringing-register leeg is en "is hij afgegaan?" niets meer betekent.

**Wat die fixture verbergt**, en waar dat gedekt is: dat de planner werkelijk dít pad
aanroept, met de juiste argumenten, is er niet meer aan te zien. Daarvoor bestaat
`test_afvuren.py::test_de_planner_laat_een_wekker_echt_afspelen` — die legt de hele
keten af zonder enige vervanging, van de inhaalslag bij setup tot een speaker die
werkelijk wordt aangesproken, en controleert onderweg dat `last_fired` het **bedoelde**
moment (06:45) draagt en niet "nu" (06:50). Zonder die ene test zou de fixture precies
de valkuil zijn waar CLAUDE.md voor waarschuwt.

De twee tests over het `started`- en `stopped`-event zijn van `test_planner.py` naar
`test_afvuren.py` verhuisd. Ze zijn niet vervallen — ze staan nu op de laag waar ze
thuishoren, en leggen daar een langere weg af.

---

## Taak I — De livecontrole, in twee rondes

Deze sectie is in twee etappes geschreven. Eerst kwam de koppeling niet verder dan
MA's inlogpagina; daarna heeft de eigenaar ingelogd en zijn de vijf toetsen uitgevoerd.
De uitkomst van de eerste etappe — de oorzaak van valkuil 32 — staat hieronder omdat
hij op zichzelf iets waard is. **De resultaten van de vijf toetsen staan onder
[De vijf toetsen, live gemeten](#de-vijf-toetsen-live-gemeten), en de belangrijkste
bevinding van deze hele fase staat daar ook: de URI-controle van SPEC 11.2 maakt van
een werkende SomaFM-wekker een stille.**

### Valkuil 32 had de verkeerde oorzaak

Fase 0b concludeerde: "`external_url` verandert het niet". Dat is waar, en de reden
staat in `helpers/config_entry_oauth2_flow.py:74-85`:

```python
def async_get_redirect_uri(hass) -> str:
    if "my" in hass.config.components:
        return MY_AUTH_CALLBACK_PATH          # https://my.home-assistant.io/redirect/oauth
    if (req := http.current_request.get()) is None:
        raise RuntimeError("No current request in context")
    if (ha_host := req.headers.get(HEADER_FRONTEND_BASE)) is None:
        raise RuntimeError("No header in request")
    return f"{ha_host}{AUTH_CALLBACK_PATH}"
```

**De eerste regel gaat vóór alles.** Zolang de `my`-integratie geladen is, wordt
`external_url` in dit pad *nooit gelezen*. Het was dus geen configuratiefout maar een
controlevraag die er niet aan te pas komt — en `my` zit in `default_config`.

### De uitweg, en die werkt

`default_config:` in `.ha-dev-config/configuration.yaml` is uiteengelegd in zijn 22
dependencies **minus `my`**. Gemeten na herstart:

| | vóór | ná |
|---|---|---|
| `my` in `hass.config.components` | ja | **nee** |
| `return_url` van de MA-flow | `my.home-assistant.io/redirect/oauth` | **`http://localhost:8129/auth/external/callback`** |

Daarmee blijft de hele flow lokaal en is het Docker-Desktop-probleem weg. `my` levert
alleen de /redirect-koppelingen naar documentatie; niets in dit product gebruikt ze.

### Twee dingen die daarbij naar boven kwamen

**De flow moet vanuit de echte frontend starten.** Een `fetch` naar
`/api/config/config_entries/flow` stuurt de header `HA-Frontend-Base` niet mee, en dan
gooit `async_get_redirect_uri` een `RuntimeError` en valt de MA-flow terug op zijn
`auth_manual`-stap — die om een long-lived MA-token vraagt. Dat is geen fout maar het
gedocumenteerde alternatief; het is wel een verklaring waarom hetzelfde commando twee
verschillende stappen kan opleveren.

**`host.docker.internal` is niet het juiste adres voor de config flow.** De flow bouwt
zijn login-URL uit de URL die je HA geeft, en de browser moet die openen. Gemeten:

```
ping host.docker.internal   (op de host)  -> could not find host
HA-container -> http://192.168.1.212:8095/info -> 200
host/browser -> http://192.168.1.212:8095/info -> 200
```

Het **LAN-IP van de host** is dus van beide kanten bereikbaar, en met dat adres hoeft
er in de adresbalk niets herschreven te worden. Dat IP komt van DHCP en kan veranderen.

### Hoe de koppeling uiteindelijk tot stand kwam

De eigenaar heeft ingelogd. De drie stappen die daarvoor nodig waren:
Integratie toevoegen → Music Assistant → URL **`http://192.168.1.212:8095`** (het
LAN-IP; `host.docker.internal` kan de browser niet vinden en `localhost` is binnen de
HA-container HA zelf) → inloggen. Registreren op my.home-assistant.io was niet nodig.

Wat er daarna stond: drie `media_player`-entiteiten — `wekker_slaapkamer`,
`wekker_keuken` en `wekkergroep` — precies de verwachting die fase 0b onder T2
opschreef, groep inbegrepen. Voor de toetsen zijn erbij gemaakt: het label
**Music Assistant Wekker** op `wekker_slaapkamer`, de `demo`-integratie voor een echte
lamp (er stond geen enkele `light`-entiteit) met het label **Verlichting Wekker** op
`light.bed_light`, en tijdelijk `homeassistant.core: debug` zodat elke service-aanroep
een tijdstempel in het log krijgt.

**Wat meteen live bleek te werken zonder dat het getoetst hoefde:** de labelfiltering
van fase 3a. `entities/list` gaf exact één speaker en één lamp terug, met
`label_exists: true` voor beide — de eerste keer dat die code tegen echte labels heeft
gelopen.

---

## De vijf toetsen, live gemeten

### BEVINDING — de URI-controle van SPEC 11.2 maakt van een werkende wekker een stille

Dit is de belangrijkste uitkomst van fase 3c, en hij kwam bij de **eerste** poging naar
boven. De eerste wekker die ik zette — SomaFM: Beat Blender, het kanaal dat CLAUDE.md
als betrouwbaar aanmerkt — ging **niet** af:

```
23:23:00.245 WARNING [afvuren] Wekker 4a852fe9… gaat NIET af:
             het geluid 'somafm://radio/beatblender' bestaat niet meer
```

Het geluid bestond wél. Twee minuten eerder had ik het via `sound/search` gevonden.

**De oorzaak, gemeten.** SPEC 11.2 schrijft voor: zoek op de **opgeslagen `name`**,
beperkt tot het opgeslagen `media_type`, en kijk of de opgeslagen `uri` in de treffers
staat. SPEC 8.2 schrijft voor dat die `name` de naam is die MA zelf teruggaf. Voor
SomaFM is dat `"SomaFM: Beat Blender"` — en dáár zit het:

| Zoekopdracht | Treffers | Bevat `somafm://radio/beatblender` |
|---|---|---|
| `"SomaFM: Beat Blender"` ← **de opgeslagen naam** | **0** | **nee** |
| `"Beat Blender"` | 3 | ja |
| `"beatblender"` | 0 | nee |

**De naam die Music Assistant teruggeeft, is een naam die Music Assistant zelf niet kan
vinden.** De weergavenaam draagt een providerprefix (`SomaFM: `) die niet in de
zoekindex zit. De route uit SPEC 11.2 is daarmee voor deze provider **zelf-verslaand**:
hij kan per definitie zijn eigen opgeslagen geluid niet terugvinden.

**Het is providerspecifiek**, en dat maakt het erger in plaats van beter. Getoetst door
elke treffer opnieuw op zijn eigen naam te zoeken:

| Provider | Voorbeeldnaam | Zelf-vindbaar |
|---|---|---|
| `somafm://` | `SomaFM: Beat Blender` | **nee** |
| `radiobrowser://` | `SomaFM Beat Blender (128k AAC)` | ja |
| iTunes-podcasts | `Radiolab` | ja |

Dus juist de provider die op deze instance betrouwbaar wérkt is de provider die faalt,
en de zelf-vindbare radioprovider is RadioBrowser — die fase 0b als **wisselvallig**
opschreef (1 van 6 zoekopdrachten lukte).

**Dit is precies het faalgeval dat SPEC 11.2 zelf als het ergste aanmerkt:**

> **Vals negatief:** is het item er nog maar geeft de zoekopdracht het niet terug […]
> dan meldt de controle onterecht dat het geluid weg is. **Dat is het ergste
> faalgeval**, want het maakt van een werkende wekker een stille.

Het staat er als risico. Het blijkt de normale uitkomst voor een hele provider.

**Wat ik niet heb gedaan.** De code niet aangepast en SPEC niet aangepast. De
implementatie doet precies wat SPEC 11.2 voorschrijft — het defect zit in het
voorgeschreven ontwerp, niet in de uitvoering — en de staande afspraak is dan: melden
en stoppen, niet zelf wijzigen. Drie richtingen die ik zie, zonder er één te kiezen:

1. **Niet op de naam zoeken maar op de URI-staart.** Voor `somafm://radio/beatblender`
   is dat `beatblender`, en dat gaf ook 0 treffers — dus dit werkt niet zonder meer.
2. **`music/item_by_uri` gebruiken**, de directe controle die SPEC 11.2.2 al als
   voorkeursroute noemt. Die kent geen zoekindex en heeft dit probleem niet. De prijs
   is `entry.runtime_data.mass`, precies de afhankelijkheid die SPEC 11.2 afwees.
   **Deze bevinding verandert de weging van die afweging**, want de zoekroute blijkt
   niet "iets minder precies" maar voor een hele provider onbruikbaar.
3. **Bij een negatieve uitkomst toch afgaan**, en alleen op de tweede noodremcontrole
   (SPEC 11.3) vertrouwen. Dan verdwijnt de hele vooraf-controle in de praktijk.

Tot dat besloten is, geldt op deze instance: **een wekker op een `somafm://`-URI gaat
niet af.** De wekkers in de toetsen hieronder gebruiken daarom de
`radiobrowser://`-variant van hetzelfde kanaal.

### T1 — de acht stappen, in volgorde, met tijdstempels

Wekker om **23:30:00** op `media_player.wekker_slaapkamer`, volume 40 %, lamp
`light.bed_light` op 60 %. Server-side tijdstempels uit `docker logs ha-alarm`:

```
21:30:00.012  music_assistant.search        stap 1   noodrem: de URI-controle
21:30:00.017  media_player.volume_set  → 0  stap 3   VÓÓR het geluid
21:30:00.022  light.turn_on                 stap 4   wake-up light
21:30:00.022  music_assistant.play_media    stap 5   geluid
21:30:02.153  [afvuren] afgegaan voor moment 2026-08-10T23:30:00+02:00, oploop naar 40%
21:30:03.155  media_player.volume_set  → 2  stap 6   eerste oploopstap
…
21:30:22.270  media_player.volume_set  → 40           laatste oploopstap
21:30:22.274  [afvuren] Oploop klaar op 40% in 20 stappen
```

De volgorde uit SPEC 9.1 klopt, en het punt waar het om gaat is meetbaar: de
`volume_set` naar 0 staat op **+17 ms** en de `play_media` op **+22 ms**. Volume nul
komt vóór geluid, met 5 ms marge. Er is dus geen uitbarsting op de stand van
gisteravond.

De lamp ging aan op 60 %: `brightness` = **153** = 0,60 × 255.

### De URI-controle duurt 5 ms — en is niet waar de tijd blijft

Gevraagd was dit expliciet te meten. Twee metingen:

**In het afvuurpad**, uit de tijdstempels hierboven: tussen de `search` (`+12 ms`) en de
`volume_set` erna (`+17 ms`) zit **5 ms**. Dat is de hele URI-controle, inclusief het
doorlopen van de acht emmers.

**Los gemeten**, vijf keer achter elkaar via `sound/search` (inclusief
WebSocket-retour): **253, 3, 4, 3, 3 ms**. De eerste is koud — MA moet de provider
aanspreken — daarna is het antwoord gecachet.

**Mijn voorspelling in dit rapport was fout.** Ik schreef dat de noodrem de afwijking
zou vergroten en dat de `search` met zijn time-out van 10 s daarvoor de kandidaat was.
De `search` kost 5 ms. Waar de tijd wél blijft:

| Van | Tot | Duur | Wat |
|---|---|---|---|
| +0 ms | +12 ms | 12 ms | planner-jitter, zoals fase 3b mat |
| +12 ms | +17 ms | **5 ms** | **de URI-controle** |
| +17 ms | +22 ms | 5 ms | volume 0, lamp |
| +22 ms | **+2153 ms** | **2131 ms** | **`play_media`, blokkerend** |

**De totale afwijking ten opzichte van de wektijd is +2,153 s, en 99 % daarvan is
`music_assistant.play_media`** die wacht tot MA de stream heeft opgezet. Dat is niet
onze code en niet de noodrem; het is een RadioBrowser-URI die een stream moet opbouwen.

Gevolg dat de moeite is om te weten: de oploop begint op **+3,138 s** en bereikt 40 %
op **+22,27 s** in plaats van +20 s. Dat is onschadelijk — het volume stond al op 0, dus
die eerste drie seconden zijn stil — maar het betekent dat "van stil naar het ingestelde
niveau in 20 seconden" (SPEC 9.3) in de praktijk **20 seconden ná het starten van het
geluid** is, niet 20 seconden na de wektijd. Bij een langzamere provider loopt dat
verder uit.

### T2 — het volume loopt op: 20 stappen, en ook aan de speakerkant

HA-kant, uit het log — waarde en cadans per stap:

```
21:30:00.017   0 %          (stap 3 van de afvuurvolgorde)
21:30:03.155   2 %   +3.138s
21:30:04.162   4 %   +1.007s
21:30:05.168   6 %   +1.006s
…              …     …
21:30:21.264  38 %   +1.005s
21:30:22.270  40 %   +1.006s
```

Reeks: `[0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40]`
— exact wat `test_de_oploop_bereikt_het_ingestelde_niveau_in_twintig_stappen` eist.
Cadans **1,004–1,007 s**, twintig keer.

**En dit is niet alleen HA's boekhouding.** Dezelfde reeks staat in het log van de
snapclient, dus aan de speakerkant:

```
23-30-00.019 (Controller) ServerSettings - buffer: 1000, latency: 0, volume: 0,  muted: 0
23-30-03.158 (Controller) ServerSettings - buffer: 1000, latency: 0, volume: 2,  muted: 0
23-30-04.164 (Controller) ServerSettings - buffer: 1000, latency: 0, volume: 4,  muted: 0
…
23-30-21.266 (Controller) ServerSettings - buffer: 1000, latency: 0, volume: 38, muted: 0
```

Dat is het bewijs dat valkuil 31 vraagt: **gemeten aan het apparaat, niet in een
browsertabblad.** Fase 0b kwam op paren van 2 stappen per 2 seconden omdat Chrome
`setTimeout` afknijpt in een achtergrondtabblad; hier is de cadans regelmatig omdat de
oploop op HA's klok loopt en de meting uit twee onafhankelijke logs komt.

**Er kwam ook werkelijk geluid uit.** De snapclient logt elke seconde
`No chunks available` als er niets stroomt. Geteld per venster:

| Venster | Duur | `No chunks` | Uitkomst |
|---|---|---|---|
| vóór het afgaan (23:29:00–23:30:03) | 63 s | **63** | stil |
| tijdens de wekker (23:30:03–23:31:40) | 97 s | **0** | **audio liep** |
| ná de stop (23:31:46–23:33:00) | 74 s | **74** | stil |

Nul van 97 seconden stilte tijdens de wekker, en 100 % stilte ervoor en erna. Dit is de
enige toets in het hele project die aantoont dat er geluid uit de speaker komt — SPEC
11.5 zegt uitdrukkelijk dat geen enkele controle in de integratie dat kan.

### T3 — `alarms/stop` zet het volume terug

Vóór de wekker stond de speaker op **0,55**. Tijdens de wekker liep hij naar 0,40. Na
`alarms/stop`, uit het log:

```
21:31:40.810  media_player.media_stop    entity_id=media_player.wekker_slaapkamer
21:31:40.818  media_player.volume_set    volume_level=0.55      ← terug naar de oude stand
21:31:40.821  [afvuren] Wekker a534188a… gestopt (user)
```

Eerst het geluid stoppen, dán het volume terugzetten — de volgorde uit SPEC 9.5, met
8 ms ertussen. Eindstand: `volume_level: 0.55`, `state: idle`. Het tweede
`alarms/stop`-commando gaf geen fout en leverde geen tweede `stopped`-event op, dus
idempotent zoals SPEC 15.8 eist.

**Waarschuwing over de meting zelf, want ik ben hier eerst in getrapt.** Mijn eerste
lezing zei dat het volume op 0,40 bleef staan en dat de speaker nog `playing` was — een
"mislukte" toets die niets mankeerde. Oorzaak: ik had `hass` aan het begin van het
script vastgehouden, en HA's frontend **vervangt** `hass.states` bij elke update in
plaats van het te muteren. Een vastgehouden `hass` leest dus een bevroren momentopname.
Met een verse `document.querySelector('home-assistant').hass` stond er 0,55 en `idle`.
Staat nu als valkuil 37 in `CLAUDE.md`.

### T4 — de afwijking ten opzichte van de wektijd

**+2,153 s**, met de opsplitsing hierboven. Ter vergelijking met de eerdere metingen:

| Fase | Wat er gemeten is | Afwijking |
|---|---|---|
| 0 | `async_track_point_in_time`, kaal | +3,4 ms |
| 3b | planner tot en met `last_fired`, zonder geluid | +12 ms |
| **3c** | **planner + noodrem + volume + lamp + geluid gestart** | **+2153 ms** |
| 3c, alleen tot de noodrem | planner + URI-controle | +17 ms |

De sprong zit volledig in `play_media`. Voor een wekker is 2 seconden verwaarloosbaar;
het staat hier omdat het de verwachting bijstelt die dit rapport eerder uitsprak, en
omdat een provider die er tien seconden over doet dezelfde vorm heeft.

### T5 — een lege noodrem remt écht

De snapclient van de slaapkamer gedood, gewacht tot HA `unavailable` meldde, en een
wekker op 23:37 gezet.

**Eerst wat er bij het wegvallen van de attributen overbleef** — valkuil 18, voor het
eerst live nagemeten op een MA-speaker:

```
state: unavailable
attributen: device_class, icon, friendly_name, supported_features, entity_picture
volume_level:      WEG
mass_player_type:  WEG
```

Precies zoals fase 0 uit de broncode voorspelde. En daarom accepteerde `alarms/save`
de speaker nog steeds, en gaf `entities/list` hem nog steeds terug: de zeef van SPEC 7.2
gaat op `supported_features`, en die overleeft. **Dat is de fase-3a-ontwerpkeuze, live
bevestigd** — was er op `mass_player_type` gefilterd, dan was de speaker uit de lijst
verdwenen op het moment dat je hem het hardst nodig hebt.

Wat er om 23:37:00 gebeurde:

```
21:37:00.014  WARNING [afvuren]   Wekker 2676508… gaat NIET af:
                                  speaker media_player.wekker_slaapkamer is niet bereikbaar
21:37:00.014  CALL light.turn_on  entity_id=light.bed_light
21:37:00.029  ERROR [meldingen]   De wekker van 23:37 is niet afgegaan:
                                  de speaker '…' was niet bereikbaar.
```

En het scherpst: **service-aanroepen naar de speaker in het venster 21:36:59–21:37:15:
nul.** Geen `volume_set`, geen `play_media`, geen `media_stop`. Dat is de eis uit taak B
geval 2, en de reden dat de controle er is: had de integratie het aan HA's
service-dispatch overgelaten, dan waren de aanroepen weggefilterd zonder één logregel —
bij label-targeting zelfs volkomen zwijgend (gemeten in fase 0).

De rest, van de kaartkant:

| | |
|---|---|
| `failed`-event | `speaker_unavailable`, om 21:37:00.030 (+30 ms) |
| `last_message` | `kind: speaker_unavailable`, `severity: error`, met de letterlijke tekst uit SPEC 11.7 |
| `persistent_notification` | aangemaakt |
| `ringing` | leeg — er is niets om te stoppen |
| **de lamp** | **aan, `brightness` 153** |
| `last_fired` | `2026-08-10T23:37:00+02:00` — het moment is verbruikt |

De lamp is het detail dat makkelijk omvalt: SPEC 11.6 punt 2 zegt dat een **ingestelde**
wake-up light wél aangaat als het geluid faalt, want hij had ook aan moeten gaan als het
geluid het had gedaan. Live bevestigd, in hetzelfde tijdstempel als de weigering.

En de eerste mislukte run (de SomaFM-bevinding hierboven) heeft ditzelfde pad
onbedoeld voor een **tweede** meldingssoort aangetoond: `sound_gone`, met lamp aan,
notificatie, `failed`-event op +14 ms en `volume_level` onaangeroerd op 0,55.

### Wat er onderweg nog bleek

**`sound/search` geeft velden terug die `alarms/save` weigert.** Letterlijk
doorgeven van een zoekresultaat als `sound` levert op:

```
invalid_format — alarm.alarms[0].sound: onbekende velden: ['album', 'artists']
```

Dat is de validatie die goed werkt: `sound` mag alleen `uri`, `name`, `media_type` en
`image` bevatten (SPEC 8.2). Maar het betekent dat **de kaart in fase 4 het
zoekresultaat moet uitkleden** voordat hij het opslaat, en dat is geen detail dat je
zelf verzint — je loopt er tegenaan. Hoort in de fase-4-opdracht.

### Opruimen van de dev-instance

- De drie toetswekkers zijn via `alarms/delete` verwijderd; `alarms/get` geeft nul
  wekkers en `ringing` is leeg.
- De snapclient van de slaapkamer draait weer; de speaker staat op `idle`, volume 0,55.
- De lamp staat uit, de `persistent_notification`s zijn weggehaald.
- **`homeassistant.core: debug` is er weer uit** — die was alleen voor de tijdstempels
  en is luidruchtig. Er staat een comment bij hoe je hem terugzet.
- **Wat blijft staan:** de `demo`-integratie (levert de lamp), de twee labels, en het
  uiteengelegde `default_config:` minus `my`.

---

## Wat niet lukte

### De URI-controle houdt een werkende SomaFM-wekker tegen

Uitgeschreven onder [BEVINDING](#bevinding--de-uri-controle-van-spec-112-maakt-van-een-werkende-wekker-een-stille).
Kort: de naam die MA teruggeeft (`"SomaFM: Beat Blender"`) is een naam die MA zelf niet
kan vinden, dus de controle uit SPEC 11.2 concludeert dat het geluid weg is en de wekker
gaat niet af. Providerspecifiek: `radiobrowser://` en podcasts zijn zelf-vindbaar,
`somafm://` niet.

**Niet gerepareerd, met opzet.** De code doet wat SPEC 11.2 voorschrijft en SPEC mocht
deze ronde alleen voor taak A gewijzigd worden. Er liggen drie richtingen; de keuze is
aan de eigenaar. Zolang die niet gemaakt is, gaat op deze instance een wekker op een
`somafm://`-URI niet af — en dat is geen testartefact maar wat een klant zou meemaken.

### Mijn voorspelling over de afwijking was fout

Dit rapport schreef, vóór de livecontrole, dat de noodrem de afwijking zou vergroten en
dat de `search` met zijn time-out van 10 s de kandidaat was. Gemeten: de URI-controle
kost **5 ms**. De 2,153 s zit vrijwel volledig in `music_assistant.play_media`, die
blokkeert tot MA de stream heeft opgezet. De voorspelling was goed in de uitkomst
("groter dan 12 ms") en fout in de oorzaak, wat betekent dat hij om de verkeerde reden
klopte.

### De cadans van de oploop is nog steeds niet als "vloeiend" vastgesteld

De cadans **is** nu gemeten, en aan twee kanten: 1,004–1,007 s per stap in HA's log én
in het log van de snapclient. Dat is meer dan fase 0b haalde. Wat er nog steeds niet is
vastgesteld, is of het **vloeiend klinkt** — daar hoort een oor bij, en dat zit niet in
een log. SPEC 9.3 zegt uitdrukkelijk dat dit één constante is die verhoogd mag worden;
de test met `aantal=100` bestaat om die verhoging goedkoop te houden.

Wat de meting wél toevoegt: de oploop begint **3,1 s ná de wektijd** omdat `play_media`
zo lang blokkeert, dus 40 % is bereikt op +22,3 s in plaats van +20 s. Dat is
onschadelijk zolang het volume op 0 staat tijdens die aanloop — en dat doet het — maar
bij een langzamere provider loopt het verder uit en verschuift de hele oploop mee.

### Eén tekst die niet uit SPEC te halen was

De melding `volume_ramp_unavailable` heeft in SPEC 11.7 een tekst en een `kind`, maar
SPEC zegt niet wanneer hij precies gestuurd wordt. Ik heb gekozen: **als de eerste
`volume_set` faalt** — dat is de enige manier waarop de integratie kan weten dat een
oploop niet gaat. De wekker gaat dan af op het ingestelde niveau. Dat staat onder de
aannames, niet als vaststaand.

---

## Aannames

1. **`ma_unavailable` versus `speaker_unavailable` gaat op de geladen config-entry.**
   SPEC 11.1 zegt dat één `available`-controle beide storingen dekt, maar niet hoe je ze
   voor de klant onderscheidt. Gekozen: is er geen geladen `music_assistant`-entry, dan
   `ma_unavailable`; is die er wel en is de speaker `unavailable`, dan
   `speaker_unavailable`. Voor de klant is dat verschil het enige dat telt — "zet je
   speaker aan" tegen "je server ligt eruit".

2. **`volume_ramp_unavailable` wordt gestuurd als de eerste `volume_set` faalt**, en de
   wekker gaat dan af op het **ingestelde** niveau in plaats van op de stand die er
   stond. Zie hierboven; SPEC 11.7 geeft de tekst maar niet het moment.

3. **De tweede noodremcontrole stopt de wekker niet.** SPEC 11.3 vraagt om opnieuw
   controleren en om de melding, niet om afbreken. Komt de speaker terug, dan speelt de
   queue verder; en tot die tijd hoort de kaart een stopknop te blijven, want het
   volume moet nog terug.

4. **Bij unload worden afgaande wekkers gestopt, zonder `stopped`-event.** SPEC 15.9
   kent precies drie redenen (`user`, `timeout`, `deleted`) en unload is er geen van.
   Een vierde verzinnen zou een machineleesbaar veld laten liegen tegen een kaart die
   er drie verwacht, dus `reason=None` stuurt geen event. Het **geluid** moet wél
   stoppen: anders speelt het door zonder stoptimer, en dat is precies de lege woning
   waar SPEC 9.4 voor bestaat.

5. **`media_player.media_stop` is de manier om het geluid te stoppen.** SPEC 10 noemt
   hem als de aanroep waarmee een gebruiker buiten de kaart om stopt; SPEC 9.4 zegt
   alleen "geluid stoppen op de speaker". Er is geen `music_assistant`-service die dat
   doet.

6. **De URI-controle doorzoekt alle acht emmers van `search`, niet alleen die van het
   opgeslagen `media_type`.** Een provider plaatst een item soms in een andere emmer
   dan het opgeslagen type doet vermoeden, en een emmer overslaan levert een vals
   negatief op — precies wat SPEC 11.2 als het ergste geval aanmerkt. Het
   `media_type` wordt wél als filter meegestuurd, om de zoekopdracht te richten.

7. **De ondergrens van `oploop.clamp()` is 0 en niet `VOLUME_PCT_MIN` (1).** Nul is een
   geldig *oploopvolume* — de oploop begint er zelfs op. De ondergrens van 1 uit SPEC
   14.2 geldt voor het **eindniveau** dat de klant instelt, en die wordt in
   `validatie.py` bewaakt.

8. **`SIMILAR_TRACKS_PROVIDERS` heeft drie namen die SPEC 8.3.1 niet noemt**:
   `subsonic`, `qobuz` en `opensubsonic` (die laatste staat er wél). SPEC eindigt de
   opsomming met "en enkele andere — kortom de streamingproviders en de mediaservers".
   Het risico van een naam te veel is beperkt tot precies het geval dat de terugval
   opvangt.

9. **De dev-instance is aangepast** (`.ha-dev-config/configuration.yaml`,
   gitignored): `default_config:` uiteengelegd minus `my`, en de `demo`-integratie erbij
   voor een echte lamp. De oude versie staat als `configuration.yaml.fase3c-backup`
   naast het bestand. Het `logger:`-blok van fase 3b blijft staan;
   `homeassistant.core: debug` is na het meten weer weggehaald.

10. **De toetsen gebruiken de `radiobrowser://`-variant van het SomaFM-kanaal** in plaats
    van `somafm://`, omdat die laatste door de bevinding hierboven niet af kan gaan. Dat
    is een uitwijk voor de meting en geen oordeel: het betekent dat T1 tot en met T4 zijn
    gemeten op een provider die fase 0b als **wisselvallig** aanmerkte. Dat de metingen
    hier alle vier in één keer slaagden zegt niets over hoe betrouwbaar RadioBrowser is.

---

## `git status --porcelain`

Na de tweede ronde (taak I), op branch `fase-3c/afvuren`:

```
M  CLAUDE.md
M  docs/fase-3c/RAPPORT.md
```

---

## Bijlage: de 39 mutaties

```
=== BASELINE ===
  GESLAAGD: 213 passed in 26.77s

A1 volume op 0 gaat NA het geluid in plaats van ervoor
  gevangen: 6 failed, 207 passed in 26.61s
    door: FAILED, FAILED, FAILED

A2 het volume wordt NA stap 3 gelezen, dus altijd 0
  gevangen: 2 failed, 211 passed in 26.63s
    door: FAILED, FAILED

A3 de speakercontrole vooraf weg
  gevangen: 5 failed, 208 passed in 26.66s
    door: FAILED, FAILED, FAILED

A4 een verdwenen URI houdt de wekker niet tegen
  gevangen: 3 failed, 210 passed in 26.43s
    door: FAILED, FAILED, FAILED

A5 de OMKERING van SPEC 11.2.1 weg: ONBEKEND houdt de wekker ook tegen
  gevangen: 3 failed, 210 passed in 26.70s
    door: FAILED, FAILED, FAILED

A6 de URI-controle geeft FOUT bij een fout in plaats van ONBEKEND
  gevangen: 2 failed, 211 passed in 26.58s
    door: FAILED, FAILED

A7 de URI-controle vergelijkt op naam in plaats van op URI
  gevangen: 2 failed, 211 passed in 26.70s
    door: FAILED, FAILED

A8 ma_unavailable en speaker_unavailable worden niet onderscheiden
  gevangen: 1 failed, 212 passed in 26.55s
    door: FAILED

A9 radio_mode wordt altijd meegestuurd
  gevangen: 7 failed, 206 passed in 26.58s
    door: FAILED, FAILED, FAILED

A10 radio_mode wordt nooit meegestuurd
  gevangen: 3 failed, 210 passed in 26.42s
    door: FAILED, FAILED, FAILED

A11 geen terugval zonder radio_mode na een HTTP 500
  gevangen: 1 failed, 212 passed in 26.65s
    door: FAILED

A12 radio_mode wordt op False gezet in plaats van weggelaten
  gevangen: 2 failed, 211 passed in 26.67s
    door: FAILED, FAILED

A13 een mislukt afspelen levert toch een afgaande wekker op
  gevangen: 11 failed, 202 passed in 26.76s
    door: FAILED, FAILED, FAILED

A14 de oploop eindigt een stap te vroeg en haalt het doel niet
  gevangen: 8 failed, 205 passed in 26.40s
    door: FAILED, FAILED, FAILED

A15 de clamp kapt niet af aan de bovenkant
  gevangen: 2 failed, 211 passed in 26.73s
    door: FAILED, FAILED

A16 de clamp meldt niet dat hij clampte
  gevangen: 1 failed, 212 passed in 26.43s
    door: FAILED

A17 de afbreekmarge wordt >= in plaats van >
  gevangen: 2 failed, 211 passed in 26.38s
    door: FAILED, FAILED

A18 een onleesbaar volume breekt de oploop af
  gevangen: 1 failed, 212 passed in 26.60s
    door: FAILED

A19 de oploop controleert niet of de wekker nog afgaat
  gevangen: 1 failed, 212 passed, 1 error in 26.54s
    door: FAILED

A20 de oploop breekt niet af als de gebruiker aan de knop draait
  gevangen: 1 failed, 212 passed in 27.28s
    door: FAILED

A21 de oploop gaat door op een weggevallen speaker
  gevangen: 1 failed, 212 passed in 26.94s
    door: FAILED

A22 volume_ramp_unavailable wordt niet gemeld
  gevangen: 1 failed, 212 passed in 27.15s
    door: FAILED

A23 de stoptimer wordt niet gezet
  gevangen: 3 failed, 210 passed in 27.23s
    door: FAILED, FAILED, FAILED

A24 de tweede noodremcontrole wordt niet gezet
  gevangen: 3 failed, 210 passed, 1 error in 26.40s
    door: FAILED, FAILED, FAILED

A25 de timers worden bij stoppen niet afgezegd
  gevangen: 213 passed, 27 errors in 27.11s
    door: 

A26 de oploop wordt bij stoppen niet afgebroken
  gevangen: 1 failed, 212 passed, 21 errors in 27.17s
    door: FAILED

A27 het volume wordt bij stoppen niet teruggezet
  gevangen: 1 failed, 212 passed in 26.93s
    door: FAILED

A28 een onbekend oud volume wordt op een verzonnen 50 gezet
  gevangen: 1 failed, 212 passed in 27.17s
    door: FAILED

A29 het geluid wordt bij stoppen niet gestopt
  gevangen: 4 failed, 209 passed in 26.47s
    door: FAILED, FAILED, FAILED

A30 stoppen is niet idempotent: pas ná het werk uit het register
  gevangen: 4 failed, 209 passed in 26.23s
    door: FAILED, FAILED, FAILED

A31 unload stopt de afgaande wekkers niet
  gevangen: 1 failed, 212 passed, 22 errors in 26.75s
    door: FAILED

A32 een falende lamp sleept de wekker mee
  gevangen: 2 failed, 211 passed in 26.33s
    door: FAILED, FAILED

A33 de lamp krijgt een transition mee
  gevangen: 1 failed, 212 passed in 26.24s
    door: FAILED

A34 bij een noodremfout gaat de ingestelde lamp NIET aan
  gevangen: 1 failed, 212 passed in 26.25s
    door: FAILED

A35 de noodremmelding komt VOOR de lamp, dus de lamp overschrijft hem
  gevangen: 1 failed, 212 passed in 26.21s
    door: FAILED

A36 de oude notificatie wordt aan het eind gewist i.p.v. na de noodrem
  gevangen: 1 failed, 212 passed in 26.13s
    door: FAILED

A37 het failed-event gaat niet uit
  gevangen: 1 failed, 212 passed in 26.23s
    door: FAILED

A38 last_fired wordt bij een noodremfout niet gezet
  gevangen: 2 failed, 211 passed in 26.33s
    door: FAILED, FAILED

A39 speaker_lost_during_play wordt niet gemeld
  gevangen: 1 failed, 212 passed in 26.31s
    door: FAILED

=== SAMENVATTING ===
39 mutaties, 0 overgeslagen
alle uitgevoerde mutaties gevangen
```
