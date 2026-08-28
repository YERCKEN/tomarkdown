/**
 * Copia a web/fonts/ solo los woff2 (subset latin) que la interfaz usa.
 *
 * Los paquetes @fontsource traen decenas de subsets y formatos; acá se toman
 * cinco archivos y se versionan, para que la app funcione sin internet y el
 * build de PyInstaller no dependa de Node.
 *
 * Uso: npm run fonts
 */

import { copyFileSync, mkdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const outDir = join(root, 'web', 'fonts');

/** Fuentes usadas por la interfaz: paquete, familia y pesos. */
const FONTS = [
  { pkg: '@fontsource/space-grotesk', family: 'space-grotesk', weights: [500, 700] },
  { pkg: '@fontsource/inter', family: 'inter', weights: [400, 500] },
  { pkg: '@fontsource/jetbrains-mono', family: 'jetbrains-mono', weights: [400] },
];

mkdirSync(outDir, { recursive: true });

let copied = 0;
for (const { pkg, family, weights } of FONTS) {
  for (const weight of weights) {
    const file = `${family}-latin-${weight}-normal.woff2`;
    const from = join(root, 'node_modules', pkg, 'files', file);
    const to = join(outDir, file);

    try {
      statSync(from);
    } catch {
      console.error(`No se encontró ${from}. ¿Corriste npm install?`);
      process.exit(1);
    }

    copyFileSync(from, to);
    copied += 1;
    console.log(`✓ ${file} (${(statSync(to).size / 1024).toFixed(1)} KB)`);
  }
}

console.log(`\n${copied} fuentes copiadas en web/fonts/`);
