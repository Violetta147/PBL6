const { app, BrowserWindow, session } = require('electron');
app.setName('PBL6 STT');
// Isolated profiles allow tests to coexist with the user's running desktop.
if (process.env.PBL6_STT_DESKTOP_DATA_DIR) {
  require('node:fs').mkdirSync(process.env.PBL6_STT_DESKTOP_DATA_DIR, { recursive: true });
  app.setPath('userData', process.env.PBL6_STT_DESKTOP_DATA_DIR);
}

const origin = process.env.PBL6_STT_APP_URL;
if (!origin || !/^http:\/\/127\.0\.0\.1:\d+$/.test(origin)) {
  process.stderr.write('Use npm run desktop or desktop:dev to launch the local application.\n');
  app.exit(1);
} else if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  let window;
  app.on('second-instance', () => { if (window) { if (window.isMinimized()) window.restore(); window.focus(); } });
  app.whenReady().then(() => {
    // Allow media (microphone) permission exclusively for our trusted local application origin.
    const allowedPermissions = new Set([
      'media',
      'microphone',
      'audioCapture',
      'speaker-selection',
      'mediaKeySystem',
    ]);

    const isLocalAppOrigin = (urlOrOrigin) => {
      if (!urlOrOrigin || urlOrOrigin === 'about:blank') return true;
      try {
        const u = new URL(urlOrOrigin);
        if (u.protocol === 'about:' || u.protocol === 'data:') return true;
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
    window = new BrowserWindow({
      width: 1180, height: 860, minWidth: 640, minHeight: 600,
      title: 'STT · Tiếng Việt', backgroundColor: '#F5F7F9', autoHideMenuBar: true,
      kiosk: process.env.PBL6_STT_KIOSK === '1',
      webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true, devTools: process.env.PBL6_STT_DEV === '1' },
    });
    window.setMenu(null);
    window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
    window.webContents.on('will-navigate', (event, url) => { if (new URL(url).origin !== origin) event.preventDefault(); });
    window.loadURL(origin);
    window.on('closed', () => { window = null; });
  });
  app.on('window-all-closed', () => app.quit());
}
