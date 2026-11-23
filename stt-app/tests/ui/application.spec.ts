import { test, expect, _electron, type WebSocketRoute } from '@playwright/test';
import { resolve } from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const fakeKey = 'TEST_NOT_A_REAL_KEY_0123456789';

test('unclear gloss waits for correction, generated sentence waits for review, edited sentence is sent', async ({ page }) => {
  const candidate = (label: string, label_id: number, score: number) => ({ label, label_id, score });
  const record = (id: string, top5: ReturnType<typeof candidate>[], low = false) => ({
    segment_id: id, utterance_id: '0', start: 0, movement_start: 0, movement_end: 1, end: 1,
    raw: { top1_label: top5[0].label, top1_id: top5[0].label_id, confidence: top5[0].score, low_confidence: low, top5 },
  });
  const glosses = [record('1', [candidate('Bố', 33, .99)]), record('2', [candidate('Ăn', 10, .4), candidate('Đi', 380, .3), candidate('Uống', 11, .2)], true), record('3', [candidate('Bệnh viện', 32, .99)])];
  let socket: WebSocketRoute;
  await page.routeWebSocket('**/ws/live', ws => {
    socket = ws;
    ws.send(JSON.stringify({ type: 'snapshot', snapshot: { session_id: 'sentence-ui', epoch: 1, running: true, draining: false,
      segmenter_state: 'READY', arms: ['rest', 'rest'], queue_depth: 0, capture_fps: 20, glosses, utterances: [] } }));
  });
  await page.route('**/api/session/glosses/2/candidate', async route => {
    const headers = { 'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST', 'access-control-allow-headers': 'content-type' };
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    expect(route.request().postDataJSON()).toMatchObject({ session_id: 'sentence-ui', label_id: 380, allow_closed: true });
    const corrected = { ...glosses[1], selected_candidate: glosses[1].raw.top5[1] };
    socket.send(JSON.stringify({ type: 'gloss_corrected', session_id: 'sentence-ui', gloss: corrected }));
    await route.fulfill({ headers, json: { gloss: corrected } });
  });
  let generated = 0, sent = 0;
  await page.route('**/api/sign-sentence', async route => {
    generated++;
    const body = route.request().postDataJSON();
    expect(body.glosses.map((g: { label: string }) => g.label)).toEqual(['Bố', 'Đi', 'Bệnh viện']);
    await route.fulfill({ json: { sentence: 'Bố đi bệnh viện.', needsClarification: false, explanation: '',
      metadata: { generatedText: 'Bố đi bệnh viện.', sourceGlossText: 'Bố Đi Bệnh viện', model: 'fixture-model', requestId: body.requestId } } });
  });
  await page.route('**/api/conversations', async route => {
    if (route.request().method() !== 'POST') return route.fulfill({ json: [] });
    sent++; const body = route.request().postDataJSON();
    expect(body.text).toBe('Bố muốn đi bệnh viện.'); expect(body.signSentence.generatedText).toBe('Bố đi bệnh viện.');
    const now = new Date().toISOString();
    const conversation = { id: 'sentence-conversation', title: body.text, createdAt: now, updatedAt: now, messageCount: 1 };
    await route.fulfill({ status: 201, json: { conversation, message: { id: 'sentence-message', conversationId: conversation.id, createdAt: now, ...body } } });
  });
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Ăn, từ chưa rõ' })).toBeVisible();
  socket!.send(JSON.stringify({ type: 'utterance_ready', utterance: { utterance_id: '0', revision: 1, reason: 'utterance_rest', timestamp: 4, raw_glosses: ['Bố', 'Ăn', 'Bệnh viện'], segments: glosses } }));
  await expect(page.getByTestId('slr-save-message-button')).toBeDisabled();
  expect(generated).toBe(0); expect(sent).toBe(0);
  await page.getByRole('button', { name: 'Đi', exact: true }).click();
  await expect(page.getByTestId('slr-save-message-button')).toBeEnabled();
  expect(generated).toBe(0);
  await page.getByTestId('slr-save-message-button').click();
  const sentence = page.getByTestId('sign-sentence-input');
  await expect(sentence).toHaveValue('Bố đi bệnh viện.');
  await expect(page.getByTestId('message-card')).toHaveCount(0); expect(sent).toBe(0);
  await sentence.fill('Bố muốn đi bệnh viện.');
  await page.getByTestId('sign-sentence-send').click();
  await expect(page.getByTestId('message-text')).toHaveText('Bố muốn đi bệnh viện.');
  expect(generated).toBe(1); expect(sent).toBe(1);
});

test('provider settings keep sidebar in landscape, top tabs in portrait, and select account models', async ({ page }, info) => {
  const account = { id: 'test-account', email: 'fixture@example.test', label: 'Tài khoản thử', connected: true, model: '' };
  const connection = { activeId: account.id, source: 'chatgpt', accounts: [account], pending: false, notice: '' };
  await page.route('**/api/chatgpt*', async route => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      expect(body).toMatchObject({ action: 'select', id: account.id, model: 'available-model' });
      account.model = body.model;
      await route.fulfill({ json: connection });
    } else if (new URL(route.request().url()).searchParams.has('models')) {
      await route.fulfill({ json: { models: [{ id: 'available-model', name: 'Model được cấp quyền' }] } });
    } else await route.fulfill({ json: connection });
  });
  await page.route('**/api/sign-sentence*', route => route.fulfill({ json: { configured: false } }));
  for (const viewport of [{ width: 1024, height: 600 }, { width: 600, height: 1024 }]) {
    await page.setViewportSize(viewport); await page.goto('/');
    await page.getByTestId('settings-button').click();
    await page.getByTestId('settings-tab-slr').click();
    const tabs = page.getByRole('navigation', { name: 'Nhóm cài đặt' });
    const content = page.getByTestId('settings-content');
    const nav = (await tabs.boundingBox())!, main = (await content.boundingBox())!;
    if (viewport.width > viewport.height) expect(nav.x + nav.width).toBeLessThanOrEqual(main.x);
    else expect(nav.y + nav.height).toBeLessThanOrEqual(main.y);
    await expect(page.getByRole('heading', { name: 'Nhà cung cấp AI', exact: true })).toBeVisible();
    await expect(page.getByLabel('API key', { exact: true })).toHaveCount(0);
    const model = page.getByTestId('chatgpt-model');
    await expect(model).toBeEnabled(); await model.selectOption('available-model');
    await expect(model).toHaveValue('available-model');
    await page.getByRole('button', { name: 'Quản lý…', exact: true }).click();
    await expect(page.getByRole('dialog', { name: 'Quản lý ChatGPT', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Đóng', exact: true }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`providers-${viewport.width}.png`) });
  }
});

test('camera and colored status occupy separate portrait halves and stack in landscape', async ({ page }, info) => {
  let live: WebSocketRoute | undefined;
  await page.routeWebSocket('**/ws/live', socket => {
    live = socket;
    socket.send(JSON.stringify({ type: 'snapshot', snapshot: {
      session_id: 'status-layout-test', epoch: 1, running: true, draining: false,
      segmenter_state: 'UNKNOWN', arms: [null, null], queue_depth: 0,
      capture_fps: 20, glosses: [], utterances: [],
    } }));
  });
  await page.setViewportSize({ width: 600, height: 1024 });
  await page.goto('/');
  const video = page.getByTestId('slr-video-panel');
  const status = page.getByTestId('slr-status-panel');
  await expect(status).toHaveAttribute('data-state', 'unknown');
  await expect(status).toHaveCSS('background-color', 'rgb(255, 247, 237)');
  await expect(video.getByTestId('slr-user-status')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Nghe lại', exact: true })).toHaveCount(0);
  for (const width of [600, 768]) {
    await page.setViewportSize({ width, height: 1024 });
    const v = (await video.boundingBox())!;
    const s = (await status.boundingBox())!;
    expect(Math.abs(v.width - s.width)).toBeLessThanOrEqual(1);
    expect(v.y).toBe(s.y);
    expect(v.height).toBe(s.height);
    expect(v.x + v.width).toBeLessThan(s.x);
    expect(s.x + s.width).toBeLessThanOrEqual(width);
  }
  const sendState = (segmenter_state: string, arms: (string | null)[]) => live!.send(JSON.stringify({
    type: 'status', segmenter_state, arms, timestamp: 1, queue_depth: 0, capture_fps: 20,
  }));
  sendState('UNKNOWN', ['rest', 'rest']);
  await expect(status).toHaveAttribute('data-state', 'rest');
  await expect(status).toHaveCSS('background-color', 'rgb(239, 246, 255)');
  sendState('READY', ['rest', 'rest']);
  await expect(status).toHaveAttribute('data-state', 'ready');
  await expect(status).toHaveCSS('background-color', 'rgb(221, 247, 233)');
  await page.screenshot({ path: info.outputPath('portrait-camera-status.png') });
  await page.setViewportSize({ width: 1024, height: 600 });
  const v = (await video.boundingBox())!;
  const s = (await status.boundingBox())!;
  expect(v.y + v.height).toBeLessThan(s.y);
  await expect(page.getByTestId('slr-dock-stop')).toBeInViewport();
});

test('conversation Read button speaks the displayed message in Vietnamese', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'speechSynthesis', { value: {
      cancel() {}, getVoices: () => [],
      speak(u: SpeechSynthesisUtterance) {
        (window as unknown as { spoken: unknown }).spoken = { text: u.text, lang: u.lang };
      },
    } });
  });
  const now = new Date().toISOString();
  const conversation = { id: 'read-test', title: 'Tin nhắn', createdAt: now, updatedAt: now, messageCount: 1 };
  await page.route('**/api/conversations', route => route.fulfill({ json: [conversation] }));
  await page.route('**/api/conversations/read-test', route => route.fulfill({ json: { conversation,
    messages: [{ id: 'read-message', conversationId: conversation.id, text: 'Tôi cần hỗ trợ.', createdAt: now, sources: ['keyboard'] }],
  } }));
  await page.goto('/');
  await page.getByTestId('history-button').click();
  await page.getByTestId('history-item-read-test').click();
  await page.getByTestId('message-read-button').click();
  expect(await page.evaluate(() => (window as unknown as { spoken: unknown }).spoken))
    .toEqual({ text: 'Tôi cần hỗ trợ.', lang: 'vi-VN' });
});

test('portrait settings tabs and signing camera use the full width', async ({ page }) => {
  await page.routeWebSocket('**/ws/live', (socket) => {
    socket.send(JSON.stringify({
      type: 'snapshot',
      snapshot: {
        session_id: 'portrait-test', epoch: 1, running: true, draining: false,
        segmenter_state: 'READY', arms: ['rest', 'rest'], queue_depth: 0,
        capture_fps: 20, glosses: [], utterances: [],
      },
    }));
  });
  await page.setViewportSize({ width: 600, height: 1024 });
  await page.goto('/');
  const dock = page.getByTestId('slr-dock');
  const conversation = page.getByTestId('conversation-area');
  await expect(dock).toBeVisible();
  await expect(dock.getByRole('img')).toHaveCSS('object-fit', 'contain');

  for (const width of [360, 600, 768]) {
    await page.setViewportSize({ width, height: 1024 });
    const cameraBox = (await dock.boundingBox())!;
    const conversationBox = (await conversation.boundingBox())!;
    expect(cameraBox.width).toBe(width);
    expect(cameraBox.y + cameraBox.height).toBeLessThan(conversationBox.y);
    await expect(page.getByTestId('slr-toggle-button')).toBeInViewport();
    await expect(page.getByTestId('send-button')).toBeInViewport();

    await page.getByTestId('settings-button').click();
    const settings = page.getByTestId('settings-content');
    const tabs = await Promise.all(['stt', 'slr', 'history'].map((tab) =>
      page.getByTestId(`settings-tab-${tab}`).boundingBox()));
    const settingsBox = (await settings.boundingBox())!;
    expect(tabs).toHaveLength(3);
    expect(tabs[0]!.y).toBe(tabs[2]!.y);
    expect(tabs[0]!.x).toBeLessThan(tabs[1]!.x);
    expect(tabs[1]!.x).toBeLessThan(tabs[2]!.x);
    expect(tabs[2]!.y + tabs[2]!.height).toBeLessThan(settingsBox.y);
    expect(settingsBox.width).toBe(width);
    await page.getByTestId('settings-tab-slr').click();
    await expect(page.getByTestId('settings-tab-slr')).toHaveAttribute('aria-pressed', 'true');
    await page.getByTestId('settings-back-button').click();
  }

  await page.setViewportSize({ width: 1024, height: 600 });
  const wideDock = (await dock.boundingBox())!;
  const wideConversation = (await conversation.boundingBox())!;
  expect(wideDock.x + wideDock.width).toBeLessThanOrEqual(wideConversation.x);
});

test('Companion can correct an earlier unclear gloss and sync the choice to Pi', async ({ context, page }) => {
  const candidate = (label: string, label_id: number, score: number) => ({ label, label_id, score });
  const gloss = (segment_id: string, top5: ReturnType<typeof candidate>[]) => ({
    segment_id, utterance_id: '0', start: 0, movement_start: 0, movement_end: 1, end: 1,
    raw: {
      top1_label: top5[0].label, top1_id: top5[0].label_id, confidence: top5[0].score,
      low_confidence: true, top5,
    },
  });
  const first = gloss('1', [candidate('Cái bàn', 1, 0.42), candidate('Cái ghế', 2, 0.31), candidate('Cái tủ', 3, 0.16)]);
  const second = gloss('2', [candidate('Bơi lội', 4, 0.42), candidate('Đi bộ', 5, 0.33), candidate('Chạy', 6, 0.11)]);
  const corrected = { ...first, selected_candidate: first.raw.top5[1] };
  const sockets: WebSocketRoute[] = [];
  await context.routeWebSocket('**/ws/live', (socket) => {
    sockets.push(socket);
    socket.send(JSON.stringify({
      type: 'snapshot',
      snapshot: {
        session_id: 'sign-test', epoch: 1, running: true, draining: false,
        segmenter_state: 'READY', arms: ['rest', 'rest'], queue_depth: 0,
        capture_fps: 20, glosses: [first, second], utterances: [],
      },
    }));
  });
  await context.route('**/api/session/glosses/1/candidate', async (route) => {
    const headers = {
      'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST',
      'access-control-allow-headers': 'content-type',
    };
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers });
      return;
    }
    expect(route.request().postDataJSON()).toMatchObject({ session_id: 'sign-test', label_id: 2 });
    for (const socket of sockets) {
      socket.send(JSON.stringify({ type: 'gloss_corrected', session_id: 'sign-test', gloss: corrected }));
    }
    await route.fulfill({ headers, json: { gloss: corrected } });
  });
  await page.goto('/');
  const companion = await context.newPage();
  await companion.goto('/companion');
  await expect(page.getByRole('button', { name: 'Cái bàn, từ chưa rõ' })).toHaveText('Cái bàn');
  await expect(companion.getByText('Gợi ý cho “Bơi lội”')).toBeVisible();
  const earlier = companion.getByRole('button', { name: 'Cái bàn, từ chưa rõ' });
  const latest = companion.getByRole('button', { name: 'Bơi lội, từ chưa rõ' });
  await expect(latest).toHaveAttribute('aria-pressed', 'true');
  const restingBorder = await earlier.evaluate((button) => getComputedStyle(button).borderTopColor);
  await earlier.click();
  await expect(earlier).toHaveAttribute('aria-pressed', 'true');
  await expect(latest).toHaveAttribute('aria-pressed', 'false');
  expect(await earlier.evaluate((button) => getComputedStyle(button).borderTopColor)).not.toBe(restingBorder);
  await expect(companion.getByText('Gợi ý cho “Cái bàn”')).toBeVisible();
  await companion.getByRole('button', { name: 'Cái ghế', exact: true }).click();
  for (const display of [page, companion]) {
    await expect(display.getByText('Cái ghế', { exact: true })).toBeVisible();
    await expect(display.getByRole('button', { name: 'Cái bàn, từ chưa rõ' })).toHaveCount(0);
  }

  await page.route('**/api/conversations', async (route) => {
    if (route.request().method() !== 'POST') return route.continue();
    const timestamp = new Date().toISOString();
    const conversation = { id: 'sign-conversation', title: 'Ký trực tiếp', createdAt: timestamp, updatedAt: timestamp, messageCount: 1 };
    await route.fulfill({
      status: 201,
      json: {
        conversation,
        message: { id: 'sign-message', conversationId: conversation.id, createdAt: timestamp, ...route.request().postDataJSON() },
      },
    });
  });
  const saved = page.waitForRequest((request) =>
    request.url().endsWith('/api/conversations') && request.method() === 'POST');
  sockets[0].send(JSON.stringify({
    type: 'utterance_ready',
    utterance: { utterance_id: '0', raw_glosses: ['Cái bàn', 'Bơi lội'], segments: [corrected, second] },
  }));
  expect((await saved).postDataJSON()).toMatchObject({
    text: 'Cái ghế Bơi lội',
    signGlosses: [
      { label: 'Cái ghế', originalLabel: 'Cái bàn', status: 'confirmed', top3: first.raw.top5 },
      { label: 'Bơi lội', status: 'unconfirmed', top3: second.raw.top5 },
    ],
  });
  const savedMessage = page.getByTestId('message-card');
  await expect(savedMessage.getByTestId('message-text')).toHaveText('Cái ghế Bơi lội');
  await expect(savedMessage.getByLabel('Bơi lội, từ chưa rõ')).toHaveClass(/bg-orange-100/);
});

test('initial screen displays Header, empty conversation, and composer with idle mic and disabled Send', async ({ page }, info) => {
  await page.goto('/');
  // Header controls
  await expect(page.getByTestId('history-button')).toHaveText('Hội thoại');
  await expect(page.getByTestId('conversation-title-locked')).toHaveCount(0);
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

test('typing enables Send and creates a conversation without a header title', async ({ page }, info) => {
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
  await expect(messageCard.getByTestId('message-text')).toHaveText('Xin chào bạn');

  // Conversation names belong to history, not the chat header.
  await expect(page.getByTestId('conversation-title-input')).toHaveCount(0);
  await expect(page.locator('header').first().getByText('Xin chào bạn', { exact: true })).toHaveCount(0);

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
  await page.addInitScript(() => {
    // This test mocks the server recorder rather than the browser microphone.
    Object.defineProperty(navigator, 'mediaDevices', { value: undefined });
  });
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
  await expect(micButton).toHaveAttribute('data-status', 'recording');
  expect(recordStarted).toBe(true);

  // Click Send during recording
  await sendButton.click();
  expect(recordStopped).toBe(true);

  // Combined message sent automatically
  await expect(page.getByTestId('message-card')).toHaveCount(1);
  await expect(page.getByTestId('message-text')).toHaveText('Tôi muốn hẹn gặp vào sáng mai');
  expect(sentText).toBe('Tôi muốn hẹn gặp vào sáng mai');
  expect(sentSources).toContain('voice');
});

test('smart latch: clicking Send during transcribing (after stopping) auto-sends once transcript arrives', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'mediaDevices', { value: undefined });
  });
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
  await expect(page.getByTestId('message-text')).toHaveText('Tôi muốn hẹn gặp vào sáng mai');
  expect(sentText).toBe('Tôi muốn hẹn gặp vào sáng mai');
});

test('chat header has one row without a title in landscape and portrait, while history keeps names', async ({ page }) => {
  const now = new Date().toISOString();
  const conversation = { id: 'header-history-test', title: 'Tên chỉ nằm trong lịch sử', createdAt: now, updatedAt: now, messageCount: 1 };
  const message = { id: 'header-message', conversationId: conversation.id, text: 'Nội dung hội thoại đã lưu', createdAt: now, sources: ['keyboard'] };
  await page.route('**/api/conversations', route => route.fulfill({ json: [conversation] }));
  await page.route('**/api/conversations/header-history-test', route => route.fulfill({ json: { conversation, messages: [message] } }));
  for (const viewport of [{ width: 1024, height: 600 }, { width: 600, height: 1024 }, { width: 768, height: 1024 }]) {
    await page.setViewportSize(viewport);
    await page.goto('/');
    const header = page.locator('header').first();
    await expect(page.getByTestId('conversation-title-locked')).toHaveCount(0);
    await expect(page.getByLabel('Tiêu đề hội thoại')).toHaveCount(0);
    await page.getByTestId('history-button').click();
    const historyItem = page.getByTestId('history-item-header-history-test');
    await expect(historyItem).toContainText(conversation.title);
    await historyItem.click();
    await expect(page.getByTestId('message-text')).toHaveText(message.text);
    await expect(header.getByText(conversation.title, { exact: true })).toHaveCount(0);
    await expect(page.getByTestId('conversation-title-input')).toHaveCount(0);
    const box = (await header.boundingBox())!;
    expect(box.height).toBeLessThanOrEqual(64);
    for (const id of ['history-button', 'slr-toggle-button', 'settings-button']) {
      await expect(page.getByTestId(id)).toBeInViewport();
      const button = (await page.getByTestId(id).boundingBox())!;
      expect(button.y + button.height).toBeLessThanOrEqual(box.y + box.height);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
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

test('the Pi conversation and controls fit above a system keyboard overlay', async ({ page }, info) => {
  await page.setViewportSize({ width: 1024, height: 600 });
  await page.addInitScript(() => {
    Object.defineProperty(window.screen, 'height', { value: 600 });
    Object.defineProperty(window, 'electronAPI', {
      value: {
        onScreenKeyboardChange: (listener: (visible: boolean) => void) => {
          const handle = (event: Event) => listener((event as CustomEvent<boolean>).detail);
          window.addEventListener('test:system-keyboard', handle);
          return () => window.removeEventListener('test:system-keyboard', handle);
        },
      },
    });
  });
  await page.goto('/');
  await page.getByTestId('composer-textarea').fill('Ngày mai chúng ta không có bài kiểm tra.');
  const showKeyboard = (visible: boolean) => page.evaluate((detail) => {
    window.dispatchEvent(new CustomEvent('test:system-keyboard', { detail }));
  }, visible);
  const bottom = async (id: string) => {
    const box = await page.getByTestId(id).boundingBox();
    if (!box) throw new Error(`Missing element: ${id}`);
    return box.y + box.height;
  };

  await expect.poll(() => bottom('composer')).toBe(600);
  await showKeyboard(true);
  await expect.poll(() => bottom('composer')).toBe(348);
  for (const id of ['composer-textarea', 'mic-button', 'send-button']) {
    expect(await bottom(id)).toBeLessThanOrEqual(348);
  }
  expect((await page.getByTestId('conversation-area').boundingBox())?.height).toBeGreaterThan(0);
  await expect(page.getByTestId('composer-textarea')).toBeFocused();
  await page.screenshot({ path: info.outputPath('pi-keyboard-overlay-1024x600.png') });

  await page.setViewportSize({ width: 1024, height: 320 });
  await expect.poll(() => bottom('composer')).toBe(320);
  await page.setViewportSize({ width: 1024, height: 600 });
  await showKeyboard(false);
  await expect.poll(() => bottom('composer')).toBe(600);
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
  await expect(page.getByTestId('conversation-title-locked')).toHaveCount(0);

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
  await expect(page.getByTestId('conversation-title-input')).toHaveCount(0);
  await expect(page.getByTestId('message-text')).toHaveText('Nội dung tin nhắn trong A');

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
  await expect(page.getByTestId('message-text')).toHaveText('Tin nhắn c-active');

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
  await expect(page.getByTestId('conversation-title-locked')).toHaveCount(0);
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
    await expect(window.getByTestId('conversation-title-locked')).toHaveCount(0);
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
