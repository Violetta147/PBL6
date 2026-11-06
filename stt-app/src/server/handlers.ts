import { AppError, errorResponse, jsonResponse } from './errors';
import { boundedBody, requireLocalOrigin } from './http';
import { publicSettings, readSettings, updateSettings } from './settings';
import { readAudio } from './audio';
import { transcribe } from './deepgram';

export async function getSettings(request: Request): Promise<Response> {
  try { requireLocalOrigin(request); return jsonResponse(publicSettings(await readSettings())); }
  catch (error) { return errorResponse(error); }
}
export async function putSettings(request: Request): Promise<Response> {
  try {
    requireLocalOrigin(request, true);
    let input;
    try { input = JSON.parse(new TextDecoder().decode(await boundedBody(request, 4096))); }
    catch (error) { if (error instanceof AppError) throw error; throw new AppError('json_invalid', 'Dữ liệu cấu hình không phải JSON hợp lệ.'); }
    return jsonResponse(await updateSettings(input));
  } catch (error) { return errorResponse(error); }
}

// The production adapter always uses the official endpoint. Injection is for offline tests only.
export function makeTranscriptionHandler(deps = { readSettings, readAudio, transcribe }) {
  return async (request: Request): Promise<Response> => {
    let acquired = false;
    const state = globalThis as typeof globalThis & { pbl6SttBusy?: boolean };
    try {
      requireLocalOrigin(request, true);
      if (state.pbl6SttBusy) throw new AppError('busy', 'Đang nhận dạng một file khác. Hãy chờ kết quả rồi gửi tiếp.', 409);
      state.pbl6SttBusy = acquired = true;
      const settings = await deps.readSettings();
      if (!settings.apiKey) throw new AppError('key_missing', 'Hãy nhập Deepgram API key trong Cài đặt trước khi nhận dạng.', 409);
      const audio = await deps.readAudio(request);
      return jsonResponse(await deps.transcribe(audio, settings, request.signal));
    } catch (error) { return errorResponse(error); }
    finally { if (acquired) state.pbl6SttBusy = false; }
  };
}
