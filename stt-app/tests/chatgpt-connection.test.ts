import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash, generateKeyPairSync, sign } from 'node:crypto';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { chatgpt, ChatGptConnection, readCompletedResponse, verifyChatGptIdentity } from '../src/server/chatgptConnection';
import { makeSignSentenceHandler } from '../src/server/signSentence';

const { privateKey, publicKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
const jwk = { ...publicKey.export({ format: 'jwk' }), kid: 'test-key', use: 'sig' };
const jwt = (overrides: Record<string, unknown> = {}) => {
  const h = Buffer.from(JSON.stringify({ alg: 'RS256', kid: 'test-key' })).toString('base64url');
  const p = Buffer.from(JSON.stringify({ iss: 'https://auth.openai.com', aud: 'oaiapp_test', sub: 'test-subject',
    email: 'fixture@example.test', exp: Math.floor(Date.now() / 1000) + 3600, nonce: 'test-nonce', ...overrides })).toString('base64url');
  return `${h}.${p}.${sign('RSA-SHA256', Buffer.from(`${h}.${p}`), privateKey).toString('base64url')}`;
};
const json = (value: unknown) => Response.json(value);
const sse = (events: unknown[]) => new Response(events.map(e => `data: ${JSON.stringify(e)}\n\n`).join(''), { headers: { 'Content-Type': 'text/event-stream' } });

test('ID token requires signed identity, matching issuer/audience/nonce and unexpired claims', () => {
  assert.equal(verifyChatGptIdentity(jwt(), 'oaiapp_test', 'test-nonce', [jwk]).sub, 'test-subject');
  for (const claims of [{ iss: 'https://attacker.test' }, { aud: 'other-client' }, { nonce: 'other-nonce' }, { exp: 1 }]) {
    assert.throws(() => verifyChatGptIdentity(jwt(claims), 'oaiapp_test', 'test-nonce', [jwk]));
  }
  const parts = jwt().split('.'); parts[2] = 'invalid';
  assert.throws(() => verifyChatGptIdentity(parts.join('.'), 'oaiapp_test', 'test-nonce', [jwk]));
});

test('Responses stream must complete; partial text and failed/quota streams never become sentences', async () => {
  const text = JSON.stringify({ status: 'ok', sentence: 'Tôi cần hỗ trợ.' });
  assert.equal(await readCompletedResponse(sse([{ type: 'response.output_text.delta', delta: text }, { type: 'response.completed' }])), text);
  await assert.rejects(readCompletedResponse(sse([{ type: 'response.output_text.delta', delta: text }])));
  await assert.rejects(readCompletedResponse(sse([{ type: 'response.output_text.delta', delta: text }, { type: 'response.failed' }])));
  await assert.rejects(readCompletedResponse(sse([{ type: 'response.incomplete' }])));
  const bytes = new TextEncoder().encode(`data: {"type":"response.output_text.delta","delta":"Tiếng Việt"}\r\n\r\ndata: {"type":"response.completed"}\r\n\r\n`);
  const stream = new ReadableStream<Uint8Array>({ start(c) { for (const byte of bytes) c.enqueue(Uint8Array.of(byte)); c.close(); } });
  assert.equal(await readCompletedResponse(new Response(stream)), 'Tiếng Việt');
});

test('OAuth loopback, private storage, refresh, model selection, structured inference and disconnect', async t => {
  const dir = await mkdtemp(join(tmpdir(), 'pbl6-chatgpt-test-'));
  const glosses = [
    { segmentId: '1', utteranceId: '0', label: 'Xin', labelId: 363, originalLabel: 'Xin', status: 'recognized' },
    { segmentId: '2', utteranceId: '0', label: 'Cảm ơn', labelId: 86, originalLabel: 'Cảm ơn', status: 'recognized' },
  ];
  const modelOutput = { status: 'ok', sentence: 'Xin cảm ơn.' };
  let events: unknown[] = [{ type: 'response.output_text.delta', delta: JSON.stringify(modelOutput) }, { type: 'response.completed' }];
  let auth: URL, grantPlan = false, refreshes = 0, inferenceCalls = 0;
  const transport: typeof fetch = async (input, init) => {
    const url = String(input);
    if (url.endsWith('/.well-known/jwks.json')) return json({ keys: [jwk] });
    if (url.endsWith('/oauth/token')) {
      const form = new URLSearchParams(String(init?.body));
      assert.equal(form.get('client_id'), 'oaiapp_test');
      assert.equal(form.get('resource'), 'https://api.openai.com/v1');
      if (form.get('grant_type') === 'refresh_token') {
        refreshes++; await new Promise(resolve => setTimeout(resolve, 20));
        assert.equal(form.get('refresh_token'), 'TEST_REFRESH_1'); assert.equal(form.has('scope'), false);
        return json({ access_token: 'TEST_ACCESS_2', refresh_token: 'TEST_REFRESH_2', token_type: 'Bearer', expires_in: 3600 });
      }
      assert.equal(createHash('sha256').update(form.get('code_verifier')!).digest('base64url'), auth.searchParams.get('code_challenge'));
      assert.equal(form.get('redirect_uri'), auth.searchParams.get('redirect_uri'));
      return json({ access_token: 'TEST_ACCESS_1', refresh_token: 'TEST_REFRESH_1', token_type: 'Bearer', expires_in: 1,
        id_token: jwt({ nonce: auth.searchParams.get('nonce') }), scope: grantPlan ? 'openid chatgpt.tokens.use.direct' : 'openid' });
    }
    if (url.endsWith('/models')) {
      assert.equal((init?.headers as Record<string, string>).Authorization, 'Bearer TEST_ACCESS_2');
      return json({ models: [{ slug: 'available-model', display_name: 'Available', visibility: 'list' }, { slug: 'hidden-model', visibility: 'hidden' }] });
    }
    if (url.endsWith('/responses')) {
      inferenceCalls++;
      const body = JSON.parse(String(init?.body));
      assert.equal(body.model, 'available-model');
      assert.equal(body.store, false);
      assert.equal(body.stream, true);
      assert.equal(body.instructions.includes(JSON.stringify(modelOutput)), true);
      assert.deepEqual(body.input, [{ role: 'user', content: JSON.stringify({ glosses: glosses.map(({ label, labelId }) => ({ label, labelId })) }) }]);
      assert.deepEqual(body.text.format, {
        type: 'json_schema', name: 'pbl6_sign_sentence', strict: true,
        schema: {
          type: 'object', properties: { status: { type: 'string', enum: ['ok', 'needs_clarification'] }, sentence: { type: 'string' } },
          required: ['status', 'sentence'], additionalProperties: false,
        },
      });
      return sse(events);
    }
    if (url.endsWith('/oauth/revoke')) {
      assert.equal(new URLSearchParams(String(init?.body)).get('token'), 'TEST_REFRESH_2');
      return new Response(null, { status: 200 });
    }
    throw new Error(`Unexpected test endpoint: ${url}`);
  };
  const connection = new ChatGptConnection(() => dir, transport);
  const callback = async (state: string) => {
    const uri = new URL(auth.searchParams.get('redirect_uri')!);
    uri.search = new URLSearchParams({ state, code: 'TEST_CODE', client_id: 'oaiapp_test' }).toString();
    return fetch(uri);
  };
  try {
    auth = new URL((await connection.start()).url);
    const hostId = auth.searchParams.get('ext_agent_host_id');
    assert.equal(auth.searchParams.get('client_id'), 'dynamic_agent_client');
    assert.equal(auth.searchParams.get('agent_name_hint'), 'PBL6');
    assert.equal(auth.searchParams.get('code_challenge_method'), 'S256');
    assert.equal((await callback('invalid-state')).status, 400);
    assert.equal((await connection.status()).pending, true);
    assert.equal((await callback(auth.searchParams.get('state')!)).status, 400);
    assert.equal((await connection.status()).accounts.length, 0);
    grantPlan = true; auth = new URL((await connection.start()).url);
    assert.equal(auth.searchParams.get('ext_agent_host_id'), hostId);
    const okRes = await callback(auth.searchParams.get('state')!);
    assert.equal(okRes.status, 200);
    assert.equal((okRes.headers.get('content-type') || '').includes('text/html'), true);
    const html = await okRes.text();
    assert.equal(html.includes('window.close()'), true);
    assert.equal(html.includes('http://127.0.0.1:3100/'), true);
    assert.equal(html.includes('Đã kết nối ChatGPT'), true);
    const status = await connection.status(), id = status.activeId!;
    assert.equal(status.accounts.length, 1);
    assert.equal(JSON.stringify(status).includes('TEST_ACCESS'), false);
    assert.equal(JSON.stringify(status).includes('TEST_REFRESH'), false);
    assert.deepEqual(await Promise.all([connection.models(id), connection.models(id)]), [
      [{ id: 'available-model', name: 'Available' }], [{ id: 'available-model', name: 'Available' }],
    ]);
    assert.equal(refreshes, 1);
    await assert.rejects(connection.select(id, 'hidden-model'));
    await connection.select(id, 'available-model');
    t.mock.method(chatgpt, 'selected', connection.selected.bind(connection));
    t.mock.method(chatgpt, 'generate', connection.generate.bind(connection));
    const handler = makeSignSentenceHandler();
    const generate = () => handler(new Request('http://localhost:3100/api/sign-sentence', {
      method: 'POST', headers: { origin: 'http://localhost:3100', host: 'localhost:3100', 'Content-Type': 'application/json' },
      body: JSON.stringify({ glosses, requestId: 'trial-subscription' }),
    }));
    const generated = await generate();
    assert.equal(generated.status, 200);
    assert.deepEqual(await generated.json(), {
      status: 'ok', sentence: 'Xin cảm ơn.', needsClarification: false, explanation: '', error: null,
      metadata: { generatedText: 'Xin cảm ơn.', sourceGlossText: 'Xin Cảm ơn', requestId: 'trial-subscription', model: 'available-model' },
    });
    for (const { streamEvents, code } of [
      { streamEvents: [{ type: 'response.output_text.delta', delta: 'Unstructured output' }, { type: 'response.completed' }], code: 'llm_output' },
      { streamEvents: [{ type: 'response.refusal.delta', delta: 'Refusal text' }, { type: 'response.completed' }], code: 'chatgpt_incomplete' },
      { streamEvents: [{ type: 'response.incomplete' }], code: 'chatgpt_incomplete' },
    ]) {
      events = streamEvents;
      const failed = await generate();
      assert.equal(failed.status, 502);
      assert.match(failed.headers.get('content-type') ?? '', /^application\/json\b/);
      const body = await failed.json();
      assert.equal(typeof body.error?.message, 'string');
      assert.deepEqual(body, { status: 'error', sentence: '', needsClarification: false, explanation: '', metadata: null, error: { code, message: body.error.message } });
    }
    assert.equal(inferenceCalls, 4);
    auth = new URL((await connection.start(id)).url);
    assert.equal(auth.searchParams.get('client_id'), 'oaiapp_test');
    assert.equal(auth.searchParams.has('agent_name_hint'), false);
    connection.cancelLogin();
    await connection.disconnect(id);
    await assert.rejects(connection.selected());
    const stored = await readFile(join(dir, 'chatgpt-connections.json'), 'utf8');
    assert.equal(stored.includes('TEST_ACCESS'), false); assert.equal(stored.includes('TEST_REFRESH'), false);
  } finally { connection.cancelLogin(); await rm(dir, { recursive: true, force: true }); }
});
