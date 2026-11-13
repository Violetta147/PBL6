import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  extractTitle,
  normalizeTitle,
  readStorage,
  listConversations,
  getConversationWithMessages,
  createConversationWithFirstMessage,
  appendMessage,
  renameConversation,
  deleteConversations,
} from '../src/server/storage';
import { AppError } from '../src/server/errors';

let directory: string;
const previous = process.env.PBL6_STT_DATA_DIR;

beforeEach(async () => {
  directory = await mkdtemp(join(tmpdir(), 'pbl6-stt-storage-test-'));
  process.env.PBL6_STT_DATA_DIR = directory;
});

afterEach(async () => {
  if (previous === undefined) {
    delete process.env.PBL6_STT_DATA_DIR;
  } else {
    process.env.PBL6_STT_DATA_DIR = previous;
  }
  await rm(directory, { recursive: true, force: true });
});

test('extractTitle collapses whitespace and truncates at word boundary under 72 chars', () => {
  assert.equal(extractTitle('  Xin   chào   thế   giới  \n\t  '), 'Xin chào thế giới');
  assert.equal(extractTitle(''), 'Hội thoại mới');
  assert.equal(extractTitle('   '), 'Hội thoại mới');

  // Exactly 72 characters
  const exact72 = 'Một câu tiếng Việt rất dài để kiểm tra độ dài đúng bảy mươi hai ký tự nè';
  assert.ok(exact72.length <= 72);
  assert.equal(extractTitle(exact72), exact72);

  // Exceeds 72 chars - should break at word boundary
  const longSentence = 'Hôm nay chúng ta cùng thảo luận về kiến trúc phần mềm cho hệ thống chuyển đổi giọng nói thành văn bản trên Raspberry Pi';
  const extracted = extractTitle(longSentence);
  assert.ok(extracted.length <= 72, `Length ${extracted.length} exceeds 72`);
  assert.ok(!extracted.endsWith(' '), 'Should not end with trailing space');
  assert.ok(longSentence.startsWith(extracted), 'Extracted title should match start of text');
  // Check word boundary
  const nextChar = longSentence[extracted.length];
  assert.equal(nextChar, ' ', 'Should break cleanly at a word boundary');

  // Single very long word without spaces
  const longWord = 'a'.repeat(100);
  assert.equal(extractTitle(longWord).length, 72);

  // Exact word boundary when 73rd character is a space
  const prefix70 = 'A'.repeat(70);
  const boundaryText = `${prefix70} B C`; // 'A'*70 + ' B' is 72 chars, followed by space and 'C'
  assert.equal(extractTitle(boundaryText), `${prefix70} B`);
});

test('normalizeTitle handles empty strings and truncation up to 72 chars', () => {
  assert.equal(normalizeTitle('   '), '');
  assert.equal(normalizeTitle('  Tên mới   hội   thoại  '), 'Tên mới hội thoại');
  const longTitle = 'Tiêu đề cuộc trò chuyện rất dài cần được cắt ngắn tại ranh giới từ để không bị cụt từ giữa chừng';
  const norm = normalizeTitle(longTitle);
  assert.ok(norm.length <= 72);
  assert.ok(longTitle.startsWith(norm));
});

test('initial storage reads empty lists when file does not exist', async () => {
  const data = await readStorage();
  assert.equal(data.schemaVersion, 1);
  assert.deepEqual(data.conversations, []);
  assert.deepEqual(data.messages, []);
});

test('create conversation with first message extracts title and stores sources', async () => {
  const { conversation, message } = await createConversationWithFirstMessage(
    'Xin chào buổi sáng mọi người',
    ['voice']
  );

  assert.ok(conversation.id);
  assert.equal(conversation.title, 'Xin chào buổi sáng mọi người');
  assert.equal(conversation.messageCount, 1);
  assert.equal(conversation.createdAt, conversation.updatedAt);

  assert.ok(message.id);
  assert.equal(message.conversationId, conversation.id);
  assert.equal(message.text, 'Xin chào buổi sáng mọi người');
  assert.deepEqual(message.sources, ['voice']);

  const list = await listConversations();
  assert.equal(list.length, 1);
  assert.equal(list[0].id, conversation.id);
});

test('rejects empty or whitespace-only first message', async () => {
  await assert.rejects(createConversationWithFirstMessage(''), { code: 'text_empty' });
  await assert.rejects(createConversationWithFirstMessage('   \n\t '), { code: 'text_empty' });
});

test('create and append filter invalid message sources gracefully', async () => {
  const { message: m1 } = await createConversationWithFirstMessage('Tin nhắn lọc nguồn', [
    'voice',
    'invalid_source_hack' as any,
  ]);
  assert.deepEqual(m1.sources, ['voice']);

  const { message: m2 } = await createConversationWithFirstMessage('Nguồn toàn bộ không hợp lệ', [
    'bogus' as any,
  ]);
  assert.deepEqual(m2.sources, ['keyboard']);

  const m3 = await appendMessage(m1.conversationId, 'Tin nhắn tiếp theo', ['sign', 123 as any]);
  assert.deepEqual(m3.sources, ['sign']);
});

test('append message updates updatedAt, increments messageCount and moves to top', async () => {
  const { conversation: conv1 } = await createConversationWithFirstMessage('Hội thoại số một');
  // Wait a small delay to ensure distinct timestamp
  await new Promise(r => setTimeout(r, 20));
  const { conversation: conv2 } = await createConversationWithFirstMessage('Hội thoại số hai');

  // Currently conv2 is newer
  let list = await listConversations();
  assert.equal(list[0].id, conv2.id);
  assert.equal(list[1].id, conv1.id);

  // Append to conv1
  await new Promise(r => setTimeout(r, 20));
  const msg2 = await appendMessage(conv1.id, 'Tin nhắn tiếp theo của hội thoại 1', ['keyboard', 'voice']);
  assert.equal(msg2.conversationId, conv1.id);
  assert.deepEqual(msg2.sources, ['keyboard', 'voice']);

  // Now conv1 must be bumped to the top of list
  list = await listConversations();
  assert.equal(list[0].id, conv1.id);
  assert.equal(list[0].messageCount, 2);
  assert.ok(new Date(list[0].updatedAt).getTime() > new Date(conv1.createdAt).getTime());

  // Check detail retrieval
  const detail = await getConversationWithMessages(conv1.id);
  assert.ok(detail);
  assert.equal(detail.conversation.messageCount, 2);
  assert.equal(detail.messages.length, 2);
  assert.equal(detail.messages[0].text, 'Hội thoại số một');
  assert.equal(detail.messages[1].text, 'Tin nhắn tiếp theo của hội thoại 1');
});

test('renameConversation updates title but NEVER changes updatedAt', async () => {
  const { conversation } = await createConversationWithFirstMessage('Tên ban đầu');
  const initialUpdatedAt = conversation.updatedAt;

  await new Promise(r => setTimeout(r, 30));

  const renamed = await renameConversation(conversation.id, 'Tên mới sau khi đổi');
  assert.equal(renamed.title, 'Tên mới sau khi đổi');
  assert.equal(renamed.updatedAt, initialUpdatedAt, 'updatedAt must NOT be modified by rename');

  // Rename with empty string must retain previous title
  const preserved = await renameConversation(conversation.id, '   ');
  assert.equal(preserved.title, 'Tên mới sau khi đổi', 'Blank rename must preserve previous title');
  assert.equal(preserved.updatedAt, initialUpdatedAt, 'updatedAt must still remain untouched');
});

test('listConversations filters by query and olderThanDays', async () => {
  const { conversation: c1 } = await createConversationWithFirstMessage('Dự án PBL6 trí tuệ nhân tạo');
  const { conversation: c2 } = await createConversationWithFirstMessage('Gặp mặt ăn trưa cuối tuần');

  // Query filter
  const searchResults = await listConversations({ query: 'PBL6' });
  assert.equal(searchResults.length, 1);
  assert.equal(searchResults[0].id, c1.id);

  const emptyResults = await listConversations({ query: 'không tồn tại' });
  assert.equal(emptyResults.length, 0);

  // olderThanDays filter: currently both are recent, so olderThanDays: 7 returns empty
  const olderThan7Days = await listConversations({ olderThanDays: 7 });
  assert.equal(olderThan7Days.length, 0);

  // Mock an older conversation in storage
  const storage = await readStorage();
  const tenDaysAgo = new Date(Date.now() - 10 * 86400000).toISOString();
  storage.conversations.push({
    id: 'old-conv-id',
    title: 'Hội thoại mười ngày trước',
    createdAt: tenDaysAgo,
    updatedAt: tenDaysAgo,
    messageCount: 1,
  });
  await writeFile(join(directory, 'conversations.json'), JSON.stringify(storage));

  const olderResults = await listConversations({ olderThanDays: 7 });
  assert.equal(olderResults.length, 1);
  assert.equal(olderResults[0].id, 'old-conv-id');
});

test('single delete and batch delete cascade to associated messages', async () => {
  const { conversation: c1 } = await createConversationWithFirstMessage('Hội thoại 1');
  await appendMessage(c1.id, 'Tin 2 của hội thoại 1');
  const { conversation: c2 } = await createConversationWithFirstMessage('Hội thoại 2');
  const { conversation: c3 } = await createConversationWithFirstMessage('Hội thoại 3');

  // Single delete
  const del1 = await deleteConversations([c1.id]);
  assert.deepEqual(del1.deletedIds, [c1.id]);
  assert.equal(del1.deletedCount, 1);

  const detail1 = await getConversationWithMessages(c1.id);
  assert.equal(detail1, null);

  const currentStorage = await readStorage();
  assert.equal(currentStorage.messages.filter(m => m.conversationId === c1.id).length, 0);

  // Batch delete c2 and c3
  const batchDel = await deleteConversations([c2.id, c3.id, 'non-existent-id']);
  assert.equal(batchDel.deletedCount, 2);
  assert.ok(batchDel.deletedIds.includes(c2.id));
  assert.ok(batchDel.deletedIds.includes(c3.id));

  const remaining = await listConversations();
  assert.equal(remaining.length, 0);
});

test('concurrent writes serialize safely without race condition or lost data', async () => {
  const { conversation } = await createConversationWithFirstMessage('Hội thoại đồng thời');
  const N = 10;
  const promises = [];
  for (let i = 0; i < N; i++) {
    promises.push(appendMessage(conversation.id, `Tin nhắn số ${i}`));
  }

  await Promise.all(promises);

  const detail = await getConversationWithMessages(conversation.id);
  assert.ok(detail);
  // Initial message + 10 appended = 11
  assert.equal(detail.conversation.messageCount, N + 1);
  assert.equal(detail.messages.length, N + 1);
});

test('corrupted storage throws storage_invalid and is not silently overwritten', async () => {
  await writeFile(join(directory, 'conversations.json'), 'CORRUPTED_JSON_DATA');
  await assert.rejects(readStorage(), { code: 'storage_invalid' });
  await assert.rejects(listConversations(), { code: 'storage_invalid' });
  assert.equal(await readFile(join(directory, 'conversations.json'), 'utf8'), 'CORRUPTED_JSON_DATA');
});
