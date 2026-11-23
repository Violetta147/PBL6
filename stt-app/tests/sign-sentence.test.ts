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
const thanksGlosses: SignGloss[] = [
  { ...glosses[0], label: 'Xin', labelId: 363, originalLabel: 'Xin' },
  { ...glosses[1], label: 'Cảm ơn', labelId: 86, originalLabel: 'Cảm ơn' },
];
const chatReply = 'Xin ở đây là một câu hỏi hay hay xin phép được bơi lội?';
function request(body: unknown, method = 'POST', origin = 'http://localhost:3100') {
  return new Request('http://localhost:3100/api/sign-sentence', { method, headers: { origin, host: 'localhost:3100', 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

async function assertErrorEnvelope(response: Response, status: number, code: string) {
  assert.equal(response.status, status);
  assert.match(response.headers.get('content-type') ?? '', /^application\/json\b/);
  const body = await response.json();
  assert.equal(typeof body.error?.message, 'string');
  assert.deepEqual(body, { status: 'error', sentence: '', needsClarification: false, explanation: '', metadata: null, error: { code, message: body.error.message } });
  return body;
}

test('Real HTTP adapter, reviewed sentence storage, and guarded failures', async t => {
  const dir = await mkdtemp(join(tmpdir(), 'pbl6-sentence-'));
  const previous = { ...process.env };
  process.env.PBL6_STT_CONFIG_DIR = dir; process.env.PBL6_STT_DATA_DIR = dir;
  for (const key of Object.keys(process.env)) if (key.startsWith('PBL6_LLM_')) delete process.env[key];
  let upstreamCalls = 0;
  let output = JSON.stringify({ status: 'ok', sentence: 'Bố đi bệnh viện.' });
  let expectedGlosses = glosses;
  const server = createServer((req, res) => {
    let raw = ''; req.on('data', b => raw += b); req.on('end', () => {
      upstreamCalls += 1;
      const data = JSON.parse(raw);
      assert.ok(!raw.includes('video') && !raw.includes('landmark'));
      res.setHeader('Content-Type', 'application/json');
      const expectedInput = { glosses: expectedGlosses.map(({ label, labelId }) => ({ label, labelId })) };
      assert.equal(req.url, '/v1/chat/completions');
      assert.equal(req.headers.authorization, 'Bearer test-sentence-secret');
      assert.equal(data.model, 'test-model');
      assert.deepEqual(JSON.parse(data.messages[1].content), expectedInput);
      assert.deepEqual(data.response_format, { type: 'json_object' });
      assert.ok(data.messages[0].content.includes('{"status":"ok","sentence":"Xin cảm ơn."}'));
      res.end(JSON.stringify({ choices: [{ message: { content: output } }] }));
    });
  });
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  const port = (server.address() as { port: number }).port;
  const handler = makeSignSentenceHandler();
  try {
    await t.test('Missing provider is an explicit failure, not a fabricated sentence', async () => {
      const response = await handler(request({ glosses, requestId: 'trial-1' }));
      await assertErrorEnvelope(response, 503, 'llm_not_configured');
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
      await assertErrorEnvelope(await handler(request({ glosses: [{ ...glosses[0], status: 'unconfirmed' }], requestId: 'bad' })), 409, 'glosses_unconfirmed');
      await assertErrorEnvelope(await handler(request({ glosses: [glosses[0], { ...glosses[1], utteranceId: '1' }], requestId: 'bad' })), 400, 'glosses_invalid');
      assert.equal(upstreamCalls, calls);
    });
    await t.test('Reject foreign origin and stale source metadata', async () => {
      assert.equal((await handler(request({ glosses, requestId: 'bad' }, 'POST', 'https://foreign.example'))).status, 403);
      await assert.rejects(createConversationWithFirstMessage('Bố đi bệnh viện.', ['sign'], glosses, { ...result.metadata, sourceGlossText: 'Khác' }));
      await assert.rejects(createConversationWithFirstMessage('Bố đi bệnh viện.', ['sign'], glosses));
    });
    await t.test('Ambiguity uses fixed UI text supplied by the application', async () => {
      output = JSON.stringify({ status: 'needs_clarification', sentence: '' });
      const response = await handler(request({ glosses, requestId: 'clarify' }));
      assert.equal(response.status, 200);
      const data = await response.json();
      assert.equal(data.status, 'needs_clarification');
      assert.equal(data.needsClarification, true);
      assert.equal(data.sentence, '');
      assert.equal(data.error, null);
      assert.equal(data.explanation, 'Chưa đủ thông tin để tạo câu. Hãy kiểm tra chuỗi gloss.');
    });
    await t.test('Sentence validation accepts well-formed JSON regardless of wording', async () => {
      expectedGlosses = thanksGlosses;
      const body = { glosses: thanksGlosses, requestId: 'thanks' };
      for (const sentence of ['Xin cảm ơn.', chatReply, 'Xin cảm ơn.\nBạn có muốn tôi giúp gì thêm không?']) {
        output = JSON.stringify({ status: 'ok', sentence });
        const response = await handler(request(body));
        assert.equal(response.status, 200);
        assert.deepEqual(await response.json(), {
          status: 'ok', sentence, needsClarification: false, explanation: '', error: null,
          metadata: { generatedText: sentence, sourceGlossText: 'Xin Cảm ơn', model: 'test-model', requestId: 'thanks' },
        });
      }
    });

    await t.test('Invalid provider output is returned in the application JSON envelope', async () => {
      for (const invalid of [
        chatReply,
        '```json\n{"status":"ok","sentence":"Xin cảm ơn."}\n```',
        '{"status":"ok"}',
        '{"status":"ok","sentence":3}',
        '{"status":"ok","sentence":"  "}',
        '{"status":"other","sentence":"Xin cảm ơn."}',
        '{"status":"needs_clarification","sentence":"Xin cảm ơn."}',
        JSON.stringify({ status: 'needs_clarification', sentence: '', explanation: chatReply }),
      ]) {
        output = invalid;
        const rejected = await handler(request({ glosses: thanksGlosses, requestId: 'thanks' }));
        const error = await assertErrorEnvelope(rejected, 502, 'llm_output');
        assert.ok(!JSON.stringify(error).includes(chatReply));
      }
    });
    await t.test('A signed question can still be returned as a sentence', async () => {
      expectedGlosses = glosses;
      output = JSON.stringify({ status: 'ok', sentence: 'Bố đi bệnh viện không?' });
      const result = await handler(request({ glosses, requestId: 'question' }));
      assert.equal(result.status, 200);
      assert.equal((await result.json()).sentence, 'Bố đi bệnh viện không?');
    });
  } finally {
    await new Promise<void>(resolve => server.close(() => resolve()));
    process.env = previous; await rm(dir, { recursive: true, force: true });
  }
});
