import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { MAX_AUDIO_BYTES } from '../src/contracts';
import { readSettings, publicSettings, updateSettings, type Settings } from '../src/server/settings';
import { AppError, errorResponse } from '../src/server/errors';
import { requireLocalOrigin, boundedBody } from '../src/server/http';
import { readAudio } from '../src/server/audio';
import { transcribe } from '../src/server/deepgram';
import { getSettings, putSettings, makeTranscriptionHandler } from '../src/server/handlers';

const fakeKey = 'TEST_NOT_A_REAL_KEY_0123456789';
const origin = 'http://127.0.0.1:3100';
let directory: string;
const previous = process.env.PBL6_STT_CONFIG_DIR;
beforeEach(async () => { directory = await mkdtemp(join(tmpdir(), 'pbl6-stt-test-')); process.env.PBL6_STT_CONFIG_DIR = directory; });
afterEach(async () => {
  if (previous === undefined) delete process.env.PBL6_STT_CONFIG_DIR; else process.env.PBL6_STT_CONFIG_DIR = previous;
  await rm(directory, { recursive: true, force: true });
});
function request(path = '/api/transcriptions', init: RequestInit = {}) {
  return new Request(origin + path, { method: 'POST', ...init, headers: { Origin: origin, ...init.headers } });
}
function wav(): Uint8Array {
  const b = new Uint8Array(76); const v = new DataView(b.buffer);
  for (const [offset, text] of [[0, 'RIFF'], [8, 'WAVE'], [12, 'fmt '], [36, 'data']] as const)
    b.set(new TextEncoder().encode(text), offset);
  v.setUint32(4, 68, true); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, 16000, true); v.setUint32(28, 32000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); v.setUint32(40, 32, true);
  return b;
}
function upload(name = 'sample.wav', bytes = wav()) {
  const form = new FormData(); form.append('file', new Blob([bytes as BlobPart]), name);
  return request(undefined, { body: form });
}
const settings: Settings = { schemaVersion: 1, apiKey: fakeKey, model: 'nova-3', timeoutSeconds: 15 };
const audio = { name: 'sample.wav', bytes: wav(), contentType: 'audio/wav' };
function mockFetch(handler: (url: URL, init: RequestInit) => Response | Promise<Response>): typeof fetch {
  return ((url: string | URL, init: RequestInit) => Promise.resolve(handler(new URL(String(url)), init))) as typeof fetch;
}
function providerResult(text: unknown = 'Xin chào Đà Nẵng.') {
  return { metadata: { duration: 1.5, request_id: 'fixture-request' }, results: { channels: [{ alternatives: [{ transcript: text }] }] } };
}

test('defaults are Vietnamese Nova-3; public settings contain no key field', async () => {
  assert.deepEqual(publicSettings(await readSettings()), { provider: 'deepgram', language: 'vi', model: 'nova-3', timeoutSeconds: 60, hasApiKey: false });
});
test('save, preserve blank key, change model and explicitly delete key', async () => {
  const output = await updateSettings({ apiKey: fakeKey });
  assert.equal(output.hasApiKey, true); assert.ok(!JSON.stringify(output).includes(fakeKey));
  await updateSettings({ apiKey: '', model: 'nova-2' });
  assert.equal((await readSettings()).apiKey, fakeKey); assert.equal((await readSettings()).model, 'nova-2');
  await updateSettings({ clearApiKey: true }); assert.equal((await readSettings()).apiKey, '');
});
test('invalid settings and secret-bearing inputs are rejected without echo', async () => {
  for (const input of [null, [], { language: 'en' }, { model: 'unknown' }, { timeoutSeconds: 14 }, { timeoutSeconds: 15.5 },
    { apiKey: fakeKey + '\n' }, { clearApiKey: 'yes' }, { apiKey: fakeKey, clearApiKey: true }]) {
    await assert.rejects(updateSettings(input), AppError);
  }
  const response = errorResponse(new Error(fakeKey));
  assert.ok(!(await response.text()).includes(fakeKey));
});
test('concurrent updates preserve the key and both validated changes', async () => {
  await Promise.all([updateSettings({ apiKey: fakeKey }), updateSettings({ model: 'nova-2', timeoutSeconds: 90 })]);
  assert.deepEqual(await readSettings(), { ...settings, model: 'nova-2', timeoutSeconds: 90 });
});
test('corrupted settings fail visibly and are never overwritten', async () => {
  await writeFile(join(directory, 'settings.json'), 'BROKEN_CONFIG');
  await assert.rejects(readSettings(), { code: 'settings_invalid' });
  await assert.rejects(updateSettings({ apiKey: fakeKey }), { code: 'settings_invalid' });
  assert.equal(await readFile(join(directory, 'settings.json'), 'utf8'), 'BROKEN_CONFIG');
});
test('local-origin guard rejects foreign origins, missing mutation origin and LAN hosts', () => {
  requireLocalOrigin(request(), true);
  assert.throws(() => requireLocalOrigin(request(undefined, { headers: { Origin: 'https://other.example' } }), true), { code: 'origin_denied' });
  assert.throws(() => requireLocalOrigin(new Request(origin), true), { code: 'origin_denied' });
  assert.throws(() => requireLocalOrigin(new Request('http://192.168.1.2:3100')), { code: 'local_only' });
  requireLocalOrigin(new Request('http://localhost:3100/api/settings', {
    headers: { Host: '127.0.0.1:3100', Origin: origin },
  }), true);
  assert.throws(() => requireLocalOrigin(request(undefined, { headers: { Host: 'other.example', Origin: origin } }), true), { code: 'local_only' });
});
test('body limit works for streamed input without content-length', async () => {
  await assert.rejects(boundedBody(request(undefined, { body: '12345' }), 4), { code: 'body_too_large' });
  await assert.rejects(boundedBody(request(undefined, { body: '1', headers: { 'Content-Length': String(MAX_AUDIO_BYTES + 1) } }), MAX_AUDIO_BYTES), { code: 'body_too_large' });
});
test('multipart accepts a valid WAV and derives its content type from content', async () => {
  const value = await readAudio(upload()); assert.equal(value.contentType, 'audio/wav'); assert.deepEqual(value.bytes, wav());
});
test('multipart rejects empty, disguised, unsupported and multiple files', async () => {
  await assert.rejects(readAudio(upload('empty.wav', new Uint8Array())), { code: 'audio_empty' });
  await assert.rejects(readAudio(upload('fake.wav', new TextEncoder().encode('this is not a WAV'))), { code: 'audio_format' });
  await assert.rejects(readAudio(upload('audio.exe')), { code: 'audio_format' });
  const form = new FormData(); form.append('file', new Blob([wav() as BlobPart]), 'one.wav'); form.append('file', new Blob([wav() as BlobPart]), 'two.wav');
  await assert.rejects(readAudio(request(undefined, { body: form })), { code: 'one_file_required' });
});
test('oversized audio is rejected after bounded multipart parsing', async () => {
  await assert.rejects(readAudio(upload('large.wav', new Uint8Array(MAX_AUDIO_BYTES + 1))), { code: 'audio_too_large' });
});
test('Deepgram request uses official HTTPS endpoint, vi and selected model; raw bytes preserved', async () => {
  const output = await transcribe(audio, settings, undefined, mockFetch((url, init) => {
    assert.equal(url.origin + url.pathname, 'https://api.deepgram.com/v1/listen');
    assert.equal(url.searchParams.get('language'), 'vi'); assert.equal(url.searchParams.get('model'), 'nova-3');
    assert.equal(url.searchParams.has('interim_results'), false); assert.equal(init.redirect, 'error');
    assert.equal((init.headers as Record<string, string>).Authorization, `Token ${fakeKey}`);
    assert.deepEqual(init.body, audio.bytes);
    return Response.json(providerResult());
  }));
  assert.equal(output.text, 'Xin chào Đà Nẵng.'); assert.equal(output.status, 'completed');
  assert.equal(output.audioSeconds, 1.5); assert.ok(output.sessionId); assert.ok(!JSON.stringify(output).includes(fakeKey));
});
test('empty transcript is explicit, not a fabricated recognition', async () => {
  const output = await transcribe(audio, settings, undefined, mockFetch(() => Response.json(providerResult(''))));
  assert.equal(output.status, 'completed_empty'); assert.equal(output.text, '');
});
test('provider auth, limit, availability and request errors are classified and redacted', async () => {
  for (const [status, code] of [[401, 'provider_auth'], [403, 'provider_auth'], [429, 'provider_limit'], [500, 'provider_unavailable'], [400, 'provider_rejected']] as const) {
    try {
      await transcribe(audio, settings, undefined, mockFetch(() => new Response(fakeKey, { status })));
      assert.fail('Expected provider failure');
    } catch (e) { assert.equal((e as AppError).code, code); assert.ok(!(e as Error).message.includes(fakeKey)); }
  }
});
test('provider network errors never leak the underlying exception', async () => {
  await assert.rejects(transcribe(audio, settings, undefined, mockFetch(() => { throw Error(fakeKey); })), { code: 'provider_network' });
});
test('malformed JSON and missing transcript fail, rather than reporting success', async () => {
  for (const response of [new Response('bad json'), Response.json({}), Response.json(providerResult(7))]) {
    await assert.rejects(transcribe(audio, settings, undefined, mockFetch(() => response)), { code: 'provider_response' });
  }
});
test('timeout and client cancellation are explicit failures', async () => {
  const pendingFetch = mockFetch((_url, init) => new Promise((_resolve, reject) => {
    const handle = setTimeout(() => reject(Error('test would hang')), 1000);
    const rejectAbort = () => { clearTimeout(handle); reject(init.signal?.reason); };
    if (init.signal?.aborted) rejectAbort(); else init.signal?.addEventListener('abort', rejectAbort, { once: true });
  }));
  await assert.rejects(transcribe(audio, { ...settings, timeoutSeconds: .005 }, undefined, pendingFetch), { code: 'provider_timeout' });
  const controller = new AbortController(); controller.abort();
  await assert.rejects(transcribe(audio, settings, controller.signal, pendingFetch), { code: 'request_cancelled' });
});
test('missing key prevents upload parsing and provider invocation', async () => {
  const handler = makeTranscriptionHandler({ readSettings: async () => ({ ...settings, apiKey: '' }),
    readAudio: async () => { assert.fail('No audio read before key validation'); }, transcribe });
  const response = await handler(request()); assert.equal(response.status, 409);
  assert.equal((await response.json()).error.code, 'key_missing');
});
test('transcription route returns a complete fixture result', async () => {
  const handler = makeTranscriptionHandler({ readSettings: async () => settings, readAudio,
    transcribe: (a, s, signal) => transcribe(a, s, signal, mockFetch(() => Response.json(providerResult()))) });
  const response = await handler(upload()); assert.equal(response.status, 200);
  assert.equal((await response.json()).text, 'Xin chào Đà Nẵng.');
});
test('concurrent requests are refused and lock is released after failure', async () => {
  let entered!: () => void; const entry = new Promise<void>(r => { entered = r; });
  let release!: () => void; const held = new Promise<void>(r => { release = r; });
  const handler = makeTranscriptionHandler({ readSettings: async () => settings, readAudio,
    transcribe: async () => { entered(); await held; throw new AppError('provider_network', 'Offline fixture', 502); } });
  const first = handler(upload()); await entry;
  const second = await handler(upload()); assert.equal(second.status, 409); assert.equal((await second.json()).error.code, 'busy');
  release(); assert.equal((await first).status, 502);
  const third = await handler(upload()); assert.equal(third.status, 502);
});
test('settings HTTP handlers validate JSON and never return stored credentials', async () => {
  const saved = await putSettings(request('/api/settings', { method: 'PUT', body: JSON.stringify({ apiKey: fakeKey }) }));
  assert.equal(saved.status, 200); assert.ok(!(await saved.text()).includes(fakeKey));
  const read = await getSettings(new Request(origin + '/api/settings')); assert.equal((await read.json()).hasApiKey, true);
  const invalid = await putSettings(request('/api/settings', { method: 'PUT', body: '{' })); assert.equal(invalid.status, 400);
  const oversized = await putSettings(request('/api/settings', { method: 'PUT', body: 'x'.repeat(4097) })); assert.equal(oversized.status, 413);
});
