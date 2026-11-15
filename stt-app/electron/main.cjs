const { app, BrowserWindow, session, utilityProcess, ipcMain } = require('electron');
const path = require('node:path');
const fs = require('node:fs');
const net = require('node:net');
const { execSync, spawn } = require('node:child_process');

app.setName('PBL6 STT');

// Isolated profiles allow tests to coexist with the user's running desktop.
if (process.env.PBL6_STT_DESKTOP_DATA_DIR) {
  fs.mkdirSync(process.env.PBL6_STT_DESKTOP_DATA_DIR, { recursive: true });
  app.setPath('userData', process.env.PBL6_STT_DESKTOP_DATA_DIR);
}

function log(line) {
  const stamp = new Date().toISOString();
  try {
    console.log(`[stt ${stamp}] ${line}`);
  } catch {}
  try {
    const dir = path.join(app.getPath('userData'), 'logs');
    fs.mkdirSync(dir, { recursive: true });
    fs.appendFileSync(path.join(dir, 'main.log'), `[${stamp}] ${line}\n`);
  } catch {}
}

let configuredOrigin = process.env.PBL6_STT_APP_URL;
let backendProcess = null;

function stopBackend() {
  if (!backendProcess) return;
  try {
    if (backendProcess.pid && process.platform === 'win32') {
      try {
        execSync(`taskkill /pid ${backendProcess.pid} /T /F`, { stdio: 'ignore' });
      } catch {}
    }
    backendProcess.kill();
  } catch {}
  backendProcess = null;
}

function resolveServerEntry() {
  // 1. Packaged LearnHarness architecture (extraResources: resources/server/standalone/server.js)
  const packagedStandalone = path.join(process.resourcesPath, 'server', 'standalone', 'server.js');
  if (fs.existsSync(packagedStandalone)) {
    return packagedStandalone;
  }

  // 2. Development / Local standalone build
  const localStandalone = path.resolve(__dirname, '..', '.next', 'standalone', 'server.js');
  if (fs.existsSync(localStandalone)) {
    return localStandalone;
  }

  // 3. Fallback to server.cjs
  return path.resolve(__dirname, 'server.cjs');
}

function checkPortFree(port) {
  return new Promise((resolve) => {
    const s = net.createServer();
    s.once('error', () => resolve(false));
    s.once('listening', () => {
      s.close(() => resolve(true));
    });
    s.listen(port, '127.0.0.1');
  });
}

async function resolveAvailablePort() {
  if (process.env.PBL6_STT_PORT && /^\d+$/.test(process.env.PBL6_STT_PORT)) {
    return Number(process.env.PBL6_STT_PORT);
  }
  const defaultPort = 3100;
  for (let candidate = defaultPort; candidate < defaultPort + 20; candidate++) {
    try {
      const res = await fetch(`http://127.0.0.1:${candidate}/api/health`, { signal: AbortSignal.timeout(500) });
      const data = await res.json();
      if (res.ok && data.application === 'pbl6-stt') {
        return candidate;
      }
    } catch {}

    if (await checkPortFree(candidate)) {
      return candidate;
    }
  }
  return defaultPort;
}

async function startBackendIfNeeded() {
  if (configuredOrigin && /^http:\/\/127\.0\.0\.1:\d+$/.test(configuredOrigin)) {
    return configuredOrigin;
  }

  const port = await resolveAvailablePort();
  const targetOrigin = `http://127.0.0.1:${port}`;
  log(`Target origin: ${targetOrigin}`);

  // Check if server is already running and healthy
  try {
    const res = await fetch(`${targetOrigin}/api/health`, { signal: AbortSignal.timeout(1000) });
    const data = await res.json();
    if (res.ok && data.application === 'pbl6-stt') {
      configuredOrigin = targetOrigin;
      log(`Reusing existing healthy backend on ${configuredOrigin}`);
      return configuredOrigin;
    }
  } catch {}

  stopBackend();

  const serverScript = resolveServerEntry();
  const isStandalone = serverScript.endsWith('server.js');
  log(`Resolved server script: ${serverScript} (isStandalone=${isStandalone})`);

  let backendExited = false;
  let backendExitCode = null;

  const serverCwd = isStandalone ? path.dirname(serverScript) : app.getAppPath();
  const serverEnv = {
    ...process.env,
    NODE_ENV: 'production',
    NEXT_TELEMETRY_DISABLED: '1',
    PORT: String(port),
    HOSTNAME: '127.0.0.1',
  };

  if (isStandalone) {
    serverEnv.ELECTRON_RUN_AS_NODE = '1';
    log(`Spawning standalone backend via spawn(process.execPath)...`);
    backendProcess = spawn(process.execPath, [serverScript], {
      cwd: serverCwd,
      env: serverEnv,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  } else {
    log(`Forking backend via utilityProcess...`);
    backendProcess = utilityProcess.fork(serverScript, [], {
      cwd: serverCwd,
      env: serverEnv,
      stdio: 'pipe',
    });
  }

  backendProcess.stdout?.on('data', (chunk) => {
    log(`[backend stdout] ${chunk}`);
  });
  backendProcess.stderr?.on('data', (chunk) => {
    log(`[backend stderr] ${chunk}`);
  });
  backendProcess.on('exit', (code) => {
    backendExited = true;
    backendExitCode = code;
    log(`[backend exit] process exited with code ${code}`);
  });

  const deadline = Date.now() + 45000;
  while (Date.now() < deadline && !backendExited) {
    try {
      const res = await fetch(`${targetOrigin}/api/health`, { signal: AbortSignal.timeout(1000) });
      const data = await res.json();
      if (res.ok && data.application === 'pbl6-stt') {
        configuredOrigin = targetOrigin;
        log(`Backend became healthy on ${configuredOrigin}`);
        return configuredOrigin;
      }
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 150));
  }

  if (backendExited) {
    log(`Backend process terminated early with code ${backendExitCode}`);
  } else {
    log('Backend startup timed out.');
  }

  configuredOrigin = targetOrigin;
  return configuredOrigin;
}

function setupPermissions(origin) {
  const allowedPermissions = new Set([
    'media',
    'microphone',
    'audioCapture',
    'speaker-selection',
    'mediaKeySystem',
  ]);

  const isLocalAppOrigin = (urlOrOrigin) => {
    if (!urlOrOrigin || urlOrOrigin === 'about:blank' || urlOrOrigin.startsWith('data:') || urlOrOrigin.startsWith('file:')) return true;
    try {
      const u = new URL(urlOrOrigin);
      if (u.protocol === 'about:' || u.protocol === 'data:' || u.protocol === 'file:') return true;
      const o = new URL(origin);
      const isLocalHost = u.hostname === '127.0.0.1' || u.hostname === 'localhost';
      const isLocalOrig = o.hostname === '127.0.0.1' || o.hostname === 'localhost';
      return isLocalHost && isLocalOrig && (u.port === o.port || !u.port || !o.port);
    } catch {
      return false;
    }
  };

  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback, details) => {
    try {
      const reqUrl = details?.requestingUrl || details?.securityOrigin || webContents?.getURL() || '';
      if (allowedPermissions.has(permission) && isLocalAppOrigin(reqUrl)) {
        return callback(true);
      }
    } catch {}
    callback(false);
  });

  session.defaultSession.setPermissionCheckHandler((webContents, permission, requestingOrigin, details) => {
    const reqUrl = details?.requestingUrl || details?.securityOrigin || requestingOrigin || webContents?.getURL() || '';
    return allowedPermissions.has(permission) && isLocalAppOrigin(reqUrl);
  });

  session.defaultSession.setDevicePermissionHandler(() => true);
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  let window;
  let isNavigatingOrReady = false;

  async function launchAndConnect() {
    if (!window || window.isDestroyed()) return;

    window.webContents.executeJavaScript(`
      (function() {
        const spinner = document.getElementById('spinner');
        if (spinner) spinner.style.display = 'block';
        const status = document.getElementById('status-text');
        if (status) status.innerText = 'Đang khởi động hệ thống...';
        const errBox = document.getElementById('error-box');
        if (errBox) errBox.style.display = 'none';
      })();
    `).catch(() => {});

    const origin = await startBackendIfNeeded();

    let isReachable = false;
    try {
      const res = await fetch(`${origin}/api/health`, { signal: AbortSignal.timeout(2000) });
      const data = await res.json();
      isReachable = res.ok && data.application === 'pbl6-stt';
    } catch {}

    if (!window || window.isDestroyed()) return;

    if (!isReachable) {
      window.webContents.executeJavaScript(`
        (function() {
          const spinner = document.getElementById('spinner');
          if (spinner) spinner.style.display = 'none';
          const status = document.getElementById('status-text');
          if (status) status.innerText = 'Không thể kết nối máy chủ STT';
          const errBox = document.getElementById('error-box');
          if (errBox) errBox.style.display = 'flex';
          const errMsg = document.getElementById('error-message');
          if (errMsg) errMsg.innerText = 'Máy chủ nội bộ không phản hồi. Vui lòng nhấn Thử lại hoặc khởi động lại ứng dụng.';
        })();
      `).catch(() => {});
      return;
    }

    setupPermissions(origin);
    isNavigatingOrReady = true;
    window.loadURL(origin);
  }

  ipcMain.on('app:retry-startup', () => {
    if (window && !window.isDestroyed() && !isNavigatingOrReady) {
      launchAndConnect();
    }
  });

  app.on('second-instance', () => {
    if (window) {
      if (window.isMinimized()) window.restore();
      window.focus();
    }
  });

  app.whenReady().then(async () => {
    const preloadPath = path.join(__dirname, 'preload.cjs');

    window = new BrowserWindow({
      width: 1180,
      height: 860,
      minWidth: 640,
      minHeight: 600,
      title: 'STT · Tiếng Việt',
      backgroundColor: '#F5F7F9',
      autoHideMenuBar: true,
      show: true,
      kiosk: process.env.PBL6_STT_KIOSK === '1',
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: true,
        preload: fs.existsSync(preloadPath) ? preloadPath : undefined,
        devTools: process.env.PBL6_STT_DEV === '1',
      },
    });

    window.setMenu(null);
    window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));

    window.webContents.on('will-navigate', (event, url) => {
      try {
        if (!configuredOrigin || new URL(url).origin !== configuredOrigin) {
          event.preventDefault();
        }
      } catch {
        event.preventDefault();
      }
    });

    window.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
      if (validatedURL && configuredOrigin && validatedURL.startsWith(configuredOrigin)) {
        console.error(`Failed to load ${validatedURL}: ${errorCode} (${errorDescription})`);
      }
    });

    const splashPath = path.join(__dirname, 'splash.html');
    if (fs.existsSync(splashPath)) {
      window.loadFile(splashPath);
    } else {
      const fallbackHtml = `<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8"/><title>STT · Tiếng Việt</title><style>body{margin:0;padding:0;background:#F5F7F9;font-family:sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;color:#18212B;}.spinner{width:40px;height:40px;border:3px solid #BAC5D0;border-top-color:#273D53;border-radius:50%;animation:spin 1s linear infinite;margin-bottom:16px;}@keyframes spin{to{transform:rotate(360deg)}}h2{font-size:20px;font-weight:600;margin:0 0 6px 0;}p{font-size:14px;color:#4F5D6B;margin:0;}</style></head><body><div class="spinner"></div><h2>STT · Tiếng Việt</h2><p>Đang khởi động hệ thống...</p></body></html>`;
      window.loadURL(`data:text/html;charset=utf-8;base64,${Buffer.from(fallbackHtml, 'utf8').toString('base64')}`);
    }

    await launchAndConnect();

    window.on('closed', () => {
      window = null;
    });
  });

  app.on('will-quit', stopBackend);
  app.on('window-all-closed', () => {
    stopBackend();
    app.quit();
  });
}
