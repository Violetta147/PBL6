// Run after node reports/render_slides.mjs. Uses the same ignored dependencies.
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const require = createRequire(path.join(root, 'data/presentation_tools/package.json'));
const puppeteer = require('puppeteer');
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
});
try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(path.join(root, 'reports/figures/slides_next.svg')).href);
  const checks = await page.evaluate(() => [...document.querySelectorAll('g.node')].map(node => {
    const rows = [...node.querySelectorAll('.text-outer-tspan')];
    if (rows.length < 2) return { valid: false };
    const main = getComputedStyle(rows[0].querySelector('.text-inner-tspan'));
    const note = getComputedStyle(rows[1].querySelector('.text-inner-tspan'));
    const box = node.querySelector('rect').getBoundingClientRect();
    const text = node.querySelector('text').getBoundingClientRect();
    return {
      label: rows[0].textContent,
      valid: Number(main.fontWeight) >= 600 && parseFloat(main.fontSize) > parseFloat(note.fontSize)
        && main.fill !== note.fill && text.left >= box.left - 1 && text.right <= box.right + 1
        && text.top >= box.top - 1 && text.bottom <= box.bottom + 1,
    };
  }));
  if (checks.length !== 4 || checks.some(check => !check.valid)) {
    throw new Error('Diagram hierarchy or label fit failed: ' + JSON.stringify(checks));
  }
  console.log('PASS: all four blocks distinguish main/secondary labels by weight, size and color; text fits.');
} finally {
  await browser.close();
}
