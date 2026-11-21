const { contextBridge, ipcRenderer } = require('electron');

let keyboardVisible = false;
const keyboardListeners = new Set();
ipcRenderer.on('app:screen-keyboard', (_event, visible) => {
  keyboardVisible = visible;
  for (const listener of keyboardListeners) listener(visible);
});

contextBridge.exposeInMainWorld('electronAPI', {
  retryStartup: () => {
    ipcRenderer.send('app:retry-startup');
  },
  onScreenKeyboardChange: (listener) => {
    keyboardListeners.add(listener);
    listener(keyboardVisible);
    return () => { keyboardListeners.delete(listener); };
  },
});
