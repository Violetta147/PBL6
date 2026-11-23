import { mkdir, readFile, writeFile, rename, rm } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';
import { MESSAGE_SOURCES, type Conversation, type Message, type MessageSource, type SignGloss, type SignSentence } from '../contracts';
import { AppError } from './errors';
import { runtimePlatform } from './settings';

export type StorageData = {
  schemaVersion: 1;
  conversations: Conversation[];
  messages: Message[];
};

const defaults: StorageData = {
  schemaVersion: 1,
  conversations: [],
  messages: [],
};

export function storageDirectory(): string {
  if (process.env.PBL6_STT_DATA_DIR) {
    return process.env.PBL6_STT_DATA_DIR;
  }
  if (runtimePlatform() === 'win32') {
    return join(process.env.LOCALAPPDATA || join(homedir(), 'AppData', 'Local'), 'PBL6-STT');
  }
  if (process.env.XDG_DATA_HOME) {
    return join(process.env.XDG_DATA_HOME, 'pbl6-stt');
  }
  if (process.env.XDG_CONFIG_HOME) {
    return join(process.env.XDG_CONFIG_HOME, 'pbl6-stt');
  }
  return join(homedir(), '.local', 'share', 'pbl6-stt');
}

function truncateAtWordBoundary(normalized: string, maxLen = 72): string {
  if (normalized.length <= maxLen) return normalized;
  // If the character immediately following the cutoff is a space, the cutoff is already at a word boundary
  if (normalized[maxLen] === ' ') {
    return normalized.slice(0, maxLen).trim();
  }
  const truncated = normalized.slice(0, maxLen);
  const lastSpace = truncated.lastIndexOf(' ');
  if (lastSpace > 0) {
    return truncated.slice(0, lastSpace).trim();
  }
  return truncated;
}

export function extractTitle(text: string): string {
  const normalized = text.trim().replace(/\s+/g, ' ');
  if (!normalized) return 'Hội thoại mới';
  return truncateAtWordBoundary(normalized, 72);
}

export function normalizeTitle(title: string): string {
  const collapsed = title.trim().replace(/\s+/g, ' ');
  if (!collapsed) return '';
  return truncateAtWordBoundary(collapsed, 72);
}

export async function readStorage(): Promise<StorageData> {
  const filePath = join(storageDirectory(), 'conversations.json');
  let raw: string;
  try {
    raw = await readFile(filePath, 'utf8');
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      return { schemaVersion: 1, conversations: [], messages: [] };
    }
    throw new AppError('storage_read', 'Không đọc được dữ liệu hội thoại.', 500);
  }
  try {
    const data = JSON.parse(raw);
    if (data.schemaVersion !== 1 || !Array.isArray(data.conversations) || !Array.isArray(data.messages)) {
      throw Error();
    }
    return {
      schemaVersion: 1,
      conversations: data.conversations,
      messages: data.messages,
    };
  } catch {
    throw new AppError('storage_invalid', 'File dữ liệu hội thoại không hợp lệ.', 500);
  }
}

async function writeStorageAtomic(data: StorageData): Promise<void> {
  const dir = storageDirectory();
  const temp = join(dir, `.conversations-${randomUUID()}.tmp`);
  try {
    await mkdir(dir, { recursive: true, mode: 0o700 });
    await writeFile(temp, JSON.stringify(data, null, 2) + '\n', { mode: 0o600, flag: 'wx' });
    await rename(temp, join(dir, 'conversations.json'));
  } catch {
    throw new AppError('storage_write', 'Không lưu được dữ liệu hội thoại.', 500);
  } finally {
    await rm(temp, { force: true }).catch(() => {});
  }
}

let writes: Promise<unknown> = Promise.resolve();

function serializeWrite<T>(op: () => Promise<T>): Promise<T> {
  const result = writes.then(op);
  writes = result.catch(() => {});
  return result;
}

function sanitizeSources(sources: unknown): MessageSource[] {
  if (!Array.isArray(sources)) return ['keyboard'];
  const valid = sources.filter((s): s is MessageSource =>
    typeof s === 'string' && (MESSAGE_SOURCES as readonly string[]).includes(s)
  );
  return valid.length > 0 ? valid : ['keyboard'];
}

export async function listConversations(filter?: {
  query?: string;
  olderThanDays?: number;
}): Promise<Conversation[]> {
  const data = await readStorage();
  let list = [...data.conversations];

  // Sort by updatedAt descending with tie-breaker
  list.sort((a, b) => {
    const diff = new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
    if (diff !== 0) return diff;
    return b.id.localeCompare(a.id);
  });

  if (filter?.query && filter.query.trim()) {
    const q = filter.query.trim().toLowerCase();
    list = list.filter(c => c.title.toLowerCase().includes(q));
  }

  if (filter?.olderThanDays !== undefined && filter.olderThanDays > 0) {
    const cutoff = Date.now() - filter.olderThanDays * 24 * 60 * 60 * 1000;
    list = list.filter(c => new Date(c.updatedAt).getTime() < cutoff);
  }

  return list;
}

export async function getConversationWithMessages(
  id: string
): Promise<{ conversation: Conversation; messages: Message[] } | null> {
  const data = await readStorage();
  const conversation = data.conversations.find(c => c.id === id);
  if (!conversation) return null;

  const messages = data.messages
    .filter(m => m.conversationId === id)
    .sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());

  return { conversation: { ...conversation }, messages };
}

function signMessageMetadata(value: unknown, sources: MessageSource[], text: string, sentence?: unknown): Pick<Message, 'signGlosses' | 'signSentence'> {
  if (value === undefined) {
    if (sentence !== undefined) throw new AppError('sign_sentence_invalid', 'Thiếu chuỗi gloss nguồn.', 400);
    return {};
  }
  const invalid = () => new AppError('sign_glosses_invalid', 'Dữ liệu ký hiệu không hợp lệ.', 400);
  if (!sources.includes('sign') || !Array.isArray(value) || value.length === 0) throw invalid();
  const signGlosses = value.map((entry: unknown): SignGloss => {
    if (!entry || typeof entry !== 'object') throw invalid();
    const { segmentId, utteranceId, label, labelId, originalLabel, status, top3 } = entry as Partial<SignGloss>;
    if (
      typeof segmentId !== 'string' || !segmentId ||
      typeof utteranceId !== 'string' || !utteranceId ||
      typeof label !== 'string' || !label || typeof labelId !== 'number' || !Number.isInteger(labelId) ||
      typeof originalLabel !== 'string' || !originalLabel ||
      (status !== 'recognized' && status !== 'unconfirmed' && status !== 'confirmed') ||
      !Array.isArray(top3) || top3.length > 3
    ) throw invalid();
    const candidates = top3.map((candidate) => {
      if (!candidate || typeof candidate.label !== 'string' || !Number.isInteger(candidate.label_id) ||
          !Number.isFinite(candidate.score) || candidate.score < 0 || candidate.score > 1) throw invalid();
      return { label: candidate.label, label_id: candidate.label_id, score: candidate.score };
    });
    return { segmentId, utteranceId, label, labelId, originalLabel, status, top3: candidates };
  });
  const sourceText = signGlosses.map(({ label }) => label).join(' ').trim();
  if (sentence === undefined) {
    if (sourceText !== text) throw invalid();
    return { signGlosses };
  }
  const s = sentence as Partial<SignSentence>;
  if (!s || typeof s !== 'object' || s.sourceGlossText !== sourceText ||
      typeof s.generatedText !== 'string' || !s.generatedText.trim() || s.generatedText.length > 2000 ||
      typeof s.model !== 'string' || !s.model || s.model.length > 200 ||
      typeof s.requestId !== 'string' || !/^[a-zA-Z0-9_-]{1,100}$/.test(s.requestId) ||
      text.length > 2000 || signGlosses.some(g => g.status === 'unconfirmed')) throw invalid();
  return { signGlosses, signSentence: { sourceGlossText: sourceText, generatedText: s.generatedText,
    model: s.model, requestId: s.requestId, confirmedAt: new Date().toISOString() } };
}

export function createConversationWithFirstMessage(
  text: string,
  sources: MessageSource[] = ['keyboard'],
  signGlosses?: unknown,
  signSentence?: unknown
): Promise<{ conversation: Conversation; message: Message }> {
  return serializeWrite(async () => {
    const trimmed = (text || '').trim();
    if (!trimmed) {
      throw new AppError('text_empty', 'Nội dung tin nhắn không được để trống.', 400);
    }
    const cleanSources: MessageSource[] = sanitizeSources(sources);

    const data = await readStorage();
    const now = new Date().toISOString();
    const conversationId = randomUUID();
    const messageId = randomUUID();
    const title = extractTitle(trimmed);

    const conversation: Conversation = {
      id: conversationId,
      title,
      createdAt: now,
      updatedAt: now,
      messageCount: 1,
    };

    const message: Message = {
      id: messageId,
      conversationId,
      text: trimmed,
      createdAt: now,
      sources: cleanSources,
      ...signMessageMetadata(signGlosses, cleanSources, trimmed, signSentence),
    };

    data.conversations.push(conversation);
    data.messages.push(message);

    await writeStorageAtomic(data);
    return { conversation, message };
  });
}

export function appendMessage(
  conversationId: string,
  text: string,
  sources: MessageSource[] = ['keyboard'],
  signGlosses?: unknown,
  signSentence?: unknown
): Promise<Message> {
  return serializeWrite(async () => {
    const trimmed = (text || '').trim();
    if (!trimmed) {
      throw new AppError('text_empty', 'Nội dung tin nhắn không được để trống.', 400);
    }
    const cleanSources: MessageSource[] = sanitizeSources(sources);

    const data = await readStorage();
    const conv = data.conversations.find(c => c.id === conversationId);
    if (!conv) {
      throw new AppError('conversation_not_found', 'Không tìm thấy hội thoại.', 404);
    }

    const now = new Date().toISOString();
    const messageId = randomUUID();

    const message: Message = {
      id: messageId,
      conversationId,
      text: trimmed,
      createdAt: now,
      sources: cleanSources,
      ...signMessageMetadata(signGlosses, cleanSources, trimmed, signSentence),
    };

    conv.updatedAt = now;
    conv.messageCount += 1;
    data.messages.push(message);

    await writeStorageAtomic(data);
    return message;
  });
}

export function renameConversation(id: string, newTitle: string): Promise<Conversation> {
  return serializeWrite(async () => {
    const data = await readStorage();
    const conv = data.conversations.find(c => c.id === id);
    if (!conv) {
      throw new AppError('conversation_not_found', 'Không tìm thấy hội thoại.', 404);
    }

    const normalized = normalizeTitle(newTitle || '');
    if (normalized) {
      conv.title = normalized;
    }
    // Note: updatedAt is deliberately preserved unchanged

    await writeStorageAtomic(data);
    return { ...conv };
  });
}

export function deleteConversations(
  ids: string[]
): Promise<{ deletedIds: string[]; deletedCount: number }> {
  return serializeWrite(async () => {
    if (!Array.isArray(ids) || ids.length === 0) {
      return { deletedIds: [], deletedCount: 0 };
    }

    const targetSet = new Set(ids);
    const data = await readStorage();

    const deletedIds: string[] = [];
    data.conversations = data.conversations.filter(c => {
      if (targetSet.has(c.id)) {
        deletedIds.push(c.id);
        return false;
      }
      return true;
    });

    const deletedSet = new Set(deletedIds);
    data.messages = data.messages.filter(m => !deletedSet.has(m.conversationId));

    await writeStorageAtomic(data);
    return { deletedIds, deletedCount: deletedIds.length };
  });
}
