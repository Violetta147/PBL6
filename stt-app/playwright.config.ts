import { defineConfig } from '@playwright/test';
import { resolve } from 'node:path';

export default defineConfig({
  testDir: './tests/ui',
  workers: 1,
  reporter: 'list',
  timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:3111', channel: process.env.PBL6_STT_TEST_BROWSER || 'chrome', viewport: { width: 1280, height: 900 } },
  webServer: {
    command: 'node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3111',
    url: 'http://127.0.0.1:3111/api/health',
    reuseExistingServer: false,
    env: { NEXT_TELEMETRY_DISABLED: '1', PBL6_STT_CONFIG_DIR: resolve('.local/ui-test-config') },
  },
});
