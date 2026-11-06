import { test, expect, _electron } from '@playwright/test';
import { resolve } from 'node:path';

const fakeKey = 'TEST_NOT_A_REAL_KEY_0123456789';
const baseSettings = { provider: 'deepgram', language: 'vi', model: 'nova-3', timeoutSeconds: 60, hasApiKey: false };
const fixture = { sessionId: 'fixture-session', fileName: 'fixture.wav', text: 'Văn bản mô phỏng để kiểm thử giao diện.', status: 'completed',
  provider: 'deepgram', language: 'vi', model: 'nova-3', requestId: 'fixture-request', audioSeconds: 1, requestMs: 123 };

test('initial screen identifies missing key and never requests browser capture', async ({ page }, info) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Nghe lại bằng con chữ.' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Nhận dạng file', exact: true }).last()).toBeDisabled();
  await expect(page.getByText('Chưa cấu hình API key.')).toBeVisible();
  await expect(page.getByText('Thu âm micro Pi và danh sách nhiều file', { exact: false })).toBeVisible();
  await page.screenshot({ path: info.outputPath('file-screen.png'), fullPage: true });
});
test('Settings uses password input, preserves blank key, and clears entered value after save', async ({ page }, info) => {
  let current = { ...baseSettings };
  await page.route('**/api/settings', async route => {
    if (route.request().method() === 'PUT') {
      const data = route.request().postDataJSON(); expect(data.apiKey).toBe(fakeKey); current = { ...current, hasApiKey: true };
    }
    await route.fulfill({ json: current });
  });
  await page.goto('/'); await page.getByRole('button', { name: 'Cài đặt', exact: true }).click();
  await expect(page.getByLabel('Deepgram API key')).toHaveAttribute('type', 'password');
  await page.getByLabel('Deepgram API key').fill(fakeKey); await page.getByRole('button', { name: 'Lưu cấu hình' }).click();
  await expect(page.getByText('Đã lưu cấu hình.', { exact: false })).toBeVisible();
  await expect(page.getByLabel('Deepgram API key')).toHaveValue('');
  await expect(page.getByLabel('Ngôn ngữ')).toHaveValue('Tiếng Việt · vi');
  await page.screenshot({ path: info.outputPath('settings-screen.png'), fullPage: true });
});
test('one-file success is displayed and remains after a subsequent failure', async ({ page }) => {
  await page.route('**/api/settings', route => route.fulfill({ json: { ...baseSettings, hasApiKey: true } }));
  let calls = 0;
  await page.route('**/api/transcriptions', route => {
    calls++;
    return calls === 1 ? route.fulfill({ json: fixture }) : route.fulfill({ status: 504, json: { error: { code: 'provider_timeout', message: 'Hết thời gian chờ (mô phỏng).' } } });
  });
  await page.goto('/');
  await page.getByLabel('Chọn file âm thanh').setInputFiles({ name: 'fixture.wav', mimeType: 'audio/wav', buffer: Buffer.from('fixture only; API intercepted') });
  await page.getByRole('button', { name: 'Nhận dạng file', exact: true }).last().click();
  await expect(page.getByTestId('transcript')).toHaveText(fixture.text);
  await page.getByRole('button', { name: 'Nhận dạng file', exact: true }).last().click();
  await expect(page.getByRole('alert').filter({ hasText: 'Hết thời gian chờ' })).toBeVisible();
  await expect(page.getByTestId('transcript')).toHaveText(fixture.text);
});
test('narrow viewport has no horizontal page overflow', async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Nghe lại bằng con chữ.' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath('mobile-screen.png'), fullPage: true });
});
test('real HTTP rejects cross-origin settings writes and missing-key recognition', async ({ request }) => {
  const rejected = await request.put('/api/settings', { headers: { Origin: 'https://other.example' }, data: { apiKey: fakeKey } });
  expect(rejected.status()).toBe(403);
  const response = await request.post('/api/transcriptions', { headers: { Origin: 'http://127.0.0.1:3111' } });
  expect(response.status()).toBe(409); expect((await response.json()).error.code).toBe('key_missing');
});
test('real HTTP saves a fixture key, redacts reads and explicitly deletes it without calling STT', async ({ request }) => {
  const headers = { Origin: 'http://127.0.0.1:3111' };
  try {
    const saved = await request.put('/api/settings', { headers, data: { apiKey: fakeKey, model: 'nova-2' } });
    expect(saved.status()).toBe(200); expect(await saved.text()).not.toContain(fakeKey);
    const read = await request.get('/api/settings'); const data = await read.json();
    expect(data.hasApiKey).toBe(true); expect(data.model).toBe('nova-2'); expect(data.language).toBe('vi');
    expect(JSON.stringify(data)).not.toContain(fakeKey);
  } finally {
    const cleared = await request.put('/api/settings', { headers, data: { clearApiKey: true, model: 'nova-3' } });
    expect(cleared.status()).toBe(200); expect((await cleared.json()).hasApiKey).toBe(false);
  }
});
test('Electron opens the same local UI with isolated renderer', async ({}, info) => {
  const env: Record<string, string> = Object.fromEntries(Object.entries(process.env).filter((item): item is [string, string] => item[1] !== undefined));
  env.PBL6_STT_APP_URL = 'http://127.0.0.1:3111';
  delete env.ELECTRON_RUN_AS_NODE;
  const desktop = await _electron.launch({ args: [resolve('electron/main.cjs')], env });
  try {
    const window = await desktop.firstWindow();
    await expect(window.getByRole('heading', { name: 'Nghe lại bằng con chữ.' })).toBeVisible();
    const globals = await window.evaluate(() => ({ require: 'require' in window, process: 'process' in window }));
    expect(globals.require).toBe(false); expect(globals.process).toBe(false);
    await window.screenshot({ path: info.outputPath('electron-screen.png'), fullPage: true });
  } finally { await desktop.close(); }
});
