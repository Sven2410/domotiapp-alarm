/**
 * De regels van de editor, zonder DOM (SPEC 5, 7.4, 8 en 14.3).
 *
 * Puur: geen lit, geen `hass`, geen klok anders dan wat je meegeeft. Alles wat
 * hier staat is in een gewone Node-test te toetsen — het criterium uit
 * CLAUDE.md. Wat er dan getekend wordt staat in `src/editor.js`.
 *
 * De duurste les uit DomotiApp Scene woont in dit bestand: **toon nooit een
 * terugvalwaarde die je niet zou opslaan** (SPEC 5.5, 19.1). Daarom is er één
 * functie die het concept maakt — met de standaarden uit SPEC 14.3 erin — en
 * één functie die het concept naar een `alarms/save`-payload vertaalt. Wat de
 * editor toont is wat er in het concept staat, en wat er in het concept staat
 * gaat één op één de opslag in.
 */

/** De standaarden voor een nieuwe wekker (SPEC 14.3). */
export const STANDAARD_TIJD = "07:00";
export const STANDAARD_VOLUME_PCT = 40;
export const STANDAARD_HELDERHEID_PCT = 60;

/** Wat een `sound`-object mag bevatten (SPEC 8.2). */
const GELUIDVELDEN = ["uri", "name", "media_type", "image"];

export const TEKST_ZOMERTIJD =
  "Let op: deze tijd bestaat twee nachten per jaar niet, of twee keer. " +
  "Bij de overgang naar zomertijd wordt het uur van 02:00 tot 03:00 overgeslagen; " +
  "die nacht gaat deze wekker niet af. Bij de overgang naar wintertijd komt dat uur " +
  "twee keer voorbij; die nacht gaat hij twee keer af. Kies een tijd vóór 02:00 of " +
  "ná 03:00 als dat een probleem is.";

export const TEKST_EINDIGE_DUUR =
  "Dit geluid stopt van zichzelf. Een los nummer is na een paar minuten voorbij; " +
  "daarna is het stil. Kies een afspeellijst of een radiostation als de wekker moet " +
  "blijven spelen tot je hem uitzet.";

export const TEKST_ZOEKEN_TRAAG = "Zoeken duurt te lang. Probeer het opnieuw.";

export const LABEL_SPEAKER = "Music Assistant Wekker";
export const LABEL_LAMP = "Verlichting Wekker";

/**
 * Een leeg concept voor een nieuwe wekker (SPEC 14.3).
 *
 * `name`, `sound` en `speaker` hebben **geen** standaard: ze zijn verplicht en
 * de gebruiker moet ze kiezen. Ze staan hier leeg en niet op een gok — een
 * voorgevulde speaker zou een keuze zijn die de klant niet heeft gemaakt en die
 * bij Opslaan wél wordt vastgelegd.
 */
export function nieuwConcept() {
  return {
    id: null,
    name: "",
    time: STANDAARD_TIJD,
    days: [],
    enabled: true,
    sound: null,
    // Of het gekozen geluid eindeloos doorspeelt (SPEC 15.6). `null` = onbekend,
    // en dat is de toestand tot er iets gekozen is. Dit veld gaat **niet** de
    // opslag in: het is een eigenschap van de provider, niet van de keuze, en
    // `sound` mag maar vier velden hebben (SPEC 8.2).
    endless: null,
    speaker: "",
    volume_pct: STANDAARD_VOLUME_PCT,
    light: null,
  };
}

/**
 * Een concept uit een bestaande wekker (SPEC 5.5).
 *
 * Alleen de velden die de gebruiker beheert. `skip_next`, `one_shot_at`,
 * `last_fired` en `last_message` blijven bij de server; ze meenemen zou
 * `alarms/save` een `invalid_format` opleveren (SPEC 15.2).
 */
export function conceptVan(wekker) {
  const basis = nieuwConcept();
  if (!wekker || typeof wekker !== "object") {
    return basis;
  }
  return {
    id: typeof wekker.id === "string" ? wekker.id : null,
    name: typeof wekker.name === "string" ? wekker.name : "",
    time: geldigeTijd(wekker.time) ? wekker.time : basis.time,
    days: Array.isArray(wekker.days) ? [...wekker.days] : [],
    enabled: wekker.enabled !== false,
    sound: kleedGeluidUit(wekker.sound),
    // Onbekend, en dat blijft het: de opslag draagt `endless` niet en de kaart
    // rekent het niet zelf uit. Er komt dus geen waarschuwing over een geluid dat
    // al gekozen wás — die hoort bij het kiezen (SPEC 8.3.1).
    endless: null,
    speaker: typeof wekker.speaker === "string" ? wekker.speaker : "",
    volume_pct: Number.isInteger(wekker.volume_pct) ? wekker.volume_pct : basis.volume_pct,
    light:
      wekker.light && typeof wekker.light === "object"
        ? {
            entity_id: wekker.light.entity_id,
            brightness_pct: Number.isInteger(wekker.light.brightness_pct)
              ? wekker.light.brightness_pct
              : STANDAARD_HELDERHEID_PCT,
          }
        : null,
  };
}

/**
 * Kleed een zoekresultaat uit tot wat de opslag accepteert (SPEC 8.2).
 *
 * `sound/search` geeft **meer** velden terug dan `alarms/save` toestaat: een
 * treffer draagt `album` en `artists`, en die letterlijk doorgeven levert
 * `invalid_format — onbekende velden` op. Dat is CLAUDE.md valkuil 39, gevonden
 * in fase 3c, en dit is de plek die hem afvangt.
 *
 * Het omgekeerde geldt ook: wat hier uitkomt is precies wat de rij op de kaart
 * en elke melding later nodig hebben (SPEC 8.2).
 */
export function kleedGeluidUit(treffer) {
  if (!treffer || typeof treffer !== "object" || Array.isArray(treffer)) {
    return null;
  }
  if (typeof treffer.uri !== "string" || !treffer.uri) {
    return null;
  }
  const uit = {};
  for (const veld of GELUIDVELDEN) {
    uit[veld] = treffer[veld] === undefined ? null : treffer[veld];
  }
  return uit;
}

/** `"06:45"` is geldig; `"6:45"`, `"06:45:00"` en `"24:00"` niet (SPEC 14.2). */
export function geldigeTijd(tijd) {
  if (typeof tijd !== "string" || tijd.length !== 5 || tijd[2] !== ":") {
    return false;
  }
  const uur = Number(tijd.slice(0, 2));
  const minuut = Number(tijd.slice(3));
  if (!/^\d\d$/.test(tijd.slice(0, 2)) || !/^\d\d$/.test(tijd.slice(3))) {
    return false;
  }
  return uur >= 0 && uur <= 23 && minuut >= 0 && minuut <= 59;
}

/**
 * Mag dit concept opgeslagen worden, en zo nee wat ontbreekt er (SPEC 5.1)?
 *
 * Speaker en geluid zijn **verplicht**: er is geen wekker zonder geluid. De naam
 * ook, want die staat in de stopknop en moet dan iets zeggen.
 *
 * De naam wordt met `trim()` beoordeeld maar **niet** getrimd opgeslagen door
 * deze functie — trimmen gebeurt bij het opslaan (`naarAlarm`), niet bij het
 * typen. Dat is CLAUDE.md valkuil 14: `.trim()` in een controlled input eet de
 * spatie op, en dan kan de klant geen "Wekker van Sven" typen.
 */
export function magOpslaan(concept) {
  const ontbreekt = [];
  if (!concept || typeof concept !== "object") {
    return { ok: false, ontbreekt: ["alles"] };
  }
  if (typeof concept.name !== "string" || !concept.name.trim()) {
    ontbreekt.push("een naam");
  }
  if (!geldigeTijd(concept.time)) {
    ontbreekt.push("een geldige tijd");
  }
  if (!concept.speaker) {
    ontbreekt.push("een speaker");
  }
  if (!concept.sound || !concept.sound.uri) {
    ontbreekt.push("een geluid");
  }
  if (!Number.isInteger(concept.volume_pct) || concept.volume_pct < 1 || concept.volume_pct > 100) {
    ontbreekt.push("een volume tussen 1 en 100");
  }
  return { ok: ontbreekt.length === 0, ontbreekt };
}

/**
 * Het concept naar een `alarms/save`-payload (SPEC 15.2).
 *
 * Drie dingen gebeuren hier en nergens anders:
 *
 * 1. **`id` valt weg als hij er niet is.** Ontbreekt `id`, dan is het een
 *    nieuwe wekker en genereert de server er een.
 * 2. **De naam wordt getrimd**, bij het opslaan en niet bij het typen
 *    (valkuil 14).
 * 3. **Het geluid wordt uitgekleed** (valkuil 39).
 */
export function naarAlarm(concept) {
  const alarm = {
    name: (concept.name || "").trim(),
    time: concept.time,
    days: [...new Set(concept.days || [])].sort((a, b) => a - b),
    enabled: concept.enabled !== false,
    sound: kleedGeluidUit(concept.sound),
    speaker: concept.speaker,
    volume_pct: concept.volume_pct,
    light: concept.light
      ? {
          entity_id: concept.light.entity_id,
          brightness_pct: concept.light.brightness_pct,
        }
      : null,
  };
  if (concept.id) {
    alarm.id = concept.id;
  }
  // Hier stond een lus die alles wat geen gebruikersveld is uit `alarm` haalde.
  // Die is weg: `alarm` wordt hierboven als **letterlijk object** opgebouwd uit
  // precies de negen velden van `GEBRUIKERSVELDEN`, dus er is geen invoer
  // waarbij die lus iets verwijdert. Nagerekend in de mutatie-oefening van fase
  // 4b (E19): het weghalen liet geen enkele test falen, en dat kwam niet door
  // een testgat maar doordat de regel onbereikbaar was (CLAUDE.md valkuil 34,
  // derde rij). De eigenschap zelf — er gaat nooit een serverveld mee — wordt
  // wél getoetst, en wordt bewaakt door de opbouw hierboven.
  return alarm;
}

/** Dag aan- of uitvinken (SPEC 5.1). Geen dag aangevinkt = eenmalig. */
export function wisselDag(dagen, dag) {
  const set = new Set(dagen || []);
  if (set.has(dag)) {
    set.delete(dag);
  } else {
    set.add(dag);
  }
  return [...set].sort((a, b) => a - b);
}

/**
 * De zomertijdwaarschuwing (SPEC 5.3). `null` als er niets te waarschuwen valt.
 *
 * **Niet blokkerend** — de tijd mag gekozen worden. Gemeten in fase 0: een
 * wekker tussen 02:00 en 02:59 gaat op de overgangsnacht in het voorjaar níét af
 * en in het najaar twee keer.
 */
export function zomertijdWaarschuwing(tijd) {
  if (!geldigeTijd(tijd)) {
    return null;
  }
  return tijd.slice(0, 2) === "02" ? TEKST_ZOMERTIJD : null;
}

/**
 * De waarschuwing bij een geluid dat uit zichzelf ophoudt (SPEC 8.3). `null` als
 * er niets te waarschuwen valt.
 *
 * **De kaart beslist hier niets.** `sound/search` geeft per treffer een veld
 * `endless` terug dat zegt of het geluid eindeloos doorspeelt (SPEC 15.6). Die
 * vraag hangt af van `SIMILAR_TRACKS_PROVIDERS`, en die lijst staat server-side
 * in `const.py` omdat het afvuren hem gebruikt om te beslissen of `radio_mode`
 * meegaat. Hem hier nóg een keer neerzetten zou betekenen dat de editor "dit
 * speelt door" kan beloven terwijl het afvuren `radio_mode` weglaat.
 *
 * Tot fase 4c waarschuwde deze functie op `media_type` alleen, en dus ook bij een
 * los nummer van een streamingprovider — waar `radio_mode` het juist eindeloos
 * maakt. Dat is een waarschuwing die soms onwaar is, en dat is precies het soort
 * dat mensen leren negeren.
 *
 * **`undefined` betekent onbekend en geeft géén waarschuwing.** Dat is de
 * toestand bij een wekker die uit de opslag komt: het opgeslagen `sound`-object
 * heeft vier velden (SPEC 8.2) en `endless` hoort daar niet bij, want het is een
 * eigenschap van de provider en niet van de keuze. De waarschuwing hoort bij het
 * **kiezen** van een geluid, en daar is het veld er wel.
 */
export function eindigeDuurWaarschuwing(endless) {
  return endless === false ? TEKST_EINDIGE_DUUR : null;
}

/**
 * Het `endless`-veld uit een zoektreffer halen (SPEC 15.6).
 *
 * Alleen een **echte boolean** telt; al het andere wordt `null`, oftewel
 * onbekend. Dat is geen achterdocht jegens de eigen server maar de regel uit
 * SPEC 19.1 in het klein: een waarde die niet klopt is geen waarde, en de
 * uitkomst van "onbekend" (zwijgen) is hier veiliger dan die van een gok.
 *
 * Deze functie staat hier en niet in `editor.js` omdat ze aan het criterium uit
 * CLAUDE.md voldoet: het is gedrag dat in een gewone Node-test op te schrijven
 * is. De mutatie-oefening van fase 4c wees dat aan — zolang dit in de
 * renderlaag stond, ving geen enkele unittest een wijziging eraan.
 */
export function endlessVan(treffer) {
  return typeof treffer?.endless === "boolean" ? treffer.endless : null;
}

/**
 * Wat de editor toont als er geen bruikbare entiteiten zijn (SPEC 7.4).
 *
 * @param {{label_exists: boolean, entities: Array, filtered_out: number}} selectie
 *   uit `entities/list`
 * @param {"speaker"|"lamp"} soort
 * @returns {string|null} de melding, of `null` als er gewoon te kiezen valt
 *
 * **De drie gevallen van SPEC 7.4 zijn sinds fase 4c alle drie te onderscheiden**,
 * dankzij `filtered_out` in het antwoord van `entities/list` (SPEC 15.7):
 *
 * | `label_exists` | `entities` | `filtered_out` | melding |
 * |---|---|---|---|
 * | `false` | leeg | 0 | het label bestaat nog niet |
 * | `true` | leeg | 0 | er hangt niets aan het label |
 * | `true` | leeg | > 0 | er hing wel iets aan, maar het viel af |
 *
 * Waarom dat verschil er toe doet: de tweede zegt tegen de eigenaar *"zet het
 * label op je speakers"* en de derde *"die speakers zijn geen Music
 * Assistant-speakers"*. Tot fase 4c toonde de kaart één tekst die beide dekte,
 * en dat is één zin die je twee keer moet lezen om te weten wat je moet doen.
 *
 * In alle gevallen is de melding **geen foutkleur**: dit is een installatiestap
 * die nog moet gebeuren, geen storing.
 */
export function labelMelding(selectie, soort) {
  const lamp = soort === "lamp";
  const label = lamp ? LABEL_LAMP : LABEL_SPEAKER;
  const meervoud = lamp ? "lampen" : "speakers";
  if (!selectie || typeof selectie !== "object") {
    return `De lijst met ${meervoud} is niet op te halen.`;
  }
  if (selectie.label_exists === false) {
    return (
      `Het label '${label}' bestaat nog niet. De beheerder moet dat label aanmaken ` +
      `en op de ${meervoud} zetten die als wekker mogen dienen.`
    );
  }
  if (Array.isArray(selectie.entities) && selectie.entities.length > 0) {
    return null;
  }
  if (Number(selectie.filtered_out) > 0) {
    return lamp
      ? `De entiteiten met het label '${label}' zijn geen lampen.`
      : "De gelabelde speakers zijn geen Music Assistant-speakers, of ze kunnen " +
          "geen volume instellen.";
  }
  return `Er zijn nog geen ${meervoud} met het label '${label}'.`;
}

/**
 * Mag er opgeslagen worden gezien de beschikbare entiteiten (SPEC 7.4)?
 *
 * Speaker en geluid zijn verplicht, dus **zonder bruikbare speakers is Opslaan
 * uitgeschakeld**. De plusknop blijft wél werken: de gebruiker mag de editor
 * openen en zien waarom het niet gaat.
 *
 * De lamp is optioneel en blokkeert dus niets.
 */
export function opslaanKan(concept, speakerselectie) {
  if (labelMelding(speakerselectie, "speaker") !== null) {
    return false;
  }
  return magOpslaan(concept).ok;
}
