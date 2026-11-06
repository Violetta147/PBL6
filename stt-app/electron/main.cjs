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
    // Capture stays in the Pi backend; this milestone never requests a browser microphone.
    session.defaultSession.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
    session.defaultSession.setPermissionCheckHandler(() => false);
    window = new BrowserWindow({
      width: 1180, height: 860, minWidth: 640, minHeight: 600,
      title: 'STT · Tiếng Việt', backgroundColor: '#f4f6f2', autoHideMenuBar: true,
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
