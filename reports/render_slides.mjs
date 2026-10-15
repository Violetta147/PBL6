// Render only presentation assets; never runs ASR or changes saved measurements.
// Install in the ignored directory before running:
// npm install --prefix data/presentation_tools @marp-team/marp-cli@4.5.1 @mermaid-js/mermaid-cli@12.0.0
// Set PUPPETEER_SKIP_DOWNLOAD=true during installation; uses installed Chrome.
// Run from the repository root: node reports/render_slides.mjs
import { spawn } from 'node:child_process';
import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const modules = path.join(root, 'data/presentation_tools/node_modules');
const chrome = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const temporary = path.join(root, 'data/presentation_tools/config');
await access(chrome);
await mkdir(temporary, { recursive: true });
await writeFile(path.join(temporary, 'browser.json'), JSON.stringify({ executablePath: chrome }));
await writeFile(path.join(temporary, 'mermaid.json'), JSON.stringify({
  theme: 'base',
  look: 'classic', htmlLabels: false, markdownAutoWrap: false,
  themeVariables: { fontFamily: 'Arial, sans-serif', fontSize: '26px', lineColor: '#607d91' },
  flowchart: { htmlLabels: false, curve: 'linear', nodeSpacing: 40, rankSpacing: 48, wrappingWidth: 280 },
}));

function run(script, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [script, ...args], {
      cwd: root, windowsHide: true, stdio: 'inherit',
      env: { ...process.env, CHROME_PATH: chrome },
    });
    child.once('error', reject);
    child.once('exit', code => code === 0 ? resolve() : reject(new Error(`Renderer exited ${code}`)));
  });
}

for (const name of ['slides_overview', 'slides_next']) {
  await run(path.join(modules, '@mermaid-js/mermaid-cli/src/cli.js'), [
    '-i', `reports/diagrams/${name}.mmd`, '-o', `reports/figures/${name}.svg`,
    '-p', path.join(temporary, 'browser.json'), '-c', path.join(temporary, 'mermaid.json'),
    '--size', '1600', '--no-font-embed', '-b', 'transparent',
  ]);
  if (name === 'slides_next') {
    // Keep the function name prominent; implementation notes use a smaller,
    // quieter line. Embed CSS in the SVG so every renderer keeps this hierarchy.
    const svgPath = path.join(root, `reports/figures/${name}.svg`);
    const svg = await readFile(svgPath, 'utf8');
    const svgId = svg.match(/<svg[^>]*\bid="([\w-]+)"/)?.[1];
    if (!svgId) throw new Error('Missing Mermaid SVG root ID');
    const hierarchy = `
      #${svgId} .node .text-outer-tspan:first-child .text-inner-tspan {
        font-weight: 600 !important; fill: #14364e !important;
      }
      #${svgId} .node .text-outer-tspan:not(:first-child) .text-inner-tspan {
        font-size: 20px !important; fill: #526b7b !important;
      }
    `;
    if (!svg.includes('</style>') || !svg.includes('text-outer-tspan')) {
      throw new Error('Unexpected Mermaid SVG structure; check label styling before export');
    }
    await writeFile(svgPath, svg.replace('</style>', hierarchy + '</style>'));
  }
}
await run(path.join(modules, '@marp-team/marp-cli/marp-cli.js'), [
  '--no-stdin', 'reports/SLIDES_BUOI_01_04.md',
  '-o', 'reports/SLIDES_BUOI_01_04.html',
]);
