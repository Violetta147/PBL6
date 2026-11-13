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
    const allowedPermissions = new Set(['media', 'microphone', 'audioCapture']);
    session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
      try {
        const urlStr = webContents.getURL();
        const reqOrigin = urlStr ? new URL(urlStr).origin : '';
        if ((!reqOrigin || reqOrigin === origin) && allowedPermissions.has(permission)) {
          return callback(true);
        }
      } catch {}
      callback(false);
    });
    session.defaultSession.setPermissionCheckHandler((webContents, permission, requestingOrigin) => {
      const normReq = requestingOrigin ? requestingOrigin.replace(/\/$/, '') : '';
      const normOrigin = origin.replace(/\/$/, '');
      return (normReq === normOrigin || !normReq) && allowedPermissions.has(permission);
    });
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
