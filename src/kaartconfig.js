/**
 * De kaart-config en de drie gevallen zonder geldige `person` (SPEC 16).
 *
 * Puur: geen DOM, geen `hass`. Wat de kaart moet weten over de config staat hier
 * en is in een gewone Node-test te toetsen; wat er dan getekend wordt staat in
 * de kaart zelf.
 */

export const PERSON_DOMEIN = "person";

/** De drie teksten uit SPEC 16.3 en 19.2, letterlijk. */
export const TEKST_KIES_PERSOON = "Kies een persoon in de kaartinstellingen.";
/**
 * Was: "De gekozen persoon bestaat niet meer." (fase 11, na goedkeuring van de
 * eigenaar).
 *
 * De kaart stelt één ding vast: `hass.states[person]` ontbreekt. Dat kan
 * betekenen dat de persoon verwijderd is, maar net zo goed dat hij **hernoemd**
 * is — SPEC 18.1 zegt zelf dat dat verschil van buiten niet te zien is. "Bestaat
 * niet meer" koos daar één van de twee uit, en bij een hernoeming stuurde het de
 * klant naar het verkeerde scherm: hij gaat een persoon terugzetten die er nog
 * gewoon is, terwijl de oplossing in de kaartinstellingen zit.
 *
 * Dit is hetzelfde patroon als `sound_gone` in fase 6 en de twee teksten van
 * fase 6b: geschreven bij de SPEC-sectie in plaats van bij de regel code die het
 * vaststelt (valkuil 53).
 */
export const TEKST_PERSOON_WEG = "De gekozen persoon is niet gevonden.";
export const TEKST_ONLEESBAAR =
  "De opgeslagen wekkers van deze persoon zijn onleesbaar.";

/**
 * Sleutels die Lovelace zelf aan een kaartconfig hangt. Ze worden **doorgelaten
 * en bewaard** zonder ze te interpreteren (SPEC 16.1) — daarom staan ze hier
 * alleen als documentatie: `valideerConfig` bewaart álles wat het niet kent.
 */
export const LOVELACE_SLEUTELS = Object.freeze([
  "grid_options",
  "layout_options",
  "view_layout",
  "visibility",
]);

/**
 * Valideer de kaartconfig. Geeft de config terug zoals hij bewaard moet worden.
 *
 * **Gooit alleen bij een `person` in het verkeerde domein.** Dat is de enige
 * plek waar de kaart mag gooien (SPEC 16.3), en het is wat Lovelace als
 * "Configuratiefout" toont. Een *ontbrekende* `person` is géén fout: dat is de
 * toestand direct na toevoegen via de kaartkiezer, want `getStubConfig` levert
 * de config bewust zonder persoon.
 *
 * Onbekende sleutels blijven staan. Lovelace hangt er zelf `grid_options` en
 * `visibility` aan; een validatie die die weggooit, verliest de plaatsing van de
 * klant bij de eerstvolgende bewerking.
 */
export function valideerConfig(config) {
  if (!config || typeof config !== "object" || Array.isArray(config)) {
    throw new Error("De kaartconfig ontbreekt of is geen object.");
  }
  const person = config.person;
  if (person === undefined || person === null || person === "") {
    return { ...config };
  }
  if (typeof person !== "string") {
    throw new Error("'person' moet een entity-ID zijn, zoals person.sven.");
  }
  if (!person.startsWith(`${PERSON_DOMEIN}.`)) {
    throw new Error(
      `'${person}' zit niet in het domein ${PERSON_DOMEIN}. ` +
        "Kies een persoon, zoals person.sven.",
    );
  }
  return { ...config };
}

/**
 * `getStubConfig` levert de config **zonder** `person` (SPEC 16.2), zodat de
 * kaart via de kaartkiezer toe te voegen is en de gebruiker de persoon daarna
 * kiest.
 */
export function stubConfig(cardType) {
  return { type: `custom:${cardType}` };
}

/**
 * Waar staat de kaart wat betreft de persoon (SPEC 16.3)?
 *
 * @param {string|undefined} person het entity-ID uit de config
 * @param {boolean} bestaat of de entiteit in `hass.states` voorkomt
 * @returns {{soort: "ok"|"ontbreekt"|"weg", tekst: string|null, isFout: boolean}}
 *
 * Het onderscheid tussen "ontbreekt" en "weg" zit in de **kleur**, en dat is
 * geen detail: het eerste is een installatiestap die nog moet gebeuren en hoort
 * er niet als storing uit te zien; het tweede is er wel een.
 */
export function personToestand(person, bestaat) {
  if (!person) {
    return { soort: "ontbreekt", tekst: TEKST_KIES_PERSOON, isFout: false };
  }
  if (!bestaat) {
    return { soort: "weg", tekst: TEKST_PERSOON_WEG, isFout: true };
  }
  return { soort: "ok", tekst: null, isFout: false };
}

/**
 * De tekst bij een fout uit een WebSocket-commando.
 *
 * `not_found` op een person betekent voor de kaart hetzelfde als een entiteit
 * die niet in `hass.states` staat: de persoon is er niet meer (SPEC 18.1). Het
 * onderscheid tussen hernoemd en verwijderd is van buiten niet te zien, dus de
 * kaart doet ook niet alsof.
 *
 * `home_assistant_error` is de onleesbare opslag uit SPEC 19.2. Dan biedt de
 * kaart **geen** editor aan — die regel staat in de kaart zelf.
 */
export function foutTekst(code, bericht) {
  if (code === "not_found") {
    return TEKST_PERSOON_WEG;
  }
  if (code === "home_assistant_error") {
    return TEKST_ONLEESBAAR;
  }
  return bericht || "Er ging iets mis bij het ophalen van de wekkers.";
}
