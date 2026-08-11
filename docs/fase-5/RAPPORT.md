# Fase 5 — HACS-klaar maken

Geen functionele wijziging: geen regel in `src/` of in `custom_components/` is
aangeraakt. Wat er verandert is de README, de `.gitignore`, een compose-bestand
voor de installatietest en de projectstand.

Alles hieronder is geverifieerd tegen **de broncode van HACS en van Home
Assistant zelf**, en de controles zijn **gedraaid** en niet nagelezen. De
HACS-broncode komt uit `hacs/integration@main`; de HA-broncode uit het draaiende
image `2026.8`. Waar DomotiApp Scene fase 6 iets had uitgezocht, is dat
overgenomen en opnieuw getoetst in plaats van herhaald.

---

## TAAK A — `manifest.json` en `hacs.json`

Beide bestanden waren al goed. Dat is geen aanname maar de uitkomst van vier
controles.

### hassfest, op een schone uitcheck

Valkuil 15: op de werkmap loopt hassfest de `.venv/` in en keurt daar HA's eigen
kernintegraties af. Dus op een `git worktree`, zoals GitHub Actions het ook doet:

```
Validating manifest... done in 0.00s
…
Integrations: 1
Invalid integrations: 0
```

**Met een negatieve controle**, want "groen" zegt niets als de stap niet kijkt.
`iot_class` één keer op onzin gezet, in de schone uitcheck en niet in de repo:

```
* [ERROR] [MANIFEST] Invalid manifest: value must be one of ['assumed_state',
  'calculated', 'cloud_polling', 'cloud_push', 'local_polling', 'local_push']
  for dictionary value @ data['iot_class']. Got 'wekker'
Invalid integrations: 1
```

Daarmee staat vast dat hassfest `iot_class` werkelijk toetst, en dat
`calculated` in de toegestane lijst staat.

### HACS' eigen schema's, uit hun broncode geladen

`HACS_MANIFEST_JSON_SCHEMA` en `INTEGRATION_MANIFEST_JSON_SCHEMA` uit
`custom_components/hacs/utils/validate.py`, losgelaten op onze twee bestanden:

```
OK    hacs.json tegen HACS_MANIFEST_JSON_SCHEMA
OK    manifest.json tegen INTEGRATION_MANIFEST_JSON_SCHEMA

hacs.json — PREVENT_EXTRA:
   Optional  content_in_root, country, filename, hacs, hide_default_branch,
             homeassistant, persistent_directory, render_readme, zip_release
   Required  name

manifest.json — ALLOW_EXTRA:
   Required  codeowners, documentation, domain, issue_tracker, name, version

Negatieve controle — een onbekende sleutel in hacs.json:
   correct geweigerd: extra keys not allowed @ data['verzonnen_sleutel']
```

Ook hier een negatieve controle, en die bevestigt wat fase 6 van Scene
vaststelde: het schema staat op **`PREVENT_EXTRA`**, dus een sleutel die er niet
in staat is geen waarschuwing maar een fout.

### Wat er in staat, en waarom

`manifest.json` — de zes verplichte sleutels staan erin. Verder:

| Sleutel | Waarde | |
|---|---|---|
| `iot_class` | `calculated` | de integratie communiceert met geen enkel apparaat en levert geen state; `backup` is HA's eigen voorbeeld van precies dit soort integratie |
| `integration_type` | `service` | geen apparaat, geen hub, geen entiteit |
| `dependencies` | `http`, `frontend`, `lovelace` | alle drie worden echt gebruikt: statische route, `add_extra_js_url`, en de Lovelace-resource |
| `version` | `0.1.0` | bij hassfest optioneel voor een custom integration, **bij HACS verplicht** — en hij moet omhoog vóór de eerste release |

`hacs.json` — vier sleutels, alle vier geldig:

```json
{
  "name": "DomotiApp Alarm",
  "render_readme": true,
  "homeassistant": "2026.8",
  "hide_default_branch": true
}
```

`homeassistant` is geen sier. HACS dwingt het af in
`_ensure_download_capabilities`:

```python
if (target_manifest.homeassistant is not None
        and self.hacs.core.ha_version < target_manifest.homeassistant):
    raise HacsException(f"This version requires Home Assistant … or newer.")
```

Een klant op een oudere HA kan dus niet downloaden, in plaats van een kapotte
kaart te krijgen.

**Geen `filename`** — die sleutel geldt alleen voor de single-item-types (plugin,
theme, template, python script). Voor een integratie pakt HACS de hele map
`custom_components/<domein>/`.

**Geen `persistent_directory`** — die bewaart één submap van de integratiemap
over een update heen. Onze opslag staat in `.storage/domotiapp_alarm.alarms`,
buiten de integratiemap, en heeft die bescherming niet nodig.

**`hide_default_branch: true`** staat er wél, anders dan bij Scene. Daarmee kan
een klant alleen een release downloaden en niet per ongeluk `main`.

---

## TAAK B — `README.md`

Herschreven. Hij beschreef nog de scaffold uit fase 0, inclusief de regel *"In
ontwikkeling — nog niet bruikbaar als wekker."*

De volgorde is die van de opdracht: eerst de klant, dan de ontwikkelaar. Met drie
schermafbeeldingen uit `docs/`, gekopieerd naar `docs/afbeeldingen/` zodat de
README niet naar een fasemap wijst — fasemappen zijn historie en die wil je niet
als productdocumentatie hergebruiken.

| Nieuw bestand | Bron |
|---|---|
| `docs/afbeeldingen/kaart.jpg` | `docs/fase-4a/beeld/03-drie-wekkers.jpg` |
| `docs/afbeeldingen/stopknop.jpg` | `docs/fase-4a/beeld/07-stoptoestand.jpg` |
| `docs/afbeeldingen/editor.jpg` | `docs/fase-4b/beeld/04-editor-volledig-ingevuld.jpg` |

De sectie *Goed om te weten* bevat de vijf punten uit de opdracht. Het
belangrijkste staat er met uitleg en niet als waarschuwing zonder reden:

> **Haal de Lovelace-resource van DomotiApp Alarm niet weg.** […] het is de
> tweede van twee laadroutes. De eerste route zet een import in Home Assistants
> `index.html`, maar een browser die Home Assistant al gebruikte vóórdat je deze
> integratie installeerde, kan een oude `index.html` uit zijn cache vasthouden —
> zonder die import. Dan toont elk dashboard "Configuratiefout".

Dat punt is bij DomotiApp Scene pas in de allerlaatste ronde gevonden en het
raakt een klant direct; daarom staat het hier met de reden erbij, zodat niemand
het voor een restant aanziet.

---

## TAAK C — `LICENSE`

**Al aanwezig en al goed:** MIT, `Copyright (c) 2026 Sven2410`, 21 regels met de
drie standaardpassages. Niets aan gedaan.

Dat het MIT is, is precies wat HACS' licentiecheck wil:

```python
POPULAR_OSI_APPROVED_LICENSES = frozenset({
    "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CDDL-1.0", "EPL-2.0",
    "GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", "MIT", "MPL-2.0"})
```

Let op de vorm van die check: hij leest **GitHub's** `spdx_id` van de repo, niet
het bestand. Een MIT-tekst die GitHub niet herkent levert `NOASSERTION` op en
faalt alsnog. De standaardtekst die er staat wordt wél herkend.

---

## TAAK D — Wat er nog mist

Eerst het onderscheid dat alles bepaalt, opnieuw nagelopen in de HACS-broncode
en **nog steeds waar**:

```python
async def async_run_repository_checks(self, repository) -> None:
    """Run all validators for a repository."""
    if not self.hacs.system.action:
        return
```

Alles in `custom_components/hacs/validate/` — licentie, brands, beschrijving,
topics, images, issues — staat op `ActionValidationBase` en draait dus
**uitsluitend in de HACS-action**, dat wil zeggen bij opname in de
standaardwinkel. Voor een klant die de repo als **custom repository** toevoegt,
draait daarvan niets.

Wat er bij zo'n installatie wél geldt, uit
`repositories/integration.py::validate_repository`:

1. er moet één map onder `custom_components/` staan — anders
   *"Repository structure … is not compliant"*;
2. daarin een `manifest.json` met een `domain` — een `KeyError` daarop is een
   validatiefout;
3. `hacs.json` moet door het schema komen;
4. `homeassistant` in `hacs.json` wordt bij het downloaden afgedwongen.

Alle vier zijn in orde. **De repo is nu installeerbaar bij een klant** — en dat
is deze ronde niet beredeneerd maar gedaan; zie taak E.

### Bevindingen

| | Nodig voor installatie? | Stand |
|---|---|---|
| LICENSE (MIT) | nee (action-only) | **staat er al** |
| `brand/icon.png` | nee (action-only) | **staat er al** — door de eigenaar toegevoegd |
| `hacs.json`, `manifest.json` | **ja** | in orde, met twee validators bewezen |
| Repositorybeschrijving op GitHub | nee (action-only) | **eigenaar**, één veld |
| GitHub-topics | nee (action-only) | **eigenaar**, één veld |
| Een release | nee — HACS valt terug op de default branch, maar die is met `hide_default_branch` verborgen, dus in de praktijk **ja** | **eigenaar** tagt zelf |
| CHANGELOG | nee | niet toegevoegd; HACS toont de release-notes van GitHub |
| `.github/` | nee | bevat `ci.yml` met vier jobs, waaronder hassfest |
| HACS-action in CI | nee | **niet toegevoegd**, met reden — zie hieronder |

Er staat **geen rommel** in wat HACS zou meeleveren: 23 getrackte bestanden onder
`custom_components/domotiapp_alarm/`, geen `.gitkeep`, geen `__pycache__`, geen
`.pyc`.

**De HACS-action is bewust niet toegevoegd.** Die zou vandaag rood staan op
beschrijving en topics — twee velden die alleen de eigenaar kan zetten. Zodra die
er zijn, is dit de job:

```yaml
hacs:
  name: HACS-validatie
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v5
    - uses: hacs/action@main
      with:
        category: integration
```

### Het icoon werkt, en dat is gemeten

Bij Scene was dit het openstaande punt (`"has_branding": false` → een grijs
"icon not available"-vakje). Hier meldt HA's eigen loader op de verse instance:

```
"has_branding": true
```

en serveert hij ons bestand **byte-identiek**:

| | |
|---|---|
| op schijf | sha256 `018491b8…2cd220`, 1.046.692 bytes |
| door HA uitgeserveerd | dezelfde sha256, dezelfde bytes, `content-type: image/png` |

De frontend vroeg om `dark_icon.png` en kreeg onze `icon.png` — dat is HA's eigen
terugvalketen binnen de `brand`-map (`ALLOWED_IMAGES` in
`components/brands/const.py`). Eén `icon.png` is dus genoeg.

---

## TAAK E — De installatietest op een verse instance

Een tweede, lege Home Assistant op **poort 8130**, met een eigen compose-naam,
eigen containernaam en een eigen configmap buiten de repo
(`docker-compose.installatietest.yml`).

De integratie is er **als kopie** in gezet, niet als bind mount — dat is wat HACS
doet, en het is het verschil tussen "werkt bij ons" en "werkt bij de klant". Wat
er neergezet is, is precies wat HACS uit de zipball pakt: de 23 getrackte
bestanden onder `custom_components/domotiapp_alarm/`, meer niet.

**De bundel kwam byte-identiek aan**, met `cmp` én met een hash:

```
4e0febfb156a9ba05fa4b75acde7bd3624f6c3f76e5967d84ec9e5fd08671ddc  repo
4e0febfb156a9ba05fa4b75acde7bd3624f6c3f76e5967d84ec9e5fd08671ddc  verse instance
cmp: identiek — 52.129 bytes
```

### Vóór de onboarding

- **HA vindt de integratie**: `We found a custom integration domotiapp_alarm …`
- **Nul fouten**: `docker logs | grep -ciE "ERROR|Traceback"` → `0`
- **HA's loader leest het manifest en importeert onze Python**, op een kaal
  2026.8-image:

  ```
  custom integrations die HA in /config vindt: ['domotiapp_alarm']
  { "domain": "domotiapp_alarm", "version": "0.1.0", "config_flow": true,
    "integration_type": "service", "iot_class": "calculated",
    "dependencies": ["http", "frontend", "lovelace"],
    "is_built_in": false, "has_translations": true, "has_branding": true }
  component geimporteerd  : custom_components.domotiapp_alarm
  config_flow geimporteerd: custom_components.domotiapp_alarm.config_flow
  async_setup_entry : True    async_unload_entry: True
  ```

- **De statische route komt uit de config entry en niet uit iets handmatigs.**
  Dezelfde URL op beide instances:

  ```
  8130 (vers, geen entry): 404
  8129 (dev,  mét entry) : 200
  ```

De onboarding is door de **eigenaar** gedaan; daar is gestopt en gemeld, conform
de opdracht.

### Ná de onboarding — de vijf punten

**1. De integratie in de lijst, mét icoon** (`01-integratie-met-icoon.jpg`).
Zoeken op "DomotiApp" in *Integratie toevoegen* geeft één treffer, met het
merkicoon links en het oranje custom-integration-blokje rechts. Het icoon is niet
alleen zichtbaar maar ook aantoonbaar het onze — zie de hashvergelijking bij taak
D.

**2. Toevoegen, en de Lovelace-resource verschijnt vanzelf.** De beginstand is
eerst vastgelegd, want anders bewijst "de resource staat er" niets:

| | vóór het toevoegen | ná het toevoegen |
|---|---|---|
| `lovelace/resources` | `[]` | één `module` naar `/domotiapp_alarm/domotiapp-alarm-card.js?v=…` |
| config entry | — | `state: loaded`, `source: user` |
| statische route | 404 | **200** |

De config flow toont één bevestigingsscherm met Nederlandse tekst
(`02-config-flow.jpg`). Niemand heeft die resource met de hand toegevoegd.

**3. De kaart in de kaartkiezer** (`03-kaartkiezer.jpg`). Zoeken op "DomotiApp"
in *Per kaart* geeft **DomotiApp Alarm — Wekkerkaart van DomotiApp (v0.1.0)**. De
kaart is toegevoegd, de persoon `dev` gekozen, en de voorbeeldweergave in de
kaarteditor toonde meteen "Geen wekkers ingesteld / Geen wekker actief".

**4. De reproductie uit fase 1 taak H.** Dit is het punt dat er het meest toe
doet, en het begon met een toevalstreffer: een gewone `fetch('/')` in de browser
gaf een index **zonder** onze import (6.006 bytes), terwijl `curl` naar dezelfde
server er één **mét** import gaf. De service worker zat ertussen — en die fetch
repareerde de cache meteen zelf, precies zoals valkuil 4 beschrijft. Bij de
volgende meting stond er 6.072 bytes mét import in de cache.

Daarom is de conditie daarna **opzettelijk** gemaakt, met `cache.put()` en niet
met een fetch:

| stap | meting |
|---|---|
| index in de cache gezet zonder onze import | 6.072 → **6.006 bytes**, `domotiapp_alarm` komt er niet meer in voor |
| binnengekomen via de **wortel-URL** `http://localhost:8130/` | beland op `/home/overview` |
| de geladen pagina | `geladen_index_bevat_onze_import: false` |
| de kaart op dat moment | `customElements.get('domotiapp-alarm-card')` → **false** |
| daarna doorgeklikt naar het Lovelace-dashboard | **de kaart rendert** |

Op het ingebouwde paneel is de kaart er dus níét — daar worden
Lovelace-resources niet geladen en de index miste de import. Op het
Lovelace-dashboard is hij er wél, en de resource-timing wijst aan waar hij
vandaan kwam:

```
bundel opgehaald: /domotiapp_alarm/domotiapp-alarm-card.js?v=…  initiator: script
lovelace resources: /domotiapp_alarm/domotiapp-alarm-card.js
```

Beide custom elements geregistreerd, kaarttekst "Geen wekkers ingesteld / Geen
wekker actief" (`04-kaart-via-de-resource.jpg`). **Dat is precies waarvoor de
tweede laadroute bestaat**, aangetoond op een instance die de integratie nooit
eerder had.

**5. Een wekker die afgaat — NIET gedaan.** Zie hieronder.

### Opgeruimd

```
docker compose -f docker-compose.installatietest.yml down -v
rm -rf .ha-install-config
```

```
containers: ma-alarm (Up), ha-alarm (Up)   — de installatietest is weg
poort 8130: geen antwoord
configmap : weg
```

Alleen de dev-instance op 8129 en de MA-server op 8095 draaien nog, zoals ze
draaiden.

---

## TAAK F — De projectstand

`CLAUDE.md` bijgewerkt: fase 4b en 4c op *gemerged*, fase 5 erbij.

De **releaseprocedure stond er al** en klopte al — inclusief de drie dingen die
niet mogen wegvallen (`npm run build` tussen versienummer en commit, manifest én
bundel in dezelfde commit, en dat een tag alleen niet genoeg is omdat HACS de
laatste *release* leest). Toegevoegd is één tabel: **wat er vóór de eerste
release klaar moet zijn**, met per punt of het de installatie blokkeert.

---

## Wat de eigenaar zelf moet doen vóór de eerste release

In volgorde van belang.

1. **Zet `version` in `custom_components/domotiapp_alarm/manifest.json` op het
   releasenummer.** Hij staat op `0.1.0`. HACS vergelijkt de tag met deze waarde.
   Vergeet daarna `npm run build` niet — de versie zit in de bundel, en CI valt
   erover als je het overslaat.
2. **Maak de tag en de release**, zonder `v`-prefix. Alleen een tag is niet
   genoeg: HACS leest de laatste *release*. En met `hide_default_branch: true` is
   er tot die tijd niets te downloaden.
3. **Zet een beschrijving en topics op de GitHub-repo.** Twee velden, allebei
   leeg. Ze blokkeren de installatie niet, maar ze zijn wél nodig als je ooit in
   de HACS-standaardwinkel wilt.
4. **Maak de installatietest af met punt 5**: een wekker die werkelijk afgaat op
   een verse instance. Wat daarvoor nodig is, staat hieronder bij *Wat niet
   lukte*.
5. **Overweeg de HACS-action** in CI zodra 3 klaar is; het snippet staat bij
   taak D.

---

## Samenvatting

De repo is installeerbaar bij een klant via HACS als custom repository, en dat is
deze ronde niet beredeneerd maar **gedaan**: op een verse Home Assistant op 8130,
met de integratie er als kopie in zoals HACS hem levert, is de hele keten
doorlopen — gevonden, gevalideerd, geïmporteerd, toegevoegd via de UI, de
resource verscheen vanzelf, de kaart stond in de kaartkiezer en rendert.

`manifest.json` en `hacs.json` waren al goed en zijn met twee validators bewezen,
allebei mét negatieve controle zodat "groen" ook iets betekent. De README is voor
de klant herschreven, met als belangrijkste toevoeging de reden dat de
Lovelace-resource niet weg mag.

Het sluitstuk is punt 4: met een index zonder onze import in de
service-workercache is de kaart op het ingebouwde paneel **weg** en op het
Lovelace-dashboard **er** — de tweede laadroute doet precies waarvoor hij in fase
1 is gebouwd, aangetoond op een instance zonder geschiedenis.

## Wat niet lukte

- **Punt 5 van de installatietest: een wekker die echt afgaat.** Dat vergt Music
  Assistant op de verse instance, en daar zitten **twee** blokkades, allebei
  gemeten en niet vermoed:

  1. De MA-config-flow komt uit op een externe stap naar
     `192.168.1.212:8095/login` — **MA's eigen inlogpagina**. Daar hoort het
     wachtwoord van de eigenaar in, en dat typ ik niet (CLAUDE.md, MA-sectie).
  2. Ook mét een login zou de flow niet afkomen. De `return_url` van die stap
     wijst naar `my.home-assistant.io/redirect/oauth`, want een verse instance
     heeft het volledige `default_config` inclusief `my` — exact wat valkuil 32
     voorspelt. De dev-instance omzeilt dat door `default_config` uiteen te
     leggen mínus `my`, en dat is een wijziging aan een *verse* instance die ik
     niet ongevraagd ga maken.

  De flow is netjes afgebroken; er is niets half aangemaakt. Wil de eigenaar dit
  afmaken, dan is de route: `configuration.yaml` op de testinstance vervangen door
  `default_config` uiteengelegd minus `my` (zoals in `.ha-dev-config/`),
  herstarten, MA toevoegen met `http://192.168.1.212:8095` en zelf inloggen,
  daarna de twee labels plakken en een wekker op twee minuten zetten.

- **De onboarding is niet door mij gedaan**, zoals afgesproken. Punt 1 tot en met
  4 zijn daarna wél volledig doorlopen.

- **`render_readme` is nog steeds niet definitief opgelost.** Hij staat in HACS'
  schema en dus is hij geldig, maar in de broncode is er geen verbruiker van te
  vinden. Laten staan is veilig; weghalen zou pas mogen als je zeker weet dat er
  nergens iets mee gebeurt, en dat weet ik niet.

## Aannames

1. **`docs/afbeeldingen/` is de goede plek voor README-plaatjes**, en niet een
   verwijzing naar een fasemap. Fasemappen zijn historie; die wil je niet als
   productdocumentatie hergebruiken.
2. **`docker-compose.installatietest.yml` hoort in de repo**, naast de twee
   compose-bestanden die er al staan. Daarmee kan de eigenaar de test herhalen en
   punt 5 afmaken. Hij levert niets mee aan een klant — HACS pakt alleen
   `custom_components/domotiapp_alarm/`.
3. **De safe-mode-regel in de README is breder dan SPEC 20.1.** Die sectie noemt
   safe mode niet; het is gedrag van Home Assistant (geen custom integrations in
   safe mode) en het gevolg voor dit product is scherper dan bij DomotiApp Scene:
   niet alleen de kaart ontbreekt, er gáát geen wekker af. Dat staat er zo.
4. **De README beschrijft de custom-repository-route**, want de repo staat niet in
   de HACS-standaardwinkel en daar is deze ronde geen aanvraag voor gedaan.

## `git status --porcelain`

Vlak vóór de commit:

```
 M .gitignore
 M CLAUDE.md
 M README.md
?? docker-compose.installatietest.yml
?? docs/afbeeldingen/
?? docs/fase-5/
```

Ná de commit is hij leeg.
