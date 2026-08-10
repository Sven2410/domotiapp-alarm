# Fase 3c — Het afvuren

Van noodrem tot stoptimer. Hierna is de server-side laag **compleet**: fase 4 kan de
kaart bouwen zonder dat er nog iets aan de serverkant bij moet.

**SPEC.md is gewijzigd op precies één plek**, en dat is de plek waar deze ronde om
vroeg: de verduidelijking bij SPEC 13.4 stap 4. Zie [Taak A](#taak-a--de-verduidelijking-in-spec-134-stap-4).

**De livecontrole (taak I) is niet gedaan.** De MA-koppeling op 8129 is wél een stuk
verder gekomen — de oorzaak van valkuil 32 is gevonden en weggenomen — maar de laatste
stap is inloggen, en Claude Code typt geen wachtwoorden. Zie
[Taak I](#taak-i--de-koppeling-op-8129-staat-klaar-maar-vraagt-een-wachtwoord).

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

## Taak I — De koppeling op 8129 staat klaar maar vraagt een wachtwoord

De livecontrole is **niet** gedaan. Wat er wél is gebeurd, is de oorzaak van valkuil 32
vinden, en die was niet wat fase 0b dacht.

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

### Wat de eigenaar moet doen

Drie stappen, en de flow rondt daarna zelf af:

1. **Instellingen → Apparaten & diensten → Integratie toevoegen → Music Assistant.**
2. Als URL: **`http://192.168.1.212:8095`** — het LAN-IP, **niet**
   `host.docker.internal:8095` (de browser kent die niet) en **niet** `localhost:8095`
   (binnen de HA-container is dat HA zelf).
3. Inloggen op de MA-pagina die verschijnt. Dat is het punt waar ik stop.

Het is niet meer nodig om de instance op my.home-assistant.io te registreren — die
route bestond alleen om de publieke redirector te laten weten waar deze instance staat,
en die redirector komt er nu niet meer aan te pas.

### Wat de eigenaar moet toetsen

Zodra de koppeling staat, is dit de livecontrole van taak I. De vraag "gaat de wekker
op tijd af" is in fase 3b al live beantwoord (12 ms); wat hier bij komt is of er
werkelijk geluid uit komt en of het volume klopt.

**Voorbereiding.** Een headless speaker met echte volumeregeling (uit CLAUDE.md):

```bash
docker exec -d ma-alarm sh -c 'snapclient tcp://127.0.0.1:1704 \
  --hostID wekker-slaapkamer --instance 1 \
  --player file:filename=/dev/null --mixer software \
  --logsink file:/tmp/snap1.log'
```

Label die speaker met **Music Assistant Wekker** en een lamp met **Verlichting
Wekker**, en zet debug-logging aan (staat al in `configuration.yaml`).

**T1 — de acht stappen in volgorde, met tijdstempels.** Zet via de kaart of via
`alarms/save` een wekker op twee minuten in de toekomst, met een SomaFM-kanaal en
volume 40. Toon daarna:

```powershell
docker logs ha-alarm --since 5m | Select-String "domotiapp_alarm"
```

**Wat er moet staan, in deze orde:** een `search` (de URI-controle), een `volume_set`
op **0**, `light.turn_on` als er een lamp is, dan `play_media`. Staat de `volume_set`
ná de `play_media`, dan is de volgorde stuk en hoort de wekker één keer hard te
beginnen — dat is ook hoorbaar.

**T2 — het volume loopt op.** Tijdens die eerste 20 seconden, in
Ontwikkelhulpmiddelen → Toestanden op `media_player.wekker_slaapkamer`, het attribuut
`volume_level` volgen. Verwacht: van 0,02 naar 0,40 in 20 stappen van 1 seconde.
**Meet dit niet uit een achtergrondtabblad** en niet op totaalduur alleen — dat is
valkuil 31, en dan lijkt een oploop van tien sprongen vloeiend. De betrouwbare meting
is de MA-kant:

```bash
docker exec ma-alarm sh -c 'grep -i volume /tmp/snap1.log | tail -30'
```

**T3 — `alarms/stop` zet het volume terug.** Noteer `volume_level` **vóór** de wekker
afgaat. Druk tijdens het afgaan op stop. Verwacht: `media_stop`, dan een `volume_set`
terug naar precies die eerste waarde — in die volgorde, want andersom klinkt de laatste
seconde op het oude volume.

**T4 — de afwijking ten opzichte van de wektijd.** Uit het log, de regel
`Wekker … afgegaan voor moment …`, vergeleken met de wektijd. Fase 3b mat 12 ms; fase
3c voegt daar de noodrem vóór het geluid aan toe, en die doet een `search` met een
time-out van 10 s. **Verwacht dus een grotere afwijking dan 12 ms**, en dat is
informatie die we niet hebben: hoe lang MA over een `search` doet op een koude
provider is niet gemeten. Als die afwijking in seconden loopt, is dat een bevinding
voor fase 4 — niet omdat een wekker 2 seconden te laat erg is, maar omdat het betekent
dat de noodrem tijd kost die niemand heeft begroot.

**T5 — een lege noodrem, om te zien dat hij écht remt.** Stop de snapclient
(`docker exec ma-alarm sh -c 'kill $(...)'`) zodat de speaker `unavailable` wordt, en
laat een wekker afgaan. Verwacht: **geen enkele** aanroep naar die speaker, een
`persistent_notification` met "de speaker … was niet bereikbaar", en de lamp wél aan
als er een lamp is ingesteld.

---

## Wat niet lukte

### De livecontrole (taak I)

Zoals hierboven: de koppeling komt tot MA's inlogpagina en daar houdt het op, want
inloggen vraagt een wachtwoord. De opdracht voorzag dit ("loopt het opnieuw vast op de
OAuth-redirect, meld dat dan en stop met taak I") — maar het is op een ándere plek
vastgelopen dan verwacht. De redirect is namelijk **wel** opgelost; wat overblijft is
alleen de inlog. Dat is een kleinere rest dan waar de opdracht op rekende, en de drie
stappen hierboven zijn zonder mij uit te voeren.

Gevolg voor deze fase: **alles in taak B tot en met H is getoetst, maar niets ervan is
live gehoord.** 213 tests zeggen dat de volgorde klopt, dat de oploop 20 stappen doet
en dat het volume teruggezet wordt. Ze zeggen niets over of een SomaFM-stream werkelijk
begint, of 2 % hoorbaar zachter is dan 40 %, en of MA's `search` snel genoeg antwoordt
om de noodrem geen merkbare vertraging te laten kosten. Die drie staan in de toetslijst.

### De cadans van de oploop is nog steeds niet als "vloeiend" vastgesteld

De tests tonen dat er 20 stappen van 1 seconde gepland worden en dat elke stap de
juiste waarde zet. Ze tonen **niet** dat het vloeiend klinkt — daar hoort een oor bij,
en fase 0b kwam er ook niet aan toe. SPEC 9.3 zegt uitdrukkelijk dat dit één constante
is die verhoogd mag worden; de test met `aantal=100` bestaat om die verhoging goedkoop
te houden.

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
   gitignored): `default_config:` uiteengelegd minus `my`. De oude versie staat als
   `configuration.yaml.fase3c-backup` naast het bestand. Het `logger:`-blok van fase 3b
   blijft staan.

---

## `git status --porcelain`

```
M  CLAUDE.md
M  SPEC.md
M  custom_components/domotiapp_alarm/__init__.py
M  custom_components/domotiapp_alarm/afvuren.py
M  custom_components/domotiapp_alarm/const.py
A  custom_components/domotiapp_alarm/noodrem.py
A  custom_components/domotiapp_alarm/oploop.py
A  custom_components/domotiapp_alarm/radiomodus.py
A  docs/fase-3c/RAPPORT.md
M  tests/conftest.py
A  tests/test_afvuren.py
A  tests/test_oploop.py
M  tests/test_planner.py
A  tests/test_radiomodus.py
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
