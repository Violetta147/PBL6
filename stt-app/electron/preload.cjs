const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  retryStartup: () => {
    ipcRenderer.send('app:retry-startup');
  },
});
