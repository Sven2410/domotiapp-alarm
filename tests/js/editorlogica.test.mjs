/**
 * src/editorlogica.js — de regels van de editor (SPEC 5, 7.4, 8 en 14.3).
 *
 * **NIEUW GEDRAG**, met dezelfde kanttekening als bij de andere JS-tests: het
 * bestand is nieuw, dus op de code van vóór deze ronde faalt alles met
 * `ERR_MODULE_NOT_FOUND`. Wat deze tests waard maakt is dat ze de twee lessen
 * vasthouden die dit project geld hebben gekost:
 *
 * - **valkuil 39** — `sound/search` geeft velden terug die `alarms/save`
 *   weigert. `kleedGeluidUit` is de plek die dat afvangt, en er staat hier een
 *   test op die precies dát controleert in plaats van "er komt een object uit".
 * - **valkuil 14** — `.trim()` in een controlled input eet de spatie op. Er is
 *   dus een test die aantoont dat de naam mét spaties bewerkbaar blijft en pas
 *   bij het opslaan getrimd wordt.
 *
 * Geen jsdom: deze module heeft geen DOM nodig.
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  STANDAARD_TIJD,
  STANDAARD_VOLUME_PCT,
  TEKST_EINDIGE_DUUR,
  TEKST_ZOMERTIJD,
  conceptVan,
  eindigeDuurWaarschuwing,
  endlessVan,
  geldigeTijd,
  kleedGeluidUit,
  labelMelding,
  magOpslaan,
  naarAlarm,
  nieuwConcept,
  opslaanKan,
  wisselDag,
  zomertijdWaarschuwing,
} from "../../src/editorlogica.js";

/** Een treffer zoals `sound/search` hem levert (SPEC 15.6). */
function treffer(velden = {}) {
  return {
    name: "Wake Up Happy",
    uri: "spotify--ZvzrFmgX://playlist/37i9dQZF1DX0UrRvztWcAU",
    media_type: "playlist",
    image: "http://localhost:8095/imageproxy?path=abc",
    artists: [{ name: "Coldplay", image: "x" }],
    album: { name: "Ghost Stories" },
    ...velden,
  };
}

function volledigConcept(velden = {}) {
  return {
    ...nieuwConcept(),
    name: "Werk",
    speaker: "media_player.slaapkamer",
    sound: kleedGeluidUit(treffer()),
    ...velden,
  };
}

const SPEAKERS_OK = {
  label_exists: true,
  entities: [{ entity_id: "media_player.slaapkamer", name: "Slaapkamer" }],
};

describe("nieuwConcept (SPEC 14.3)", () => {
  it("vult de standaarden en laat de verplichte velden leeg (NIEUW GEDRAG)", () => {
    const c = nieuwConcept();
    assert.equal(c.time, STANDAARD_TIJD);
    assert.equal(c.volume_pct, STANDAARD_VOLUME_PCT);
    assert.deepEqual(c.days, []);
    assert.equal(c.enabled, true);
    assert.equal(c.light, null);

    // `name`, `sound` en `speaker` hebben geen standaard: ze zijn verplicht en
    // de gebruiker moet ze kiezen. Een voorgevulde speaker zou een keuze zijn
    // die de klant niet heeft gemaakt en die bij Opslaan wél wordt vastgelegd
    // (SPEC 5.5, 19.1).
    assert.equal(c.name, "");
    assert.equal(c.speaker, "");
    assert.equal(c.sound, null);
  });

  it("levert wat er ook echt opgeslagen wordt (NIEUW GEDRAG)", () => {
    // De duurste les uit DomotiApp Scene: nooit iets tonen wat bij Opslaan
    // nergens terechtkomt. Wat `nieuwConcept` toont, moet `naarAlarm` doorgeven.
    const alarm = naarAlarm(volledigConcept());
    assert.equal(alarm.time, STANDAARD_TIJD);
    assert.equal(alarm.volume_pct, STANDAARD_VOLUME_PCT);
    assert.equal(alarm.light, null);
    assert.deepEqual(alarm.days, []);
  });
});

describe("conceptVan (SPEC 5.5)", () => {
  it("neemt alleen de gebruikersvelden over (NIEUW GEDRAG)", () => {
    // De servervelden meenemen zou `alarms/save` een invalid_format opleveren
    // (SPEC 15.2) — precies de fout die fase 4a's clear_message-test vastlegt.
    const c = conceptVan({
      id: "a1f4",
      name: "Werk",
      time: "06:45",
      days: [1, 2],
      enabled: false,
      sound: treffer(),
      speaker: "media_player.slaapkamer",
      volume_pct: 55,
      light: { entity_id: "light.bed", brightness_pct: 30 },
      skip_next: true,
      one_shot_at: "2026-08-12T05:20:00+02:00",
      last_fired: "2026-08-10T06:45:00+02:00",
      last_message: { kind: "x", severity: "error", text: "y" },
    });
    assert.deepEqual(Object.keys(c).sort(), [
      "days",
      "enabled",
      "endless",
      "id",
      "light",
      "name",
      "sound",
      "speaker",
      "time",
      "volume_pct",
    ]);
    // `endless` is onbekend voor een opgeslagen wekker: de opslag draagt het veld
    // niet (SPEC 8.2) en de kaart rekent het niet zelf uit (SPEC 15.6).
    assert.equal(c.endless, null);
    assert.equal(c.enabled, false);
    assert.equal(c.volume_pct, 55);
    assert.deepEqual(c.light, { entity_id: "light.bed", brightness_pct: 30 });
  });

  it("kleedt het opgeslagen geluid ook uit (NIEUW GEDRAG)", () => {
    // Een wekker die ooit met een te ruim geluid is opgeslagen mag bij het
    // opnieuw opslaan niet alsnog stuklopen.
    const c = conceptVan({ sound: treffer() });
    assert.deepEqual(Object.keys(c.sound).sort(), ["image", "media_type", "name", "uri"]);
  });

  it("laat een wekker zonder enabled-veld AAN staan (NIEUW GEDRAG)", () => {
    // Gevonden met mutatie E15 van fase 4b. `wekker.enabled !== false` en
    // `wekker.enabled === true` zijn gelijk voor elke waarde die de server kan
    // leveren, maar niet voor een ontbrekend veld — en dan is het verschil dat
    // de wekker bij het openen-en-opslaan van de editor **stil uit** zou gaan.
    // Dat is precies het soort stille fout dat dit product niet mag maken
    // (SPEC 19.1), dus de keuze wordt hier vastgelegd.
    assert.equal(conceptVan({}).enabled, true);
    assert.equal(conceptVan({ name: "Werk" }).enabled, true);
    // Positieve controle: een expliciete `false` blijft wél uit.
    assert.equal(conceptVan({ enabled: false }).enabled, false);
    assert.equal(naarAlarm(conceptVan({})).enabled, true);
  });

  it("valt terug op de standaarden bij rommel (NIEUW GEDRAG)", () => {
    const c = conceptVan({ time: "kwart voor zeven", volume_pct: "hard" });
    assert.equal(c.time, STANDAARD_TIJD);
    assert.equal(c.volume_pct, STANDAARD_VOLUME_PCT);
    // En die terugval wordt ook opgeslagen — hij wordt niet alleen getoond.
    assert.equal(naarAlarm(c).time, STANDAARD_TIJD);
  });
});

describe("kleedGeluidUit (SPEC 8.2, valkuil 39)", () => {
  it("houdt precies vier velden over (NIEUW GEDRAG)", () => {
    // Dit is valkuil 39, gevonden in fase 3c: `sound/search` draagt `album` en
    // `artists`, en `alarms/save` weigert die met invalid_format. Zonder deze
    // functie is elke opslag vanuit de editor kapot.
    const uit = kleedGeluidUit(treffer());
    assert.deepEqual(Object.keys(uit).sort(), ["image", "media_type", "name", "uri"]);
    assert.equal("artists" in uit, false);
    assert.equal("album" in uit, false);
    assert.equal(uit.uri, treffer().uri);
  });

  it("maakt ontbrekende velden expliciet null (NIEUW GEDRAG)", () => {
    // `undefined` verdwijnt in JSON; `null` komt door. De opslag eist alle vier
    // de sleutels (SPEC 14.2), dus een treffer zonder afbeelding moet
    // `image: null` opleveren en niet een ontbrekende sleutel.
    const uit = kleedGeluidUit({ uri: "somafm://radio/x", name: "X" });
    assert.deepEqual(uit, {
      uri: "somafm://radio/x",
      name: "X",
      media_type: null,
      image: null,
    });
  });

  it("weigert wat geen geluid is (NIEUW GEDRAG)", () => {
    for (const rommel of [null, undefined, "somafm://x", 42, [], {}, { name: "geen uri" }]) {
      assert.equal(kleedGeluidUit(rommel), null, JSON.stringify(rommel));
    }
  });
});

describe("geldigeTijd (SPEC 14.2)", () => {
  it("accepteert alleen HH:MM (NIEUW GEDRAG)", () => {
    for (const goed of ["00:00", "06:45", "23:59", "02:30"]) {
      assert.equal(geldigeTijd(goed), true, goed);
    }
    for (const fout of ["6:45", "06:45:00", "24:00", "06:60", "0645", "", null, 645, "ab:cd"]) {
      assert.equal(geldigeTijd(fout), false, String(fout));
    }
  });
});

describe("magOpslaan (SPEC 5.1)", () => {
  it("laat een volledig concept door (NIEUW GEDRAG)", () => {
    // De positieve controle: zonder deze zou een implementatie die altijd
    // weigert door alle tests hierna komen.
    assert.deepEqual(magOpslaan(volledigConcept()), { ok: true, ontbreekt: [] });
  });

  it("eist naam, speaker en geluid (NIEUW GEDRAG)", () => {
    // Speaker en geluid zijn verplicht: er is geen wekker zonder geluid. De naam
    // ook, want die staat in de stopknop (SPEC 4) en moet dan iets zeggen.
    assert.equal(magOpslaan(volledigConcept({ name: "   " })).ok, false);
    assert.equal(magOpslaan(volledigConcept({ speaker: "" })).ok, false);
    assert.equal(magOpslaan(volledigConcept({ sound: null })).ok, false);
    assert.match(magOpslaan(volledigConcept({ name: "" })).ontbreekt.join(), /naam/);
  });

  it("eist een geldige tijd en een volume binnen bereik (NIEUW GEDRAG)", () => {
    assert.equal(magOpslaan(volledigConcept({ time: "2:30" })).ok, false);
    assert.equal(magOpslaan(volledigConcept({ volume_pct: 0 })).ok, false);
    assert.equal(magOpslaan(volledigConcept({ volume_pct: 101 })).ok, false);
    // Volume 1 is de ondergrens en hoort te mogen: een wekker op 0 is geen
    // wekker, maar 1 is een keuze (SPEC 14.2).
    assert.equal(magOpslaan(volledigConcept({ volume_pct: 1 })).ok, true);
  });
});

describe("naarAlarm (SPEC 15.2)", () => {
  it("trimt de naam bij het opslaan en niet bij het typen (NIEUW GEDRAG)", () => {
    // CLAUDE.md valkuil 14. Trimmen tijdens het typen eet de spatie op en dan
    // kan de klant geen "Wekker van Sven" intikken. Het concept houdt de spatie;
    // de payload niet.
    const c = volledigConcept({ name: "Wekker van Sven " });
    assert.equal(c.name, "Wekker van Sven ", "het concept houdt de spatie");
    assert.equal(naarAlarm(c).name, "Wekker van Sven");
    // En een naam mét spaties erin blijft heel.
    assert.equal(naarAlarm(volledigConcept({ name: "Trein naar Utrecht" })).name, "Trein naar Utrecht");
  });

  it("laat id weg bij een nieuwe wekker (NIEUW GEDRAG)", () => {
    // Ontbreekt `id`, dan is het een nieuwe wekker en genereert de server er een
    // (SPEC 15.2). Een `id: null` meesturen zou invalid_format geven.
    assert.equal("id" in naarAlarm(volledigConcept({ id: null })), false);
    assert.equal(naarAlarm(volledigConcept({ id: "a1f4" })).id, "a1f4");
  });

  it("stuurt `endless` nooit mee naar de opslag (NIEUW GEDRAG)", () => {
    // `endless` komt uit `sound/search` (SPEC 15.6) en hoort niet in het
    // `sound`-object van de opslag, dat vier velden kent (SPEC 8.2). Zou het
    // meegaan, dan weigert `alarms/save` de hele wekker met `invalid_format` —
    // dezelfde valkuil 39 als met `album` en `artists`.
    const alarm = naarAlarm({ ...volledigConcept(), endless: true });
    assert.equal("endless" in alarm, false);
    assert.equal("endless" in alarm.sound, false);
    assert.deepEqual(Object.keys(alarm.sound).sort(), ["image", "media_type", "name", "uri"]);
  });

  it("stuurt nooit een serverveld mee (NIEUW GEDRAG)", () => {
    const alarm = naarAlarm({
      ...volledigConcept(),
      skip_next: true,
      last_fired: "2026-08-10T06:45:00+02:00",
      last_message: { kind: "x" },
      one_shot_at: "2026-08-12T05:20:00+02:00",
    });
    for (const verboden of ["skip_next", "last_fired", "last_message", "one_shot_at"]) {
      assert.equal(verboden in alarm, false, verboden);
    }
  });

  it("kleedt het geluid uit en ontdubbelt de dagen (NIEUW GEDRAG)", () => {
    const alarm = naarAlarm(volledigConcept({ days: [5, 1, 1, 3] }));
    assert.deepEqual(alarm.days, [1, 3, 5]);
    assert.deepEqual(Object.keys(alarm.sound).sort(), ["image", "media_type", "name", "uri"]);
  });
});

describe("wisselDag (SPEC 5.1)", () => {
  it("vinkt aan en uit en houdt de volgorde (NIEUW GEDRAG)", () => {
    assert.deepEqual(wisselDag([], 3), [3]);
    assert.deepEqual(wisselDag([3], 1), [1, 3]);
    assert.deepEqual(wisselDag([1, 3], 3), [1]);
    assert.deepEqual(wisselDag([1], 1), [], "leeg is eenmalig, geen fout");
  });
});

describe("zomertijdWaarschuwing (SPEC 5.3)", () => {
  it("waarschuwt alleen tussen 02:00 en 02:59 (NIEUW GEDRAG)", () => {
    assert.equal(zomertijdWaarschuwing("02:00"), TEKST_ZOMERTIJD);
    assert.equal(zomertijdWaarschuwing("02:30"), TEKST_ZOMERTIJD);
    assert.equal(zomertijdWaarschuwing("02:59"), TEKST_ZOMERTIJD);
    // De randen: 01:59 en 03:00 zijn gewone tijden. Gemeten in fase 0 gaat het
    // precies om het uur dat bij de overgang wordt overgeslagen of verdubbeld.
    assert.equal(zomertijdWaarschuwing("01:59"), null);
    assert.equal(zomertijdWaarschuwing("03:00"), null);
    assert.equal(zomertijdWaarschuwing("06:45"), null);
  });

  it("waarschuwt niet over een tijd die geen tijd is (NIEUW GEDRAG)", () => {
    assert.equal(zomertijdWaarschuwing("2:30"), null);
    assert.equal(zomertijdWaarschuwing(null), null);
  });
});

describe("eindigeDuurWaarschuwing (SPEC 8.3 en 15.6)", () => {
  it("waarschuwt als de server zegt dat het geluid ophoudt (NIEUW GEDRAG)", () => {
    assert.equal(eindigeDuurWaarschuwing(false), TEKST_EINDIGE_DUUR);
  });

  it("waarschuwt NIET als het geluid eindeloos doorspeelt (NIEUW GEDRAG)", () => {
    // Dit is het gat dat fase 4c dicht. Tot dan waarschuwde de kaart op
    // `media_type` alleen, en dus ook bij een los nummer van een provider mét
    // SIMILAR_TRACKS — waar `radio_mode` het juist eindeloos maakt. Een
    // waarschuwing die soms onwaar is, is er een die mensen leren negeren.
    assert.equal(eindigeDuurWaarschuwing(true), null);
  });

  it("waarschuwt niet bij onbekend (NIEUW GEDRAG)", () => {
    // De toestand bij een wekker die uit de opslag komt: `endless` staat er niet
    // in, dus er valt niets te beweren. Zwijgen is dan juist — de waarschuwing
    // hoort bij het kiezen van een geluid (SPEC 8.3.1).
    assert.equal(eindigeDuurWaarschuwing(null), null);
    assert.equal(eindigeDuurWaarschuwing(undefined), null);
  });

  it("interpreteert niets zelf (NIEUW GEDRAG)", () => {
    // De kaart mag niet op `media_type` of op de URI gaan rekenen: dan bestaat
    // SIMILAR_TRACKS_PROVIDERS twee keer en kan de editor "dit speelt door"
    // beloven terwijl het afvuren `radio_mode` weglaat. Alleen de boolean telt.
    assert.equal(eindigeDuurWaarschuwing("false"), null);
    assert.equal(eindigeDuurWaarschuwing(0), null);
    assert.equal(eindigeDuurWaarschuwing({ media_type: "track" }), null);
  });
});

describe("endlessVan (SPEC 15.6)", () => {
  it("neemt de boolean over zoals de server hem gaf (NIEUW GEDRAG)", () => {
    assert.equal(endlessVan({ endless: true }), true);
    assert.equal(endlessVan({ endless: false }), false);
  });

  it("maakt van alles wat geen boolean is onbekend (NIEUW GEDRAG)", () => {
    // SPEC 19.1 in het klein: een waarde die niet klopt is geen waarde. En
    // "onbekend" zwijgt, wat hier veiliger is dan gokken.
    for (const rommel of [undefined, null, "true", "false", 0, 1, {}, []]) {
      assert.equal(endlessVan({ endless: rommel }), null, JSON.stringify(rommel));
    }
    assert.equal(endlessVan(undefined), null);
    assert.equal(endlessVan(null), null);
    assert.equal(endlessVan({}), null);
  });

  it("werkt samen met de waarschuwing (NIEUW GEDRAG)", () => {
    // De keten die de editor doorloopt: treffer -> endlessVan -> waarschuwing.
    assert.equal(eindigeDuurWaarschuwing(endlessVan({ endless: false })), TEKST_EINDIGE_DUUR);
    assert.equal(eindigeDuurWaarschuwing(endlessVan({ endless: true })), null);
    assert.equal(eindigeDuurWaarschuwing(endlessVan({})), null);
  });
});

describe("labelMelding (SPEC 7.4)", () => {
  it("zegt niets als er gewoon te kiezen valt (NIEUW GEDRAG)", () => {
    assert.equal(labelMelding(SPEAKERS_OK, "speaker"), null);
  });

  it("onderscheidt de drie situaties uit SPEC 7.4 (NIEUW GEDRAG)", () => {
    // Sinds fase 4c zijn het er drie in plaats van twee. Het onderscheid tussen
    // de laatste twee is voor de eigenaar het verschil tussen "zet het label op
    // je speakers" en "die speakers zijn geen Music Assistant-speakers".
    const geenLabel = labelMelding({ label_exists: false, entities: [], filtered_out: 0 }, "speaker");
    const leegLabel = labelMelding({ label_exists: true, entities: [], filtered_out: 0 }, "speaker");
    const afgevallen = labelMelding({ label_exists: true, entities: [], filtered_out: 2 }, "speaker");

    assert.match(geenLabel, /bestaat nog niet/);
    assert.match(geenLabel, /Music Assistant Wekker/);
    assert.match(leegLabel, /nog geen speakers met het label/);
    assert.match(afgevallen, /geen Music Assistant-speakers/);

    // Alle drie verschillend — dat is de eis, en zonder deze assertie zou één
    // tekst voor twee gevallen er doorheen komen.
    assert.equal(new Set([geenLabel, leegLabel, afgevallen]).size, 3);
  });

  it("noemt het juiste label per soort (NIEUW GEDRAG)", () => {
    assert.match(
      labelMelding({ label_exists: false, entities: [], filtered_out: 0 }, "lamp"),
      /Verlichting Wekker/,
    );
    assert.match(labelMelding({ label_exists: true, entities: [], filtered_out: 0 }, "lamp"), /lampen/);
  });

  it("onderscheidt de drie situaties ook bij de lampen (NIEUW GEDRAG)", () => {
    // De wake-up light is optioneel en blokkeert niets, maar de eigenaar die zijn
    // label op de verkeerde entiteit plakt verdient dezelfde uitleg.
    const leeg = labelMelding({ label_exists: true, entities: [], filtered_out: 0 }, "lamp");
    const afgevallen = labelMelding({ label_exists: true, entities: [], filtered_out: 1 }, "lamp");
    assert.match(leeg, /nog geen lampen/);
    assert.match(afgevallen, /zijn geen lampen/);
    assert.notEqual(leeg, afgevallen);
  });

  it("zwijgt zodra er iets te kiezen valt, ook als er iets afviel (NIEUW GEDRAG)", () => {
    // De positieve controle onder alle bovenstaande: `filtered_out > 0` is geen
    // melding waard zolang er een bruikbare speaker overblijft.
    assert.equal(
      labelMelding({ label_exists: true, entities: [{ entity_id: "x" }], filtered_out: 3 }, "speaker"),
      null,
    );
  });

  it("verzwijgt een ontbrekend antwoord niet (NIEUW GEDRAG)", () => {
    assert.match(labelMelding(null, "speaker"), /niet op te halen/);
  });
});

describe("opslaanKan (SPEC 7.4)", () => {
  it("staat opslaan toe als alles er is (NIEUW GEDRAG)", () => {
    assert.equal(opslaanKan(volledigConcept(), SPEAKERS_OK), true);
  });

  it("blokkeert opslaan zonder bruikbare speakers (NIEUW GEDRAG)", () => {
    // Speaker en geluid zijn verplicht, dus zonder speakers kan er geen wekker
    // opgeslagen worden. De plusknop blijft wél werken — de gebruiker mag zien
    // waarom het niet gaat. Dat laatste zit in de editor zelf.
    assert.equal(opslaanKan(volledigConcept(), { label_exists: false, entities: [] }), false);
    assert.equal(opslaanKan(volledigConcept(), { label_exists: true, entities: [] }), false);
  });

  it("blokkeert opslaan bij een onvolledig concept (NIEUW GEDRAG)", () => {
    assert.equal(opslaanKan(volledigConcept({ name: "" }), SPEAKERS_OK), false);
  });
});
