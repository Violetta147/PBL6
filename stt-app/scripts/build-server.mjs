import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const STANDALONE = path.join(ROOT, '.next', 'standalone');

const copyTree = (from, to) => {
  fs.cpSync(from, to, { recursive: true });
};

const exists = (p) => fs.existsSync(p);

if (!exists(path.join(STANDALONE, 'server.js'))) {
  console.error('[build-server] .next/standalone/server.js missing — run `next build` first (output: "standalone").');
  process.exit(1);
}

// 1) Copy .next/static -> .next/standalone/.next/static
const staticFrom = path.join(ROOT, '.next', 'static');
const staticTo = path.join(STANDALONE, '.next', 'static');
if (!exists(staticFrom)) {
  console.error('[build-server] .next/static missing — build looks incomplete.');
  process.exit(1);
}
fs.mkdirSync(path.dirname(staticTo), { recursive: true });
copyTree(staticFrom, staticTo);
console.log('[build-server] Copied .next/static -> standalone/.next/static');

// 2) Copy public -> .next/standalone/public (if exists)
const publicFrom = path.join(ROOT, 'public');
if (exists(publicFrom)) {
  copyTree(publicFrom, path.join(STANDALONE, 'public'));
  console.log('[build-server] Copied public/ -> standalone/public');
}

// 3) Clean unwanted bloated payload swept into standalone
for (const extra of ['dist', path.join('node_modules', 'electron')]) {
  const target = path.join(STANDALONE, extra);
  if (exists(target)) {
    fs.rmSync(target, { recursive: true, force: true });
    console.log(`[build-server] Removed build-only payload: ${extra}`);
  }
}

console.log('[build-server] Server payload curated successfully at:', STANDALONE);
