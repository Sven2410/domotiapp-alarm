# Fase 2 — SPEC.md

> **Dit is het verslag van de eerste ronde en op twee punten achterhaald.** De
> tien open vragen uit sectie 21 zijn inmiddels beantwoord en sectie 21 bestaat
> niet meer; `last_failure` heet nu `last_message`. Zie
> **[`RAPPORT-2B.md`](RAPPORT-2B.md)** voor de tweede ronde. Dit bestand blijft
> ongewijzigd als verslag van wat er in ronde 1 is gebeurd.

Doel: één bestand, `SPEC.md` in de wortel van de repo, als bron van waarheid voor
alle volgende fasen.

Geen code, geen tests, geen wijziging aan de integratie of de kaart. Geen
container gestart, geen browser geopend.

---

## Samenvatting

`SPEC.md` staat er: **1794 regels, 21 secties**. Alle vastgelegde beslissingen uit
de opdracht zijn letterlijk overgenomen en uitgewerkt tot iets waar een
fase-3-prompt uit te schrijven is.

De zeven punten die de opdracht expliciet eiste, en waar ze staan:

| Eis | Sectie |
|---|---|
| Opslagschema met letterlijk JSON-voorbeeld, versieveld en migratie | [14](../../SPEC.md#14-opslag), voorbeeld in 14.4, migratie in 14.6 |
| Elk WebSocket-commando: naam, invoer, uitvoer, fouten, wie | [15](../../SPEC.md#15-websocket-api), negen commando's plus 15.10 "wat er bewust géén commando is" |
| De kaart-config: sleutels, verplicht, wat de editor toont | [16](../../SPEC.md#16-de-kaart-config) |
| Person hernoemd/verwijderd, speaker weg, lamp weg, MA weg | [18](../../SPEC.md#18-entiteiten-die-verdwijnen-of-veranderen), vijf subsecties |
| Foutgedrag in het model van Scene SPEC 18 | [19](../../SPEC.md#19-foutgedrag), met geval A/B/C |
| Wat NIET in v1 zit, met per punt één regel waarom | [20](../../SPEC.md#20-wat-niet-in-v1-zit), 14 punten plus 6 bekende beperkingen |
| Open vragen, niet zelf ingevuld | [21](../../SPEC.md#21-open-vragen), 10 vragen |

**Markeringen:** 36 keer **VOORSTEL** (door mij ingevuld, niet vastgelegd), 13
keer **GEMETEN** (met vindplaats in fase 0, 0b of 1), 10 **OPEN VRAGEN**.

### Wat ik heb nagemeten in plaats van aangenomen

Twee controles op het document zelf, want een SPEC met kapotte verwijzingen is
een SPEC die niemand naslaat:

1. **Alle JSON-blokken die letterlijk bedoeld zijn, parseren.** Het opslagschema
   uit 14.4 is door `json.loads` gehaald. Daarbij kwam een fout boven die ik zelf
   had gemaakt: in een van de wekker-ID's stond een Arabische letter
   (`…c7e2ف1a5b9d4`) — een typefout die geldige JSON oplevert maar onzin is als
   hex-ID. Gecorrigeerd. Twee andere blokken zijn illustratief (met `…`) en
   parseren met opzet niet.
2. **Alle 129 interne verwijzingen resolveren**, en er zijn geen dubbele koppen.
   Mijn eerste controle meldde 8 kapotte links; dat bleek een fout in mijn
   **controlescript** — het streepte underscores weg als markdown-nadruk, terwijl
   GitHub die in anchors bewaart. Na correctie van het script: nul kapotte links.
   De links in het document waren al goed.

Ik heb ook het registry-entry-ID in het voorbeeld gecorrigeerd van een ULID naar
een **32-teken hex**, omdat fase 0 heeft vastgesteld dat het een
`random_uuid_hex` is (`helpers/entity_registry.py:234-235`). Een ULID is de vorm
van een *config entry*-ID, niet van een registry-entry-ID; dat door elkaar halen
zou in fase 3 een verkeerde validatie opleveren.

### Drie plekken waar ik iets heb toegevoegd dat de opdracht niet noemde

Deze zijn als VOORSTEL gemarkeerd, maar ze zijn groot genoeg om hier apart te
noemen omdat ze het schema of de API raken:

1. **Het veld `last_fired` in de opslag.** Zonder dat veld is het respijtvenster
   uit sectie 13.4 niet uitvoerbaar: de integratie kan bij setup niet weten of
   een wekker die om 06:45 had moeten afgaan al is afgegaan. Dan zou een herstart
   om 06:50 de wekker een tweede keer laten afgaan. Het veld bestaat uitsluitend
   daarvoor, en dat staat er ook zo bij.

2. **Een abonnement `ringing/subscribe`.** De opdracht legde vast dat de kaart
   van vorm verandert als een wekker afgaat, maar niet hoe de kaart dat te weten
   komt. Een abonnement is de keuze; het alternatief (een `binary_sensor` per
   persoon) staat als open vraag 6, omdat dat het product van een
   `integration_type: service` in een entiteitenleverancier verandert.

3. **Het volume wordt na de wekker teruggezet** (sectie 9.5). Niet gevraagd, wel
   nodig: zonder dit staat de speaker de rest van de dag op het wekvolume. Fase
   0b had dit al als aandachtspunt.

### Eén plek waar ik de opdracht heb aangevuld met een waarschuwing

De opdracht zegt dat geluid verplicht is, en dat zoeken alle soorten mag
teruggeven. Maar een **los nummer stopt van zichzelf** na een paar minuten,
waarna het stil is terwijl niemand wakker is. Sectie 8.3 laat de editor daarom
waarschuwen bij `track`, `podcast` en `audiobook`, niet-blokkerend. Het
alternatief — `radio_mode: true` meesturen zodat MA doorspeelt — is niet getoetst
en staat als open vraag 5.

---

## Wat niet lukte

1. **Drie open vragen kon ik niet sluiten omdat het metingen zijn die er niet
   zijn.** Ze staan als open vraag 1, 2 en 3 en verwijzen naar de toetslijst T3,
   T4 en T5 uit `docs/fase-0b/RAPPORT.md`:
   - hoeveel stappen een volume-oploop vloeiend maken (geen oor bij de speaker,
     en de browsertimer knijpt af);
   - of album, artiest en los nummer echt zoekbaar en afspeelbaar zijn (geen
     streamingprovider op de testinstance);
   - de volumeresolutie van andere hardware dan de Sonos die de eigenaar heeft
     bevestigd.

   Sectie 8 belooft nu dat alle zeven soorten werken. **Als open vraag 2 negatief
   uitpakt, is dat een SPEC-correctie**, en dat staat er expliciet bij in plaats
   van dat het later een verrassing wordt.

2. **De vorm van de tijdkiezer is niet geverifieerd.** Sectie 5.2 eist dat hij op
   iOS, Android en desktop werkt en stelt `ha-time-input` voor met
   `<input type="time">` als terugval. Ik heb geen van beide op een echt toestel
   gezien; dit is een eis met een voorstel, geen gemeten keuze. Fase 3 of 4 moet
   het aantonen — en dat is precies het soort claim waar de werkafspraak "echte
   kliks in een echte browser" voor bestaat.

3. **Ik heb geen uitspraak kunnen doen over de stoptoestand op HA's ingebouwde
   panelen.** Fase 1 stelde vast dat Lovelace-resources daar niet worden geladen,
   dus de kaart komt er alleen binnen via `add_extra_js_url` en dat werkt alleen
   met een verse `index.html`. Of dat de stopknop op `/home/overview` onbetrouwbaar
   maakt, is niet gemeten. Staat als open vraag 9, omdat het bepaalt welke
   dashboards de eigenaar mag aanbevelen — en de stopknop is de enige manier
   waarop een klant een wekker uitzet.

4. **Twee JSON-blokken in het document parseren met opzet niet.** Het blok in
   15.1 gebruikt `…` om naar sectie 14.2 te verwijzen, en het blok in 15.9 bevat
   drie losse berichten in plaats van één document. Beide zijn illustratief. Ik
   heb ze niet omgezet naar geldige JSON omdat dat het voorbeeld langer zou maken
   zonder het duidelijker te maken; wie ze automatisch wil valideren, moet ze
   overslaan.

---

## Aannames

De opdracht vroeg om onduidelijkheden zichtbaar te maken in plaats van stil in te
vullen. Dat is gebeurd met **36 VOORSTEL-markeringen** in `SPEC.md` en **10 open
vragen**. Wat hieronder staat zijn de aannames die *niet* als VOORSTEL in het
document staan omdat ze de vorm van het document raken en niet de inhoud van het
product:

1. **De sectienummering en -indeling zijn van mij.** De opdracht gaf een lijst
   eisen, geen structuur. Ik heb de indeling van DomotiApp Scene's `SPEC.md`
   aangehouden (product → architectuur → kaart → editor → opslag → API → rechten
   → foutgedrag → niet-in-v1), omdat de eigenaar die vorm kent en omdat de
   fase-rapporten ernaar kunnen verwijzen.

2. **`SPEC.md` staat in de wortel**, zoals opgedragen, en verwijst naar de
   fase-rapporten in `docs/` in plaats van hun inhoud te herhalen. Waar een keuze
   uit een meting volgt, staat de vindplaats erbij (bestand plus regelnummer waar
   dat bestond).

3. **Ik heb `CLAUDE.md` niet gewijzigd.** De projectstandtabel daar noemt fase 2
   nog niet. Dat is bewust: de werkafspraak zegt dat de projectstand meegaat in de
   PR van de fase die hem verandert, maar de opdracht voor deze fase zegt
   uitdrukkelijk "branch fase-2/spec met **alleen** SPEC.md". Die instructie is
   specifieker en gaat voor. **Dit is wel een punt om te beslissen**: blijft de
   projectstand achterlopen, dan krijgen we dezelfde achterstand die DomotiApp
   Scene met `CLAUDE.md` opliep.

Geen andere aannames gedaan.

---

## `git status --porcelain`

Zie de terminaluitvoer van deze ronde; op het moment van committen leeg op de
bestanden van deze fase na.
