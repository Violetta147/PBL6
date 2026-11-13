import { AppError, errorResponse, jsonResponse } from './errors';
import { boundedBody, requireLocalOrigin } from './http';
import { publicSettings, readSettings, updateSettings } from './settings';
import { readAudio } from './audio';
import { transcribe } from './deepgram';
import { MAX_AUDIO_BYTES } from '../contracts';
import {
  listConversations,
  getConversationWithMessages,
  createConversationWithFirstMessage,
  appendMessage,
  renameConversation,
  deleteConversations,
} from './storage';
import { getRecorder } from './recorder';

export async function getSettings(request: Request): Promise<Response> {
  try {
    requireLocalOrigin(request);
    return jsonResponse(publicSettings(await readSettings()));
  } catch (error) {
    return errorResponse(error);
  }
}

export async function putSettings(request: Request): Promise<Response> {
  try {
    requireLocalOrigin(request, true);
    let input: unknown;
    try {
      input = JSON.parse(new TextDecoder().decode(await boundedBody(request, 4096)));
    } catch (error) {
      if (error instanceof AppError) throw error;
      throw new AppError('json_invalid', 'Dữ liệu cấu hình không phải JSON hợp lệ.');
    }
    return jsonResponse(await updateSettings(input));
  } catch (error) {
    return errorResponse(error);
  }
}

// The production adapter always uses the official endpoint. Injection is for offline tests only.
export function makeTranscriptionHandler(deps = { readSettings, readAudio, transcribe }) {
  return async (request: Request): Promise<Response> => {
    let acquired = false;
    const state = globalThis as typeof globalThis & { pbl6SttBusy?: boolean };
    try {
      requireLocalOrigin(request, true);
      if (state.pbl6SttBusy) {
        throw new AppError('busy', 'Đang nhận dạng một file khác. Hãy chờ kết quả rồi gửi tiếp.', 409);
      }
      state.pbl6SttBusy = acquired = true;
      const settings = await deps.readSettings();
      if (!settings.apiKey) {
        throw new AppError('key_missing', 'Hãy nhập Deepgram API key trong Cài đặt trước khi nhận dạng.', 409);
      }
      const audio = await deps.readAudio(request);
      return jsonResponse(await deps.transcribe(audio, settings, request.signal));
    } catch (error) {
      return errorResponse(error);
    } finally {
      if (acquired) state.pbl6SttBusy = false;
    }
  };
}

type RouteContext<T> = { params: Promise<T> | T };

async function resolveParams<T>(context: RouteContext<T>): Promise<T> {
  return Promise.resolve(context.params);
}

// Conversation Handlers
export async function getConversationsHandler(request: Request): Promise<Response> {
  try {
    requireLocalOrigin(request);
    const url = new URL(request.url);
    const query = url.searchParams.get('query') || undefined;
    const filterDaysParam = url.searchParams.get('filterDays') || url.searchParams.get('olderThanDays');
    let olderThanDays: number | undefined;
    if (filterDaysParam) {
      const parsed = parseInt(filterDaysParam, 10);
      if (!isNaN(parsed) && parsed > 0) {
        olderThanDays = parsed;
      }
    }
    const conversations = await listConversations({ query, olderThanDays });
    return jsonResponse(conversations);
  } catch (error) {
    return errorResponse(error);
  }
}

export async function postConversationHandler(request: Request): Promise<Response> {
  try {
    requireLocalOrigin(request, true);
    let body: any;
    try {
      body = JSON.parse(new TextDecoder().decode(await boundedBody(request, 65536)));
    } catch (error) {
      if (error instanceof AppError) throw error;
      throw new AppError('json_invalid', 'Dữ liệu tin nhắn không phải JSON hợp lệ.');
    }
    if (!body || typeof body !== 'object' || typeof body.text !== 'string') {
      throw new AppError('text_missing', 'Nội dung tin nhắn không hợp lệ.', 400);
    }
    const result = await createConversationWithFirstMessage(body.text, body.sources);
    return jsonResponse(result, 201);
  } catch (error) {
    return errorResponse(error);
  }
}

export async function getConversationHandler(
  request: Request,
  context: RouteContext<{ id: string }>
): Promise<Response> {
  try {
    requireLocalOrigin(request);
    const { id } = await resolveParams(context);
    const data = await getConversationWithMessages(id);
    if (!data) {
      throw new AppError('conversation_not_found', 'Không tìm thấy hội thoại.', 404);
    }
    return jsonResponse(data);
  } catch (error) {
    return errorResponse(error);
  }
}

export async function patchConversationHandler(
  request: Request,
  context: RouteContext<{ id: string }>
): Promise<Response> {
  try {
    requireLocalOrigin(request, true);
    const { id } = await resolveParams(context);
    let body: any;
    try {
      body = JSON.parse(new TextDecoder().decode(await boundedBody(request, 4096)));
    } catch (error) {
      if (error instanceof AppError) throw error;
      throw new AppError('json_invalid', 'Dữ liệu không phải JSON hợp lệ.');
    }
    if (!body || typeof body !== 'object' || typeof body.title !== 'string') {
      throw new AppError('title_invalid', 'Tên hội thoại không hợp lệ.', 400);
    }
    const conv = await renameConversation(id, body.title);
    return jsonResponse(conv);
  } catch (error) {
    return errorResponse(error);
  }
}

export async function deleteConversationHandler(
  request: Request,
  context: RouteContext<{ id: string }>
): Promise<Response> {
  try {
    requireLocalOrigin(request, true);
    const { id } = await resolveParams(context);
    const result = await deleteConversations([id]);
    return jsonResponse({ deleted: result.deletedCount > 0, id });
  } catch (error) {
    return errorResponse(error);
  }
}

export async function postMessageHandler(
  request: Request,
  context: RouteContext<{ id: string }>
): Promise<Response> {
  try {
    requireLocalOrigin(request, true);
    const { id } = await resolveParams(context);
    let body: any;
    try {
      body = JSON.parse(new TextDecoder().decode(await boundedBody(request, 65536)));
    } catch (error) {
      if (error instanceof AppError) throw error;
      throw new AppError('json_invalid', 'Dữ liệu tin nhắn không phải JSON hợp lệ.');
    }
    if (!body || typeof body !== 'object' || typeof body.text !== 'string') {
      throw new AppError('text_missing', 'Nội dung tin nhắn không hợp lệ.', 400);
    }
    const message = await appendMessage(id, body.text, body.sources);
    return jsonResponse(message, 201);
  } catch (error) {
    return errorResponse(error);
  }
}

export async function postBatchDeleteHandler(request: Request): Promise<Response> {
  try {
    requireLocalOrigin(request, true);
    let body: any;
    try {
      body = JSON.parse(new TextDecoder().decode(await boundedBody(request, 65536)));
    } catch (error) {
      if (error instanceof AppError) throw error;
      throw new AppError('json_invalid', 'Dữ liệu không phải JSON hợp lệ.');
    }
    if (!body || !Array.isArray(body.ids)) {
      throw new AppError('invalid_ids', 'Danh sách ID cần xóa không hợp lệ.', 400);
    }
    const targetIds = body.ids.filter((id: unknown): id is string => typeof id === 'string' && id.trim().length > 0);
    const result = await deleteConversations(targetIds);
    return jsonResponse(result);
  } catch (error) {
    return errorResponse(error);
  }
}

// Recorder Handlers
export async function postRecordStartHandler(request: Request): Promise<Response> {
  try {
    requireLocalOrigin(request, true);
    let options: { deviceId?: string; maxDurationSeconds?: number } = {};
    if (request.body) {
      try {
        const raw = await boundedBody(request, 4096);
        if (raw.length > 0) {
          const text = new TextDecoder().decode(raw).trim();
          if (text) {
            options = JSON.parse(text);
          }
        }
      } catch (error) {
        if (error instanceof AppError && error.code === 'body_empty') {
          // Empty body is permitted for record start
        } else if (error instanceof AppError) {
          throw error;
        } else {
          throw new AppError('json_invalid', 'Dữ liệu tùy chọn thu âm không phải JSON hợp lệ.');
        }
      }
    }
    const recorder = getRecorder();
    const state = await recorder.start(options);
    return jsonResponse({ success: true, state });
  } catch (error) {
    return errorResponse(error);
  }
}

export async function postRecordStopHandler(request: Request): Promise<Response> {
  try {
    requireLocalOrigin(request, true);
    const contentType = request.headers.get('content-type') || '';
    if (contentType.startsWith('multipart/form-data')) {
      const settings = await readSettings();
      if (!settings.apiKey) {
        throw new AppError('key_missing', 'Hãy nhập Deepgram API key trong Cài đặt trước khi nhận dạng.', 409);
      }
      const bytes = await boundedBody(request, MAX_AUDIO_BYTES + 128 * 1024);
      let form: FormData;
      try {
        form = await new Response(bytes as BodyInit, { headers: { 'Content-Type': contentType } }).formData();
      } catch {
        throw new AppError('upload_invalid', 'Không đọc được dữ liệu tải lên.');
      }
      const fileEntry = form.get('audio') || form.get('file');
      if (!fileEntry || typeof fileEntry === 'string') {
        throw new AppError('file_required', 'Hãy gửi kèm file audio WAV cần nhận dạng.');
      }
      const file = fileEntry as File;
      if (!file.size) {
        throw new AppError('audio_empty', 'File audio trống.');
      }
      const audioBytes = new Uint8Array(await file.arrayBuffer());
      const result = await transcribe(
        { name: 'recording.wav', bytes: audioBytes, contentType: 'audio/wav' },
        settings,
        request.signal
      );
      return jsonResponse({
        success: true,
        transcript: result.text,
        durationMs: Math.round((result.audioSeconds || 0) * 1000),
      });
    }

    const recorder = getRecorder();
    const result = await recorder.stop();
    return jsonResponse(result);
  } catch (error) {
    return errorResponse(error);
  }
}

export async function postRecordCancelHandler(request: Request): Promise<Response> {
  try {
    requireLocalOrigin(request, true);
    const recorder = getRecorder();
    const result = await recorder.cancel();
    return jsonResponse(result);
  } catch (error) {
    return errorResponse(error);
  }
}

export async function getRecordStatusHandler(request: Request): Promise<Response> {
  try {
    requireLocalOrigin(request);
    const recorder = getRecorder();
    return jsonResponse(recorder.getState());
  } catch (error) {
    return errorResponse(error);
  }
}

// Microphones Handler
export async function getMicrophonesHandler(request: Request): Promise<Response> {
  try {
    requireLocalOrigin(request);
    const recorder = getRecorder();
    const devices = await recorder.listMicrophones();
    const settings = await readSettings();
    const logLine = `[Devices] Enumerated ${devices.length} microphone(s): ${devices.map(d => d.name).join(', ')}`;
    console.log(logLine);
    try { process.stdout.write(logLine + '\n'); } catch {}
    return jsonResponse({ devices, selectedId: settings.selectedMicrophoneId });
  } catch (error) {
    const errLine = `[Devices] Failed to enumerate microphones: ${error}`;
    console.error(errLine);
    try { process.stderr.write(errLine + '\n'); } catch {}
    return errorResponse(error);
  }
}
