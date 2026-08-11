/**
 * src/menu.js — waar het overloopmenu komt te staan (SPEC 3.2).
 *
 * **Alles NIEUW GEDRAG.** De module bestaat pas in fase 6b; op de code van
 * daarvóór faalt de import met `ERR_MODULE_NOT_FOUND`. Dat is een triviale
 * mislukking, dus elke test hieronder legt een **eigenschap** vast die ook bij een
 * latere wijziging kan sneuvelen — niet alleen dat de functie bestaat.
 *
 * De bevinding die dit oplost: het menu stond altijd 40 px onder de knop en stak
 * bij de onderste rij onder de kaart uit. De eigenschap die dat repareert is
 * meetbaar en staat hier: **het menu blijft binnen de kaart**, en past het er
 * onder niet, dan klapt het erboven.
 *
 * Alle getallen zijn CSS-pixels, net als `getBoundingClientRect` — uitdrukkelijk
 * niet de schermafdrukcoördinaten waarin de browsertool klikt (valkuil 43).
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { MENU_MARGE, plaatsMenu } from "../../src/menu.js";

/** Een ruim venster, zodat alleen de kaart de uitkomst bepaalt. */
const RUIM = { breedte: 1200, hoogte: 900 };
const MENU = { breedte: 168, hoogte: 96 };

describe("plaatsMenu (SPEC 3.2)", () => {
  it("hangt het menu onder de knop als het daar binnen de kaart past (NIEUW GEDRAG)", () => {
    const anker = { top: 100, bottom: 140, right: 400 };
    const kaart = { top: 60, bottom: 600 };

    const uit = plaatsMenu(anker, kaart, MENU, RUIM);

    assert.equal(uit.richting, "onder");
    assert.equal(uit.top, 140 + MENU_MARGE);
    assert.equal(uit.binnenKaart, true);
  });

  it("klapt het menu boven de knop als het er onder niet past (NIEUW GEDRAG)", () => {
    // De onderste rij: de knop staat vlak boven de onderrand van de kaart.
    const anker = { top: 520, bottom: 560, right: 400 };
    const kaart = { top: 60, bottom: 600 };

    const uit = plaatsMenu(anker, kaart, MENU, RUIM);

    assert.equal(uit.richting, "boven");
    assert.equal(uit.top, 520 - MENU.hoogte - MENU_MARGE);
    assert.equal(uit.binnenKaart, true);
  });

  it("laat het menu binnen de kaart, ook op de onderste rij (NIEUW GEDRAG)", () => {
    // Dit is de bevinding zelf, als eigenschap in plaats van als geval: waar de
    // knop ook staat, het menu steekt niet onder of boven de kaart uit.
    const kaart = { top: 60, bottom: 600 };
    for (let bodem = 100; bodem <= 600; bodem += 20) {
      const uit = plaatsMenu({ top: bodem - 40, bottom: bodem, right: 400 }, kaart, MENU, RUIM);
      assert.ok(uit.top >= kaart.top, `top ${uit.top} steekt boven de kaart uit`);
      assert.ok(
        uit.top + MENU.hoogte <= kaart.bottom,
        `onderkant ${uit.top + MENU.hoogte} steekt onder de kaart uit`,
      );
    }
  });

  it("lijnt het menu rechts uit op de knop (NIEUW GEDRAG)", () => {
    // Links uitlijnen zou het menu over de schakelaar en de naam heen leggen; de
    // knop staat in het rechterdeel van de rij.
    const uit = plaatsMenu({ top: 100, bottom: 140, right: 400 }, { top: 60, bottom: 600 }, MENU, RUIM);
    assert.equal(uit.left, 400 - MENU.breedte);
  });

  it("houdt het menu binnen het venster als de knop bijna tegen de rand staat (NIEUW GEDRAG)", () => {
    // Een smalle kaart op een telefoon: de ⋮-knop staat vlak bij de rechterrand,
    // en zonder klem zou het menu links buiten beeld beginnen.
    const smal = { breedte: 160, hoogte: 900 };
    const uit = plaatsMenu({ top: 100, bottom: 140, right: 150 }, { top: 60, bottom: 600 }, MENU, smal);
    assert.ok(uit.left >= MENU_MARGE, `left ${uit.left} valt buiten beeld`);
  });

  it("laat het venster winnen van de kaart als het menu nergens in past (NIEUW GEDRAG)", () => {
    // Een kaart met één rij is lager dan het menu hoog is. Dan is er geen plek
    // binnen de kaart, en telt alleen nog of het menu **bereikbaar** blijft: een
    // menu dat half buiten beeld valt is erger dan een menu dat een randje
    // overlapt.
    const kaart = { top: 400, bottom: 460 };
    const uit = plaatsMenu({ top: 410, bottom: 450, right: 400 }, kaart, MENU, RUIM);

    assert.equal(uit.binnenKaart, false);
    assert.ok(uit.top >= MENU_MARGE);
    assert.ok(uit.top + MENU.hoogte <= RUIM.hoogte - MENU_MARGE);
  });

  it("begint op de marge als het venster kleiner is dan het menu (NIEUW GEDRAG)", () => {
    // Positieve controle op de klemvolgorde: bij een venster kleiner dan het menu
    // is de bovengrens lager dan de ondergrens. Wint de bovengrens, dan is `top`
    // negatief en begint het menu buiten beeld — dan is er niets aan te klikken.
    const krap = { breedte: 1200, hoogte: 50 };
    const uit = plaatsMenu({ top: 10, bottom: 40, right: 400 }, { top: 0, bottom: 50 }, MENU, krap);
    assert.equal(uit.top, MENU_MARGE);
  });

  it("gebruikt de GEMETEN hoogte en niet een vaste (NIEUW GEDRAG)", () => {
    // Bij een groter lettertype is het menu hoger, en dan hoort het eerder om te
    // klappen. Een geraden hoogte zou het bij precies die gebruiker alsnog over de
    // kaartrand duwen — de bevinding, maar dan alleen bij wie groot leest.
    const anker = { top: 480, bottom: 520, right: 400 };
    const kaart = { top: 60, bottom: 600 };

    const klein = plaatsMenu(anker, kaart, { breedte: 168, hoogte: 60 }, RUIM);
    const groot = plaatsMenu(anker, kaart, { breedte: 168, hoogte: 140 }, RUIM);

    assert.equal(klein.richting, "onder");
    assert.equal(groot.richting, "boven");
  });
});
