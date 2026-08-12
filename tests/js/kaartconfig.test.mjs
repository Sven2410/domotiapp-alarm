/**
 * src/kaartconfig.js — de kaart-config en de drie gevallen zonder geldige
 * `person` (SPEC 16).
 *
 * **NIEUW GEDRAG**, met dezelfde kanttekening als bij de andere JS-tests: het
 * bestand is nieuw, dus op de oude code faalt alles met
 * `ERR_MODULE_NOT_FOUND`. Wat deze tests waard maakt is dat ze het **verschil**
 * tussen de drie gevallen vastleggen. Dat verschil is het interessante deel van
 * SPEC 16.3: gooien mag precies één keer, en de andere twee gevallen zijn
 * teksten die verschillend gekleurd horen te zijn.
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  TEKST_KIES_PERSOON,
  TEKST_ONLEESBAAR,
  TEKST_PERSOON_WEG,
  foutTekst,
  personToestand,
  stubConfig,
  valideerConfig,
} from "../../src/kaartconfig.js";

const TYPE = "custom:domotiapp-alarm-card";

describe("valideerConfig (SPEC 16.1 en 16.3)", () => {
  it("laat een config zonder person door (NIEUW GEDRAG)", () => {
    // Dit is de toestand direct ná toevoegen via de kaartkiezer. Gooien zou de
    // kaart onmiddellijk "Configuratiefout" laten tonen op iets wat helemaal
    // geen fout is.
    assert.doesNotThrow(() => valideerConfig({ type: TYPE }));
    assert.deepEqual(valideerConfig({ type: TYPE }), { type: TYPE });
    assert.doesNotThrow(() => valideerConfig({ type: TYPE, person: "" }));
  });

  it("laat een geldige person door (NIEUW GEDRAG)", () => {
    // Positieve controle: zonder deze zou een implementatie die áltijd gooit
    // door de volgende test heen komen.
    const config = valideerConfig({ type: TYPE, person: "person.sven" });
    assert.equal(config.person, "person.sven");
  });

  it("gooit bij een person in het verkeerde domein (NIEUW GEDRAG)", () => {
    // De enige plek waar de kaart mag gooien (SPEC 16.3). Lovelace maakt hier
    // "Configuratiefout" van, en dat hoort ook: de config is ongeldig.
    for (const verkeerd of [
      "light.bedlamp",
      "media_player.slaapkamer",
      "sven",
      "personx.sven",
    ]) {
      assert.throws(
        () => valideerConfig({ type: TYPE, person: verkeerd }),
        /domein person|entity-ID/,
        `${verkeerd} had geweigerd moeten worden`,
      );
    }
  });

  it("gooit bij een person die geen tekst is (NIEUW GEDRAG)", () => {
    assert.throws(() => valideerConfig({ type: TYPE, person: 42 }));
    assert.throws(() => valideerConfig({ type: TYPE, person: ["person.sven"] }));
  });

  it("gooit als de config zelf onbruikbaar is (NIEUW GEDRAG)", () => {
    assert.throws(() => valideerConfig(undefined));
    assert.throws(() => valideerConfig(null));
    assert.throws(() => valideerConfig([]));
    assert.throws(() => valideerConfig("custom:domotiapp-alarm-card"));
  });

  it("bewaart de sleutels die Lovelace er zelf aan hangt (NIEUW GEDRAG)", () => {
    // SPEC 16.1: doorlaten en bewaren zonder ze te interpreteren. Een validatie
    // die alleen `type` en `person` overhoudt, gooit de plaatsing van de klant
    // weg bij de eerstvolgende bewerking.
    const binnen = {
      type: TYPE,
      person: "person.sven",
      grid_options: { columns: 6, rows: "auto" },
      layout_options: { grid_columns: 6 },
      view_layout: { position: "sidebar" },
      visibility: [{ condition: "user", users: ["abc"] }],
    };
    assert.deepEqual(valideerConfig(binnen), binnen);
  });
});

describe("stubConfig (SPEC 16.2)", () => {
  it("levert de config zonder person (NIEUW GEDRAG)", () => {
    // Mét person zou de kaartkiezer een willekeurige persoon opdringen, en dan
    // staat er na toevoegen iemands wekkerlijst op het scherm die de gebruiker
    // niet heeft gekozen.
    const stub = stubConfig("domotiapp-alarm-card");
    assert.deepEqual(stub, { type: TYPE });
    assert.equal("person" in stub, false);
  });
});

describe("personToestand (SPEC 16.3)", () => {
  it("onderscheidt de drie gevallen, inclusief de kleur (NIEUW GEDRAG)", () => {
    const ontbreekt = personToestand(undefined, false);
    assert.equal(ontbreekt.soort, "ontbreekt");
    assert.equal(ontbreekt.tekst, TEKST_KIES_PERSOON);
    assert.equal(
      ontbreekt.isFout,
      false,
      "direct na toevoegen is geen storing en mag er niet als storing uitzien",
    );

    const weg = personToestand("person.sven", false);
    assert.equal(weg.soort, "weg");
    assert.equal(weg.tekst, TEKST_PERSOON_WEG);
    assert.equal(weg.isFout, true);

    const goed = personToestand("person.sven", true);
    assert.equal(goed.soort, "ok");
    assert.equal(goed.tekst, null);
    assert.equal(goed.isFout, false);
  });

  it("beweert niet dat de persoon verwijderd is (REGRESSIEWACHT)", () => {
    // Fase 11, na goedkeuring van de eigenaar. De kaart stelt vast dat de
    // entiteit ontbreekt; of hij verwijderd dan wel HERNOEMD is, weet ze niet —
    // SPEC 18.1 zegt dat zelf. Een tekst die "bestaat niet meer" zegt kiest er
    // een van twee en stuurt de klant bij een hernoeming naar het verkeerde
    // scherm. Zelfde patroon als sound_gone in fase 6 (valkuil 53).
    //
    // REGRESSIEWACHT en geen NIEUW GEDRAG: hij houdt een beslissing vast, en op
    // de oude tekst faalt hij ook — maar dat komt doordat de tekst zelf de
    // wijziging is, niet doordat er gedrag bij is gekomen.
    assert.ok(
      !/bestaat niet meer/i.test(TEKST_PERSOON_WEG),
      `de tekst mag geen verwijdering claimen: ${TEKST_PERSOON_WEG}`,
    );
    // Positieve controle: er staat wél iets, en het gaat over de persoon.
    assert.match(TEKST_PERSOON_WEG, /persoon/i);
  });

  it("laat een lege person als ontbrekend gelden (NIEUW GEDRAG)", () => {
    assert.equal(personToestand("", true).soort, "ontbreekt");
    assert.equal(personToestand(null, true).soort, "ontbreekt");
  });
});

describe("foutTekst (SPEC 18.1 en 19.2)", () => {
  it("vertaalt de foutcodes naar de teksten uit SPEC (NIEUW GEDRAG)", () => {
    assert.equal(foutTekst("not_found", "person.sven niet gevonden"), TEKST_PERSOON_WEG);
    assert.equal(foutTekst("home_assistant_error", "kapot"), TEKST_ONLEESBAAR);
  });

  it("verzwijgt een onbekende fout niet (NIEUW GEDRAG)", () => {
    // Een onbekende fout wegwerken achter een vriendelijke standaardtekst is
    // het stille doorgaan uit SPEC 19.1. Wat de server zei, komt op het scherm.
    assert.equal(foutTekst("iets_anders", "de verbinding viel weg"), "de verbinding viel weg");
    assert.match(foutTekst(undefined, undefined), /mis/);
  });
});
