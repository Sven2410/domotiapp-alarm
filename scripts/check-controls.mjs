/**
 * Bewaakt dat een native formuliercontrol met `width: 100%` een EIGEN
 * achtergrondkleur houdt (fase 12).
 *
 * ## Waarom dit een script is en geen test
 *
 * Opmaak bestaat pas als een echte browser een echte cascade toepast, en
 * CLAUDE.md verbiedt jsdom. Een unittest kan deze fout dus niet vangen. Wat wél
 * kan is bewaken dat de regel in de bron staat — precies zoals
 * `check-registratie.mjs` de registratieregel bewaakt zonder een browser te
 * starten (valkuil 1). Het is een zwakkere garantie dan een meting, en daarom
 * staat hier ook wat het NIET bewijst: dat de kleuren leesbaar zijn. Dat is in
 * fase 12 in de browser gemeten en staat in docs/fase-12/RAPPORT.md.
 *
 * ## Wat het vangt
 *
 * Fase 10 verhuisde rand en padding van de control naar een wrapper en zette
 * `background: transparent` op de control. Voor een `input` klopt dat. Voor een
 * `select` niet: de browser tekent het UITKLAPPANEEL met de achtergrondkleur van
 * de select zelf, en dat paneel valt buiten onze shadow root. Transparant
 * betekent daar "val terug op wit", en met de lichte tekst van een donker thema
 * werd de lijst onleesbaar. Dat is een release lang onopgemerkt gebleven omdat
 * niemand de dropdown had uitgeklapt.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const WORTEL = join(dirname(fileURLToPath(import.meta.url)), "..");
const EDITOR = join(WORTEL, "src", "editor.js");

const bron = readFileSync(EDITOR, "utf8");
const fouten = [];

// 1. Elke select in de editor hoort in een .vak te staan (de eis van fase 10).
const selects = (bron.match(/<select\b/g) ?? []).length;
const vakken = (bron.match(/class="vak[^"]*"[\s\S]{0,120}?<select\b/g) ?? []).length;
if (selects === 0) {
  fouten.push("geen enkele <select> gevonden — is de editor verbouwd?");
} else if (vakken !== selects) {
  fouten.push(
    `${selects} <select> gevonden maar ${vakken} met een .vak eromheen; ` +
      "een control zonder vak krijgt zijn padding en rand weer zelf (fase 10)",
  );
}

// 2. De select en zijn opties hebben een EIGEN achtergrondkleur, en die is niet
//    transparant. Dit is de regel die in fase 12 is toegevoegd.
const eisen = [
  [/\.vak select\s*\{[^}]*background-color:\s*var\(/, ".vak select mist een eigen background-color"],
  [/\.vak select option\s*\{[^}]*background-color:\s*var\(/, ".vak select option mist een eigen background-color"],
  [/\.vak select option:checked\s*\{[^}]*background-color:/, ".vak select option:checked mist een markering"],
];
for (const [patroon, boodschap] of eisen) {
  if (!patroon.test(bron)) fouten.push(boodschap);
}

// 3. En nergens mag een select transparant gezet worden.
if (/\.vak select[^{]*\{[^}]*background(-color)?:\s*transparent/.test(bron)) {
  fouten.push("een .vak select staat op background transparent — dat is de fout van fase 12");
}

if (fouten.length > 0) {
  console.error("FOUT in de opmaak van de formuliercontrols:");
  for (const f of fouten) console.error(`  - ${f}`);
  process.exit(1);
}

console.log(
  `OK: ${selects} select(s), elk in een .vak, met een eigen achtergrondkleur en een markering.`,
);
