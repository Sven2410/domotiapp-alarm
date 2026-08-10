/**
 * src/registreer.js — de wachtlus op HA's custom-element-registry.
 *
 * Alles hier is **NIEUW GEDRAG**: `registreer.js` bestaat pas in deze fase, dus
 * elke test faalt op de code van vóór deze ronde met "module not found". Dat is
 * een triviale mislukking en bewijst weinig, dus de tests zijn zo opgezet dat
 * ze het *mechanisme* aantonen in plaats van alleen het bestaan ervan:
 *
 * - de eerste test bewijst dat er **niet** geregistreerd wordt zolang de marker
 *   ontbreekt. Dat is precies de regressie die de registry-race veroorzaakt, en
 *   een implementatie die meteen `define` aanroept faalt hier.
 * - de derde test bewijst dat de registry bij **elke** poging opnieuw wordt
 *   gelezen. Een implementatie die hem in een variabele bewaart, faalt.
 *
 * Geen jsdom: deze module heeft geen imports en geen DOM nodig, dus de registry
 * is met een gewone Map na te bootsen.
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  HA_MARKER,
  MAX_WACHT_MS,
  registreerWanneerGereed,
} from "../../src/registreer.js";

/** Een registry die zich als `customElements` gedraagt. */
function nepRegistry(voorgedefinieerd = []) {
  const map = new Map(voorgedefinieerd.map((naam) => [naam, class {}]));
  return {
    map,
    get: (naam) => map.get(naam),
    define: (naam, klasse) => {
      if (map.has(naam)) {
        throw new Error(`'${naam}' has already been defined`);
      }
      map.set(naam, klasse);
    },
  };
}

/** Een planner die de taken in de hand houdt in plaats van echte timers. */
function nepPlanner() {
  const taken = [];
  return {
    plan: (fn) => taken.push(fn),
    /** Draai alle nu wachtende taken, één ronde. */
    tik() {
      const ronde = taken.splice(0, taken.length);
      for (const fn of ronde) {
        fn();
      }
      return ronde.length;
    },
    get open() {
      return taken.length;
    },
  };
}

class Kaart {}

describe("registreerWanneerGereed", () => {
  it("registreert NIET zolang home-assistant ontbreekt (NIEUW GEDRAG)", () => {
    const registry = nepRegistry();
    const planner = nepPlanner();

    const meteen = registreerWanneerGereed({
      leesRegistry: () => registry,
      definities: [["domotiapp-alarm-card", Kaart]],
      plan: planner.plan,
      nu: () => 0,
    });

    assert.equal(meteen, false, "mag niet meteen registreren");
    assert.equal(
      registry.map.has("domotiapp-alarm-card"),
      false,
      "de kaart mag nog niet in de registry staan; dat is de registry-race",
    );
    assert.ok(planner.open > 0, "er moet een herpoging gepland zijn");
  });

  it("registreert zodra de marker verschijnt (NIEUW GEDRAG)", () => {
    const registry = nepRegistry();
    const planner = nepPlanner();

    registreerWanneerGereed({
      leesRegistry: () => registry,
      definities: [["domotiapp-alarm-card", Kaart]],
      plan: planner.plan,
      nu: () => 0,
    });

    planner.tik();
    assert.equal(registry.map.has("domotiapp-alarm-card"), false);

    // HA's frontend is nu geladen.
    registry.map.set(HA_MARKER, class {});
    planner.tik();

    assert.equal(registry.map.get("domotiapp-alarm-card"), Kaart);
  });

  it("registreert meteen als de marker er al is (NIEUW GEDRAG)", () => {
    const registry = nepRegistry([HA_MARKER]);
    const planner = nepPlanner();

    const meteen = registreerWanneerGereed({
      leesRegistry: () => registry,
      definities: [["domotiapp-alarm-card", Kaart]],
      plan: planner.plan,
      nu: () => 0,
    });

    assert.equal(meteen, true);
    assert.equal(registry.map.get("domotiapp-alarm-card"), Kaart);
    assert.equal(planner.open, 0, "geen herpoging nodig");
  });

  it("leest de registry bij elke poging opnieuw (NIEUW GEDRAG)", () => {
    // De polyfill vervángt het registry-object. Wie hem in een variabele
    // bewaart, registreert daarna in het verkeerde object.
    const eerste = nepRegistry();
    const tweede = nepRegistry([HA_MARKER]);
    let huidig = eerste;
    const planner = nepPlanner();

    registreerWanneerGereed({
      leesRegistry: () => huidig,
      definities: [["domotiapp-alarm-card", Kaart]],
      plan: planner.plan,
      nu: () => 0,
    });

    huidig = tweede;
    planner.tik();

    assert.equal(
      tweede.map.get("domotiapp-alarm-card"),
      Kaart,
      "moet in de nieuwe registry landen",
    );
    assert.equal(
      eerste.map.has("domotiapp-alarm-card"),
      false,
      "en niet in de oude",
    );
  });

  it("registreert na de bovengrens alsnog, met waarschuwing (NIEUW GEDRAG)", () => {
    const registry = nepRegistry(); // marker komt nooit
    const planner = nepPlanner();
    const waarschuwingen = [];
    let klok = 0;

    registreerWanneerGereed({
      leesRegistry: () => registry,
      definities: [["domotiapp-alarm-card", Kaart]],
      plan: planner.plan,
      nu: () => klok,
      waarschuw: (bericht) => waarschuwingen.push(bericht),
    });

    klok = MAX_WACHT_MS;
    planner.tik();

    assert.equal(
      registry.map.get("domotiapp-alarm-card"),
      Kaart,
      "een kaart die misschien niet werkt is beter dan geen kaart",
    );
    assert.equal(waarschuwingen.length, 1);
    assert.match(waarschuwingen[0], /niet verschenen/);
    assert.equal(planner.open, 0, "de lus moet stoppen");
  });

  it("gooit niet bij een dubbele registratie (NIEUW GEDRAG)", () => {
    // De bundel komt langs twee laadroutes binnen en kan dus twee keer
    // geëvalueerd worden. Onze nepRegistry.define gooit bij een dubbele naam,
    // net als de echte.
    const registry = nepRegistry([HA_MARKER, "domotiapp-alarm-card"]);
    const waarschuwingen = [];

    assert.doesNotThrow(() => {
      registreerWanneerGereed({
        leesRegistry: () => registry,
        definities: [["domotiapp-alarm-card", Kaart]],
        plan: () => {},
        nu: () => 0,
        waarschuw: (bericht) => waarschuwingen.push(bericht),
      });
    });

    // Al gedefinieerd, dus define wordt niet eens aangeroepen: geen fout, geen
    // waarschuwing.
    assert.deepEqual(waarschuwingen, []);
  });

  it("laat een mislukte definitie de rest niet meeslepen (NIEUW GEDRAG)", () => {
    const registry = nepRegistry([HA_MARKER]);
    const waarschuwingen = [];
    // Een naam die de registry weigert.
    const stuk = {
      get: registry.get,
      define: (naam, klasse) => {
        if (naam === "stuk") {
          throw new Error("invalid name");
        }
        registry.map.set(naam, klasse);
      },
    };

    registreerWanneerGereed({
      leesRegistry: () => stuk,
      definities: [
        ["stuk", Kaart],
        ["domotiapp-alarm-card", Kaart],
      ],
      plan: () => {},
      nu: () => 0,
      waarschuw: (bericht) => waarschuwingen.push(bericht),
    });

    assert.equal(registry.map.get("domotiapp-alarm-card"), Kaart);
    assert.equal(waarschuwingen.length, 1);
    assert.match(waarschuwingen[0], /kon stuk niet registreren/);
  });

  it("gooit niet als er (nog) geen registry is (NIEUW GEDRAG)", () => {
    const planner = nepPlanner();
    assert.doesNotThrow(() => {
      registreerWanneerGereed({
        leesRegistry: () => undefined,
        definities: [["domotiapp-alarm-card", Kaart]],
        plan: planner.plan,
        nu: () => 0,
      });
    });
    assert.ok(planner.open > 0);
  });
});
