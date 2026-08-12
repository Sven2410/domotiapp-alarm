/**
 * DomotiApp Alarm — de kaart in rusttoestand en in de stoptoestand.
 *
 * Fase 4a bouwde SPEC 3, 4 en 16: de lijst met wekkers, de schakelaar, het
 * overloopmenu, de melding met "Begrepen", en de kaart die zichzelf in één
 * grote stopknop verandert zodra er een wekker afgaat. Fase 4b hangt daar de
 * **editor** (SPEC 5) aan, achter de plusknop en achter een tik op een rij; die
 * staat in `src/editor.js`.
 *
 * ## Wat hier bewust niet gebeurt
 *
 * - **De kaart rekent niet zelf uit wanneer de eerstvolgende wekker afgaat.**
 *   Die tekst komt kant-en-klaar uit `alarms/get` als `next_fire.text`
 *   (SPEC 3.3). Twee implementaties van dezelfde planning lopen uiteen.
 * - **De kaart sorteert niet.** `alarms/get` levert de lijst al gesorteerd
 *   volgens SPEC 3.4.
 * - **De kaart pollt niet.** Dat er een wekker afgaat komt via
 *   `updates/subscribe` (SPEC 15.9), en bij het openen meteen uit het veld
 *   `ringing` van `alarms/get` — zodat een kaart die opengaat terwijl de wekker
 *   al loopt niet op een gebeurtenis hoeft te wachten die al voorbij is.
 *   Sinds fase 4b meldt datzelfde abonnement óók **opslagwijzigingen**, zodat
 *   een wekker die op de telefoon wordt gewijzigd op het wandtablet verschijnt
 *   zonder herlaadbeurt. Elk bericht betekent hetzelfde: haal de toestand
 *   opnieuw op.
 *
 * ## Waarom er nauwelijks HA-componenten in zitten
 *
 * De schakelaar, het overloopmenu en de iconen zijn eigen elementen. Een
 * `ha-switch` of `ha-button-menu` wordt door HA lui geladen: op een dashboard
 * waar deze kaart de enige kaart is, is er niets dat ze binnenhaalt, en een
 * ongedefinieerd custom element rendert als een leeg inline-element. Dan is de
 * schakelaar onzichtbaar zonder dat er een fout in de console staat. Wat er wél
 * gebruikt wordt is `ha-card` (de dashboardchrome laadt hem hoe dan ook) en
 * `ha-form` in de config-editor, die alleen bestaat binnen HA's eigen
 * kaarteditor-dialoog — precies waar `ha-form` gegarandeerd geladen is.
 *
 * Bijkomend voordeel, en het is de reden dat het ook meetbaar beter is:
 * CLAUDE.md valkuil 8 zegt dat een klik op een knop zonder opgehaald icoon mist.
 * Deze knoppen hebben hun oppervlak uit CSS en niet uit een asynchroon icoon.
 *
 * `__CARD_VERSION__` wordt bij het bundelen vervangen door de `version` uit
 * custom_components/domotiapp_alarm/manifest.json (scripts/build.mjs).
 */
import { LitElement, css, html, nothing, unsafeCSS } from "lit";

import {
  ACCENT,
  CARD_NAME,
  CARD_TYPE,
  CMD,
  DOCS_URL,
  EDITOR_TYPE,
  WEKKER_EDITOR_TYPE,
} from "./const.js";
import { bevestigingsTekst } from "./bevestiging.js";
import { DomotiappAlarmEditor } from "./editor.js";
import {
  foutTekst,
  personToestand,
  stubConfig,
  valideerConfig,
} from "./kaartconfig.js";
import { registreerWanneerGereed } from "./registreer.js";
import {
  TEKST_STOPPEN,
  kopTekst,
  meldingVan,
  stopToestand,
  subtitel,
} from "./weergave.js";

const VERSION = __CARD_VERSION__;


/**
 * Iconen als inline SVG in plaats van `ha-icon`. Zie de kop van dit bestand:
 * een `ha-icon` die nog niet geladen is, geeft een knop zonder oppervlak.
 * Paden komen uit Material Design Icons; `currentColor` houdt ze op de
 * themakleur van de knop waar ze in staan.
 */
const ICOON_PLUS =
  "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z";
// mdi:trash-can-outline. Eén handeling per rij sinds fase 7; het overloopmenu is
// vervallen omdat de overlay eronder elke klik opat (zie de moduledocstring).
const ICOON_PRULLENBAK =
  "M9,3V4H4V6H5V19A2,2 0 0,0 7,21H17A2,2 0 0,0 19,19V6H20V4H15V3H9M7,6H17V19H7V6M9,8V17H11V8H9M13,8V17H15V8H13Z";
const ICOON_INFO =
  "M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z";
const ICOON_FOUT =
  "M13,14H11V9H13M13,18H11V16H13M1,21H23L12,2L1,21Z";

const svg = (pad, klasse = "icoon") =>
  html`<svg class=${klasse} viewBox="0 0 24 24" aria-hidden="true">
    <path d=${pad} />
  </svg>`;

class DomotiappAlarmCard extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
    _toestand: { state: true },
    _fout: { state: true },
    _bevestigVoor: { state: true },
    _bezig: { state: true },
    _tijdelijkeMelding: { state: true },
    _editorVoor: { state: true },
    _entiteiten: { state: true },
  };

  constructor() {
    super();
    this._toestand = null;
    this._fout = null;
    this._bevestigVoor = null;
    this._bezig = false;
    this._tijdelijkeMelding = null;
    // `undefined` = dicht. `null` = open voor een nieuwe wekker. Een object =
    // open voor die bestaande wekker (SPEC 5).
    this._editorVoor = undefined;
    this._entiteiten = null;
    /** De persoon waarvoor het huidige abonnement loopt. */
    this._abonnementVoor = null;
    this._afmelden = null;
  }

  /**
   * Lovelace roept dit aan met de kaartconfig. Gooien mag hier, en alleen hier
   * (SPEC 16.3): een `person` in het verkeerde domein is een ongeldige config
   * en Lovelace hoort daar "Configuratiefout" van te maken.
   */
  setConfig(config) {
    const nieuw = valideerConfig(config);
    const anders = nieuw.person !== this._config?.person;
    this._config = nieuw;
    if (anders) {
      // Andere persoon: alles wat we van de vorige wisten is niet meer waar.
      this._toestand = null;
      this._fout = null;
      this._bevestigVoor = null;
      this._herstartAbonnement();
    }
  }

  /** De Lovelace-config-editor: één entiteitenkiezer (SPEC 16.2). */
  static getConfigElement() {
    return document.createElement(EDITOR_TYPE);
  }

  /** Zonder `person`, zodat de kaart via de kaartkiezer toe te voegen is. */
  static getStubConfig() {
    return stubConfig(CARD_TYPE);
  }

  /**
   * `rows: "auto"` en nooit een getal. Een getal geeft de kaart in het
   * sections-grid een vaste hoogte, en dan loopt hij over zijn vak en over de
   * "+"-knop eronder heen zodra hij hoger wordt. Deze kaart wórdt hoger: er
   * komen wekkers bij, en een melding voegt een regel toe. Zie CLAUDE.md
   * valkuil 12.
   */
  getGridOptions() {
    return { rows: "auto", columns: 12, min_columns: 6 };
  }

  /**
   * Voor masonry-weergaven, die geen `rows: "auto"` kennen en een getal in
   * eenheden van ~50 px willen. Eén per wekkerrij plus één voor de kopbalk;
   * de stoptoestand is één blok van ongeveer drie eenheden.
   */
  getCardSize() {
    if (this._stop()) {
      return 3;
    }
    const aantal = this._toestand?.alarms?.length ?? 0;
    return 1 + Math.max(aantal, 1);
  }

  connectedCallback() {
    super.connectedCallback();
    this._herstartAbonnement();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._stopAbonnement();
  }

  updated(gewijzigd) {
    // `hass` komt na `setConfig`, dus het abonnement kan pas hier beginnen.
    if (gewijzigd.has("hass") && this.hass) {
      this._startAbonnement();
    }
  }

  // --- de verbinding met de integratie ---------------------------------

  /**
   * Eén abonnement per kaart (CLAUDE.md valkuil 9). Twee abonnementen leveren
   * elke gebeurtenis dubbel op, en dat wordt makkelijk voor een
   * gedragsverandering aangezien.
   */
  async _startAbonnement() {
    const person = this._config?.person;
    if (!this.hass || !person || !this.isConnected) {
      return;
    }
    if (this._abonnementVoor === person) {
      return;
    }
    this._abonnementVoor = person;

    try {
      const afmelden = await this.hass.connection.subscribeMessage(
        (bericht) => this._opGebeurtenis(bericht),
        { type: CMD.subscribe, person },
      );
      if (this._abonnementVoor !== person) {
        // De config is veranderd terwijl we wachtten. Meteen weer opzeggen,
        // anders blijft er een abonnement op de vorige persoon hangen.
        afmelden();
        return;
      }
      this._afmelden = afmelden;
    } catch (fout) {
      console.warn(`${CARD_TYPE}: abonneren mislukt: ${fout?.message ?? fout}`);
    }

    await this._haalOp();
  }

  _stopAbonnement() {
    if (this._afmelden) {
      try {
        this._afmelden();
      } catch (fout) {
        console.warn(`${CARD_TYPE}: afmelden mislukt: ${fout?.message ?? fout}`);
      }
      this._afmelden = null;
    }
    this._abonnementVoor = null;
  }

  _herstartAbonnement() {
    this._stopAbonnement();
    this._startAbonnement();
  }

  /**
   * Een gebeurtenis uit `ringing/subscribe` (SPEC 15.9).
   *
   * De toestand wordt **eerst plaatselijk** bijgewerkt en daarna opgehaald. Het
   * plaatselijke deel is wat de kaart binnen één beeldopbouw een stopknop maakt;
   * de aanroep erna is de gezaghebbende toestand en brengt bij `failed` ook de
   * melding mee die de server net heeft opgeslagen.
   */
  _opGebeurtenis(bericht) {
    const id = bericht?.alarm_id;
    const soort = bericht?.event;
    if (typeof id === "string" && this._toestand) {
      const nu = new Set(this._toestand.ringing ?? []);
      if (soort === "started") {
        nu.add(id);
      } else {
        // `stopped` en `failed`: in beide gevallen gaat er niets (meer) af.
        nu.delete(id);
      }
      this._toestand = { ...this._toestand, ringing: [...nu] };
    }
    this._haalOp();
  }

  async _haalOp() {
    const person = this._config?.person;
    if (!this.hass || !person) {
      return;
    }
    try {
      const toestand = await this.hass.callWS({ type: CMD.get, person });
      if (this._config?.person !== person) {
        return; // de config veranderde tijdens de aanroep
      }
      this._toestand = toestand;
      this._fout = null;
    } catch (fout) {
      if (this._config?.person !== person) {
        return;
      }
      this._toestand = null;
      this._fout = foutTekst(fout?.code, fout?.message);
    }
  }

  /**
   * Elk commando geeft de volledige nieuwe toestand terug (SPEC 15.2), dus er
   * is nooit een tweede aanroep nodig om te weten wat er nu staat.
   */
  async _roep(payload) {
    if (!this.hass || this._bezig) {
      return;
    }
    this._bezig = true;
    try {
      const toestand = await this.hass.callWS(payload);
      if (toestand && typeof toestand === "object") {
        this._toestand = toestand;
        this._fout = null;
      }
    } catch (fout) {
      this._toon(fout?.message ?? "De opdracht is niet gelukt.");
    } finally {
      this._bezig = false;
    }
  }

  /**
   * Open de editor (SPEC 5). `wekker` is `null` voor een nieuwe.
   *
   * De gelabelde speakers en lampen worden hier opgehaald en niet in de editor:
   * dan is er één plek die weet wanneer die lijst verouderd is, en de editor
   * krijgt hem als gewone eigenschap binnen.
   */
  async _openEditor(wekker) {
    this._bevestigVoor = null;
    this._editorVoor = wekker;
    if (!this.hass) {
      return;
    }
    try {
      this._entiteiten = await this.hass.callWS({ type: CMD.entities });
    } catch (fout) {
      // Geen lijst is geen reden om de editor niet te openen: SPEC 7.4 zegt
      // uitdrukkelijk dat de gebruiker mag zien wáárom het niet gaat.
      this._entiteiten = null;
      console.warn(`${CARD_TYPE}: entiteitenlijst ophalen mislukt: ${fout?.message ?? fout}`);
    }
  }

  _sluitEditor() {
    this._editorVoor = undefined;
  }

  /** Een korte melding in de kaart zelf, zonder afhankelijkheid van HA's toast. */
  _toon(tekst) {
    this._tijdelijkeMelding = tekst;
    clearTimeout(this._meldingTimer);
    this._meldingTimer = setTimeout(() => {
      this._tijdelijkeMelding = null;
    }, 6000);
  }

  // --- handelingen -----------------------------------------------------

  _person() {
    return this._config?.person;
  }

  _zetAan(wekker, aan) {
    this._roep({
      type: CMD.setEnabled,
      person: this._person(),
      alarm_id: wekker.id,
      enabled: aan,
    });
  }

  _verwijder(wekker) {
    this._bevestigVoor = null;
    this._roep({
      type: CMD.delete,
      person: this._person(),
      alarm_id: wekker.id,
    });
  }

  /**
   * "Begrepen" wist de melding in de **opslag** (SPEC 11.7, 15.10). Lokaal
   * verbergen zou hem laten staan op het wandtablet en terugzetten na een
   * herlaadbeurt.
   */
  _begrepen(wekker) {
    this._roep({
      type: CMD.clearMessage,
      person: this._person(),
      alarm_id: wekker.id,
    });
  }

  /**
   * Stoppen is idempotent (SPEC 15.8), dus twee schermen tegelijk is geen
   * probleem. Gaan er twee wekkers van dezelfde persoon af, dan stopt deze ene
   * knop ze **allebei** (SPEC 4).
   */
  async _stopAlles(ids) {
    for (const id of ids) {
      // Eén voor één en niet parallel: elk antwoord is de volledige toestand,
      // en die van de laatste is de juiste.
      // eslint-disable-next-line no-await-in-loop
      await this._roep({ type: CMD.stop, person: this._person(), alarm_id: id });
    }
  }

  _stop() {
    if (!this._toestand) {
      return null;
    }
    return stopToestand(this._toestand.alarms, this._toestand.ringing);
  }

  // --- tekenen ---------------------------------------------------------

  static styles = css`
    /* unsafeCSS en niet de constante rechtstreeks: lit weigert een gewone
       string in een css-template en gooit dan — op modulescope, wat SPEC 19.4
       verbiedt. De waarde is onze eigen constante en komt nergens van buiten. */
    :host {
      --domotiapp-accent: ${unsafeCSS(ACCENT)};
      /* De kaart meet zich aan zijn eigen breedte en niet aan het venster: in een
         bubble pop-up is de kaart smal terwijl het venster breed is. Gemeten in
         fase 8 bij 244 px: de naam werd tot een enkele letter platgeknepen en de
         dagen stapelden verticaal.

         display:block is hier GEEN opmaakvoorkeur maar een voorwaarde. Gemeten:
         HA geeft de kaarthost display:inline, en op een inline element doet
         container-type niets — de host wordt dan geen query-container en de
         regels hieronder komen nooit aan bod.

         En de container heeft een NAAM. Zonder naam kiest de browser de
         dichtstbijzijnde container-voorouder, en dat kan er een van HA zelf zijn;
         dan hangt onze opmaak af van de afmeting van iets waar wij niet over
         gaan. */
      display: block;
      container: domotiapp-kaart / inline-size;
    }
    /* Geen overflow:hidden op de kaart: de stopknop houdt daarom zelf de
       hoekafronding van de kaart. Er staat sinds fase 7 niets meer boven de kaart
       te zweven — de volle-viewportlaag die het overloopmenu afsloot, is precies
       wat die knoppen onklikbaar maakte. */
    .mededeling {
      padding: 16px;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-m, 14px);
    }
    .mededeling.fout {
      color: var(--error-color);
    }

    /* --- de lijst --- */
    .rij {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    button.tikvlak {
      display: flex;
      align-items: center;
      gap: 12px;
      flex: 1;
      min-width: 0;
      border: none;
      background: none;
      padding: 0;
      margin: 0;
      cursor: pointer;
      text-align: left;
      font-family: inherit;
      color: inherit;
    }
    .tijd {
      font-size: 28px;
      line-height: 1.1;
      font-weight: 400;
      color: var(--primary-text-color);
      font-variant-numeric: tabular-nums;
      min-width: 82px;
      flex: 0 0 auto;
    }
    /* Onder de 300 px is er geen ruimte voor 28 px cijfers naast een naam, een
       schakelaar en een prullenbak. Kleinere cijfers zijn dan beter dan een naam
       van een letter. */
    @container domotiapp-kaart (max-width: 300px) {
      .tijd {
        font-size: 22px;
        min-width: 62px;
      }
      .rij {
        gap: 8px;
        padding: 10px 12px;
      }
    }
    /* De onderste regel van de kaart krijgt geen streep: er staat niets onder om
       van te scheiden. Sinds de kopbalk boven staat is dat de laatste wekkerrij, en
       niet meer de voetregel die er toen achter kwam. */
    .rij:last-child,
    .onderrij:last-child {
      border-bottom: none;
    }
    .rij.uit .tijd,
    .rij.uit .naam {
      color: var(--secondary-text-color);
    }
    .tekst {
      flex: 1;
      min-width: 0;
    }
    .naam {
      color: var(--primary-text-color);
      font-size: var(--ha-font-size-m, 14px);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .sub {
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-s, 12px);
    }

    /* --- de schakelaar; eigen knop, zie de kop van dit bestand --- */
    .schakelaar {
      flex: 0 0 auto;
      width: 44px;
      height: 24px;
      border-radius: 12px;
      border: none;
      padding: 0;
      cursor: pointer;
      position: relative;
      background: var(--disabled-text-color, #9e9e9e);
      transition: background 0.2s ease;
    }
    .schakelaar[aria-checked="true"] {
      background: var(--domotiapp-accent);
    }
    .schakelaar::after {
      content: "";
      position: absolute;
      top: 2px;
      left: 2px;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: var(--card-background-color, #fff);
      transition: transform 0.2s ease;
    }
    .schakelaar[aria-checked="true"]::after {
      transform: translateX(20px);
    }

    /* --- knoppen en iconen --- */
    button.icoonknop {
      flex: 0 0 auto;
      width: 40px;
      height: 40px;
      border: none;
      border-radius: 50%;
      background: none;
      cursor: pointer;
      color: var(--secondary-text-color);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0;
    }
    button.icoonknop:hover {
      background: var(--divider-color);
    }
    .icoon {
      width: 24px;
      height: 24px;
      fill: currentColor;
    }
    .icoon.klein {
      width: 18px;
      height: 18px;
      flex: 0 0 auto;
    }

    /* --- melding en bevestiging op een rij ---

       WIKKELT, sinds fase 9. Gemeten in een échte Bubble Card-pop-up op 390 px —
       telefoonbreedte, de conditie waarin de klant hem gebruikt — met een wekker
       die "Zaterdagochtendzwemtraining" heet: de knop "Verwijderen" stak 27 px
       buiten de kaart en 9 px buiten de pop-up, en dat laatste betekent dat een
       deel van hem niet meer aan te wijzen is. Met een korte naam gebeurt het
       onder een kaartbreedte van 276 px.

       Waarom het niet opviel: .boodschap had flex 1, dus min-width auto,
       en dan kan de tekst niet onder zijn langste woord krimpen. De rij liep over
       en duwde de knoppen naar rechts naar buiten. Fase 8 heeft dit voor .voet
       en de zoekrij opgelost maar deze rij niet meegenomen, omdat de meting de
       bevestiging nooit heeft geopend.

       Dat het uitgerekend de knop van een ONOMKEERBARE handeling is die wegvalt,
       is de reden dat dit geen schoonheidsfoutje is. */
    .onderrij {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      padding: 0 16px 12px 16px;
      border-bottom: 1px solid var(--divider-color);
      font-size: var(--ha-font-size-s, 12px);
    }
    .onderrij .boodschap {
      /* Een ondergrens in plaats van flex 1: onder de 8em gaan de knoppen naar
         de volgende regel in plaats van dat ze de rij uit worden geduwd. */
      flex: 1 1 8em;
      /* min-width 0 haalt de impliciete ondergrens van de flexitem weg en
         overflow-wrap breekt een naam die zelf breder is dan de kaart — een
         wekkernaam is invoer van de klant en heeft geen bovengrens. */
      min-width: 0;
      overflow-wrap: anywhere;
      color: var(--secondary-text-color);
    }
    .onderrij.fout .boodschap,
    .onderrij.fout .icoon {
      color: var(--error-color);
    }
    button.tekstknop {
      /* Hier stond in de eerste opzet van fase 9 een flex 0 0 auto, geleend van de
         voetregel in de editor (fase 8). De mutatieproef wees uit dat die regel
         hier NIETS doet: hem terugzetten op de standaard 0 1 auto veranderde bij
         390, 244 én 180 px geen enkele positie. De reden is de white-space
         hieronder — een knop die niet mag afbreken kan door flexbox niet onder
         zijn tekstbreedte geknepen worden, dus er valt niets te krimpen. Volgens
         valkuil 34, derde rij, gaat zo'n regel eruit in plaats van dat er een
         test bij verzonnen wordt. */
      border: 1px solid var(--divider-color);
      border-radius: 16px;
      background: none;
      color: var(--primary-text-color);
      padding: 6px 14px;
      cursor: pointer;
      font-size: var(--ha-font-size-s, 12px);
      font-family: inherit;
      white-space: nowrap;
    }
    button.tekstknop:hover {
      background: var(--divider-color);
    }
    button.tekstknop.gevaar {
      color: var(--error-color);
      border-color: var(--error-color);
    }

    /* De bevestigingsregel mag niet in het niets opgaan tussen de wekkers: hij
       vraagt iets onomkeerbaars. Zelfde vorm als een melding, met de tekst in de
       primaire kleur in plaats van de secundaire. */
    .onderrij.bevestiging .boodschap {
      color: var(--primary-text-color);
    }

    /* --- kopbalk (SPEC 3.1 en 3.2) ---
       Bovenaan sinds fase 6b: met tien wekkers stonden de eerstvolgende wektijd en
       de plusknop onder de vouw. Bij een lege lijst is dit de hele kaart en hoort er
       geen scheidingslijn onder — er staat niets om van te scheiden. */
    .kop {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-m, 14px);
      border-bottom: 1px solid var(--divider-color);
    }
    .kop.leeg {
      border-bottom: none;
    }
    .kop .volgende {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    /* --- de stoptoestand (SPEC 4) --- */
    button.stopknop {
      display: block;
      width: 100%;
      border: none;
      border-radius: var(--ha-card-border-radius, 12px);
      cursor: pointer;
      background: var(--domotiapp-accent);
      color: #fff;
      padding: 32px 16px;
      font-family: inherit;
      text-align: center;
    }
    .stopknop .stop-tijd {
      font-size: 44px;
      line-height: 1.1;
      font-variant-numeric: tabular-nums;
    }
    .stopknop .stop-naam {
      font-size: var(--ha-font-size-l, 16px);
      opacity: 0.9;
      margin-top: 4px;
    }
    .stopknop .stop-woord {
      margin-top: 20px;
      font-size: 24px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
  `;

  render() {
    if (!this._config) {
      return nothing;
    }

    const person = this._config.person;
    const bestaat = Boolean(person && this.hass?.states?.[person]);
    const toestand = personToestand(person, bestaat);
    if (toestand.soort !== "ok") {
      return this._mededeling(toestand.tekst, toestand.isFout);
    }
    if (this._fout) {
      return this._mededeling(this._fout, true);
    }
    if (!this._toestand) {
      return this._mededeling("Wekkers ophalen…", false);
    }

    // De editor vervangt de lijst zolang hij open is (SPEC 5: een eigen
    // formulier ín de kaart, geen pop-up). Een afgaande wekker wint: dan hoort
    // de kaart een stopknop te zijn en niet een formulier.
    const stop = this._stop();
    if (this._editorVoor !== undefined && !stop) {
      return html`<ha-card>
        <domotiapp-alarm-editor
          .hass=${this.hass}
          .person=${this._config.person}
          .wekker=${this._editorVoor}
          .entiteiten=${this._entiteiten}
          @editor-dicht=${() => this._sluitEditor()}
          @editor-opgeslagen=${(e) => {
            this._toestand = e.detail.toestand;
            this._sluitEditor();
          }}
        ></domotiapp-alarm-editor>
      </ha-card>`;
    }
    return html`<ha-card>
      ${stop ? this._stopknop(stop) : this._lijst()}
      ${this._tijdelijkeMelding
        ? html`<div class="onderrij">
            ${svg(ICOON_INFO, "icoon klein")}
            <span class="boodschap">${this._tijdelijkeMelding}</span>
          </div>`
        : nothing}
    </ha-card>`;
  }

  _mededeling(tekst, isFout) {
    return html`<ha-card>
      <div class="mededeling ${isFout ? "fout" : ""}">${tekst}</div>
    </ha-card>`;
  }

  /**
   * De hele kaart is één knop (SPEC 4). Geen pop-up: een dialoog vergt iemand
   * die hem wegklikt op het moment dat hij verschijnt, en dat werkt niet op een
   * wandtablet dat op een dashboard staat.
   */
  _stopknop(stop) {
    return html`<button
      class="stopknop"
      @click=${() => this._stopAlles(stop.ids)}
    >
      <div class="stop-tijd">${stop.tijd}</div>
      <div class="stop-naam">${stop.naam}</div>
      <div class="stop-woord">${TEKST_STOPPEN}</div>
    </button>`;
  }

  /**
   * De kopbalk plus de lijst (SPEC 3.1 en 3.2).
   *
   * **De kopbalk staat sinds fase 6b bovenaan.** Hij stond eronder, en met tien
   * wekkers moest je scrollen om te zien wanneer je wekker gaat en om er een toe te
   * voegen — precies de twee dingen waarvoor je de kaart opent.
   *
   * **Bij een lege lijst is de kopbalk de hele kaart.** SPEC 3.1 vraagt één regel
   * "Geen wekkers ingesteld" met een plusknop en uitdrukkelijk "niets anders"; met
   * de balk bovenaan ís dat de kopbalk. Het alternatief — de balk plus een aparte
   * lege regel eronder — zet twee ontkenningen onder elkaar ("Geen wekker actief"
   * boven "Geen wekkers ingesteld") en geeft de kaart twee plusknoppen of een
   * plusknop die verspringt zodra je je eerste wekker maakt.
   */
  _lijst() {
    const wekkers = this._toestand.alarms ?? [];
    const nu = Date.now();
    return html`
      <div class="kop ${wekkers.length === 0 ? "leeg" : ""}">
        <span class="volgende">${kopTekst(this._toestand)}</span>
        <button
          class="icoonknop"
          title="Wekker toevoegen"
          aria-label="Wekker toevoegen"
          @click=${() => this._openEditor(null)}
        >
          ${svg(ICOON_PLUS)}
        </button>
      </div>
      ${wekkers.map((wekker) => this._rij(wekker, nu))}
    `;
  }

  /**
   * De bevestiging bij het verwijderen (SPEC 3.2): een regel in de kaart.
   *
   * **Geen dialoog, en dat is gemeten** — zie de kop van `bevestiging.js`.
   * `ha-dialog` bestaat op een dashboard, maar zijn sloten zijn in 2026.8 van mwc
   * naar Web Awesome gegaan en de knoppen kwamen als 0 x 0 uit de verf.
   *
   * **Deze regel overlapt niets.** Hij duwt de rijen eronder omlaag in plaats van
   * eroverheen te gaan, en er ligt geen laag over de kaart die klikken opvangt.
   * Dat laatste is de hele bevinding van fase 7.
   *
   * **Annuleren doet niets** — geen aanroep, alleen `_bevestigVoor` terug op
   * `null`. Dat is de hele eis, en het is de reden dat er hier geen `_roep` staat
   * die je per ongeluk kunt aanzetten.
   */
  _bevestiging(wekker) {
    return html`<div class="onderrij bevestiging">
      <span class="boodschap">${bevestigingsTekst(wekker)}</span>
      <button
        class="tekstknop"
        @click=${() => {
          this._bevestigVoor = null;
        }}
      >
        Annuleren
      </button>
      <button class="tekstknop gevaar" @click=${() => this._verwijder(wekker)}>
        Verwijderen
      </button>
    </div>`;
  }

  _rij(wekker, nu) {
    const melding = meldingVan(wekker);
    const aan = Boolean(wekker.enabled);
    return html`
      <div class="rij ${aan ? "" : "uit"}">
        <button
          class="tikvlak"
          type="button"
          aria-label="Wekker ${wekker.name} bewerken"
          @click=${() => this._openEditor(wekker)}
        >
          <div class="tijd">${wekker.time}</div>
          <div class="tekst">
            <div class="naam">${wekker.name}</div>
            <div class="sub">${subtitel(wekker, nu)}</div>
          </div>
        </button>
        <button
          class="schakelaar"
          role="switch"
          aria-checked=${aan ? "true" : "false"}
          aria-label="Wekker ${wekker.name} aan of uit"
          @click=${() => this._zetAan(wekker, !aan)}
        ></button>
        <button
          class="icoonknop"
          title="Verwijderen"
          aria-label="Wekker ${wekker.name} verwijderen"
          @click=${() => {
            this._bevestigVoor = wekker.id;
          }}
        >
          ${svg(ICOON_PRULLENBAK)}
        </button>
      </div>
      ${this._bevestigVoor === wekker.id ? this._bevestiging(wekker) : nothing}
      ${melding
        ? html`<div class="onderrij ${melding.isFout ? "fout" : ""}">
            ${svg(melding.isFout ? ICOON_FOUT : ICOON_INFO, "icoon klein")}
            <span class="boodschap">${melding.tekst}</span>
            <button class="tekstknop" @click=${() => this._begrepen(wekker)}>
              Begrepen
            </button>
          </div>`
        : nothing}
    `;
  }
}

/**
 * De Lovelace-config-editor: één entiteitenkiezer, beperkt tot het
 * `person`-domein (SPEC 16.2).
 *
 * `ha-form` is HA's eigen component en lost de zoek- en toetsenbordafhandeling
 * al op. Hij is hier veilig te gebruiken: deze editor bestaat alleen binnen
 * HA's kaarteditor-dialoog, en die dialoog is zelf van `ha-form` gemaakt.
 */
class DomotiappAlarmCardEditor extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
  };

  setConfig(config) {
    this._config = { ...config };
  }

  static styles = css`
    .uitleg {
      padding: 0 0 12px 0;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-s, 12px);
    }
  `;

  static _SCHEMA = [
    {
      name: "person",
      required: true,
      selector: { entity: { filter: { domain: "person" } } },
    },
  ];

  _label = (schema) =>
    schema.name === "person" ? "Persoon" : schema.name;

  render() {
    if (!this._config || !this.hass) {
      return nothing;
    }
    return html`
      <div class="uitleg">
        Elke persoon heeft zijn eigen wekkerlijst. De kaart toont alleen de
        wekkers van de gekozen persoon.
      </div>
      <ha-form
        .hass=${this.hass}
        .data=${this._config}
        .schema=${DomotiappAlarmCardEditor._SCHEMA}
        .computeLabel=${this._label}
        @value-changed=${this._gewijzigd}
      ></ha-form>
    `;
  }

  /**
   * Lovelace bewaart wat hier uit komt. De hele config gaat mee en niet alleen
   * `person`, zodat `grid_options` en `visibility` behouden blijven (SPEC 16.1).
   */
  _gewijzigd(event) {
    event.stopPropagation();
    const config = { ...this._config, ...event.detail.value };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config },
        bubbles: true,
        composed: true,
      }),
    );
  }
}

// Alles hieronder draait op modulescope en mag daarom nooit gooien (SPEC 19.4).
//
// Registreren gebeurt niet meteen maar zodra HA's frontend klaar is. Zie
// src/registreer.js voor het waarom: onze import() en die van HA's app zijn
// siblings in index.html, en wie als eerste klaar is bepaalt in wélke
// custom-element-registry we landen. Registreren we te vroeg, dan zijn we
// achteraf onzichtbaar voor HA.
registreerWanneerGereed({
  leesRegistry: () => globalThis.customElements,
  definities: [
    [CARD_TYPE, DomotiappAlarmCard],
    [EDITOR_TYPE, DomotiappAlarmCardEditor],
    [WEKKER_EDITOR_TYPE, DomotiappAlarmEditor],
  ],
  waarschuw: (bericht) => console.warn(`${CARD_TYPE}: ${bericht}`),
});

// De kaartkiezer leest window.customCards; dat is een gewone array en heeft
// met de registry niets te maken. Die vullen we wél meteen, zodat de kaart in
// de kiezer staat ook als het registreren nog even duurt.
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === CARD_TYPE)) {
  window.customCards.push({
    type: CARD_TYPE,
    name: CARD_NAME,
    description: `Wekkerkaart van DomotiApp (v${VERSION}).`,
    preview: false,
    documentationURL: DOCS_URL,
  });
}
