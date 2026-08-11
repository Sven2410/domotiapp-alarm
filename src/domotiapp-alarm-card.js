/**
 * DomotiApp Alarm — de kaart in rusttoestand en in de stoptoestand.
 *
 * Fase 4a bouwt SPEC 3, 4 en 16: de lijst met wekkers, de schakelaar, het
 * overloopmenu, de melding met "Begrepen", en de kaart die zichzelf in één
 * grote stopknop verandert zodra er een wekker afgaat. De **editor** (SPEC 5)
 * is fase 4b; de plusknop staat er wel en zegt dat.
 *
 * ## Wat hier bewust niet gebeurt
 *
 * - **De kaart rekent niet zelf uit wanneer de eerstvolgende wekker afgaat.**
 *   Die tekst komt kant-en-klaar uit `alarms/get` als `next_fire.text`
 *   (SPEC 3.3). Twee implementaties van dezelfde planning lopen uiteen.
 * - **De kaart sorteert niet.** `alarms/get` levert de lijst al gesorteerd
 *   volgens SPEC 3.4.
 * - **De kaart pollt niet.** Dat er een wekker afgaat komt via
 *   `ringing/subscribe` (SPEC 15.9), en bij het openen meteen uit het veld
 *   `ringing` van `alarms/get` — zodat een kaart die opengaat terwijl de wekker
 *   al loopt niet op een gebeurtenis hoeft te wachten die al voorbij is.
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
} from "./const.js";
import {
  foutTekst,
  personToestand,
  stubConfig,
  valideerConfig,
} from "./kaartconfig.js";
import { registreerWanneerGereed } from "./registreer.js";
import {
  TEKST_GEEN_WEKKERS,
  TEKST_GEEN_WEKKER_ACTIEF,
  TEKST_STOPPEN,
  meldingVan,
  stopToestand,
  subtitel,
} from "./weergave.js";

const VERSION = __CARD_VERSION__;

/** Tijdelijke melding achter de plusknop; de editor is fase 4b. */
const TEKST_EDITOR_KOMT_NOG =
  "De editor komt in fase 4b. Zet je wekkers voorlopig via de WebSocket-API.";

/**
 * Iconen als inline SVG in plaats van `ha-icon`. Zie de kop van dit bestand:
 * een `ha-icon` die nog niet geladen is, geeft een knop zonder oppervlak.
 * Paden komen uit Material Design Icons; `currentColor` houdt ze op de
 * themakleur van de knop waar ze in staan.
 */
const ICOON_PLUS =
  "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z";
const ICOON_MENU =
  "M12,16A2,2 0 0,1 14,18A2,2 0 0,1 12,20A2,2 0 0,1 10,18A2,2 0 0,1 12,16M12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12A2,2 0 0,1 12,10M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8A2,2 0 0,1 10,6A2,2 0 0,1 12,4Z";
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
    _menuVoor: { state: true },
    _bevestigVoor: { state: true },
    _bezig: { state: true },
    _tijdelijkeMelding: { state: true },
  };

  constructor() {
    super();
    this._toestand = null;
    this._fout = null;
    this._menuVoor = null;
    this._bevestigVoor = null;
    this._bezig = false;
    this._tijdelijkeMelding = null;
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
      this._menuVoor = null;
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
   * eenheden van ~50 px willen. Eén per wekkerrij plus één voor de voetregel;
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

  _overslaan(wekker) {
    this._menuVoor = null;
    this._roep({
      type: CMD.skipNext,
      person: this._person(),
      alarm_id: wekker.id,
      skip: !wekker.skip_next,
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
    }
    /* Geen overflow:hidden op de kaart: dat knipt het overloopmenu van de
       onderste rij af. De stopknop krijgt daarom zelf de hoekafronding van de
       kaart. */
    .sluiter {
      position: fixed;
      inset: 0;
      z-index: 2;
    }
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
    .tijd {
      font-size: 28px;
      line-height: 1.1;
      font-weight: 400;
      color: var(--primary-text-color);
      font-variant-numeric: tabular-nums;
      min-width: 82px;
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

    /* --- overloopmenu --- */
    .menuhouder {
      position: relative;
      flex: 0 0 auto;
    }
    .menu {
      position: absolute;
      right: 0;
      top: 40px;
      z-index: 3;
      min-width: 168px;
      background: var(--card-background-color, #fff);
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.28);
      overflow: hidden;
    }
    .menu button {
      display: block;
      width: 100%;
      text-align: left;
      padding: 12px 16px;
      border: none;
      background: none;
      cursor: pointer;
      color: var(--primary-text-color);
      font-size: var(--ha-font-size-m, 14px);
      font-family: inherit;
    }
    .menu button:hover {
      background: var(--divider-color);
    }

    /* --- melding en bevestiging op een rij --- */
    .onderrij {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 16px 12px 16px;
      border-bottom: 1px solid var(--divider-color);
      font-size: var(--ha-font-size-s, 12px);
    }
    .onderrij .boodschap {
      flex: 1;
      color: var(--secondary-text-color);
    }
    .onderrij.fout .boodschap,
    .onderrij.fout .icoon {
      color: var(--error-color);
    }
    button.tekstknop {
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

    /* --- voetregel --- */
    .voet {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-m, 14px);
    }
    .voet .volgende {
      flex: 1;
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

    const stop = this._stop();
    return html`<ha-card>
      ${this._menuVoor
        ? html`<div
            class="sluiter"
            @click=${() => {
              this._menuVoor = null;
            }}
          ></div>`
        : nothing}
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

  _lijst() {
    const wekkers = this._toestand.alarms ?? [];
    const nu = Date.now();
    return html`
      ${wekkers.length === 0
        ? html`<div class="mededeling">${TEKST_GEEN_WEKKERS}</div>`
        : wekkers.map((wekker) => this._rij(wekker, nu))}
      <div class="voet">
        <span class="volgende">
          ${this._toestand.next_fire?.text ?? TEKST_GEEN_WEKKER_ACTIEF}
        </span>
        <button
          class="icoonknop"
          title="Wekker toevoegen"
          aria-label="Wekker toevoegen"
          @click=${() => this._toon(TEKST_EDITOR_KOMT_NOG)}
        >
          ${svg(ICOON_PLUS)}
        </button>
      </div>
    `;
  }

  _rij(wekker, nu) {
    const melding = meldingVan(wekker);
    const aan = Boolean(wekker.enabled);
    return html`
      <div class="rij ${aan ? "" : "uit"}">
        <div class="tijd">${wekker.time}</div>
        <div class="tekst">
          <div class="naam">${wekker.name}</div>
          <div class="sub">${subtitel(wekker, nu)}</div>
        </div>
        <button
          class="schakelaar"
          role="switch"
          aria-checked=${aan ? "true" : "false"}
          aria-label="Wekker ${wekker.name} aan of uit"
          @click=${() => this._zetAan(wekker, !aan)}
        ></button>
        <div class="menuhouder">
          <button
            class="icoonknop"
            title="Meer"
            aria-label="Meer voor ${wekker.name}"
            @click=${() => {
              this._menuVoor = this._menuVoor === wekker.id ? null : wekker.id;
            }}
          >
            ${svg(ICOON_MENU)}
          </button>
          ${this._menuVoor === wekker.id
            ? html`<div class="menu">
                <button @click=${() => this._overslaan(wekker)}>
                  ${wekker.skip_next ? "Toch niet overslaan" : "Overslaan"}
                </button>
                <button
                  @click=${() => {
                    this._menuVoor = null;
                    this._bevestigVoor = wekker.id;
                  }}
                >
                  Verwijderen
                </button>
              </div>`
            : nothing}
        </div>
      </div>
      ${this._bevestigVoor === wekker.id
        ? html`<div class="onderrij">
            <span class="boodschap">
              Wekker "${wekker.name}" van ${wekker.time} verwijderen?
            </span>
            <button
              class="tekstknop"
              @click=${() => {
                this._bevestigVoor = null;
              }}
            >
              Annuleren
            </button>
            <button
              class="tekstknop gevaar"
              @click=${() => this._verwijder(wekker)}
            >
              Verwijderen
            </button>
          </div>`
        : nothing}
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
