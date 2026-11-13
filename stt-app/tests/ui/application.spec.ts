import { test, expect, _electron } from '@playwright/test';
import { resolve } from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const fakeKey = 'TEST_NOT_A_REAL_KEY_0123456789';

test('initial screen displays Header, empty conversation, and composer with idle mic and disabled Send', async ({ page }, info) => {
  await page.goto('/');
  // Header controls
  await expect(page.getByTestId('history-button')).toHaveText('Hội thoại');
  await expect(page.getByTestId('conversation-title-locked')).toHaveText('Hội thoại mới');
  await expect(page.getByTestId('settings-button')).toHaveText('Cài đặt');

  // Composer
  const textarea = page.getByTestId('composer-textarea');
  await expect(textarea).toBeVisible();
  const micButton = page.getByTestId('mic-button');
  await expect(micButton).toHaveAttribute('data-status', 'idle');
  const sendButton = page.getByTestId('send-button');
  await expect(sendButton).toBeDisabled();

  // No messages initially
  await expect(page.getByTestId('message-card')).toHaveCount(0);
  await page.screenshot({ path: info.outputPath('stage2-initial-screen.png'), fullPage: true });
});

test('typing enables Send button; sending first message creates conversation and unlocks title editing', async ({ page }, info) => {
  const convFixture = {
    id: 'conv-test-1',
    title: 'Xin chào bạn',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    messageCount: 1,
  };
  const msgFixture = {
    id: 'msg-test-1',
    conversationId: 'conv-test-1',
    text: 'Xin chào bạn',
    createdAt: new Date().toISOString(),
    sources: ['keyboard'],
  };

  await page.route('**/api/conversations', async route => {
    if (route.request().method() === 'POST') {
      const data = route.request().postDataJSON();
      expect(data.text).toBe('Xin chào bạn');
      expect(data.sources).toEqual(['keyboard']);
      return route.fulfill({ status: 201, json: { conversation: convFixture, message: msgFixture } });
    }
    return route.continue();
  });

  await page.goto('/');
  const textarea = page.getByTestId('composer-textarea');
  const sendButton = page.getByTestId('send-button');

  // Type text
  await textarea.fill('Xin chào bạn');
  await expect(sendButton).toBeEnabled();

  // Send message
  await sendButton.click();

  // Textarea cleared
  await expect(textarea).toHaveValue('');
  // Message card rendered
  const messageCard = page.getByTestId('message-card');
  await expect(messageCard).toHaveCount(1);
  await expect(messageCard).toHaveText('Xin chào bạn');

  // Title unlocked for inline editing
  const titleInput = page.getByTestId('conversation-title-input');
  await expect(titleInput).toBeVisible();
  await expect(titleInput).toHaveValue('Xin chào bạn');

  await page.screenshot({ path: info.outputPath('stage2-message-sent.png'), fullPage: true });
});

test('send failure preserves composer draft, shows error beside mic, and re-enables send', async ({ page }) => {
  await page.route('**/api/conversations', async route => {
    return route.fulfill({ status: 500, json: { error: { code: 'storage_error', message: 'Lỗi máy chủ' } } });
  });

  await page.goto('/');
  const textarea = page.getByTestId('composer-textarea');
  const sendButton = page.getByTestId('send-button');

  await textarea.fill('Tin nhắn thử nghiệm lỗi');
  await sendButton.click();

  // Draft preserved
  await expect(textarea).toHaveValue('Tin nhắn thử nghiệm lỗi');
  // Error notice displayed beside mic
  const errorNotice = page.getByTestId('composer-error-notice');
  await expect(errorNotice).toBeVisible();
  await expect(errorNotice).toHaveText('Không gửi được. Hãy thử lại.');

  // Send button re-enabled for retry
  await expect(sendButton).toBeEnabled();

  // Error notice clears on keystroke
  await textarea.type(' thêm');
  await expect(errorNotice).toBeHidden();
});

test('smart latch: clicking Send during recording triggers stop, enters transcribing, and auto-sends combined message', async ({ page }) => {
  let recordStarted = false;
  let recordStopped = false;

  await page.route('**/api/record/start', async route => {
    recordStarted = true;
    return route.fulfill({ json: { success: true, state: { status: 'recording', durationMs: 0 } } });
  });

  await page.route('**/api/record/stop', async route => {
    recordStopped = true;
    return route.fulfill({
      json: {
        sessionId: 'sess-latch',
        fileName: 'latch.wav',
        text: 'hẹn gặp vào sáng mai',
        status: 'completed',
        provider: 'deepgram',
        language: 'vi',
        model: 'nova-3',
        requestId: 'req-latch',
        audioSeconds: 2,
        requestMs: 200,
      },
    });
  });

  let sentText = '';
  let sentSources: string[] = [];
  await page.route('**/api/conversations', async route => {
    const data = route.request().postDataJSON();
    sentText = data.text;
    sentSources = data.sources;
    return route.fulfill({
      status: 201,
      json: {
        conversation: { id: 'c-latch', title: data.text, createdAt: '', updatedAt: '', messageCount: 1 },
        message: { id: 'm-latch', conversationId: 'c-latch', text: data.text, createdAt: '', sources: data.sources },
      },
    });
  });

  await page.goto('/');
  const textarea = page.getByTestId('composer-textarea');
  const micButton = page.getByTestId('mic-button');
  const sendButton = page.getByTestId('send-button');

  // Type draft prefix
  await textarea.fill('Tôi muốn');

  // Start recording
  await micButton.click();
  expect(recordStarted).toBe(true);
  await expect(micButton).toHaveAttribute('data-status', 'recording');

  // Click Send during recording
  await sendButton.click();
  expect(recordStopped).toBe(true);

  // Combined message sent automatically
  await expect(page.getByTestId('message-card')).toHaveCount(1);
  await expect(page.getByTestId('message-card')).toHaveText('Tôi muốn hẹn gặp vào sáng mai');
  expect(sentText).toBe('Tôi muốn hẹn gặp vào sáng mai');
  expect(sentSources).toContain('voice');
});

test('smart latch: clicking Send during transcribing (after stopping) auto-sends once transcript arrives', async ({ page }) => {
  let resolveStopFetch: ((value: any) => void) | null = null;
  const stopPromise = new Promise((resolve) => {
    resolveStopFetch = resolve;
  });

  await page.route('**/api/record/start', async route => {
    return route.fulfill({ json: { success: true, state: { status: 'recording', durationMs: 0 } } });
  });

  await page.route('**/api/record/stop', async route => {
    await stopPromise;
    return route.fulfill({
      json: {
        sessionId: 'sess-latch-transcribe',
        fileName: 'latch.wav',
        text: 'hẹn gặp vào sáng mai',
        status: 'completed',
        provider: 'deepgram',
        language: 'vi',
        model: 'nova-3',
        requestId: 'req-latch-2',
        audioSeconds: 2,
        requestMs: 200,
      },
    });
  });

  let sentText = '';
  await page.route('**/api/conversations', async route => {
    const data = route.request().postDataJSON();
    sentText = data.text;
    return route.fulfill({
      status: 201,
      json: {
        conversation: { id: 'c-latch-2', title: data.text, createdAt: '', updatedAt: '', messageCount: 1 },
        message: { id: 'm-latch-2', conversationId: 'c-latch-2', text: data.text, createdAt: '', sources: data.sources },
      },
    });
  });

  await page.goto('/');
  const textarea = page.getByTestId('composer-textarea');
  const micButton = page.getByTestId('mic-button');
  const sendButton = page.getByTestId('send-button');

  await textarea.fill('Tôi muốn');
  // Start recording
  await micButton.click();
  await expect(micButton).toHaveAttribute('data-status', 'recording');

  // Stop recording via mic square button -> transitions to transcribing
  await micButton.click();
  await expect(micButton).toHaveAttribute('data-status', 'transcribing');

  // Now click Send while transcribing
  await sendButton.click();
  await expect(sendButton).toHaveAttribute('data-latched', 'true');

  // Now resolve transcription
  resolveStopFetch!(true);

  // Combined message is sent automatically
  await expect(page.getByTestId('message-card')).toHaveCount(1);
  await expect(page.getByTestId('message-card')).toHaveText('Tôi muốn hẹn gặp vào sáng mai');
  expect(sentText).toBe('Tôi muốn hẹn gặp vào sáng mai');
});

test('inline title rename cancels and restores original title on Escape', async ({ page }) => {
  const convFixture = {
    id: 'conv-escape-test',
    title: 'Tiêu đề gốc',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    messageCount: 1,
  };
  const msgFixture = {
    id: 'msg-escape-test',
    conversationId: 'conv-escape-test',
    text: 'Tiêu đề gốc',
    createdAt: new Date().toISOString(),
    sources: ['keyboard'],
  };

  let patchCalled = false;
  await page.route('**/api/conversations', async route => {
    return route.fulfill({ status: 201, json: { conversation: convFixture, message: msgFixture } });
  });
  await page.route('**/api/conversations/**', async route => {
    if (route.request().method() === 'PATCH') {
      patchCalled = true;
      return route.fulfill({ status: 200, json: convFixture });
    }
    return route.continue();
  });

  await page.goto('/');
  await page.getByTestId('composer-textarea').fill('Tiêu đề gốc');
  await page.getByTestId('send-button').click();

  const titleInput = page.getByTestId('conversation-title-input');
  await expect(titleInput).toHaveValue('Tiêu đề gốc');

  // Edit title then press Escape
  await titleInput.fill('Tiêu đề mới không mong muốn');
  await titleInput.press('Escape');

  // Value should revert to original title and PATCH should not have been called
  await expect(titleInput).toHaveValue('Tiêu đề gốc');
  expect(patchCalled).toBe(false);
});

test('touchscreen target dimensions 1024x600 has no horizontal overflow and minimum 44px tap targets', async ({ page }, info) => {
  await page.setViewportSize({ width: 1024, height: 600 });
  await page.goto('/');

  const noOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
  expect(noOverflow).toBe(true);

  // Tap targets check
  const micBox = await page.getByTestId('mic-button').boundingBox();
  expect(micBox?.height).toBeGreaterThanOrEqual(44);
  expect(micBox?.width).toBeGreaterThanOrEqual(44);

  const sendBox = await page.getByTestId('send-button').boundingBox();
  expect(sendBox?.height).toBeGreaterThanOrEqual(44);
  expect(sendBox?.width).toBeGreaterThanOrEqual(44);

  const histBox = await page.getByTestId('history-button').boundingBox();
  expect(histBox?.height).toBeGreaterThanOrEqual(44);

  const settBox = await page.getByTestId('settings-button').boundingBox();
  expect(settBox?.height).toBeGreaterThanOrEqual(44);

  await page.screenshot({ path: info.outputPath('stage2-touchscreen-1024x600.png'), fullPage: true });
});

test('Stage 3 History Drawer opens, shows empty state, closes via 3 methods, and + Hội thoại mới resets draft', async ({ page }, info) => {
  let conversationsFixture: any[] = [];
  await page.route('**/api/conversations*', async (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({ status: 200, json: conversationsFixture });
    }
    return route.continue();
  });

  await page.goto('/');

  // 1. Open drawer
  const historyBtn = page.getByTestId('history-button');
  await historyBtn.click();

  const drawer = page.getByTestId('history-drawer');
  await expect(drawer).toBeVisible();

  // Width is 360px on 1024x600
  const drawerBox = await drawer.boundingBox();
  expect(drawerBox?.width).toBe(360);

  // Empty state initially
  const emptyNotice = page.getByTestId('history-empty');
  await expect(emptyNotice).toHaveText('Chưa có hội thoại đã lưu.');

  // Method 1 to close: Close button
  const closeBtn = page.getByTestId('history-drawer-close');
  await closeBtn.click();
  await expect(drawer).toBeHidden();

  // Method 2 to close: Backdrop
  await historyBtn.click();
  await expect(drawer).toBeVisible();
  const backdrop = page.getByTestId('history-drawer-backdrop');
  await backdrop.click({ position: { x: 500, y: 300 } });
  await expect(drawer).toBeHidden();

  // Test "+ Hội thoại mới" with existing draft
  const textarea = page.getByTestId('composer-textarea');
  await textarea.fill('Bản nháp chưa gửi');

  await historyBtn.click();
  await expect(drawer).toBeVisible();

  const newChatBtn = page.getByTestId('new-conversation-button');
  await newChatBtn.click();
  await expect(drawer).toBeHidden();

  // Draft must be discarded per spec
  await expect(textarea).toHaveValue('');
  await expect(page.getByTestId('conversation-title-locked')).toHaveText('Hội thoại mới');

  // Method 3 to close: Select a conversation
  const convA = {
    id: 'conv-a-test',
    title: 'Hội thoại kiểm tra A',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    messageCount: 1,
  };
  const msgA = {
    id: 'msg-a-test',
    conversationId: 'conv-a-test',
    text: 'Nội dung tin nhắn trong A',
    createdAt: new Date().toISOString(),
    sources: ['voice'],
  };

  conversationsFixture = [convA];

  await page.route('**/api/conversations/conv-a-test', async (route) => {
    return route.fulfill({
      status: 200,
      json: { conversation: convA, messages: [msgA] },
    });
  });

  await historyBtn.click();
  await expect(drawer).toBeVisible();

  const itemA = page.getByTestId('history-item-conv-a-test');
  await expect(itemA).toBeVisible();
  await itemA.click();

  // Drawer closes and conversation is loaded
  await expect(drawer).toBeHidden();
  await expect(page.getByTestId('conversation-title-input')).toHaveValue('Hội thoại kiểm tra A');
  await expect(page.getByTestId('message-card')).toHaveText('Nội dung tin nhắn trong A');

  // Test selecting the currently active conversation: draft must be preserved
  await textarea.fill('Bản nháp không được mất khi bấm lại cùng hội thoại');
  await historyBtn.click();
  await expect(drawer).toBeVisible();
  await itemA.click();
  await expect(drawer).toBeHidden();
  await expect(textarea).toHaveValue('Bản nháp không được mất khi bấm lại cùng hội thoại');

  await page.screenshot({ path: info.outputPath('stage3-history-drawer.png'), fullPage: true });
});

test('Stage 3 Settings View: STT validation, dirty detection, unsaved confirmation modal, and save', async ({ page }, info) => {
  const initialSettings = {
    provider: 'deepgram',
    language: 'vi',
    model: 'nova-3',
    timeoutSeconds: 60,
    hasApiKey: false,
    maxRecordSeconds: 120,
    selectedMicrophoneId: 'mic-unplugged-usb',
  };
  const mockMics = {
    devices: [
      { id: 'mic-os-default', name: 'PipeWire Default Source', isDefault: true },
      { id: 'mic-usb-headset', name: 'USB Headset Microphone', isDefault: false },
    ],
    selectedId: 'mic-unplugged-usb',
  };

  await page.route('**/api/settings', async (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({ status: 200, json: initialSettings });
    }
    if (route.request().method() === 'PUT') {
      const data = route.request().postDataJSON();
      return route.fulfill({
        status: 200,
        json: { ...initialSettings, ...data },
      });
    }
    return route.continue();
  });

  await page.route('**/api/devices/microphones', async (route) => {
    return route.fulfill({ status: 200, json: mockMics });
  });

  await page.goto('/');

  // 1. Open settings
  const settingsBtn = page.getByTestId('settings-button');
  await settingsBtn.click();

  const settingsView = page.getByTestId('settings-view');
  await expect(settingsView).toBeVisible();

  // Check STT controls
  const micSelect = page.getByTestId('settings-mic-select');
  await expect(micSelect).toBeVisible();
  // Saved disconnected mic is displayed in dropdown with fallback option
  await expect(micSelect).toHaveValue('mic-unplugged-usb');
  await expect(micSelect.locator('option[value="mic-unplugged-usb"]')).toContainText('Đã ngắt kết nối');

  const maxDurationInput = page.getByTestId('settings-max-duration');
  await expect(maxDurationInput).toHaveValue('120');

  const saveBtn = page.getByTestId('settings-save-button');
  // Initially clean -> save button is disabled
  await expect(saveBtn).toBeDisabled();

  // Test API key invalid format error
  const apiKeyInput = page.getByTestId('settings-api-key');
  await apiKeyInput.fill('short-key');
  const keyError = page.getByTestId('api-key-error');
  await expect(keyError).toBeVisible();
  await expect(keyError).toHaveText('API key phải dài 16–512 ký tự, không chứa khoảng trắng hoặc ký tự điều khiển.');
  await expect(saveBtn).toBeDisabled();
  await apiKeyInput.fill('');
  await expect(keyError).toBeHidden();

  // Validation: enter invalid max duration (> 300)
  await maxDurationInput.fill('400');
  const errorNotice = page.getByTestId('max-duration-error');
  await expect(errorNotice).toBeVisible();
  await expect(errorNotice).toHaveText('Thời lượng thu tối đa phải là số nguyên từ 5 đến 300 giây.');
  await expect(saveBtn).toBeDisabled();

  // Valid edit
  await maxDurationInput.fill('150');
  await expect(errorNotice).toBeHidden();
  await expect(saveBtn).toBeEnabled();

  // Unsaved changes confirmation modal on navigation
  const backBtn = page.getByTestId('settings-back-button');
  await backBtn.click();

  const unsavedModal = page.getByTestId('unsaved-modal');
  await expect(unsavedModal).toBeVisible();
  await expect(unsavedModal).toContainText('Bạn có muốn lưu thay đổi?');

  // Modal: "Ở lại" preserves edits
  const stayBtn = page.getByTestId('unsaved-stay');
  await stayBtn.click();
  await expect(unsavedModal).toBeHidden();
  await expect(settingsView).toBeVisible();
  await expect(maxDurationInput).toHaveValue('150');

  // Save settings via Save button
  await saveBtn.click();
  await expect(page.getByTestId('save-notice')).toHaveText('Đã lưu cài đặt.');
  await expect(saveBtn).toBeDisabled();

  // Return to main view
  await backBtn.click();
  await expect(settingsView).toBeHidden();

  await page.screenshot({ path: info.outputPath('stage3-settings-view.png'), fullPage: true });
});

test('Stage 3 Settings View: draft preservation rule', async ({ page }) => {
  await page.goto('/');

  const textarea = page.getByTestId('composer-textarea');
  await textarea.fill('Câu nháp đang soạn rất quan trọng');

  // Open Settings
  await page.getByTestId('settings-button').click();
  await expect(page.getByTestId('settings-view')).toBeVisible();

  // Return to conversation
  await page.getByTestId('settings-back-button').click();
  await expect(page.getByTestId('settings-view')).toBeHidden();

  // Draft is preserved!
  await expect(textarea).toHaveValue('Câu nháp đang soạn rất quan trọng');
});

test('Stage 3 Settings View: History management batch delete resets active session if deleted', async ({ page }) => {
  const conv1 = { id: 'c-active', title: 'Hội thoại đang hoạt động', createdAt: '', updatedAt: '', messageCount: 1 };
  const conv2 = { id: 'c-archive', title: 'Hội thoại lưu trữ cũ', createdAt: '', updatedAt: '', messageCount: 1 };

  let currentConversations = [conv1, conv2];
  let batchDeleteCalled = false;

  await page.route('**/api/conversations*', async (route) => {
    return route.fulfill({ status: 200, json: currentConversations });
  });

  await page.route('**/api/conversations/c-active', async (route) => {
    return route.fulfill({
      status: 200,
      json: { conversation: conv1, messages: [{ id: 'm1', conversationId: 'c-active', text: 'Tin nhắn c-active', createdAt: '', sources: ['keyboard'] }] },
    });
  });

  await page.route('**/api/conversations/batch-delete', async (route) => {
    batchDeleteCalled = true;
    const body = route.request().postDataJSON();
    currentConversations = currentConversations.filter((c) => !body.ids.includes(c.id));
    return route.fulfill({ status: 200, json: { deletedCount: body.ids.length } });
  });

  await page.goto('/');

  // Load conv1 as active conversation
  await page.getByTestId('history-button').click();
  await page.getByTestId('history-item-c-active').click();
  await expect(page.getByTestId('conversation-title-input')).toHaveValue('Hội thoại đang hoạt động');

  // Enter some draft
  const textarea = page.getByTestId('composer-textarea');
  await textarea.fill('Nháp trong c-active');

  // Open Settings and go to History tab
  await page.getByTestId('settings-button').click();
  await page.getByTestId('settings-tab-history').click();

  const historyList = page.getByTestId('history-management-list');
  await expect(historyList).toBeVisible();

  // Select all
  const selectAllBtn = page.getByTestId('history-select-all-button');
  await expect(selectAllBtn).toHaveText('Chọn 2 kết quả');
  await selectAllBtn.click();
  await expect(selectAllBtn).toHaveText('Bỏ chọn tất cả');

  // Batch delete button
  const deleteBtn = page.getByTestId('batch-delete-button');
  await expect(deleteBtn).toHaveText('Xóa 2 hội thoại');
  await deleteBtn.click();
  expect(batchDeleteCalled).toBe(true);

  // Close settings
  await page.getByTestId('settings-back-button').click();

  // Since active conversation was deleted, active session reset to blank and draft cleared!
  await expect(page.getByTestId('conversation-title-locked')).toHaveText('Hội thoại mới');
  await expect(textarea).toHaveValue('');
  await expect(page.getByTestId('message-card')).toHaveCount(0);
});

test('real HTTP rejects cross-origin settings writes and missing-key recognition', async ({ request }) => {
  const rejected = await request.put('/api/settings', { headers: { Origin: 'https://other.example' }, data: { apiKey: fakeKey } });
  expect(rejected.status()).toBe(403);
  const response = await request.post('/api/transcriptions', { headers: { Origin: 'http://127.0.0.1:3111' } });
  expect(response.status()).toBe(409);
  expect((await response.json()).error.code).toBe('key_missing');
});

test('real HTTP saves a fixture key, redacts reads and explicitly deletes it without calling STT', async ({ request }) => {
  const headers = { Origin: 'http://127.0.0.1:3111' };
  try {
    const saved = await request.put('/api/settings', { headers, data: { apiKey: fakeKey, model: 'nova-2' } });
    expect(saved.status()).toBe(200);
    expect(await saved.text()).not.toContain(fakeKey);
    const read = await request.get('/api/settings');
    const data = await read.json();
    expect(data.hasApiKey).toBe(true);
    expect(data.model).toBe('nova-2');
    expect(data.language).toBe('vi');
    expect(JSON.stringify(data)).not.toContain(fakeKey);
  } finally {
    const cleared = await request.put('/api/settings', { headers, data: { clearApiKey: true, model: 'nova-3' } });
    expect(cleared.status()).toBe(200);
    expect((await cleared.json()).hasApiKey).toBe(false);
  }
});

test('Electron opens the same local UI with isolated renderer', async ({}, info) => {
  const env: Record<string, string> = Object.fromEntries(
    Object.entries(process.env).filter((item): item is [string, string] => item[1] !== undefined)
  );
  env.PBL6_STT_APP_URL = 'http://127.0.0.1:3111';
  env.PBL6_STT_DESKTOP_DATA_DIR = info.outputPath('electron-profile');
  delete env.ELECTRON_RUN_AS_NODE;
  const desktop = await _electron.launch({ args: [resolve('electron/main.cjs')], env });
  try {
    const window = await desktop.firstWindow();
    await expect(window.getByTestId('conversation-title-locked')).toHaveText('Hội thoại mới');
    const globals = await window.evaluate(() => ({ require: 'require' in window, process: 'process' in window }));
    expect(globals.require).toBe(false);
    expect(globals.process).toBe(false);
    await window.screenshot({ path: info.outputPath('electron-screen.png'), fullPage: true });
  } finally {
    await desktop.close();
  }
});

test('Windows production launcher creates a visible Electron window', async () => {
  test.skip(process.platform !== 'win32', 'Windows window-visibility regression');
  test.setTimeout(60000);
  const directory = await mkdtemp(join(tmpdir(), 'pbl6-visible-desktop-'));
  const child = spawn(process.execPath, ['scripts/desktop.mjs'], {
    cwd: process.cwd(),
    windowsHide: true,
    stdio: 'ignore',
    env: {
      ...process.env,
      PBL6_STT_PORT: '3112',
      PBL6_STT_CONFIG_DIR: join(directory, 'config'),
      PBL6_STT_DESKTOP_DATA_DIR: join(directory, 'profile'),
      NEXT_TELEMETRY_DISABLED: '1',
    },
  });
  try {
    await expect
      .poll(
        async () => {
          if (child.exitCode !== null) return `launcher exited ${child.exitCode}`;
          const script = `$items = Get-CimInstance Win32_Process -Filter \"ParentProcessId = ${child.pid}\" | Where-Object { $_.Name -eq 'electron.exe' }; foreach ($item in $items) { $p = Get-Process -Id $item.ProcessId -ErrorAction SilentlyContinue; if ($p.MainWindowHandle -ne 0) { $p.MainWindowTitle } }`;
          return execFileSync(
            'powershell.exe',
            ['-NoProfile', '-NonInteractive', '-Command', script],
            { encoding: 'utf8', windowsHide: true }
          ).trim();
        },
        { timeout: 45000, intervals: [500, 1000] }
      )
      .toBe('STT · Tiếng Việt');
  } finally {
    if (child.pid && child.exitCode === null) {
      try {
        execFileSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], {
          stdio: 'ignore',
          windowsHide: true,
        });
      } catch {}
    }
    await rm(directory, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
  }
});
