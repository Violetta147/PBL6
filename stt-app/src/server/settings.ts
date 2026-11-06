import { mkdir, readFile, writeFile, rename, rm } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';
import { MODELS, type Model, type PublicSettings } from '../contracts';
import { AppError } from './errors';

export type Settings = { schemaVersion: 1; apiKey: string; model: Model; timeoutSeconds: number };
const defaults: Settings = { schemaVersion: 1, apiKey: '', model: 'nova-3', timeoutSeconds: 60 };

export function settingsDirectory(): string {
  return process.env.PBL6_STT_CONFIG_DIR || (process.platform === 'win32'
    ? join(process.env.LOCALAPPDATA || join(homedir(), 'AppData', 'Local'), 'PBL6-STT')
    : join(process.env.XDG_CONFIG_HOME || join(homedir(), '.config'), 'pbl6-stt'));
}

function validKey(value: unknown): value is string {
  return typeof value === 'string' && (value === '' || /^[A-Za-z0-9_-]{16,512}$/.test(value));
}
function validModel(value: unknown): value is Model { return MODELS.includes(value as Model); }
function validTimeout(value: unknown): value is number {
  return Number.isInteger(value) && Number(value) >= 15 && Number(value) <= 180;
}

export async function readSettings(): Promise<Settings> {
  let raw: string;
  try { raw = await readFile(join(settingsDirectory(), 'settings.json'), 'utf8'); }
  catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return { ...defaults };
    throw new AppError('settings_read', 'Không đọc được cấu hình tại máy chạy ứng dụng.', 500);
  }
  try {
    const s = JSON.parse(raw);
    if (s.schemaVersion !== 1 || !validKey(s.apiKey) || !validModel(s.model) || !validTimeout(s.timeoutSeconds)) throw Error();
    return { schemaVersion: 1, apiKey: s.apiKey, model: s.model, timeoutSeconds: s.timeoutSeconds };
  } catch {
    throw new AppError('settings_invalid', 'File cấu hình không hợp lệ. Giữ lại file để kiểm tra, không tự ghi đè.', 500);
  }
}

export function publicSettings(s: Settings): PublicSettings {
  return { provider: 'deepgram', language: 'vi', model: s.model, timeoutSeconds: s.timeoutSeconds, hasApiKey: Boolean(s.apiKey) };
}

// Serialize updates within this local backend. Write a complete file before replacing.
let writes: Promise<unknown> = Promise.resolve();
export function updateSettings(input: unknown): Promise<PublicSettings> {
  const result = writes.then(async () => {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new AppError('settings_input', 'Cấu hình phải là một đối tượng.');
    const value = input as Record<string, unknown>;
    if (Object.keys(value).some(k => !['apiKey', 'clearApiKey', 'model', 'timeoutSeconds'].includes(k)))
      throw new AppError('settings_input', 'Cấu hình có trường không được hỗ trợ. Ngôn ngữ của ứng dụng là vi.');
    if (value.apiKey !== undefined && !validKey(value.apiKey)) throw new AppError('key_invalid', 'API key phải dài 16–512 ký tự, không chứa khoảng trắng hoặc ký tự điều khiển.');
    if (value.clearApiKey !== undefined && typeof value.clearApiKey !== 'boolean') throw new AppError('settings_input', 'Yêu cầu xóa key không hợp lệ.');
    if (value.clearApiKey && value.apiKey) throw new AppError('settings_input', 'Chọn nhập key mới hoặc xóa key, không thực hiện cả hai.');
    if (value.model !== undefined && !validModel(value.model)) throw new AppError('model_invalid', 'Model được hỗ trợ: nova-3 hoặc nova-2.');
    if (value.timeoutSeconds !== undefined && !validTimeout(value.timeoutSeconds)) throw new AppError('timeout_invalid', 'Thời gian chờ phải là số nguyên từ 15 đến 180 giây.');
    const s = await readSettings();
    if (value.clearApiKey) s.apiKey = '';
    // An empty password field means preserve, never erase an existing key silently.
    else if (typeof value.apiKey === 'string' && value.apiKey) s.apiKey = value.apiKey;
    if (validModel(value.model)) s.model = value.model;
    if (validTimeout(value.timeoutSeconds)) s.timeoutSeconds = value.timeoutSeconds;
    const directory = settingsDirectory();
    const temp = join(directory, `.settings-${randomUUID()}.tmp`);
    try {
      await mkdir(directory, { recursive: true, mode: 0o700 });
      await writeFile(temp, JSON.stringify(s, null, 2) + '\n', { mode: 0o600, flag: 'wx' });
      await rename(temp, join(directory, 'settings.json'));
    } catch {
      throw new AppError('settings_write', 'Không lưu được cấu hình tại máy chạy ứng dụng.', 500);
    } finally { await rm(temp, { force: true }).catch(() => {}); }
    return publicSettings(s);
  });
  writes = result.catch(() => {});
  return result;
}
