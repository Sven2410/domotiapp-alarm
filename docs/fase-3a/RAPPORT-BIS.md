# Fase 3a-bis — SPEC bijgewerkt naar de bevindingen van fase 3a

Drie beslissingen van de eigenaar verwerkt. Dit was een ronde waarin `SPEC.md` **op
verzoek** gewijzigd is. Geen code, geen tests.

---

## Samenvatting

`SPEC.md` ging van 2019 naar **2138 regels**.

| Beslissing | Verwerkt in |
|---|---|
| 1. `radio_mode` wordt **voorwaardelijk** meegestuurd | **8.3.1 herschreven**, plus 20.1 punt 9 |
| 2. De directe URI-controle wordt **niet** gebruikt | **11.2 herschreven**, **11.2.2 nieuw**, 11.2.1 aangevuld, plus 20.1 punt 8 |
| 3. Repair issues komen in fase 3b | **`CLAUDE.md`**, als openstaand punt met de fase erbij. **SPEC 19.2 ongewijzigd.** |

### Beslissing 1 — `radio_mode` voorwaardelijk

SPEC 8.3.1 heette *"`radio_mode` wordt in fase 3 uitgezocht"* met twee takken; hij
heet nu **"`radio_mode` wordt voorwaardelijk meegestuurd"** en beschrijft één regel:

- **meesturen als en alleen als** de provider van het gekozen geluid
  `SIMILAR_TRACKS` ondersteunt;
- anders het veld **weglaten** — niet op `false` zetten, maar weglaten, zodat MA zijn
  eigen standaard houdt;
- **faalt de controle zelf, dan géén `radio_mode`.**

De meting uit 3a staat erin als onderbouwing, met de vindplaatsen: de doorverbinding
(`services.py:141`, `media_player.py:406`/`:556`, client `player_queues.py:209`), de
gemeten tegenstelling (HTTP 200 met 1 item versus HTTP 500 met een lege queue), de
serverfout, en `ProviderFeature.SIMILAR_TRACKS` op
`music_assistant_models/enums.py:627`. Ook welke providers de feature hebben, zodat
niemand hoeft te gokken.

Hoe de integratie de provider vaststelt staat er ook: het deel vóór de `://` in de
opgeslagen `uri` is het instantie-ID of domein van de provider.

**Wat ik daar zelf aan heb toegevoegd, en waarom.** De asymmetrie met 11.2.1 sprong
eruit: daar laat een mislukte controle de wekker juist doorgaan. Dat kan als
inconsistentie lezen, dus er staat nu een tabel bij die laat zien dat het dezelfde
afweging is op andere feiten:

| | Bij twijfel meesturen | Bij twijfel weglaten |
|---|---|---|
| Provider kan het wél | eindeloos doorspelen | geluid stopt na het item — hinderlijk |
| Provider kan het **niet** | **HTTP 500, geen geluid** | geluid stopt na het item — hinderlijk |

De rechterkolom heeft geen enkel geval waarin er niets klinkt. Dat is precies de
reden die de eigenaar gaf, nu in het document.

De waarschuwing uit 8.3 blijft staan en is nu **scherper afgebakend**: hij geldt voor
precies de gevallen waarin `radio_mode` niet meegestuurd wordt — een geluid met een
eindige duur waarvan de provider de feature niet heeft, of waarvan dat niet vast te
stellen is.

### Beslissing 2 — de zoekroute is de vastgelegde route

SPEC 11.2 had "tak A of tak B"; de zoekroute is nu **de** route, met de reden van de
eigenaar erin: ingrijpen in de binnenkant van een andere integratie is precies wat bij
een update stilletjes breekt, en dit product mag niet stil breken. De vergelijking met
de groep-constanten uit DomotiApp Scene staat erbij.

De zwakte is **niet afgezwakt** maar preciezer opgeschreven:

- de kop van het blok is nu *"De zoekroute is geen identiteitscontrole"* in plaats van
  "niet waterdicht";
- de meting met **twee albums `"Ghost Stories"` van verschillende artiesten** staat er
  als onderbouwing;
- vals positief én vals negatief staan er, met de aantekening dat het vals negatief
  **het ergste faalgeval** is omdat het van een werkende wekker een stille maakt.

**11.2.2 is nieuw** en legt `music/item_by_uri` vast als **voorkeursoptie zodra MA hem
via een gepubliceerde service beschikbaar stelt**, met de drie gemeten uitkomsten en
hun vindplaatsen. Er staat een expliciet **criterium om over te stappen**: de controle
verschijnt als service in `components/music_assistant/services.yaml`, naast de zes die
er nu zijn. Dat is dezelfde soort openstaande post als de tweede laadroute, en dat
staat er ook zo.

### Beslissing 3 — repair issues in 3b

In `CLAUDE.md` staat nu een tabel **"Openstaande punten met een fase erbij"**, met het
repair-issuepunt als eerste regel: wat er ontbreekt (SPEC 19.2 geval B regel 4 en
geval C regel 3), wat de code nu wél doet (`ERROR` loggen met de reden), waar het
zit (`store.py`), en in welke fase het hoort (**3b**, samen met de
`persistent_notification` uit SPEC 11.7, omdat die dezelfde machinerie gebruiken).

**SPEC 19.2 is niet aangeraakt.** Die beschrijft het gewenste gedrag en dat verandert
niet — het is de implementatie die achterloopt, niet de eis.

Ik heb de tabel meteen gebruikt om de twee kaartpunten uit fase 1 (`getCardSize()`,
`panel: true`) en de MA-voorkeursroute erin te zetten, zodat er één plek is waar
openstaande punten met een fase staan in plaats van drie losse alinea's.

---

## Wat de consistentiecontrole opleverde

Twee echte fouten in mijn eigen wijzigingen, plus één inconsistentie die door de
beslissingen ontstond.

**1. Een kapotte ankerlink.** Door het hernoemen van 8.3.1 wees een verwijzing in
sectie 15.6 naar de oude titel:

```
KAPOT: 831-radio_mode-wordt-in-fase-3-uitgezocht
```

Gerepareerd. Dit is precies waarom die controle bestaat: de link stond 700 regels
verderop en was met lezen niet te vinden.

**2. 11.2.2 stond vóór 11.2.1.** Ik had de nieuwe subsectie direct achter de tekst van
11.2 gezet, waardoor de nummering `[2, 1]` werd. Herordend, met een controle dat de
tekstlengte gelijk bleef zodat er bij het verplaatsen niets verdween.

Mijn controlescript is daarvoor uitgebreid met een **subsectienummeringscontrole** per
bovenliggende sectie. Die bestond nog niet — in de vorige rondes controleerde ik
alleen de hoofdsecties, en deze fout zou daar dus door zijn geglipt.

**3. Een VOORSTEL op iets dat nu vastligt.** De opdracht vroeg hier expliciet naar, en
er was er één: SPEC 15.6 markeerde de `limit` als *"VOORSTEL standaard 10, maximum
50"*. Maar 11.2 gebruikt nu **50** als bovengrens om het valse negatief te beperken —
dus dat maximum is load-bearing geworden. Gesplitst:

> `| limit | int | nee — standaard **VOORSTEL** 10; **maximum 50 ligt vast** |`

met de reden eronder: verlaag je het maximum, dan wordt een geldige URI eerder
onterecht als verdwenen gemeld en gaat een werkende wekker niet af. De standaard van
10 blijft een voorstel, want die geldt alleen voor de editor waar de gebruiker
meekijkt.

**Eindstand van de controle:**

| Controle | Uitkomst |
|---|---|
| Ankerlinks | **150 links, 0 kapot, 0 dubbele koppen** |
| Inhoudsopgave vs secties | 20 op 20, labels en ankers kloppen, nummering 1–20 |
| Subsectienummering | alle aaneensluitend, ook 11.2.1/11.2.2 |
| Bekende beperkingen 20.1 | aaneensluitend 1–12 (twee nieuwe erbij) |
| Restanten van "tak A/tak B" of "fase 3 zoekt uit" | **0** |
| Open vragen / verwijzingen naar sectie 21 | **0** |
| VOORSTEL | 30 (was 30; één gesplitst, geen nieuwe) |
| GEMETEN | 16 (was 15) |
| JSON-blokken | 3 van 5 parseren; 2 illustratief, onveranderd |

---

## Wat niet lukte

1. **Beslissing 1 en beslissing 2 leken elkaar tegen te spreken, en dat kostte een
   herziening halverwege deze ronde.** Beslissing 1 vraagt of de provider
   `SIMILAR_TRACKS` heeft; beslissing 2 wijst juist de route af waarlangs je dat het
   makkelijkst vraagt (`entry.runtime_data.mass`). Mijn eerste versie van 8.3.1 zei
   daarom dat het "een open punt" was hoe de integratie erbij komt — met als
   praktisch gevolg dat `radio_mode` **nooit** meegestuurd zou worden en de
   beslissing dood letter bleef.

   Dat was fout, en ik heb het rechtgezet in plaats van laten staan: **de feature is
   ook zonder die internals vast te stellen.** Welke providerdomeinen
   `SIMILAR_TRACKS` hebben staat in MA's broncode, en welke provider bij een geluid
   hoort staat in het deel vóór de `://` van de opgeslagen `uri`. Een constante met
   die domeinen is dezelfde constructie als de groep-constanten in DomotiApp Scene:
   geen afhankelijkheid van andermans binnenkant, tegen de prijs dat de lijst stil
   kan verouderen.

   SPEC 8.3.1 heeft nu een tabel met beide routes en de vastgelegde keuze, plus een
   analyse van wat het stille verouderen kost in beide richtingen — en de eis dat
   fase 3b de HTTP 500 van `play_media` **expliciet afvangt** in plaats van op de
   lijst te vertrouwen. Dat laatste staat ook in de openstaande punten.

2. **Geen van de wijzigingen is getoetst tegen code.** Deze ronde raakte alleen
   `SPEC.md` en `CLAUDE.md`; er is geen implementatie van `radio_mode` of van de
   URI-controle, want dat is fase 3b. Wat er is getoetst, is het document zelf: links,
   nummering, markeringen.

---

## Aannames

1. **Het rapport staat in `docs/fase-3a/RAPPORT-BIS.md`**, naast het rapport van 3a,
   omdat dit dezelfde fase corrigeert. `RAPPORT.md` van 3a is **niet** gewijzigd: dat
   beschrijft de metingen en die veranderen niet door een beslissing. Anders dan bij
   fase 2 heb ik er ook geen verwijzing bovenin gezet, omdat er in 3a niets onwaar is
   geworden — de bevindingen staan, alleen de gevolgtrekking is nu beslist.

2. **De provider is af te leiden uit het deel vóór `://` in de URI.** Dat is de vorm
   die in de metingen van fase 0b en van de eigenaar voorkomt
   (`spotify--ZvzrFmgX://`, `somafm://`, `library://`, `itunes_podcasts://`,
   `radiobrowser://`). Dat **elke** provider zich zo gedraagt is aangenomen, niet
   nagemeten — en het is een aanname waar de hele `radio_mode`-regel op rust.

3. **De lijst providerdomeinen met `SIMILAR_TRACKS` is uit MA's broncode afgeleid**,
   door te zoeken welke providers die feature noemen. Dat is een grep en geen
   gemeten gedrag: dat een provider de feature noemt betekent niet noodzakelijk dat
   hij hem op elke server ook levert.

4. **Het maximum van 50 in `limit` is load-bearing verklaard** op grond van mijn eigen
   redenering over het valse negatief, niet op grond van een meting. Er is niet
   gemeten bij welke `limit` een geldige URI daadwerkelijk buiten de treffers valt.

Geen andere aannames gedaan.

---

## `git status --porcelain`

Zie de terminaluitvoer van deze ronde; op het moment van committen leeg op de
bestanden van deze ronde na.
