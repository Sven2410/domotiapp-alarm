# Fase 2b — SPEC.md: de open vragen gesloten

Tweede ronde op branch `fase-2/spec`, PR #4. De eigenaar heeft de tien open vragen
uit sectie 21 beantwoord; die zijn verwerkt en sectie 21 is verwijderd.

**Waarom een apart rapportbestand.** `docs/fase-2/RAPPORT.md` beschrijft de eerste
ronde en klopt voor die ronde: hij noemt tien open vragen en zegt dat sectie 8
alle zeven mediasoorten aanneemt. Dat is nu allebei achterhaald. Dat rapport
bijwerken zou het onleesbaar maken als verslag van wat er tóen is gebeurd, en de
geschiedenis van dit project is bruikbaar juist omdat elke ronde zijn eigen
verslag heeft. Er staat nu één verwijzing bovenaan `RAPPORT.md` naar dit bestand,
zodat niemand de oude tekst als actueel leest.

---

## Samenvatting

Alle tien beslissingen zijn verwerkt. `SPEC.md` ging van 1794 naar **1947 regels**
en heeft **20 secties** — sectie 21 is weg, inclusief alle verwijzingen ernaar.

| | Beslissing | Verwerkt in |
|---|---|---|
| O1 | 20 stappen van 1 s, vastgelegd; één constante, techniek laat 100 toe | 9.3, VOORSTEL weg |
| O2 | Album, artiest en los nummer werken — gemeten door de eigenaar | **8.2.1 nieuw**, met de drie aanroepen en hun uitkomsten |
| O3 | Volumeresolutie op Sonos exact; andere merken aanvaard risico | 9.3 + verplaatst naar **20.1 punt 3** |
| O4 | URI-validatie: fase 3 zoekt een directe controle; zoekroute is terugval | 11.2, **beide takken uitgeschreven** |
| O5 | `radio_mode`: fase 3 zoekt het uit | **8.3.1 nieuw**, beide uitkomsten uitgeschreven |
| O6 | Abonnement, geen entiteit | 15.9, VOORSTEL weg |
| O7 | Overgeslagen wekker wordt getoond, als mededeling | 11.7, 13.4, **14.2.1 nieuw**, schema in 14.2 |
| O8 | Eenmalige wekker blijft staan met `enabled: false` | 14.5, VOORSTEL weg |
| O9 | Stoptoestand niet op ingebouwde panelen | verplaatst naar **20.1 punt 2** |
| O10 | Time-out `sound/search` 10 s | 15.6, met de letterlijke tekst |

**VOORSTEL** ging van 36 naar **31**; **GEMETEN** van 13 naar **15**. De
metingen van de eigenaar staan als *"gemeten door de eigenaar, augustus 2026"*
met de getallen erbij, omdat ze in geen enkel faserapport staan.

### De ene keuze die ik zelf moest maken: O7

De opdracht liet open of `last_failure` ook voor niet-fouten gebruikt wordt of er
een tweede veld bij komt. **Gekozen: één veld, hernoemd naar `last_message`, met
een `severity` van `"error"` of `"notice"`.** De verantwoording staat in
`SPEC.md` 14.2.1; kort:

- **Eén veld** geeft één codepad, één "Begrepen"-knop, één plek in het schema, en
  één regel voor de kaart: toon `last_message`, kies kleur en toon op `severity`.
- **Twee velden** roept de vraag op wat er gebeurt als ze **beide** gevuld zijn —
  welke toont de kaart, in welke kleur? De kaart heeft één regel per wekker, dus
  die toestand voegt niets toe.
- **Hernoemen** was nodig omdat `last_failure` zou liegen zodra er mededelingen in
  staan. Er is geen migratiekost: er is nog geen versie in productie.

De prijs staat er expliciet bij als bekende beperking (20.1 punt 9): **een nieuwe
melding overschrijft de vorige.** Een wekker die gisteren mislukte en vandaag werd
overgeslagen, toont alleen het overslaan.

Er zijn nu twee soorten `kind` voor overslaan: `skipped_grace_window` (HA stond
uit) met de tekst die de eigenaar heeft vastgelegd, en `skipped_by_user` (de klant
had het zelf ingesteld).

### Wat de consistentiecontrole opleverde

Ik heb de controle uit fase 2 opnieuw gedraaid en uitgebreid:

| Controle | Uitkomst |
|---|---|
| Verwijzingen naar OPEN VRAAG of sectie 21 | **0** |
| Interne ankerlinks | **130 links, 0 kapot, 0 dubbele koppen** |
| Inhoudsopgave vs secties | **20 vs 20**, labels én ankers kloppen, nummering aaneensluitend 1–20 |
| JSON-blokken | 3 van 5 parseren; 2 zijn illustratief (met `…`), zoals in ronde 1 |
| Nummering van 20.1 | aaneensluitend **1–10** |

Twee keer bleek mijn eigen **controlescript** fout te zitten en niet het document
— hetzelfde patroon als in ronde 1, waar het script underscores wegstreepte:

1. De eerste TOC-controle meldde **71 secties "niet in de inhoudsopgave"**. Dat
   kwam doordat ik álle koppen met een cijfer vergeleek, inclusief subsecties als
   `11.2`, terwijl de inhoudsopgave alleen de twintig hoofdsecties opsomt — precies
   zoals in DomotiApp Scene.
2. De tweede poging meldde twintig mismatches met een verschuiving van precies
   één. Oorzaak: `## Inhoud` is zelf een kop op niveau 2 en schoof de vergelijking
   op.

Na correctie van het script: alles klopt. Ik noteer het omdat het inmiddels drie
keer is voorgekomen dat mijn meetgereedschap eerder stuk was dan het gemeten
object.

---

## Wat niet lukte

**Twee tegenstrijdigheden gevonden, niet stil opgelost.** De opdracht vroeg die te
melden in plaats van ze zelf recht te trekken. Ze zijn hieronder beschreven zoals
ik ze aantrof; **de eigenaar heeft ze daarna allebei beslist en ze zijn verwerkt**
— zie het [addendum](#addendum--de-twee-tegenstrijdigheden-beslist).

1. **Sectie 15.6 motiveert de sorteervolgorde met iets dat kan vervallen.**
   Daar staat als VOORSTEL: *"afspeellijsten en radio eerst, want dat zijn de
   soorten die bij een wekker passen"*, met een verwijzing naar 8.3. Maar onder
   **tak A van O5** (`radio_mode` werkt) zijn alle soorten gelijkwaardig en valt de
   motivering weg — een los nummer is dan een even goede wekker als een
   radiostation.

   **Wat er beslist moet worden:** blijft de sorteervolgorde staan omdat radio en
   afspeellijsten in de praktijk toch de logische keuze zijn, of vervalt hij samen
   met de waarschuwing? Fase 3 komt hier vanzelf langs bij het uitzoeken van
   `radio_mode`; het is één regel in 15.6.

2. **Sectie 19.5 zegt dat `INFO` voor "precies één geval" is, en dat is er nu
   twee.** De tabel noemt alleen *"een wekker overgeslagen wegens het
   respijtvenster"*. O7 heeft daar een tweede overslaan naast gezet
   (`skipped_by_user`), en van dat geval staat het logniveau nergens.

   **Wat er beslist moet worden:** wordt een door de klant ingesteld overslaan óók
   op `INFO` gelogd — dan moet de zin "precies één geval" weg — of op `DEBUG`,
   omdat het verwacht gedrag is dat de klant zelf heeft aangezet? Mijn neiging is
   `DEBUG`, maar dat is niet aan mij en het is één cel in een tabel.

Verder:

3. **`audiobook` blijft ongetoetst**, zoals de opdracht al vaststelde. Nu
   vastgelegd als bekende beperking 20.1 punt 8, met de aantekening dat het één
   regel in de soortenlijst is als het niet werkt.

4. **Twee JSON-blokken parseren nog steeds niet**, met opzet: het blok in 15.1
   gebruikt `…` om naar 14.2 te verwijzen, en het blok in 15.9 bevat drie losse
   berichten in plaats van één document. Ongewijzigd gelaten om dezelfde reden als
   in ronde 1.

---

## Aannames

1. **Apart rapportbestand in plaats van `RAPPORT.md` bijwerken.** Verantwoord
   bovenaan dit bestand. In `RAPPORT.md` staat nu één verwijzing hiernaartoe.

2. **De twee nieuwe subsecties hebben een nummer binnen hun sectie gekregen**
   (`8.2.1`, `8.3.1`, `14.2.1`) in plaats van dat ik de bestaande nummering heb
   opgeschoven. Dat houdt alle bestaande verwijzingen in het document en in de
   faserapporten geldig. `8.2.1` staat bij "Sla de URI op" omdat de gemeten
   soorten en de dubbele-namenbevinding daar hun consequentie hebben.

3. **De `limit` van 50 in tak B van de URI-controle** is van mij, en staat als
   zodanig in 11.2: het is het maximum uit 15.6 en het beperkt het valse
   negatief. Niet gemeten.

4. **Dat tak B niet faalt op een time-out** — kan de controle niet worden
   uitgevoerd, dan start de wekker wél — is ook van mij. De redenering staat er:
   liever een wekker die misschien niets speelt dan een wekker die zeker niets
   speelt. Dat is een omkering van de noodremlogica op precies dit punt en
   verdient de aandacht van de eigenaar.

Geen andere aannames gedaan; al het overige is een letterlijke verwerking van de
tien beslissingen.

---

## Addendum — de twee tegenstrijdigheden beslist

De eigenaar heeft de twee gemelde tegenstrijdigheden beslist en aanname 4
bevestigd. Alle drie zijn in dezelfde branch verwerkt.

**1. SPEC 15.6 — de sorteervolgorde blijft, de motivering verandert.**
Afspeellijsten en radio staan nog steeds eerst, maar de reden is nu **wat mensen in
de praktijk voor een wekker kiezen**, niet dat de andere soorten technisch
tekortschieten. De verwijzing naar 8.3 als onderbouwing is weg, en er staat
expliciet bij dat de regel geldig blijft ongeacht wat fase 3 over `radio_mode`
vindt. Daarmee is de VOORSTEL-markering vervallen: dit is nu vastgelegd.

**2. SPEC 19.5 — het onderscheid tussen de twee overslagen.**
`skipped_grace_window` blijft **`INFO`**: de klant kon er niets aan doen, Home
Assistant stond uit, en dat hoort in een log dat een beheerder zonder debugniveau
leest. `skipped_by_user` wordt **`DEBUG`**: dat is precies wat de klant vroeg. De
zin over "precies één geval" klopt daarmee weer en noemt het onderscheid nu zelf.
Er staat één regel bij die de twee lagen scheidt: **het logniveau gaat over de
beheerder, de mededeling op de kaart over de klant** — beide gevallen leveren wél
een mededeling op.

**3. SPEC 11.2.1 nieuw — de omkering van de noodremlogica staat er nu expliciet.**
Aanname 4 is akkoord en ongewijzigd gebleven, maar hij was impliciet: hij stond als
één bijzin in een blockquote. Nu is het een eigen subsectie die zegt **dat** het
een bewuste omkering is en **waarom**:

- overal elders in sectie 11 geldt "kun je niet vaststellen dat het goed gaat, ga
  dan niet af"; hier geldt het omgekeerde;
- een trage zoekopdracht is geen reden om iemand niet te wekken;
- het verschil is dat de andere controles iets vaststellen over de **speaker**, en
  dus over de kans op geluid, terwijl deze iets vaststelt over een **hulpaanroep
  die zelf kan falen** zonder dat er met het geluid iets aan de hand is;
- het slechtste geval wordt achteraf opgevangen door de tweede
  `available`-controle uit 11.3, met de melding die daarbij hoort.

Er staat een tabel bij die de twee uitkomsten scheidt, omdat ze in code op elkaar
lijken: **"de URI bestaat niet"** (controle gelukt, antwoord negatief) houdt de
wekker tegen; **"de controle kon niet worden uitgevoerd"** (time-out of fout) niet.
En de subsectie geldt óók onder tak A, want een directe controle kan net zo goed
onbereikbaar zijn.

**Consistentiecontrole opnieuw gedraaid** na deze drie wijzigingen:

| Controle | Uitkomst |
|---|---|
| Interne ankerlinks | **133 links, 0 kapot, 0 dubbele koppen** |
| Inhoudsopgave vs secties | 20 op 20, labels en ankers kloppen |
| Verwijzingen naar OPEN VRAAG of sectie 21 | **0** |
| JSON-blokken | 3 van 5 parseren; 2 illustratief, onveranderd |
| VOORSTEL | 31 → **30** (15.6 is nu vastgelegd) |

`SPEC.md` staat nu op **1991 regels**. Er zijn geen openstaande
tegenstrijdigheden meer.

---

## `git status --porcelain`

Zie de terminaluitvoer van deze ronde; op het moment van committen leeg op de
bestanden van deze ronde na.
