import { randomUUID } from 'node:crypto';
import type { Transcript } from '../contracts';
import type { AudioInput } from './audio';
import type { Settings } from './settings';
import { AppError } from './errors';

export async function transcribe(audio: AudioInput, settings: Settings, clientSignal?: AbortSignal,
  fetcher: typeof fetch = fetch): Promise<Transcript> {
  if (!settings.apiKey) throw new AppError('key_missing', 'Hãy nhập Deepgram API key trong Cài đặt trước khi nhận dạng.', 409);
  const url = new URL('https://api.deepgram.com/v1/listen');
  url.search = new URLSearchParams({ model: settings.model, language: 'vi', smart_format: 'true', punctuate: 'true' }).toString();
  const timeout = AbortSignal.timeout(settings.timeoutSeconds * 1000);
  const signal = clientSignal ? AbortSignal.any([timeout, clientSignal]) : timeout;
  const started = performance.now();
  try {
    const response = await fetcher(url, {
      method: 'POST', headers: { Authorization: `Token ${settings.apiKey}`, 'Content-Type': audio.contentType },
      body: audio.bytes as BodyInit, signal, redirect: 'error',
    });
    if (!response.ok) {
      const status = response.status;
      await response.body?.cancel();
      if (status === 401 || status === 403) throw new AppError('provider_auth', 'Deepgram từ chối xác thực hoặc quyền truy cập. Kiểm tra key trong Cài đặt.', 502);
      if (status === 429) throw new AppError('provider_limit', 'Deepgram giới hạn yêu cầu hoặc hạn mức tài khoản. Hãy kiểm tra tài khoản rồi thử lại.', 502);
      if (status >= 500) throw new AppError('provider_unavailable', 'Dịch vụ Deepgram đang báo lỗi. Hãy thử lại sau.', 502);
      throw new AppError('provider_rejected', 'Deepgram không chấp nhận audio hoặc cấu hình yêu cầu. Kiểm tra file và model đã chọn.', 502);
    }
    let data;
    try { data = await response.json(); }
    catch { throw new AppError('provider_response', 'Deepgram trả về dữ liệu không đọc được.', 502); }
    const text = data?.results?.channels?.[0]?.alternatives?.[0]?.transcript;
    if (typeof text !== 'string') throw new AppError('provider_response', 'Phản hồi Deepgram thiếu trường transcript.', 502);
    const duration = data?.metadata?.duration;
    const id = data?.metadata?.request_id;
    return {
      sessionId: randomUUID(), fileName: audio.name, text: text.trim(), status: text.trim() ? 'completed' : 'completed_empty',
      provider: 'deepgram', language: 'vi', model: settings.model,
      requestId: typeof id === 'string' && /^[a-zA-Z0-9-]{1,100}$/.test(id) ? id : null,
      audioSeconds: typeof duration === 'number' && Number.isFinite(duration) && duration >= 0 ? duration : null,
      requestMs: Math.round(performance.now() - started),
    };
  } catch (error) {
    if (timeout.aborted) throw new AppError('provider_timeout', 'Hết thời gian chờ Deepgram. Chưa có kết quả được xác nhận; bạn có thể thử lại.', 504);
    if (clientSignal?.aborted) throw new AppError('request_cancelled', 'Yêu cầu đã bị ngắt trước khi nhận đủ kết quả.', 499);
    if (error instanceof AppError) throw error;
    throw new AppError('provider_network', 'Không kết nối được Deepgram. Kiểm tra Internet rồi thử lại.', 502);
  }
}
