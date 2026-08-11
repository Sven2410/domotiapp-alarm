/**
 * De editor: een wekker instellen (SPEC 5).
 *
 * **Geen Lovelace-config-editor.** Dit is een eigen formulier ín de kaart, dat de
 * opslag van de integratie bewerkt. De Lovelace-config-editor is iets anders en
 * staat in `domotiapp-alarm-card.js`; die kiest alleen de persoon (SPEC 16.2).
 *
 * ## Waarom hier gewone HTML-controls staan
 *
 * Zelfde reden als bij de kaart in fase 4a, en het is valkuil 44: Home Assistant
 * laadt zijn componenten lui, en een custom element dat niet gedefinieerd is
 * rendert als een leeg inline-element — zonder fout in de console. Op een
 * dashboard waar deze kaart de enige kaart is, is er niets dat `ha-time-input`,
 * `ha-textfield` of `ha-select` binnenhaalt.
 *
 * `<input type="time">` is bovendien precies wat SPEC 5.2 als terugval noemt, en
 * die terugval is hier de eerste keus: het is native op iOS, Android en desktop,
 * het bestaat altijd, en het is met echte toetsaanslagen én met kliks te
 * bedienen. Dat `ha-time-input` op ons dashboard inderdaad niet geladen is, is in
 * fase 4b gemeten en staat in `docs/fase-4b/RAPPORT.md`.
 *
 * ## De duurste les uit DomotiApp Scene
 *
 * **Nooit een terugvalwaarde tonen die niet opgeslagen zou worden** (SPEC 5.5,
 * 19.1). Daarom komt alles wat dit formulier toont uit één `_concept`, komen de
 * standaarden uit `editorlogica.nieuwConcept()` — dus uit SPEC 14.3 — en gaat
 * datzelfde concept via `naarAlarm()` de opslag in. Er wordt nergens een waarde
 * uit een levende entiteit gelezen om te tonen.
 */
import { LitElement, css, html, nothing, unsafeCSS } from "lit";

import { ACCENT, CMD } from "./const.js";
import {
  STANDAARD_HELDERHEID_PCT,
  conceptVan,
  eindigeDuurWaarschuwing,
  kleedGeluidUit,
  labelMelding,
  magOpslaan,
  naarAlarm,
  nieuwConcept,
  opslaanKan,
  wisselDag,
  zomertijdWaarschuwing,
} from "./editorlogica.js";

const DAGEN = [
  [1, "ma"],
  [2, "di"],
  [3, "wo"],
  [4, "do"],
  [5, "vr"],
  [6, "za"],
  [7, "zo"],
];

const SOORTEN = [
  ["", "Alles"],
  ["playlist", "Afspeellijsten"],
  ["radio", "Radio"],
  ["artist", "Artiesten"],
  ["album", "Albums"],
  ["track", "Nummers"],
  ["podcast", "Podcasts"],
];

const ICOON_INFO =
  "M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z";

export class DomotiappAlarmEditor extends LitElement {
  static properties = {
    hass: { attribute: false },
    person: { attribute: false },
    wekker: { attribute: false },
    entiteiten: { attribute: false },
    _concept: { state: true },
    _zoekterm: { state: true },
    _soort: { state: true },
    _treffers: { state: true },
    _zoekt: { state: true },
    _melding: { state: true },
    _speelt: { state: true },
    _bezig: { state: true },
  };

  constructor() {
    super();
    this._concept = nieuwConcept();
    this._zoekterm = "";
    this._soort = "";
    this._treffers = null;
    this._zoekt = false;
    this._melding = null;
    this._speelt = false;
    this._bezig = false;
    this._afmeldenVoorbeeld = null;
    this._opEscape = (event) => {
      if (event.key === "Escape") {
        this._annuleren();
      }
    };
  }

  connectedCallback() {
    super.connectedCallback();
    // Escape sluit de editor, en sluiten stopt het voorbeeld (SPEC 5.4).
    window.addEventListener("keydown", this._opEscape, true);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener("keydown", this._opEscape, true);
    // Dit is het vangnet onder alle manieren van sluiten die we hier níét
    // kennen: de kaart die uit de DOM gaat, een dashboard dat wegnavigeert.
    this._stopVoorbeeld();
  }

  willUpdate(gewijzigd) {
    if (gewijzigd.has("wekker")) {
      this._concept = this.wekker ? conceptVan(this.wekker) : nieuwConcept();
      this._treffers = null;
      this._zoekterm = "";
      this._melding = null;
    }
  }

  // --- concept bijwerken ------------------------------------------------

  _zet(velden) {
    this._concept = { ...this._concept, ...velden };
  }

  // --- het voorbeeld (SPEC 5.4) ----------------------------------------

  /**
   * Start het voorbeeld met de waarden zoals ze **nu** in de editor staan.
   *
   * Het abonnement ís het voorbeeld: afmelden stopt het geluid en zet het volume
   * terug (SPEC 15.11). Daarom hoeft er hier maar op één plek opgeruimd te
   * worden, en dekt dat ook de gevallen die deze code niet kan zien — een
   * tabblad dat verdwijnt, een verbinding die wegvalt.
   */
  async _startVoorbeeld() {
    if (this._speelt || !this.hass) {
      return;
    }
    if (!this._concept.speaker || !this._concept.sound) {
      this._melding = { tekst: "Kies eerst een speaker en een geluid.", fout: true };
      return;
    }
    this._melding = null;
    try {
      this._afmeldenVoorbeeld = await this.hass.connection.subscribeMessage(() => {}, {
        type: CMD.previewStart,
        speaker: this._concept.speaker,
        sound: kleedGeluidUit(this._concept.sound),
        volume_pct: this._concept.volume_pct,
      });
      this._speelt = true;
    } catch (fout) {
      // De noodrem zit hierachter (SPEC 11.1): dit is precies het moment waarop
      // de klant wil weten dat zijn speaker onbereikbaar is.
      this._melding = {
        tekst: fout?.message ?? "Het voorbeeld kon niet starten.",
        fout: true,
      };
    }
  }

  _stopVoorbeeld() {
    if (this._afmeldenVoorbeeld) {
      try {
        this._afmeldenVoorbeeld();
      } catch (fout) {
        console.warn(`domotiapp-alarm-editor: afmelden mislukt: ${fout?.message ?? fout}`);
      }
      this._afmeldenVoorbeeld = null;
    }
    this._speelt = false;
  }

  // --- zoeken (SPEC 8.1 en 15.6) ---------------------------------------

  async _zoek() {
    const query = (this._zoekterm || "").trim();
    if (!query || !this.hass) {
      return;
    }
    this._zoekt = true;
    this._melding = null;
    try {
      const payload = { type: CMD.search, query, limit: 20 };
      if (this._soort) {
        payload.media_types = [this._soort];
      }
      const antwoord = await this.hass.callWS(payload);
      this._treffers = antwoord.results ?? [];
    } catch (fout) {
      // De time-out van 10 s komt hier binnen met de tekst uit SPEC 15.6; die
      // wordt server-side gezet zodat hij niet van de versie van de kaart afhangt.
      this._treffers = [];
      this._melding = { tekst: fout?.message ?? "Zoeken is mislukt.", fout: true };
    } finally {
      this._zoekt = false;
    }
  }

  /** Valkuil 39: uitkleden vóór het opslaan, niet erna. */
  _kiesGeluid(treffer) {
    this._zet({ sound: kleedGeluidUit(treffer) });
    this._treffers = null;
  }

  // --- opslaan en annuleren (SPEC 5.5 en 15.2) -------------------------

  async _opslaan() {
    if (this._bezig || !this.hass) {
      return;
    }
    const oordeel = magOpslaan(this._concept);
    if (!oordeel.ok) {
      this._melding = {
        tekst: `Er ontbreekt nog ${oordeel.ontbreekt.join(", ")}.`,
        fout: true,
      };
      return;
    }
    this._bezig = true;
    try {
      const toestand = await this.hass.callWS({
        type: CMD.save,
        person: this.person,
        alarm: naarAlarm(this._concept),
      });
      // Opslaan is ook sluiten, en sluiten stopt het voorbeeld (SPEC 5.4).
      this._stopVoorbeeld();
      this.dispatchEvent(
        new CustomEvent("editor-opgeslagen", {
          detail: { toestand },
          bubbles: true,
          composed: true,
        }),
      );
    } catch (fout) {
      this._melding = { tekst: fout?.message ?? "Opslaan is mislukt.", fout: true };
    } finally {
      this._bezig = false;
    }
  }

  _annuleren() {
    this._stopVoorbeeld();
    this.dispatchEvent(new CustomEvent("editor-dicht", { bubbles: true, composed: true }));
  }

  // --- tekenen ----------------------------------------------------------

  static styles = css`
    :host {
      --domotiapp-accent: ${unsafeCSS(ACCENT)};
      display: block;
    }
    .blok {
      padding: 12px 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    .kop {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    .kop h2 {
      margin: 0;
      flex: 1;
      font-size: var(--ha-font-size-l, 16px);
      font-weight: 500;
      color: var(--primary-text-color);
    }
    label.veld {
      display: block;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-s, 12px);
      margin-bottom: 6px;
    }
    input[type="text"],
    input[type="time"],
    select {
      width: 100%;
      box-sizing: border-box;
      padding: 10px;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      font-family: inherit;
      font-size: var(--ha-font-size-m, 14px);
    }
    input[type="time"] {
      font-size: 24px;
      font-variant-numeric: tabular-nums;
    }
    input[type="range"] {
      width: 100%;
      accent-color: var(--domotiapp-accent);
    }
    .dagen {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .dagen button {
      flex: 1 1 0;
      min-width: 38px;
      padding: 8px 0;
      border: 1px solid var(--divider-color);
      border-radius: 18px;
      background: none;
      color: var(--secondary-text-color);
      cursor: pointer;
      font-family: inherit;
      font-size: var(--ha-font-size-s, 12px);
    }
    .dagen button[aria-pressed="true"] {
      background: var(--domotiapp-accent);
      border-color: var(--domotiapp-accent);
      color: #fff;
    }
    .rij {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .rij > :first-child {
      flex: 1;
    }
    button.knop {
      border: 1px solid var(--divider-color);
      border-radius: 18px;
      background: none;
      color: var(--primary-text-color);
      padding: 9px 16px;
      cursor: pointer;
      font-family: inherit;
      font-size: var(--ha-font-size-m, 14px);
      white-space: nowrap;
    }
    button.knop:hover:not(:disabled) {
      background: var(--divider-color);
    }
    button.knop:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }
    button.knop.primair {
      background: var(--domotiapp-accent);
      border-color: var(--domotiapp-accent);
      color: #fff;
    }
    .waarschuwing,
    .uitleg {
      display: flex;
      gap: 8px;
      align-items: flex-start;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-s, 12px);
      margin-top: 8px;
    }
    .waarschuwing.fout {
      color: var(--error-color);
    }
    .icoon {
      width: 18px;
      height: 18px;
      flex: 0 0 auto;
      fill: currentColor;
    }
    .treffers {
      margin-top: 8px;
      max-height: 260px;
      overflow-y: auto;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
    }
    .treffer {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      padding: 8px 10px;
      border: none;
      border-bottom: 1px solid var(--divider-color);
      background: none;
      color: var(--primary-text-color);
      cursor: pointer;
      text-align: left;
      font-family: inherit;
      font-size: var(--ha-font-size-s, 12px);
    }
    .treffer:last-child {
      border-bottom: none;
    }
    .treffer:hover {
      background: var(--divider-color);
    }
    .treffer img,
    .gekozen img {
      width: 40px;
      height: 40px;
      border-radius: 4px;
      object-fit: cover;
      flex: 0 0 auto;
      background: var(--divider-color);
    }
    .treffer .soort {
      color: var(--secondary-text-color);
      margin-left: auto;
      white-space: nowrap;
    }
    .gekozen {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      color: var(--primary-text-color);
      font-size: var(--ha-font-size-s, 12px);
    }
    .voet {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
      padding: 12px 16px;
    }
    .voet .voorbeeld {
      margin-right: auto;
    }
  `;

  _svg(pad) {
    return html`<svg class="icoon" viewBox="0 0 24 24" aria-hidden="true">
      <path d=${pad} />
    </svg>`;
  }

  render() {
    if (!this.hass) {
      return nothing;
    }
    const c = this._concept;
    const speakers = this.entiteiten?.speakers;
    const lampen = this.entiteiten?.lights;
    const speakerMelding = labelMelding(speakers, "speaker");
    const lampMelding = labelMelding(lampen, "lamp");
    const zomertijd = zomertijdWaarschuwing(c.time);
    const eindig = eindigeDuurWaarschuwing(c.sound);
    const kanOpslaan = opslaanKan(c, speakers);

    return html`
      <div class="kop">
        <h2>${c.id ? "Wekker bewerken" : "Nieuwe wekker"}</h2>
      </div>

      <div class="blok">
        <label class="veld" for="tijd">Tijd</label>
        <input
          id="tijd"
          type="time"
          .value=${c.time}
          required
          @input=${(e) => this._zet({ time: e.target.value })}
        />
        ${zomertijd
          ? html`<div class="waarschuwing">
              ${this._svg(ICOON_INFO)}<span>${zomertijd}</span>
            </div>`
          : nothing}
      </div>

      <div class="blok">
        <label class="veld">Herhaling</label>
        <div class="dagen">
          ${DAGEN.map(
            ([nummer, kort]) => html`<button
              type="button"
              aria-pressed=${c.days.includes(nummer) ? "true" : "false"}
              aria-label=${kort}
              @click=${() => this._zet({ days: wisselDag(c.days, nummer) })}
            >
              ${kort}
            </button>`,
          )}
        </div>
        <div class="uitleg">
          ${c.days.length === 0
            ? "Geen dag aangevinkt: deze wekker gaat één keer af, de eerstvolgende keer dat die tijd voorbijkomt."
            : "Deze wekker herhaalt zich op de aangevinkte dagen."}
        </div>
      </div>

      <div class="blok">
        <label class="veld" for="naam">Naam</label>
        <input
          id="naam"
          type="text"
          .value=${c.name}
          placeholder="Bijvoorbeeld: Werk"
          @input=${(e) => this._zet({ name: e.target.value })}
        />
      </div>

      <div class="blok">
        <label class="veld" for="speaker">Speaker</label>
        ${speakerMelding
          ? html`<div class="uitleg">${this._svg(ICOON_INFO)}<span>${speakerMelding}</span></div>`
          : html`<select
              id="speaker"
              .value=${c.speaker}
              @change=${(e) => this._zet({ speaker: e.target.value })}
            >
              <option value="">Kies een speaker…</option>
              ${(speakers?.entities ?? []).map(
                (s) => html`<option value=${s.entity_id} ?selected=${s.entity_id === c.speaker}>
                  ${s.name}
                </option>`,
              )}
            </select>`}
      </div>

      <div class="blok">
        <label class="veld" for="zoek">Geluid</label>
        ${c.sound
          ? html`<div class="gekozen">
              ${c.sound.image
                ? html`<img src=${c.sound.image} alt="" />`
                : nothing}
              <span>${c.sound.name || c.sound.uri}</span>
              <span class="soort" style="margin-left:auto">${c.sound.media_type ?? ""}</span>
            </div>`
          : nothing}
        <div class="rij" style="margin-top:8px">
          <input
            id="zoek"
            type="text"
            .value=${this._zoekterm}
            placeholder="Zoek in Music Assistant…"
            @input=${(e) => {
              this._zoekterm = e.target.value;
            }}
            @keydown=${(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                this._zoek();
              }
            }}
          />
          <select
            aria-label="Soort"
            @change=${(e) => {
              this._soort = e.target.value;
            }}
            style="width:auto"
          >
            ${SOORTEN.map(
              ([waarde, naam]) => html`<option value=${waarde}>${naam}</option>`,
            )}
          </select>
          <button class="knop" type="button" @click=${() => this._zoek()}>
            ${this._zoekt ? "Bezig…" : "Zoeken"}
          </button>
        </div>
        ${this._treffers
          ? html`<div class="treffers">
              ${this._treffers.length === 0
                ? html`<div class="treffer">Niets gevonden.</div>`
                : this._treffers.map(
                    (t) => html`<button
                      class="treffer"
                      type="button"
                      @click=${() => this._kiesGeluid(t)}
                    >
                      ${t.image ? html`<img src=${t.image} alt="" />` : nothing}
                      <span>${t.name}</span>
                      <span class="soort">${t.media_type ?? ""}</span>
                    </button>`,
                  )}
            </div>`
          : nothing}
        ${eindig
          ? html`<div class="waarschuwing">${this._svg(ICOON_INFO)}<span>${eindig}</span></div>`
          : nothing}
      </div>

      <div class="blok">
        <label class="veld" for="volume">Volume: ${c.volume_pct}%</label>
        <input
          id="volume"
          type="range"
          min="1"
          max="100"
          .value=${String(c.volume_pct)}
          @input=${(e) => this._zet({ volume_pct: Number(e.target.value) })}
        />
        <div class="uitleg">
          Het niveau waar de wekker in twintig seconden naartoe groeit.
        </div>
      </div>

      <div class="blok">
        <label class="veld" for="lamp">Wake-up light (optioneel)</label>
        ${lampMelding
          ? html`<div class="uitleg">${this._svg(ICOON_INFO)}<span>${lampMelding}</span></div>`
          : html`
              <select
                id="lamp"
                @change=${(e) =>
                  this._zet({
                    light: e.target.value
                      ? {
                          entity_id: e.target.value,
                          brightness_pct: c.light?.brightness_pct ?? STANDAARD_HELDERHEID_PCT,
                        }
                      : null,
                  })}
              >
                <option value="">Geen lamp</option>
                ${(lampen?.entities ?? []).map(
                  (l) => html`<option
                    value=${l.entity_id}
                    ?selected=${l.entity_id === c.light?.entity_id}
                  >
                    ${l.name}
                  </option>`,
                )}
              </select>
              ${c.light
                ? html`<label class="veld" style="margin-top:10px" for="helderheid">
                      Helderheid: ${c.light.brightness_pct}%
                    </label>
                    <input
                      id="helderheid"
                      type="range"
                      min="1"
                      max="100"
                      .value=${String(c.light.brightness_pct)}
                      @input=${(e) =>
                        this._zet({
                          light: { ...c.light, brightness_pct: Number(e.target.value) },
                        })}
                    />`
                : nothing}
            `}
      </div>

      ${this._melding
        ? html`<div class="blok">
            <div class="waarschuwing ${this._melding.fout ? "fout" : ""}">
              ${this._svg(ICOON_INFO)}<span>${this._melding.tekst}</span>
            </div>
          </div>`
        : nothing}

      <div class="voet">
        <button
          class="knop voorbeeld"
          type="button"
          @click=${() => (this._speelt ? this._stopVoorbeeld() : this._startVoorbeeld())}
        >
          ${this._speelt ? "Voorbeeld stoppen" : "Voorbeeld"}
        </button>
        <button class="knop" type="button" @click=${() => this._annuleren()}>Annuleren</button>
        <button
          class="knop primair"
          type="button"
          ?disabled=${!kanOpslaan || this._bezig}
          @click=${() => this._opslaan()}
        >
          Opslaan
        </button>
      </div>
    `;
  }
}
