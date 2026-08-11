/**
 * Gedeelde constanten voor de kaart.
 *
 * Dit bestand importeert niets en mag niets gooien: het wordt op modulescope
 * uitgevoerd bij élke pagina van élke gebruiker.
 */

export const CARD_TYPE = "domotiapp-alarm-card";
/** De Lovelace-config-editor: kiest de persoon (SPEC 16.2). */
export const EDITOR_TYPE = "domotiapp-alarm-card-editor";
/** De wekker-editor in de kaart zelf (SPEC 5). Iets anders dan de vorige. */
export const WEKKER_EDITOR_TYPE = "domotiapp-alarm-editor";

/** Naam en beschrijving in de kaartkiezer. */
export const CARD_NAME = "DomotiApp Alarm";

export const DOCS_URL = "https://github.com/Sven2410/domotiapp-alarm";

/** Het domein van de integratie; elk commando begint ermee (SPEC 15). */
export const DOMAIN = "domotiapp_alarm";

/** De tien commando's uit SPEC 15. `skipNext` is in fase 7 vervallen. */
export const CMD = Object.freeze({
  get: `${DOMAIN}/alarms/get`,
  save: `${DOMAIN}/alarms/save`,
  setEnabled: `${DOMAIN}/alarms/set_enabled`,
  delete: `${DOMAIN}/alarms/delete`,
  stop: `${DOMAIN}/alarms/stop`,
  clearMessage: `${DOMAIN}/alarms/clear_message`,
  search: `${DOMAIN}/sound/search`,
  entities: `${DOMAIN}/entities/list`,
  previewStart: `${DOMAIN}/preview/start`,
  // Fase 4b: hernoemd van `ringing/subscribe`. Het abonnement gaat over alles wat
  // een open kaart actueel houdt, niet alleen over afgaan (SPEC 15.9).
  subscribe: `${DOMAIN}/updates/subscribe`,
});

/**
 * De accentkleur (SPEC 1.1). **Alleen voor accenten**: een actieve schakelaar en
 * de stopknop. Al het andere loopt via HA-themavariabelen, zodat de kaart
 * meebeweegt met het thema van de klant.
 */
export const ACCENT = "#026FA1";
