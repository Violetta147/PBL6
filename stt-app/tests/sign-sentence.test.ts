import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { makeSignSentenceHandler, putSentenceConfiguration, sentenceConfiguration } from '../src/server/signSentence';
import { createConversationWithFirstMessage, getConversationWithMessages, listConversations } from '../src/server/storage';
import type { SignGloss } from '../src/contracts';

const glosses: SignGloss[] = [
  { segmentId: '1', utteranceId: '0', label: 'Bố', labelId: 33, originalLabel: 'Bố', status: 'recognized', top3: [] },
  { segmentId: '2', utteranceId: '0', label: 'Đi', labelId: 380, originalLabel: 'Ăn', status: 'confirmed', top3: [] },
  { segmentId: '3', utteranceId: '0', label: 'Bệnh viện', labelId: 32, originalLabel: 'Bệnh viện', status: 'recognized', top3: [] },
];
function request(body: unknown, method = 'POST', origin = 'http://localhost:3100') {
  return new Request('http://localhost:3100/api/sign-sentence', { method, headers: { origin, host: 'localhost:3100', 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

test('Real HTTP adapter, reviewed sentence storage, and guarded failures', async t => {
  const dir = await mkdtemp(join(tmpdir(), 'pbl6-sentence-'));
  const previous = { ...process.env };
  process.env.PBL6_STT_CONFIG_DIR = dir; process.env.PBL6_STT_DATA_DIR = dir;
  for (const key of Object.keys(process.env)) if (key.startsWith('PBL6_LLM_')) delete process.env[key];
  let upstreamCalls = 0;
  let mode = 'ok';
  const server = createServer((req, res) => {
    let raw = ''; req.on('data', b => raw += b); req.on('end', () => {
      upstreamCalls += 1;
      const data = JSON.parse(raw);
      assert.equal(req.url, '/v1/chat/completions');
      assert.equal(req.headers.authorization, 'Bearer test-sentence-secret');
      assert.equal(data.model, 'test-model');
      const input = JSON.parse(data.messages[1].content);
      assert.deepEqual(input.glosses.map((g: any) => g.label), ['Bố', 'Đi', 'Bệnh viện']);
      assert.ok(!raw.includes('video') && !raw.includes('landmark'));
      res.setHeader('Content-Type', 'application/json');
      const output = mode === 'clarify' ? { sentence: '', needsClarification: true, explanation: 'Ai đi bệnh viện?' }
        : { sentence: 'Bố đi bệnh viện.', needsClarification: false, explanation: '' };
      res.end(JSON.stringify({ choices: [{ message: { content: mode === 'invalid' ? 'invalid' : JSON.stringify(output) } }] }));
    });
  });
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  const port = (server.address() as { port: number }).port;
  const handler = makeSignSentenceHandler();
  try {
    await t.test('Missing provider is an explicit failure, not a fabricated sentence', async () => {
      const response = await handler(request({ glosses, requestId: 'trial-1' }));
      assert.equal(response.status, 503); assert.equal((await response.json()).error.code, 'llm_not_configured');
    });
    await t.test('Configure provider without returning its key', async () => {
      const response = await putSentenceConfiguration(request({ provider: 'openai', baseUrl: `http://127.0.0.1:${port}/v1`, model: 'test-model', apiKey: 'test-sentence-secret' }, 'PUT'));
      assert.equal(response.status, 200); assert.ok(!(await response.text()).includes('test-sentence-secret'));
      const status = await sentenceConfiguration(new Request('http://localhost:3100/api/sign-sentence'));
      assert.equal((await status.json()).configured, true);
    });
    let result: any;
    await t.test('Generate from selected glosses without publishing', async () => {
      const response = await handler(request({ glosses, requestId: 'trial-1' }));
      assert.equal(response.status, 200); result = await response.json();
      assert.equal(result.sentence, 'Bố đi bệnh viện.');
      assert.equal(result.metadata.sourceGlossText, 'Bố Đi Bệnh viện');
      assert.equal(result.metadata.requestId, 'trial-1');
      assert.equal((await listConversations()).length, 0);
    });
    await t.test('User-edited sentence persists separately from original glosses and generation', async () => {
      const saved = await createConversationWithFirstMessage('Bố đến bệnh viện.', ['sign'], glosses, result.metadata);
      const restored = await getConversationWithMessages(saved.conversation.id);
      assert.equal(restored?.messages[0].text, 'Bố đến bệnh viện.');
      assert.equal(restored?.messages[0].signSentence?.generatedText, 'Bố đi bệnh viện.');
      assert.deepEqual(restored?.messages[0].signGlosses, glosses);
    });
    await t.test('Reject unresolved and mixed-utterance inputs before calling provider', async () => {
      const calls = upstreamCalls;
      assert.equal((await handler(request({ glosses: [{ ...glosses[0], status: 'unconfirmed' }], requestId: 'bad' }))).status, 409);
      assert.equal((await handler(request({ glosses: [glosses[0], { ...glosses[1], utteranceId: '1' }], requestId: 'bad' }))).status, 400);
      assert.equal(upstreamCalls, calls);
    });
    await t.test('Reject foreign origin and stale source metadata', async () => {
      assert.equal((await handler(request({ glosses, requestId: 'bad' }, 'POST', 'https://foreign.example'))).status, 403);
      await assert.rejects(createConversationWithFirstMessage('Bố đi bệnh viện.', ['sign'], glosses, { ...result.metadata, sourceGlossText: 'Khác' }));
      await assert.rejects(createConversationWithFirstMessage('Bố đi bệnh viện.', ['sign'], glosses));
    });
    await t.test('Ambiguity stays a clarification, invalid output stays an error', async () => {
      mode = 'clarify';
      const response = await handler(request({ glosses, requestId: 'clarify' }));
      const data = await response.json(); assert.equal(data.needsClarification, true); assert.equal(data.sentence, '');
      mode = 'invalid'; assert.equal((await handler(request({ glosses, requestId: 'invalid' }))).status, 502);
    });
  } finally {
    await new Promise<void>(resolve => server.close(() => resolve()));
    process.env = previous; await rm(dir, { recursive: true, force: true });
  }
});
