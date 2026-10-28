import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = fileURLToPath(new URL('.', import.meta.url));
const types = { '.html': 'text/html; charset=utf-8', '.json': 'application/json', '.glb': 'model/gltf-binary', '.png': 'image/png', '.md': 'text/plain; charset=utf-8' };
http.createServer(async (req, res) => {
  try {
    const name = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const target = path.resolve(root, `.${name === '/' ? '/index.html' : name}`);
    if (!target.startsWith(root) || !types[path.extname(target)]) { res.writeHead(403).end(); return; }
    const data = await readFile(target); res.writeHead(200, { 'content-type': types[path.extname(target)] }); res.end(data);
  } catch { res.writeHead(404).end('Not found'); }
}).listen(8766, '127.0.0.1', () => console.log('PBL6 viewer: http://127.0.0.1:8766'));
