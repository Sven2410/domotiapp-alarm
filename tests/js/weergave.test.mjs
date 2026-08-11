/**
 * src/weergave.js — wat er in een rij staat, en of de kaart een stopknop is.
 *
 * Alles hier is **NIEUW GEDRAG**: `weergave.js` bestaat pas in deze fase, dus
 * elke test faalt op de code van vóór deze ronde met `ERR_MODULE_NOT_FOUND`.
 * Dat is een triviale mislukking en bewijst weinig — precies de valkuil die
 * CLAUDE.md beschrijft. De tests zijn daarom zo opgezet dat ze een **eigenschap
 * uit SPEC** vastleggen die ook bij een latere wijziging kan sneuvelen, en er
 * staan positieve controles naast de negatieve (valkuil 36): een test die
 * alleen op "geen stopknop" let, komt door een implementatie die er nooit een
 * maakt.
 *
 * Geen jsdom: deze module heeft geen DOM nodig. Dat is geen toeval maar het
 * criterium uit CLAUDE.md — kan het in een gewone Node-test, dan hoort het hier
 * en niet in de renderfunctie.
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  TEKST_AFGELOPEN,
  TEKST_EENMALIG,
  TEKST_GEEN_WEKKERS,
  TEKST_GEEN_WEKKER_ACTIEF,
  TEKST_MELDING_ZONDER_TEKST,
  TEKST_OVERGESLAGEN,
  dagenTekst,
  isAfgelopen,
  kopTekst,
  meldingVan,
  stopToestand,
  subtitel,
} from "../../src/weergave.js";

const NU = Date.parse("2026-08-11T09:00:00+02:00");
const STRAKS = "2026-08-12T05:20:00+02:00";
const EERDER = "2026-08-05T05:20:00+02:00";

/** Een wekker zoals `alarms/get` hem levert (SPEC 14.2). */
function wekker(velden = {}) {
  return {
    id: "a1f4",
    name: "Werk",
    time: "06:45",
    days: [1, 2, 3, 4, 5],
    enabled: true,
    skip_next: false,
    one_shot_at: null,
    sound: { uri: "somafm://radio/x", name: "X", media_type: "radio", image: null },
    speaker: "media_player.slaapkamer",
    volume_pct: 40,
    light: null,
    last_fired: null,
    last_message: null,
    ...velden,
  };
}

describe("dagenTekst (SPEC 3.2)", () => {
  it("geeft de Nederlandse afkortingen in ISO-volgorde (NIEUW GEDRAG)", () => {
    assert.equal(dagenTekst([1, 2, 3, 4, 5]), "ma di wo do vr");
    assert.equal(dagenTekst([6, 7]), "za zo");
    // 1 = maandag en 7 = zondag; een implementatie die 0-gebaseerd telt of die
    // JS' getDay()-volgorde aanhoudt (0 = zondag) faalt op deze twee.
    assert.equal(dagenTekst([1]), "ma");
    assert.equal(dagenTekst([7]), "zo");
  });

  it("geeft Eenmalig bij een lege lijst (NIEUW GEDRAG)", () => {
    assert.equal(dagenTekst([]), TEKST_EENMALIG);
    assert.equal(dagenTekst(undefined), TEKST_EENMALIG);
  });

  it("sorteert en ontdubbelt (NIEUW GEDRAG)", () => {
    assert.equal(dagenTekst([5, 1, 3]), "ma wo vr");
    assert.equal(dagenTekst([2, 2]), "di");
  });
});

describe("isAfgelopen (SPEC 14.5)", () => {
  it("kijkt naar het moment en niet naar enabled (NIEUW GEDRAG)", () => {
    // Een gemiste eenmalige wekker staat nog op enabled: true (Home Assistant
    // stond uit, SPEC 13.4) en is tóch afgelopen. Wie op enabled kijkt, toont
    // hem als een wekker die nog gaat komen.
    assert.equal(
      isAfgelopen(wekker({ days: [], one_shot_at: EERDER, enabled: true }), NU),
      true,
    );
    // Positieve controle de andere kant op: uitgezet maar nog in de toekomst is
    // niet afgelopen.
    assert.equal(
      isAfgelopen(wekker({ days: [], one_shot_at: STRAKS, enabled: false }), NU),
      false,
    );
  });

  it("geldt alleen voor eenmalige wekkers (NIEUW GEDRAG)", () => {
    // Een herhalende wekker heeft geen one_shot_at, maar mocht er ooit een
    // achterblijven, dan mag hij de rij niet als "afgelopen" markeren: die
    // wekker gaat morgen gewoon weer af.
    assert.equal(
      isAfgelopen(wekker({ days: [1, 2], one_shot_at: EERDER }), NU),
      false,
    );
  });

  it("verzint niets bij een ontbrekende of kapotte datum (NIEUW GEDRAG)", () => {
    assert.equal(isAfgelopen(wekker({ days: [], one_shot_at: null }), NU), false);
    assert.equal(isAfgelopen(wekker({ days: [], one_shot_at: "morgen" }), NU), false);
  });
});

describe("subtitel (SPEC 3.2 en 14.5)", () => {
  it("toont de herhaaldagen als er niets bijzonders is (NIEUW GEDRAG)", () => {
    // De positieve controle onder de drie tests hierna: zonder deze zou een
    // implementatie die áltijd "Morgen overgeslagen" teruggeeft er doorheen
    // komen.
    assert.equal(subtitel(wekker(), NU), "ma di wo do vr");
    assert.equal(subtitel(wekker({ days: [], one_shot_at: STRAKS }), NU), TEKST_EENMALIG);
  });

  it("toont Morgen overgeslagen bij skip_next (NIEUW GEDRAG)", () => {
    assert.equal(subtitel(wekker({ skip_next: true }), NU), TEKST_OVERGESLAGEN);
  });

  it("toont Eenmalig — afgelopen als het moment voorbij is (NIEUW GEDRAG)", () => {
    assert.equal(
      subtitel(wekker({ days: [], one_shot_at: EERDER, enabled: false }), NU),
      TEKST_AFGELOPEN,
    );
  });

  it("laat afgelopen vóór overgeslagen gaan (NIEUW GEDRAG)", () => {
    // "Morgen overgeslagen" is een belofte over een morgen die niet komt: deze
    // wekker gaat sowieso niet meer af. De volgorde in de implementatie is dus
    // gedrag en geen smaak.
    assert.equal(
      subtitel(wekker({ days: [], one_shot_at: EERDER, skip_next: true }), NU),
      TEKST_AFGELOPEN,
    );
  });
});

describe("meldingVan (SPEC 11.7)", () => {
  it("geeft niets als er geen melding is (NIEUW GEDRAG)", () => {
    assert.equal(meldingVan(wekker()), null);
    assert.equal(meldingVan(wekker({ last_message: undefined })), null);
  });

  it("kiest kleur en toon op severity, niet op kind (NIEUW GEDRAG)", () => {
    // SPEC 11.7: `kind` is om op te vergelijken, `severity` bepaalt hoe het
    // eruitziet. Beide meldingen hieronder hebben een `kind` dat op een fout
    // lijkt; alleen de severity mag tellen.
    const fout = meldingVan(
      wekker({
        last_message: {
          at: EERDER,
          kind: "speaker_unavailable",
          severity: "error",
          text: "De wekker van 05:20 is niet afgegaan.",
        },
      }),
    );
    assert.equal(fout.isFout, true);
    assert.equal(fout.severity, "error");
    assert.equal(fout.tekst, "De wekker van 05:20 is niet afgegaan.");

    const mededeling = meldingVan(
      wekker({
        last_message: {
          at: EERDER,
          kind: "skipped_grace_window",
          severity: "notice",
          text: "Je wekker van 06:45 is niet afgegaan omdat Home Assistant uit stond.",
        },
      }),
    );
    assert.equal(mededeling.isFout, false);
    assert.equal(mededeling.severity, "notice");
  });

  it("behandelt een onbekende severity als mededeling (NIEUW GEDRAG)", () => {
    // Alleen "error" is een fout. Een onbekende waarde als fout tonen zou een
    // mededeling er als storing uit laten zien, en dat onderscheid is in SPEC
    // 11.7 juist vastgelegd.
    const m = meldingVan(
      wekker({ last_message: { kind: "iets", severity: "urgent", text: "x" } }),
    );
    assert.equal(m.isFout, false);
    assert.equal(m.severity, "notice");
  });

  it("houdt iets dat geen melding-object is buiten de rij (NIEUW GEDRAG)", () => {
    // Gevonden met mutatie J21 van fase 4a: het weghalen van de typecontrole
    // liet geen enkele test falen, terwijl het gedrag wél verandert — dan zou
    // een kapot opslagveld op de kaart verschijnen als "er is een melding, maar
    // de tekst ontbreekt". Dat beweert dat er iets met de wekker is gebeurd,
    // terwijl er alleen iets met de opslag mis is.
    for (const kapot of ["een melding", 42, true, ["x"]]) {
      assert.equal(
        meldingVan(wekker({ last_message: kapot })),
        null,
        `${JSON.stringify(kapot)} is geen melding`,
      );
    }
  });

  it("laat een melding zonder tekst niet verdwijnen (NIEUW GEDRAG)", () => {
    // SPEC 19.1: nooit stil terugvallen. Een gebeurtenis die de klant moet zien
    // mag niet wegvallen omdat één veld leeg is.
    const m = meldingVan(
      wekker({ last_message: { kind: "sound_gone", severity: "error", text: "  " } }),
    );
    assert.notEqual(m, null);
    assert.equal(m.tekst, TEKST_MELDING_ZONDER_TEKST);
    assert.equal(m.isFout, true);
  });
});

describe("stopToestand (SPEC 4)", () => {
  it("is null als er niets afgaat (NIEUW GEDRAG)", () => {
    assert.equal(stopToestand([wekker()], []), null);
    assert.equal(stopToestand([wekker()], undefined), null);
  });

  it("geeft naam en tijd van de afgaande wekker (NIEUW GEDRAG)", () => {
    const stop = stopToestand([wekker()], ["a1f4"]);
    assert.deepEqual(stop.ids, ["a1f4"]);
    assert.equal(stop.naam, "Werk");
    assert.equal(stop.tijd, "06:45");
  });

  it("maakt van twee wekkers tegelijk één knop die beide stopt (NIEUW GEDRAG)", () => {
    // SPEC 4: twee wekkers van dezelfde persoon mogen dezelfde tijd hebben. Eén
    // stopknop die er maar één stopt, laat de andere doorspelen tot de
    // stoptimer van 30 minuten — het faalgeval waar deze knop voor bestaat.
    const stop = stopToestand(
      [wekker(), wekker({ id: "7c2b", name: "Reserve", time: "06:45" })],
      ["a1f4", "7c2b"],
    );
    assert.deepEqual(stop.ids, ["a1f4", "7c2b"]);
    assert.equal(stop.naam, "Werk en Reserve");
    assert.equal(stop.tijd, "06:45", "één keer, niet twee keer dezelfde tijd");
  });

  it("noemt twee verschillende tijden allebei (NIEUW GEDRAG)", () => {
    const stop = stopToestand(
      [wekker(), wekker({ id: "7c2b", name: "Reserve", time: "07:15" })],
      ["a1f4", "7c2b"],
    );
    assert.equal(stop.tijd, "06:45 en 07:15");
  });

  it("houdt de knop overeind bij een onbekend ID (NIEUW GEDRAG)", () => {
    // Tussen twee aanroepen door kan het register al bijgewerkt zijn en de
    // lijst nog niet. Verdwijnt de knop dan, dan krijgt de klant het geluid pas
    // na 30 minuten uit (SPEC 9.4). Er staat een neutrale naam in plaats van
    // een verzonnen naam.
    const stop = stopToestand([wekker()], ["onbekend"]);
    assert.notEqual(stop, null);
    assert.deepEqual(stop.ids, ["onbekend"]);
    assert.equal(stop.naam, "Wekker");
    assert.equal(stop.tijd, "");
  });

  it("ontdubbelt en negeert rommel in ringing (NIEUW GEDRAG)", () => {
    const stop = stopToestand([wekker()], ["a1f4", "a1f4", null, 7]);
    assert.deepEqual(stop.ids, ["a1f4"]);
    assert.equal(stop.naam, "Werk");
  });
});

describe("kopTekst (SPEC 3.1 en 3.2)", () => {
  it("toont de tekst die de server meestuurt (NIEUW GEDRAG)", () => {
    const toestand = {
      alarms: [{ id: "a" }],
      next_fire: { at: "2026-08-12T06:45:00+02:00", text: "Morgen 06:45" },
    };
    assert.equal(kopTekst(toestand), "Morgen 06:45");
  });

  it("REKENT de tekst niet zelf uit (NIEUW GEDRAG)", () => {
    // De belangrijkste eigenschap van deze functie, en de reden dat hij zo saai is.
    // `at` en `text` spreken elkaar hier tegen; de kaart hoort `text` te tonen en
    // niet uit `at` iets anders af te leiden (SPEC 3.3). Een implementatie die zelf
    // rekent, valt hier door de mand.
    const toestand = {
      alarms: [{ id: "a" }],
      next_fire: { at: "2026-08-12T06:45:00+02:00", text: "Over drie kwartier" },
    };
    assert.equal(kopTekst(toestand), "Over drie kwartier");
  });

  it("zegt 'geen wekkers ingesteld' als de lijst leeg is (NIEUW GEDRAG)", () => {
    assert.equal(kopTekst({ alarms: [], next_fire: null }), TEKST_GEEN_WEKKERS);
  });

  it("onderscheidt 'geen wekkers' van 'geen wekker actief' (NIEUW GEDRAG)", () => {
    // Twee verschillende dingen, en vóór fase 6b liepen ze door elkaar: een lege
    // lijst kreeg dezelfde regel als een lijst waarin alles uit staat. De eerste
    // vraagt "maak er een", de tweede "zet er een aan".
    assert.equal(kopTekst({ alarms: [], next_fire: null }), TEKST_GEEN_WEKKERS);
    assert.equal(
      kopTekst({ alarms: [{ id: "a", enabled: false }], next_fire: null }),
      TEKST_GEEN_WEKKER_ACTIEF,
    );
  });

  it("valt terug op 'geen wekker actief' bij een lege of rare tekst (NIEUW GEDRAG)", () => {
    const wekkers = [{ id: "a" }];
    assert.equal(kopTekst({ alarms: wekkers, next_fire: { text: "   " } }), TEKST_GEEN_WEKKER_ACTIEF);
    assert.equal(kopTekst({ alarms: wekkers, next_fire: { text: 42 } }), TEKST_GEEN_WEKKER_ACTIEF);
    assert.equal(kopTekst({ alarms: wekkers }), TEKST_GEEN_WEKKER_ACTIEF);
  });

  it("valt niet om op een ontbrekende of kapotte toestand (NIEUW GEDRAG)", () => {
    // De kaart tekent de kopbalk vóór het eerste antwoord binnen is, en `alarms`
    // hoeft dan nog geen lijst te zijn. Gooien zou de hele kaart leeg laten.
    assert.equal(kopTekst(undefined), TEKST_GEEN_WEKKERS);
    assert.equal(kopTekst({}), TEKST_GEEN_WEKKERS);
    assert.equal(kopTekst({ alarms: "twee" }), TEKST_GEEN_WEKKERS);
  });
});
