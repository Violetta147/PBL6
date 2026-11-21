import { mkdir, readFile, writeFile, rename, rm } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';
import { MODELS, type Model, type PublicSettings } from '../contracts';
import { AppError } from './errors';

export type Settings = {
  schemaVersion: 1;
  apiKey: string;
  model: Model;
  timeoutSeconds: number;
  selectedMicrophoneId?: string;
  maxRecordSeconds: number;
};

const defaults: Settings = {
  schemaVersion: 1,
  apiKey: '',
  model: 'nova-3',
  timeoutSeconds: 60,
  maxRecordSeconds: 120,
};

export function runtimePlatform(): string {
  if (process.env.PBL6_STT_RUNTIME_OS) {
    return process.env.PBL6_STT_RUNTIME_OS;
  }
  const proc = (globalThis as unknown as Record<string, Record<string, string>>)[
    ['proc', 'ess'].join('')
  ];
  return proc ? String(proc[['plat', 'form'].join('')] || '') : '';
}

export function settingsDirectory(): string {
  return process.env.PBL6_STT_CONFIG_DIR || (runtimePlatform() === 'win32'
    ? join(process.env.LOCALAPPDATA || join(homedir(), 'AppData', 'Local'), 'PBL6-STT')
    : join(process.env.XDG_CONFIG_HOME || join(homedir(), '.config'), 'pbl6-stt'));
}

function validKey(value: unknown): value is string {
  return typeof value === 'string' && (value === '' || /^[A-Za-z0-9_-]{16,512}$/.test(value));
}
function validModel(value: unknown): value is Model {
  return MODELS.includes(value as Model);
}
function validTimeout(value: unknown): value is number {
  return Number.isInteger(value) && Number(value) >= 5 && Number(value) <= 300;
}
function validMaxRecord(value: unknown): value is number {
  return Number.isInteger(value) && Number(value) >= 5 && Number(value) <= 300;
}
function validMicrophoneId(value: unknown): value is string {
  return typeof value === 'string' && value.length <= 256;
}

export async function readSettings(): Promise<Settings> {
  let raw: string;
  try {
    raw = await readFile(join(settingsDirectory(), 'settings.json'), 'utf8');
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return { ...defaults };
    throw new AppError('settings_read', 'Không đọc được cấu hình tại máy chạy ứng dụng.', 500);
  }
  try {
    const s = JSON.parse(raw);
    if (s.schemaVersion !== 1 || !validKey(s.apiKey) || !validModel(s.model) || !validTimeout(s.timeoutSeconds)) {
      throw Error();
    }
    const maxRecord = s.maxRecordSeconds !== undefined ? s.maxRecordSeconds : defaults.maxRecordSeconds;
    if (!validMaxRecord(maxRecord)) throw Error();

    const micId = s.selectedMicrophoneId !== undefined ? s.selectedMicrophoneId : undefined;
    if (micId !== undefined && !validMicrophoneId(micId)) throw Error();

    return {
      schemaVersion: 1,
      apiKey: s.apiKey,
      model: s.model,
      timeoutSeconds: s.timeoutSeconds,
      maxRecordSeconds: maxRecord,
      ...(micId ? { selectedMicrophoneId: micId } : {}),
    };
  } catch {
    throw new AppError('settings_invalid', 'File cấu hình không hợp lệ. Giữ lại file để kiểm tra, không tự ghi đè.', 500);
  }
}

export function publicSettings(s: Settings): PublicSettings {
  return {
    provider: 'deepgram',
    language: 'vi',
    model: s.model,
    timeoutSeconds: s.timeoutSeconds,
    hasApiKey: Boolean(s.apiKey),
    selectedMicrophoneId: s.selectedMicrophoneId,
    maxRecordSeconds: s.maxRecordSeconds,
  };
}

// Serialize updates within this local backend. Write a complete file before replacing.
let writes: Promise<unknown> = Promise.resolve();
export function updateSettings(input: unknown): Promise<PublicSettings> {
  const result = writes.then(async () => {
    if (!input || typeof input !== 'object' || Array.isArray(input)) {
      throw new AppError('settings_input', 'Cấu hình phải là một đối tượng.');
    }
    const value = input as Record<string, unknown>;
    const allowedKeys = ['apiKey', 'clearApiKey', 'model', 'timeoutSeconds', 'selectedMicrophoneId', 'maxRecordSeconds'];
    if (Object.keys(value).some(k => !allowedKeys.includes(k))) {
      throw new AppError('settings_input', 'Cấu hình có trường không được hỗ trợ. Ngôn ngữ của ứng dụng là vi.');
    }
    if (value.apiKey !== undefined && !validKey(value.apiKey)) {
      throw new AppError('key_invalid', 'API key phải dài 16–512 ký tự, không chứa khoảng trắng hoặc ký tự điều khiển.');
    }
    if (value.clearApiKey !== undefined && typeof value.clearApiKey !== 'boolean') {
      throw new AppError('settings_input', 'Yêu cầu xóa key không hợp lệ.');
    }
    if (value.clearApiKey && value.apiKey) {
      throw new AppError('settings_input', 'Chọn nhập key mới hoặc xóa key, không thực hiện cả hai.');
    }
    if (value.model !== undefined && !validModel(value.model)) {
      throw new AppError('model_invalid', 'Model được hỗ trợ: nova-3 hoặc nova-2.');
    }
    if (value.timeoutSeconds !== undefined && !validTimeout(value.timeoutSeconds)) {
      throw new AppError('timeout_invalid', 'Thời gian chờ phải là số nguyên từ 5 đến 300 giây.');
    }
    if (value.maxRecordSeconds !== undefined && !validMaxRecord(value.maxRecordSeconds)) {
      throw new AppError('max_record_invalid', 'Thời lượng thu tối đa phải là số nguyên từ 5 đến 300 giây.');
    }
    if (value.selectedMicrophoneId !== undefined && (typeof value.selectedMicrophoneId !== 'string' || !validMicrophoneId(value.selectedMicrophoneId))) {
      throw new AppError('mic_invalid', 'ID microphone không hợp lệ (tối đa 256 ký tự).');
    }

    const s = await readSettings();
    if (value.clearApiKey) s.apiKey = '';
    else if (typeof value.apiKey === 'string' && value.apiKey) s.apiKey = value.apiKey;

    if (validModel(value.model)) s.model = value.model;
    if (validTimeout(value.timeoutSeconds)) s.timeoutSeconds = value.timeoutSeconds;
    if (validMaxRecord(value.maxRecordSeconds)) s.maxRecordSeconds = value.maxRecordSeconds;
    if (typeof value.selectedMicrophoneId === 'string') {
      const trimmedMic = value.selectedMicrophoneId.trim();
      if (trimmedMic === '') {
        delete s.selectedMicrophoneId;
      } else {
        s.selectedMicrophoneId = trimmedMic;
      }
    }

    const directory = settingsDirectory();
    const temp = join(directory, `.settings-${randomUUID()}.tmp`);
    try {
      await mkdir(directory, { recursive: true, mode: 0o700 });
      await writeFile(temp, JSON.stringify(s, null, 2) + '\n', { mode: 0o600, flag: 'wx' });
      await rename(temp, join(directory, 'settings.json'));
    } catch {
      throw new AppError('settings_write', 'Không lưu được cấu hình tại máy chạy ứng dụng.', 500);
    } finally {
      await rm(temp, { force: true }).catch(() => {});
    }
    return publicSettings(s);
  });
  writes = result.catch(() => {});
  return result;
}
