/**
 * src/bevestiging.js — waar de verwijderbevestiging in komt, en wat er staat.
 *
 * **Alles NIEUW GEDRAG**: de module bestaat pas in fase 7, dus op de code van
 * daarvóór faalt de import met `ERR_MODULE_NOT_FOUND`. Dat is een triviale
 * mislukking, en daarom legt elke test hieronder een **eigenschap** vast die ook
 * bij een latere wijziging kan sneuvelen.
 *
 * De tekst staat in een eigen module en niet in de renderfunctie omdat het een
 * beslissing is met vier uitkomsten, en die horen in een gewone Node-test
 * (CLAUDE.md). Waaróm er geen `ha-dialog` omheen zit, staat in de kop van
 * `src/bevestiging.js` — dat is een meting, geen smaak.
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { bevestigingsTekst } from "../../src/bevestiging.js";

describe("bevestigingsTekst (SPEC 3.2)", () => {
  it("noemt naam én tijd (NIEUW GEDRAG)", () => {
    // Beide, want een lijst met vier wekkers heeft er zo twee van "Werk". Alleen
    // de naam maakt de vraag onbeantwoordbaar op precies het moment dat hij
    // onomkeerbaar wordt.
    assert.equal(
      bevestigingsTekst({ name: "Werk", time: "06:45" }),
      'Wil je de wekker "Werk" van 06:45 verwijderen?',
    );
  });

  it("stelt de vraag ook zonder naam of zonder tijd (NIEUW GEDRAG)", () => {
    assert.equal(bevestigingsTekst({ name: "Werk" }), 'Wil je de wekker "Werk" verwijderen?');
    assert.equal(bevestigingsTekst({ time: "06:45" }), "Wil je de wekker van 06:45 verwijderen?");
  });

  it("verzint geen naam voor een wekker zonder naam (NIEUW GEDRAG)", () => {
    // Een verzonnen naam verwijst naar een wekker die de klant niet herkent, en
    // dat is erger dan een vraag zonder naam.
    assert.equal(bevestigingsTekst({}), "Wil je deze wekker verwijderen?");
    assert.equal(bevestigingsTekst(undefined), "Wil je deze wekker verwijderen?");
    assert.equal(bevestigingsTekst({ name: "   ", time: "  " }), "Wil je deze wekker verwijderen?");
    assert.equal(bevestigingsTekst({ name: 42, time: null }), "Wil je deze wekker verwijderen?");
  });
});
