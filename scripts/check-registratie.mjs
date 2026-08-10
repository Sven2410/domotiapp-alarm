/**
 * Bewaakt de registratieregel (CLAUDE.md, valkuil 1).
 *
 * De regressie die dit vangt: registreren op modulescope, vóórdat HA's
 * frontend zijn scoped-custom-element-registry heeft geïnstalleerd. De
 * definitie landt dan in de native registry en is daarna onzichtbaar voor HA —
 * zonder fout, zonder log, met alleen "Configuratiefout" op elke kaart en een
 * kaartkiezer die eindeloos blijft laden. Zie src/registreer.js.
 *
 * Twee controles:
 *
 * 1. In `src/` roept alléén `registreer.js` `customElements.define` aan. Ieder
 *    ander bestand dat dat doet, omzeilt de wachtlus.
 * 2. De gebouwde bundel bevat de markernaam waarop gewacht wordt. Zou de
 *    wachtlus wegvallen of wegoptimaliseerd worden, dan verdwijnt die string.
 *
 * De eerste controle staat op de bron en niet op de geminificeerde uitvoer,
 * omdat je daar een gate niet betrouwbaar uit kunt aflezen.
 */
import { readFile, readdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "src");
const BUNDEL = join(
  ROOT,
  "custom_components",
  "domotiapp_alarm",
  "frontend",
  "domotiapp-alarm-card.js",
);

const TOEGESTAAN_IN = "registreer.js";
const MARKER = "home-assistant";

const fouten = [];

const bestanden = (await readdir(SRC)).filter((naam) => naam.endsWith(".js"));
for (const naam of bestanden) {
  const inhoud = await readFile(join(SRC, naam), "utf8");
  if (!inhoud.includes("customElements.define")) {
    continue;
  }
  if (naam !== TOEGESTAAN_IN) {
    fouten.push(
      `src/${naam} roept customElements.define aan. Dat mag alleen in ` +
        `src/${TOEGESTAAN_IN}, anders wordt de wachtlus op HA's registry ` +
        `omzeild en is de kaart onzichtbaar voor Home Assistant.`,
    );
  }
}

if (!bestanden.includes(TOEGESTAAN_IN)) {
  fouten.push(`src/${TOEGESTAAN_IN} ontbreekt.`);
}

let bundel = "";
try {
  bundel = await readFile(BUNDEL, "utf8");
} catch {
  fouten.push(`${BUNDEL} ontbreekt; draai eerst npm run build.`);
}

if (bundel && !bundel.includes(MARKER)) {
  fouten.push(
    `De gebouwde bundel bevat "${MARKER}" niet. Zonder die marker is er geen ` +
      `wachtlus op HA's custom-element-registry.`,
  );
}

if (fouten.length) {
  console.error("FOUT: de registratieregel wordt niet nageleefd.\n");
  for (const fout of fouten) {
    console.error(`  - ${fout}`);
  }
  process.exit(1);
}

console.log(
  `OK: alleen src/${TOEGESTAAN_IN} registreert, en de bundel wacht op "${MARKER}".`,
);
