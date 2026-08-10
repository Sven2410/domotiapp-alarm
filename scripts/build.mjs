/**
 * Bundelt src/domotiapp-alarm-card.js naar
 * custom_components/domotiapp_alarm/frontend/domotiapp-alarm-card.js.
 *
 * Twee modi:
 *   node scripts/build.mjs          schrijft de bundel naar schijf
 *   node scripts/build.mjs --check  bouwt in geheugen en faalt als het
 *                                   gecommitte bestand afwijkt (CI)
 *
 * Eén codepad voor beide modi, zodat de vergelijking niet kan afwijken van de
 * build.
 *
 * De uitvoer is reproduceerbaar: geen tijdstempel, geen contenthash, geen
 * bestandsnaam met hash, `legalComments: "none"`. Dezelfde bron plus dezelfde
 * esbuild-versie geven byte-voor-byte hetzelfde bestand — dat is de voorwaarde
 * waarop de CI-job "Bundel komt overeen met de bron" rust.
 *
 * Het versienummer komt uit één bron: `version` in manifest.json, via
 * `define`. Een versieverhoging verandert dus de bytes van de bundel, ook als
 * er in src/ niets is gewijzigd. `npm run build` mag daarom nooit wegvallen
 * tussen het versienummer en de commit; zie CLAUDE.md, Releaseprocedure.
 */
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { build } from "esbuild";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const ENTRY = join(ROOT, "src", "domotiapp-alarm-card.js");
const MANIFEST = join(
  ROOT,
  "custom_components",
  "domotiapp_alarm",
  "manifest.json",
);
const OUTFILE = join(
  ROOT,
  "custom_components",
  "domotiapp_alarm",
  "frontend",
  "domotiapp-alarm-card.js",
);

const checkOnly = process.argv.includes("--check");

const manifest = JSON.parse(await readFile(MANIFEST, "utf8"));
const version = manifest.version;
if (typeof version !== "string" || version === "") {
  throw new Error(`Geen bruikbare "version" in ${MANIFEST}`);
}

const result = await build({
  entryPoints: [ENTRY],
  bundle: true,
  format: "esm",
  target: "es2021",
  minify: true,
  legalComments: "none",
  sourcemap: false,
  write: false,
  define: {
    // Enige bron van het versienummer: manifest.json.
    __CARD_VERSION__: JSON.stringify(version),
  },
  outfile: OUTFILE,
});

const bundel = result.outputFiles[0].contents;
const hash = (buf) => createHash("sha256").update(buf).digest("hex");

if (!checkOnly) {
  await mkdir(dirname(OUTFILE), { recursive: true });
  await writeFile(OUTFILE, bundel);
  console.log(
    `Gebouwd: ${OUTFILE}\n  versie ${version}\n  ${bundel.length} bytes\n  sha256 ${hash(bundel)}`,
  );
  process.exit(0);
}

let gecommit;
try {
  gecommit = await readFile(OUTFILE);
} catch {
  console.error(
    `FOUT: ${OUTFILE} ontbreekt. De bundel hoort meegecommit te worden.`,
  );
  process.exit(1);
}

if (Buffer.compare(gecommit, Buffer.from(bundel)) !== 0) {
  console.error(
    "FOUT: de gecommitte bundel wijkt af van wat de bron oplevert.\n" +
      `  op schijf : ${gecommit.length} bytes, sha256 ${hash(gecommit)}\n` +
      `  uit bron  : ${bundel.length} bytes, sha256 ${hash(bundel)}\n` +
      "Draai 'npm run build' en commit het resultaat.",
  );
  process.exit(1);
}

console.log(
  `OK: bundel is actueel (versie ${version}, ${bundel.length} bytes, sha256 ${hash(bundel)}).`,
);
