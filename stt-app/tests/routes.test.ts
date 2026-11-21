import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  getConversationsHandler,
  postConversationHandler,
  getConversationHandler,
  patchConversationHandler,
  deleteConversationHandler,
  postMessageHandler,
  postBatchDeleteHandler,
  postRecordStartHandler,
  getRecordStatusHandler,
  postRecordStopHandler,
  postRecordCancelHandler,
  getMicrophonesHandler,
  getSettings,
  getOskHandler,
  postOskHandler,
} from '../src/server/handlers';
import { updateSettings } from '../src/server/settings';

const origin = 'http://127.0.0.1:3100';
let configDir: string;
let dataDir: string;
const prevConfig = process.env.PBL6_STT_CONFIG_DIR;
const prevData = process.env.PBL6_STT_DATA_DIR;

beforeEach(async () => {
  configDir = await mkdtemp(join(tmpdir(), 'pbl6-route-config-'));
  dataDir = await mkdtemp(join(tmpdir(), 'pbl6-route-data-'));
  process.env.PBL6_STT_CONFIG_DIR = configDir;
  process.env.PBL6_STT_DATA_DIR = dataDir;
  await updateSettings({ apiKey: 'FAKE_KEY_FOR_TESTS_123456789' });
});

afterEach(async () => {
  if (prevConfig === undefined) delete process.env.PBL6_STT_CONFIG_DIR; else process.env.PBL6_STT_CONFIG_DIR = prevConfig;
  if (prevData === undefined) delete process.env.PBL6_STT_DATA_DIR; else process.env.PBL6_STT_DATA_DIR = prevData;
  await rm(configDir, { recursive: true, force: true });
  await rm(dataDir, { recursive: true, force: true });
});

function req(path: string, init: RequestInit = {}) {
  return new Request(origin + path, {
    ...init,
    headers: {
      Origin: origin,
      Host: '127.0.0.1:3100',
      ...init.headers,
    },
  });
}

test('Conversations API: create, list, get, patch, message, batch-delete, delete', async () => {
  // 1. Create conversation with first message
  const createRes = await postConversationHandler(
    req('/api/conversations', {
      method: 'POST',
      body: JSON.stringify({ text: 'Chào mừng bạn đến với ứng dụng PBL6', sources: ['voice'] }),
    })
  );
  assert.equal(createRes.status, 201);
  const created = await createRes.json();
  assert.ok(created.conversation.id);
  assert.equal(created.conversation.title, 'Chào mừng bạn đến với ứng dụng PBL6');
  assert.equal(created.message.text, 'Chào mừng bạn đến với ứng dụng PBL6');
  assert.deepEqual(created.message.sources, ['voice']);

  const convId = created.conversation.id;

  // 2. List conversations
  const listRes = await getConversationsHandler(req('/api/conversations'));
  assert.equal(listRes.status, 200);
  const list = await listRes.json();
  assert.equal(list.length, 1);
  assert.equal(list[0].id, convId);

  // 3. Get single conversation
  const getRes = await getConversationHandler(req(`/api/conversations/${convId}`), {
    params: Promise.resolve({ id: convId }),
  });
  assert.equal(getRes.status, 200);
  const getDetail = await getRes.json();
  assert.equal(getDetail.conversation.id, convId);
  assert.equal(getDetail.messages.length, 1);

  // 4. Append message
  const msgRes = await postMessageHandler(req(`/api/conversations/${convId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ text: 'Tôi muốn hẹn gặp vào sáng mai.', sources: ['keyboard'] }),
  }), {
    params: Promise.resolve({ id: convId }),
  });
  assert.equal(msgRes.status, 201);
  const appended = await msgRes.json();
  assert.equal(appended.conversationId, convId);
  assert.equal(appended.text, 'Tôi muốn hẹn gặp vào sáng mai.');

  // Verify conversation updated
  const getRes2 = await getConversationHandler(req(`/api/conversations/${convId}`), {
    params: Promise.resolve({ id: convId }),
  });
  const detail2 = await getRes2.json();
  assert.equal(detail2.conversation.messageCount, 2);
  assert.equal(detail2.messages.length, 2);

  // 5. Rename conversation
  const patchRes = await patchConversationHandler(req(`/api/conversations/${convId}`, {
    method: 'PATCH',
    body: JSON.stringify({ title: 'Hẹn gặp sáng mai' }),
  }), {
    params: Promise.resolve({ id: convId }),
  });
  assert.equal(patchRes.status, 200);
  const patched = await patchRes.json();
  assert.equal(patched.title, 'Hẹn gặp sáng mai');

  // 6. Delete conversation
  const delRes = await deleteConversationHandler(req(`/api/conversations/${convId}`, {
    method: 'DELETE',
  }), {
    params: Promise.resolve({ id: convId }),
  });
  assert.equal(delRes.status, 200);
  const delData = await delRes.json();
  assert.equal(delData.deleted, true);

  // 7. Verify empty list
  const listRes2 = await getConversationsHandler(req('/api/conversations'));
  assert.equal((await listRes2.json()).length, 0);
});

test('Batch delete API removes selected conversations', async () => {
  const c1 = await (await postConversationHandler(req('/api/conversations', {
    method: 'POST', body: JSON.stringify({ text: 'Conv 1' }),
  }))).json();
  const c2 = await (await postConversationHandler(req('/api/conversations', {
    method: 'POST', body: JSON.stringify({ text: 'Conv 2' }),
  }))).json();
  const c3 = await (await postConversationHandler(req('/api/conversations', {
    method: 'POST', body: JSON.stringify({ text: 'Conv 3' }),
  }))).json();

  const batchRes = await postBatchDeleteHandler(req('/api/conversations/batch-delete', {
    method: 'POST',
    body: JSON.stringify({ ids: [c1.conversation.id, c2.conversation.id] }),
  }));
  assert.equal(batchRes.status, 200);
  const batchData = await batchRes.json();
  assert.equal(batchData.deletedCount, 2);

  const remaining = await (await getConversationsHandler(req('/api/conversations'))).json();
  assert.equal(remaining.length, 1);
  assert.equal(remaining[0].id, c3.conversation.id);
});

test('Recording & Devices API handlers execute cleanly', async () => {
  // 1. Status initially idle
  const statusRes = await getRecordStatusHandler(req('/api/record/status'));
  assert.equal(statusRes.status, 200);
  assert.equal((await statusRes.json()).status, 'idle');

  // 2. Microphones list
  const micRes = await getMicrophonesHandler(req('/api/devices/microphones'));
  assert.equal(micRes.status, 200);
  const micData = await micRes.json();
  assert.ok(Array.isArray(micData.devices));

  // 3. Start record
  const startRes = await postRecordStartHandler(req('/api/record/start', {
    method: 'POST',
    body: JSON.stringify({ maxDurationSeconds: 10 }),
  }));
  assert.equal(startRes.status, 200);
  assert.equal((await startRes.json()).state.status, 'recording');

  // 4. Cancel record
  const cancelRes = await postRecordCancelHandler(req('/api/record/cancel', {
    method: 'POST',
  }));
  assert.equal(cancelRes.status, 200);
  assert.equal((await cancelRes.json()).cancelled, true);

  // Status back to idle
  const statusRes2 = await getRecordStatusHandler(req('/api/record/status'));
  assert.equal((await statusRes2.json()).status, 'idle');
});

test('CSRF protection: routes reject non-local origin on mutations', async () => {
  const badReq = new Request(origin + '/api/conversations', {
    method: 'POST',
    headers: {
      Origin: 'https://evil.attacker.com',
      Host: '127.0.0.1:3100',
    },
    body: JSON.stringify({ text: 'Phishing attack' }),
  });

  const res = await postConversationHandler(badReq);
  assert.equal(res.status, 403);
  const body = await res.json();
  assert.equal(body.error.code, 'origin_denied');
});

test('Record start handles empty body and query supports olderThanDays param', async () => {
  // Start with empty body
  const startRes = await postRecordStartHandler(req('/api/record/start', {
    method: 'POST',
  }));
  assert.equal(startRes.status, 200);
  assert.equal((await startRes.json()).state.status, 'recording');

  await postRecordCancelHandler(req('/api/record/cancel', { method: 'POST' }));

  // Query with olderThanDays
  const listRes = await getConversationsHandler(req('/api/conversations?olderThanDays=30'));
  assert.equal(listRes.status, 200);
  assert.deepEqual(await listRes.json(), []);

  // Batch delete with non-string and empty strings filtered out
  const batchRes = await postBatchDeleteHandler(req('/api/conversations/batch-delete', {
    method: 'POST',
    body: JSON.stringify({ ids: [123, null, '', '   '] }),
  }));
  assert.equal(batchRes.status, 200);
  assert.equal((await batchRes.json()).deletedCount, 0);
});

test('Record stop handler accepts multipart WAV audio payload', async () => {
  const formData = new FormData();
  const wavBytes = new Uint8Array(44 + 320);
  wavBytes.set(new TextEncoder().encode('RIFF'), 0);
  wavBytes.set(new TextEncoder().encode('WAVE'), 8);
  const blob = new Blob([wavBytes], { type: 'audio/wav' });
  formData.append('audio', blob, 'test.wav');

  const stopReq = new Request(origin + '/api/record/stop', {
    method: 'POST',
    headers: {
      Origin: origin,
      Host: '127.0.0.1:3100',
    },
    body: formData,
  });

  const res = await postRecordStopHandler(stopReq);
  // With mock or fake key, verify handler handles request properly (200 or 502 with valid error structure)
  assert.ok(res.status === 200 || res.status === 502);
  const data = await res.json();
  if (res.status === 200) {
    assert.equal(data.success, true);
  } else {
    assert.ok(data.error);
  }
});

test('LAN companion read access allows GET conversations from RFC1918 LAN while keeping mutations and settings loopback-only', async () => {
  const createRes = await postConversationHandler(req('/api/conversations', {
    method: 'POST',
    body: JSON.stringify({ text: 'Xin chào từ Kiosk', sources: ['sign'] }),
  }));
  assert.equal(createRes.status, 201);
  const { conversation } = await createRes.json();

  const lanHost = '192.168.1.50:3100';
  const lanOrigin = `http://${lanHost}`;
  const lanHeaders = { Host: lanHost, Origin: lanOrigin };

  const lanList = await getConversationsHandler(new Request(`${lanOrigin}/api/conversations`, { headers: lanHeaders }));
  assert.equal(lanList.status, 200);
  const listData = await lanList.json();
  assert.equal(listData.length, 1);

  const lanDetail = await getConversationHandler(
    new Request(`${lanOrigin}/api/conversations/${conversation.id}`, { headers: lanHeaders }),
    { params: Promise.resolve({ id: conversation.id }) }
  );
  assert.equal(lanDetail.status, 200);
  assert.equal((await lanDetail.json()).messages[0].text, 'Xin chào từ Kiosk');

  const lanCreateBlocked = await postConversationHandler(new Request(`${lanOrigin}/api/conversations`, {
    method: 'POST',
    headers: lanHeaders,
    body: JSON.stringify({ text: 'Blocked remote mutation', sources: ['keyboard'] }),
  }));
  assert.equal(lanCreateBlocked.status, 403);
  assert.equal((await lanCreateBlocked.json()).error.code, 'local_only');

  const lanSettingsBlocked = await getSettings(new Request(`${lanOrigin}/api/settings`, { headers: lanHeaders }));
  assert.equal(lanSettingsBlocked.status, 403);
  assert.equal((await lanSettingsBlocked.json()).error.code, 'local_only');
});

test('OSK endpoint toggles visibility on loopback and blocks non-local origins', async () => {
  const showRes = await postOskHandler(req('/api/osk', {
    method: 'POST',
    body: JSON.stringify({ visible: true }),
  }));
  assert.equal(showRes.status, 200);
  assert.equal((await showRes.json()).visible, true);

  const getRes = await getOskHandler(req('/api/osk'));
  assert.equal(getRes.status, 200);
  assert.equal((await getRes.json()).visible, true);

  const toggleOffRes = await postOskHandler(req('/api/osk', { method: 'POST' }));
  assert.equal(toggleOffRes.status, 200);
  assert.equal((await toggleOffRes.json()).visible, false);

  const lanOrigin = 'http://192.168.1.50:3100';
  const lanBlocked = await postOskHandler(new Request(`${lanOrigin}/api/osk`, {
    method: 'POST',
    headers: { Host: '192.168.1.50:3100', Origin: lanOrigin },
    body: JSON.stringify({ visible: true }),
  }));
  assert.equal(lanBlocked.status, 403);
  assert.equal((await lanBlocked.json()).error.code, 'local_only');
});
