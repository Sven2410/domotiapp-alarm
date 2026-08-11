/**
 * Wat er in een rij komt te staan, en of de kaart een stopknop is.
 *
 * Deze module is **puur**: geen DOM, geen lit, geen `hass`, geen klok anders dan
 * wat je meegeeft. Daardoor is hij in een gewone Node-test te toetsen zonder
 * jsdom — het criterium uit CLAUDE.md: *kan ik dit gedrag in een gewone
 * Node-test opschrijven?* Alles hieronder kan dat, dus het hoort hier en niet in
 * de renderfunctie.
 *
 * **Wat hier NIET in zit, en waarom.** De regel "eerstvolgende wekker" wordt
 * server-side berekend en komt kant-en-klaar mee in `next_fire.text`
 * (SPEC 3.3). De kaart mag die planningslogica niet dupliceren: twee
 * implementaties lopen uiteen, en dat is de fout die DomotiApp Scene met de
 * helderheidsschaal maakte. Om dezelfde reden **sorteert de kaart niet zelf**:
 * `alarms/get` levert de lijst al gesorteerd volgens SPEC 3.4.
 */

/** Nederlandse dagafkortingen, ISO-volgorde: 1 = maandag. */
const DAGEN_KORT = ["ma", "di", "wo", "do", "vr", "za", "zo"];

export const TEKST_GEEN_WEKKERS = "Geen wekkers ingesteld";
export const TEKST_EENMALIG = "Eenmalig";
export const TEKST_AFGELOPEN = "Eenmalig — afgelopen";
export const TEKST_OVERGESLAGEN = "Morgen overgeslagen";
export const TEKST_GEEN_WEKKER_ACTIEF = "Geen wekker actief";
export const TEKST_STOPPEN = "Stoppen";

/** Als er wél een melding is maar geen leesbare tekst. Zie `meldingVan`. */
export const TEKST_MELDING_ZONDER_TEKST =
  "Er is een melding over deze wekker, maar de tekst ontbreekt.";

/**
 * `[1,2,3,4,5]` naar `"ma di wo do vr"`; leeg naar `"Eenmalig"` (SPEC 3.2).
 *
 * Spiegelt `dagen_tekst` in `volgende.py`. Dat is bewust géén planningslogica
 * maar een opmaakregel over een lijstje getallen dat de server al heeft
 * gevalideerd; er valt niets uiteen te lopen dat de kaart en de server anders
 * zouden berekenen.
 */
export function dagenTekst(dagen) {
  if (!Array.isArray(dagen) || dagen.length === 0) {
    return TEKST_EENMALIG;
  }
  const uniek = [...new Set(dagen)].sort((a, b) => a - b);
  return uniek.map((d) => DAGEN_KORT[d - 1] ?? "?").join(" ");
}

/**
 * Is dit een eenmalige wekker waarvan het moment voorbij is (SPEC 14.5)?
 *
 * Het criterium is het **moment**, niet `enabled`. Een eenmalige wekker die is
 * afgegaan staat op `enabled: false` met `last_fired` gevuld, maar een die is
 * gemist doordat Home Assistant uit stond staat nog op `enabled: true` — en die
 * is net zo goed afgelopen. Op `enabled` kijken zou de tweede als een wekker
 * tonen die nog gaat komen.
 */
export function isAfgelopen(wekker, nuMs) {
  if (!wekker || (Array.isArray(wekker.days) && wekker.days.length > 0)) {
    return false;
  }
  // Geen aparte NaN-controle. `Date.parse` geeft NaN bij een ontbrekende of
  // onleesbare waarde, en **elke** vergelijking met NaN is `false` — dus
  // `NaN <= nuMs` levert al "niet afgelopen" op. Nagerekend in de
  // mutatie-oefening van fase 4a (J22): het weghalen van die controle liet geen
  // enkele test falen, en er is ook geen invoer te bedenken waarbij hij iets
  // verandert. Een test erbij verzinnen zou dekking suggereren die er niet is
  // (CLAUDE.md valkuil 34, derde rij).
  return Date.parse(wekker?.one_shot_at ?? "") <= nuMs;
}

/**
 * De regel onder de naam: herhaaldagen, "Eenmalig", of een van de twee
 * bijzondere toestanden (SPEC 3.2 en 14.5).
 *
 * De volgorde is vastgelegd door wat waar is en niet door voorkeur:
 * "afgelopen" gaat vóór "overgeslagen", want een wekker waarvan het moment al
 * voorbij is gaat sowieso niet meer af — dan is "Morgen overgeslagen" een
 * belofte over een morgen die niet komt.
 */
export function subtitel(wekker, nuMs) {
  if (isAfgelopen(wekker, nuMs)) {
    return TEKST_AFGELOPEN;
  }
  if (wekker?.skip_next) {
    return TEKST_OVERGESLAGEN;
  }
  return dagenTekst(wekker?.days);
}

/**
 * De melding op de rij, met kleur en toon op `severity` en niet op `kind`
 * (SPEC 11.7).
 *
 * `kind` is machineleesbaar en bedoeld om op te vergelijken; `severity` bepaalt
 * hoe het eruitziet. Een fout vraagt een handeling, een mededeling niet.
 *
 * Een melding zonder bruikbare tekst wordt **niet stil weggelaten**: dan zou een
 * gebeurtenis die de klant moet zien verdwijnen omdat één veld leeg is
 * (SPEC 19.1). Er komt een expliciete regel voor in de plaats.
 *
 * **Iets dat helemaal geen melding-object is, is géén melding.** Dat is een
 * ander geval dan een leeg `text`-veld en het wordt bewust anders behandeld:
 * bij het eerste is er een gebeurtenis met een kapotte tekst, bij het tweede is
 * het veld zelf kapot. Er dan alsnog een regel over tonen zou beweren dat er
 * iets met de wekker gebeurd is, terwijl er alleen iets met de opslag mis is.
 */
export function meldingVan(wekker) {
  const bericht = wekker?.last_message;
  // `typeof [] === "object"` in JavaScript, dus een lijst moet er apart uit.
  if (!bericht || typeof bericht !== "object" || Array.isArray(bericht)) {
    return null;
  }
  const tekst =
    typeof bericht.text === "string" && bericht.text.trim()
      ? bericht.text
      : TEKST_MELDING_ZONDER_TEKST;
  return {
    tekst,
    severity: bericht.severity === "error" ? "error" : "notice",
    isFout: bericht.severity === "error",
    kind: typeof bericht.kind === "string" ? bericht.kind : null,
  };
}

/**
 * Wordt de kaart een stopknop, en wat staat erin (SPEC 4)?
 *
 * `null` betekent: rusttoestand. Anders `{ ids, naam, tijd }`, waarbij `ids`
 * **alle** afgaande wekkers bevat: gaan er twee wekkers van dezelfde persoon
 * tegelijk af, dan is er één stopknop die ze **beide** stopt.
 *
 * **Een afgaand ID zonder bijbehorende wekker blijft meetellen.** Dat kan
 * voorkomen tussen twee aanroepen door — het register is bijgewerkt en de lijst
 * nog niet. De stopknop moet dan blijven werken: hem laten verdwijnen zou
 * betekenen dat de klant het geluid niet uit krijgt tot de stoptimer van 30
 * minuten afloopt (SPEC 9.4), en dat is precies het faalgeval waar deze knop
 * voor bestaat. Er staat dan een neutrale naam in plaats van een verzonnen naam.
 */
export function stopToestand(alarms, ringing) {
  const ids = [...new Set((ringing ?? []).filter((id) => typeof id === "string"))];
  if (ids.length === 0) {
    return null;
  }
  const bekend = ids
    .map((id) => (alarms ?? []).find((w) => w?.id === id))
    .filter(Boolean);

  const namen = bekend.map((w) => w.name).filter(Boolean);
  const tijden = [...new Set(bekend.map((w) => w.time).filter(Boolean))];

  return {
    ids,
    naam: namen.length ? namen.join(" en ") : "Wekker",
    tijd: tijden.join(" en "),
  };
}
