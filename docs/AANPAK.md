# Aanpak — wat er van DomotiApp Alarm herbruikbaar is

Geschreven aan het eind van fase 11, toen het product functioneel af was en
1.0.4 bij de eigenaar draaide.

> **Over het model.** De opdracht verwees naar `C:\dev\domotiapp-scene\docs\AANPAK.md`.
> Dat bestand bestaat daar niet — `docs/` bevat alleen fasemappen, en in de wortel
> staan `CLAUDE.md`, `INVENTARIS.md`, `ONDERZOEK-FRONTEND.md`, `README.md` en
> `SPEC.md`. Dit stuk is daarom van nul opgezet, met `INVENTARIS.md` als enige
> stijlvoorbeeld (vindplaats bij elke bewering).

Dit is geen samenvatting van wat er gebouwd is; daarvoor zijn de fase-rapporten.
Dit gaat over **wat een derde product hiervan moet overnemen**, en vooral over wat
achteraf anders had gemoeten. Dat laatste staat onderaan en is het nuttigste deel.

---

## 1. Wat je één op één kunt overnemen

| Wat | Waar | Waarom het werkte |
|---|---|---|
| **De laadketen met twee routes plus een lader** | `__init__.py`, `resource.py`, `loader.py` | Drie onafhankelijke faalgevallen van HA's frontend afgedekt: een verouderde `index.html`, een verouderd document mét onze import, en de registratierace. Elk is apart gemeten. Neem dit over vóórdat je iets anders bouwt |
| **`registreer.js`** | `src/registreer.js` + `scripts/check-registratie.mjs` | Eén plek die `customElements.define` aanroept, plus een script dat bewaakt dat het één plek blijft. De scoped-registry-race van HA 2026.8 kost anders dagen |
| **De bundelhash als `?v=`, berekend bij setup** | `__init__.py` | Verandert precies wanneer de inhoud verandert. Het versienummer gebruiken is de klassieke vergissing |
| **De meetopstelling voor de frontend** | `scripts/telefoon.html`, `scripts/meet-afsnijden.js`, `scripts/bubble-meetopstelling.md` | Meet in de conditie van de klant en meet de oorzaak, niet het gevolg. Zie fase 8 t/m 10 |
| **De mutatieproef als scriptje per fase** | `scripts/mutaties-fase-*.py` | Tekstvervanging + testrun + terugzetten. Kost een half uur en vindt in dit project in **elke** ronde iets |
| **De scheiding puur / onzuiver** | `volgende.py`, `oploop.py`, `radiomodus.py`, `weergave.js`, `editorlogica.js` | Alles wat een beslissing is, staat in een functie zonder `hass` en zonder klok. Dat is waarom de getallen in gewone tests staan en niet in browsermetingen |
| **De valkuilenlijst met vindplaats** | `CLAUDE.md` | Zonder vindplaats wordt zo'n lijst binnen twee maanden folklore. Mét vindplaats is hij na te rekenen — en in fase 11 bleek er één (62) fout te zijn, wat alleen op te merken was doordat de meting erbij stond |

## 2. Wat je moet overnemen als houding, niet als code

**Een test telt pas als hij aantoonbaar faalt op de code van vóór de fix.** En
dan nog: laat hem faliekant falen, niet met een importfout. In fase 11 leverde
de eerste poging een `ERROR` op omdat de nieuwe constante ontbrak — dat bewijst
niets. De juiste opzet was de constanten laten staan en alléén de bedrading
terugdraaien.

**Positieve controles.** Een test die alleen op falen let, komt door een
implementatie die altijd faalt. Elke "X gebeurt niet"-test heeft hier een
"maar Y gebeurt wél" naast zich.

**Zeg alleen wat je hebt vastgesteld.** Dit is drie keer misgegaan (fase 6, 6b,
11) en het patroon is elke keer hetzelfde: de tekst is geschreven bij de
SPEC-sectie, niet bij de regel code die hem verstuurt. De grammaticale toets
werkt: elk *omdat*, *want* of elke bewering over de buitenwereld is verdacht.

**Meet de oorzaak, niet het gevolg.** Fase 8 mat overloop naar rechts, fase 9
voegde overloop naar links en tekst-buiten-element toe, fase 10 voegde
"getekende breedte tegen beschikbare breedte" toe. Alleen die laatste vindt een
fout die op de meetmachine niet zichtbaar is.

---

## 3. Wat achteraf anders had gemoeten

Dit is het deel dat een volgend product tijd bespaart.

### 3.1 De updatetest had fase 1 moeten zijn, niet fase 11

**Dit is de duurste les van het hele project.** De laadketen is in fase 1
gebouwd en met twee routes gemeten. Wat er níét gemeten is, is de handeling die
elke klant elke release doet: **bijwerken van een oude versie naar een nieuwe**.
Dat is een halve dag werk (een verse instance, een oude versie erop, de nieuwe
eroverheen) en het bleef tien fases liggen.

Wat het gekost heeft: de eigenaar heeft het drie keer meegemaakt tijdens het
testen en elke keer opgelost door de app volledig af te sluiten — een handeling
die je van een klant niet kunt vragen en die het probleem onzichtbaar maakte
voor iedereen die niet toevallig oplette. En de fout stond de hele tijd in
`CLAUDE.md`, als valkuil 62, met een **verkeerde diagnose**.

De regel voor een volgend product: **een installatiepad dat de klant loopt, toets
je in de ronde waarin je hem bouwt.** Installeren is in fase 5 getoetst,
bijwerken pas in fase 11. Dat is dezelfde handeling voor de klant.

### 3.2 Valkuil 62 was tien fases lang fout, en de vorm van de fout is leerzaam

Fase 7 mat `cache.match(url, {ignoreSearch: true})` en zag een oude bundel
terugkomen. Daaruit volgde de conclusie "de `?v=` is geen cache-buster". Maar
`ignoreSearch: true` was een vlag **van de lezer**, niet van de service worker.
De service worker zet die vlag alleen op de wortelroute; de file-cache-route
respecteert de querystring gewoon.

Zes rondes lang is er tijd gestoken in het opruimen van caches vóór elke
meting, op grond van een conclusie die niet klopte. En de échte oorzaak — het
**document** wordt gecachet, met de hash erin — is nooit onderzocht omdat de
valkuil al een verklaring bood.

De regel: **een valkuil die een verklaring biedt, stopt het onderzoek.** Schrijf
er daarom bij wat je precies hebt gemeten en met welke parameters, zodat een
latere ronde de conclusie kan narekenen in plaats van hem te geloven. Dat was
hier gelukkig gedaan, en alleen dáárdoor was de fout te vinden.

### 3.3 Twee rondes waren achteraf één ronde

**Fase 8 en 9 gingen allebei over afsnijden in een bubble card.** Fase 8 mat een
benadering (`grid_options: columns 6`) omdat de echte conditie er niet was; fase
9 bouwde de echte conditie en vond meteen iets dat fase 8 niet kón zien. Als de
echte conditie in fase 8 was opgezet — een uurtje werk, Bubble Card is een
bestand in `www/` plus een resource — was fase 9 niet nodig geweest.

Zelfde patroon bij **3a/3b/3c** en **4a/4b/4c**: die splitsingen waren wél
verstandig (ze hielden de PR's leesbaar), maar 3c-bis en 4a-bis waren
reparatierondes op een beslissing die één meting eerder te nemen was geweest.

De regel: **bouw de meetconditie voordat je de meting nodig hebt**, niet
andersom. Een benadering die je zelf "strenger dan de werkelijkheid" noemt, is
een aanname.

### 3.4 De aanname die een halve dag kostte

**"`box-sizing: border-box` declareren is genoeg."** Die stond nergens
opgeschreven, want niemand schrijft zoiets op — het is CSS zoals CSS werkt. In
fase 8 en 9 is het tijdveld twee keer onderzocht, twee keer met de conclusie
"het past ruim", en beide keren was dat waar op de meetmachine. Fase 10 vond de
oorzaak pas doordat de eigenaar screenshots stuurde die pixelmatig op te meten
waren: iOS past `border-box` niet toe op `input[type="time"]`.

Wat de tijd kostte was niet de reparatie (een wrapper, tien regels) maar de twee
rondes waarin de verkeerde vraag werd beantwoord: hoeveel ruimte heeft de
**tekst** nodig, terwijl het ging om hoe breed de **doos** getekend wordt.

De regel, en die staat nu als valkuil 70: **native formuliercontrols zijn de
enige plek waar een desktopmeting niet overdraagt.** Geef zo'n control nooit
zelf padding of een rand als hij `width: 100%` krijgt — dan is het boxmodel niet
meer relevant en hoef je het verschil ook niet te kennen.

### 3.5 Wat er goed ging en waarom het niet vanzelf gaat

De browsermetingen met echte kliks, `isTrusted`, en gemeten posities in plaats
van screenshots hebben in dit project vier fouten gevonden die een screenshot
niet had laten zien. Dat werkt alleen omdat het een **werkafspraak** is en geen
goede bedoeling: de verleiding om "het ziet er goed uit" te schrijven is bij elke
ronde aanwezig.

Hetzelfde geldt voor de mutatieproef. Hij is elf keer gedraaid en heeft elf keer
iets gevonden — twee keer een echte fout in de implementatie, vier keer een gat
in de tests, en vijf keer een regel die eruit kon omdat hij niets deed. Die
laatste categorie is de onverwachte opbrengst: **de proef maakt de code kleiner,
niet groter.**

---

## 4. Wat een derde product als eerste zou moeten doen

In deze volgorde, en de eerste drie vóór er één regel productcode is:

1. **De laadketen opzetten en de updatetest bouwen.** Verse instance, oude
   versie erop, nieuwe eroverheen, en aantonen dat de browser de nieuwe draait.
   Zie fase 11.
2. **De meetconditie van de klant opzetten.** Voor een Lovelace-kaart betekent
   dat: een echte Bubble Card-pop-up op telefoonbreedte, met een meetfunctie die
   per element rect én scrollWidth én getekende-tegen-beschikbare breedte
   vergelijkt. `scripts/` uit dit project is over te nemen.
3. **`registreer.js` en zijn bewaker overnemen.**
4. Dan pas SPEC schrijven, en daarna bouwen.

En bij elke ronde: mutatieproef in twee rondes, waarvan de tweede pas geschreven
wordt nadat de eerste groen is en die zich richt op de regels waarvan je zou
moeten toegeven dat je ze niet toetst.
