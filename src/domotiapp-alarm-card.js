/**
 * DomotiApp Alarm — de rooktestkaart.
 *
 * Deze kaart doet in fase 1 opzettelijk bijna niets: één `ha-card` met één
 * tekstregel en het versienummer. Het doel van de ronde is de **laadketen**
 * aantonen — dat de integratie haar eigen bundel serveert, dat de kaart langs
 * beide routes binnenkomt en dat het custom element zichtbaar is voor Home
 * Assistant. Wekkerlogica, opslag en editor komen in latere fases.
 *
 * `__CARD_VERSION__` wordt bij het bundelen vervangen door de `version` uit
 * custom_components/domotiapp_alarm/manifest.json (scripts/build.mjs). Er is
 * dus één bron voor het versienummer.
 */
import { LitElement, css, html } from "lit";

import { CARD_NAME, CARD_TYPE, DOCS_URL } from "./const.js";
import { registreerWanneerGereed } from "./registreer.js";

const VERSION = __CARD_VERSION__;

class DomotiappAlarmCard extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
  };

  /**
   * Lovelace roept dit aan met de kaartconfig. In deze fase valt er niets in
   * te stellen; we bewaren hem alleen zodat Lovelace tevreden is.
   */
  setConfig(config) {
    this._config = config ?? {};
  }

  /**
   * Zonder deze methode kan de kaartkiezer geen voorbeeldconfig maken en is de
   * kaart niet via de UI toe te voegen.
   */
  static getStubConfig() {
    return { type: `custom:${CARD_TYPE}` };
  }

  /**
   * `rows: "auto"` en geen getal. Een getal geeft de kaart in het
   * sections-grid een vaste hoogte en dan loopt hij over zijn vak heen zodra
   * hij hoger wordt. Zie CLAUDE.md, valkuil 12.
   */
  getGridOptions() {
    return { rows: "auto", columns: 12, min_columns: 6 };
  }

  static styles = css`
    .regel {
      padding: 16px;
      color: var(--primary-text-color);
      font-size: var(--ha-font-size-m, 14px);
    }
    .versie {
      color: var(--secondary-text-color);
    }
  `;

  render() {
    return html`
      <ha-card>
        <div class="regel">
          DomotiApp Alarm — rooktest
          <span class="versie">(v${VERSION})</span>
        </div>
      </ha-card>
    `;
  }
}

// Alles hieronder draait op modulescope en mag daarom nooit gooien.
//
// Registreren gebeurt niet meteen maar zodra HA's frontend klaar is. Zie
// src/registreer.js voor het waarom: onze import() en die van HA's app zijn
// siblings in index.html, en wie als eerste klaar is bepaalt in wélke
// custom-element-registry we landen. Registreren we te vroeg, dan zijn we
// achteraf onzichtbaar voor HA.
registreerWanneerGereed({
  leesRegistry: () => globalThis.customElements,
  definities: [[CARD_TYPE, DomotiappAlarmCard]],
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
