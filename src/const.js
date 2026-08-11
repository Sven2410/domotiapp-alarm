/**
 * Gedeelde constanten voor de kaart.
 *
 * Dit bestand importeert niets en mag niets gooien: het wordt op modulescope
 * uitgevoerd bij élke pagina van élke gebruiker.
 */

export const CARD_TYPE = "domotiapp-alarm-card";
export const EDITOR_TYPE = "domotiapp-alarm-card-editor";

/** Naam en beschrijving in de kaartkiezer. */
export const CARD_NAME = "DomotiApp Alarm";

export const DOCS_URL = "https://github.com/Sven2410/domotiapp-alarm";

/** Het domein van de integratie; elk commando begint ermee (SPEC 15). */
export const DOMAIN = "domotiapp_alarm";

/**
 * De commando's die de kaart in deze fase gebruikt. `sound/search` hoort bij de
 * editor en dus bij fase 4b; die staat hier bewust nog niet.
 */
export const CMD = Object.freeze({
  get: `${DOMAIN}/alarms/get`,
  setEnabled: `${DOMAIN}/alarms/set_enabled`,
  skipNext: `${DOMAIN}/alarms/skip_next`,
  delete: `${DOMAIN}/alarms/delete`,
  stop: `${DOMAIN}/alarms/stop`,
  clearMessage: `${DOMAIN}/alarms/clear_message`,
  subscribe: `${DOMAIN}/ringing/subscribe`,
});

/**
 * De accentkleur (SPEC 1.1). **Alleen voor accenten**: een actieve schakelaar en
 * de stopknop. Al het andere loopt via HA-themavariabelen, zodat de kaart
 * meebeweegt met het thema van de klant.
 */
export const ACCENT = "#026FA1";
