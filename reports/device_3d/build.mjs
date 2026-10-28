import { build } from 'esbuild';
import { readFile, writeFile } from 'node:fs/promises';
import { specification, partSpecs } from './spec.mjs';
const bundle = await build({ entryPoints: ['app.mjs'], bundle: true, minify: true, format: 'iife', write: false, legalComments: 'eof', target: ['es2022'] });
const template = await readFile(new URL('template.html', import.meta.url), 'utf8');
const page = template.replace('__BUNDLE__', () => bundle.outputFiles[0].text.replaceAll('</script', '<\\/script'));
await writeFile(new URL('index.html', import.meta.url), page.replace(/[\t ]+$/gm, ''));
await writeFile(new URL('specification.json', import.meta.url), JSON.stringify({ ...specification, parts: partSpecs }, null, 2));
console.log(`Built offline index.html (${bundle.outputFiles[0].text.length} JS characters); ${partSpecs.length} assemblies.`);
