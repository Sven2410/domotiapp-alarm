/**
 * Het registreren van de custom elements, bestand tegen de registry-race.
 *
 * ## Het probleem
 *
 * Home Assistant 2026.8 draait `@webcomponents/scoped-custom-element-registry`.
 * Die polyfill vervangt `window.customElements` door een eigen object en
 * patcht `CustomElementRegistry.prototype`. De gepatchte `get` leest
 * **uitsluitend** de interne Map van de polyfill, zonder fallback naar de
 * native registry.
 *
 * Onze kaart wordt geladen met een `import()` in `index.html`, náást de
 * `import()` van HA's eigen app. Welke van die twee als eerste klaar is, is een
 * race. Winnen wij, dan roepen we de **native** `customElements.define` aan,
 * landt de definitie in de browserregistry, en is hij daarna via de gepatchte
 * `get` onzichtbaar. `whenDefined` lost dan ook nooit op — vandaar een
 * kaartkiezer die eindeloos blijft laden en kaarten die "Configuratiefout"
 * tonen, terwijl `window.customCards` (een gewone array) wél gevuld is.
 *
 * ## De oplossing
 *
 * Niet registreren tot HA's frontend zijn eigen elementen heeft geregistreerd.
 * `home-assistant` is daarvoor het signaal: dat element bestaat pas nadat de
 * polyfill is geïnstalleerd, dus vanaf dat moment landen wij gegarandeerd in
 * dezelfde registry als waarin HA kijkt.
 *
 * `customElements` wordt bij elke poging **opnieuw gelezen**, nooit in een
 * variabele bewaard. Dat is wat deze aanpak ook bestand maakt tegen het
 * vervangen van het registry-object zelf.
 *
 * Deze module heeft bewust geen enkele import: hij is in een gewone Node-test
 * te toetsen met nagebootste registry's, zonder DOM en zonder jsdom.
 */

/** Het element waaraan we zien dat HA's frontend geladen is. */
export const HA_MARKER = "home-assistant";

/** Hoe vaak we kijken of het zover is. */
export const INTERVAL_MS = 20;

/**
 * Na deze tijd registreren we alsnog. Een kaart die misschien niet werkt is
 * beter dan een kaart die gegarandeerd nooit verschijnt, bijvoorbeeld op een
 * pagina waar `home-assistant` niet voorkomt.
 */
export const MAX_WACHT_MS = 10000;

/**
 * Registreer zodra HA's frontend klaar is.
 *
 * @param {object} args
 * @param {() => {get: Function, define: Function}|undefined} args.leesRegistry
 *   Geeft de *huidige* registry. Wordt bij elke poging opnieuw aangeroepen.
 * @param {[string, Function][]} args.definities  paren van naam en klasse
 * @param {(bericht: string) => void} [args.waarschuw]
 * @param {(fn: Function, ms: number) => unknown} [args.plan]
 * @param {() => number} [args.nu]
 * @param {string} [args.marker]
 * @param {number} [args.intervalMs]
 * @param {number} [args.maxWachtMs]
 * @returns {boolean} of er meteen geregistreerd is
 */
export function registreerWanneerGereed({
  leesRegistry,
  definities,
  waarschuw = () => {},
  plan = (fn, ms) => setTimeout(fn, ms),
  nu = () => Date.now(),
  marker = HA_MARKER,
  intervalMs = INTERVAL_MS,
  maxWachtMs = MAX_WACHT_MS,
}) {
  const start = nu();

  /** Registreer nu, ongeacht of de marker er is. Gooit nooit. */
  function registreerNu() {
    const registry = leesRegistry();
    if (!registry) {
      return false;
    }
    for (const [naam, klasse] of definities) {
      try {
        if (!registry.get(naam)) {
          registry.define(naam, klasse);
        }
      } catch (fout) {
        // Nooit gooien op modulescope. Een dubbele registratie of een
        // geweigerde naam mag de rest niet meeslepen. Dat de bundel een
        // dubbele evaluatie overleeft is geen overdreven zorgvuldigheid: hij
        // komt langs twee laadroutes binnen (zie resource.py).
        waarschuw(`kon ${naam} niet registreren: ${fout && fout.message}`);
      }
    }
    return true;
  }

  /** Probeer, maar alleen als HA's frontend er al is. */
  function probeer() {
    const registry = leesRegistry();
    if (!registry || !registry.get(marker)) {
      return false;
    }
    return registreerNu();
  }

  if (probeer()) {
    return true;
  }

  const tik = () => {
    if (probeer()) {
      return;
    }
    if (nu() - start >= maxWachtMs) {
      waarschuw(
        `${marker} is na ${maxWachtMs} ms niet verschenen; de kaart wordt alsnog geregistreerd`,
      );
      registreerNu();
      return;
    }
    plan(tik, intervalMs);
  };

  plan(tik, intervalMs);
  return false;
}
