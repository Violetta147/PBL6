import { createRequire } from 'node:module';
import { spawn, execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { once } from 'node:events';
import net from 'node:net';

const require = createRequire(import.meta.url);
const root = fileURLToPath(new URL('../', import.meta.url));
const dev = process.argv.includes('--dev');
const kiosk = process.argv.includes('--kiosk');
const port = 3100;
const origin = `http://127.0.0.1:${port}`;
// Refuse to attach a desktop to an unrelated or already-running server.
const probe = net.createServer();
try { probe.listen(port, '127.0.0.1'); await once(probe, 'listening'); }
catch { console.error(`Port ${port} is occupied. Close the existing STT server before starting desktop mode.`); process.exit(1); }
await new Promise(resolve => probe.close(resolve));

const env = { ...process.env, NEXT_TELEMETRY_DISABLED: '1' };
delete env.ELECTRON_RUN_AS_NODE;
const server = spawn(process.execPath, [require.resolve('next/dist/bin/next'), dev ? 'dev' : 'start', '--hostname', '127.0.0.1', '--port', String(port)], { cwd: root, env, stdio: 'inherit', windowsHide: true, detached: process.platform !== 'win32' });
let desktop;
let stopped = false;
function stopChild(child) {
  if (!child?.pid || child.exitCode !== null) return;
  if (process.platform === 'win32') {
    try { execFileSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true }); } catch {}
  } else {
    try { process.kill(-child.pid, 'SIGTERM'); } catch { child.kill('SIGTERM'); }
  }
}
function cleanup() { if (stopped) return; stopped = true; stopChild(desktop); stopChild(server); }
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => { cleanup(); process.exit(0); });
process.on('exit', cleanup);
server.on('error', () => { console.error('Cannot start the local backend.'); cleanup(); process.exitCode = 1; });
server.on('exit', () => { if (!stopped) { console.error('The local backend stopped.'); cleanup(); process.exitCode = 1; } });

try {
  const deadline = Date.now() + 90000;
  let ready = false;
  while (Date.now() < deadline && !stopped) {
    try {
      const response = await fetch(`${origin}/api/health`, { signal: AbortSignal.timeout(2000) });
      const health = await response.json();
      if (response.ok && health.application === 'pbl6-stt') { ready = true; break; }
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 400));
  }
  if (!ready) throw new Error('Backend startup failed or timed out.');
  desktop = spawn(require('electron'), [fileURLToPath(new URL('../electron/main.cjs', import.meta.url))], {
    cwd: root, env: { ...env, PBL6_STT_APP_URL: origin, PBL6_STT_KIOSK: kiosk ? '1' : '0', PBL6_STT_DEV: dev ? '1' : '0' },
    stdio: 'inherit', windowsHide: true, detached: process.platform !== 'win32',
  });
  desktop.on('error', () => { console.error('Cannot launch Electron.'); cleanup(); process.exitCode = 1; });
  desktop.on('exit', code => { cleanup(); process.exitCode = code || 0; });
} catch (error) { console.error(error.message); cleanup(); process.exitCode = 1; }
