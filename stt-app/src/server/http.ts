import { AppError } from './errors';

export function requireLocalOrigin(request: Request, mutation = false): void {
  const url = new URL(request.url);
  if (!['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname))
    throw new AppError('local_only', 'Mốc hiện tại chỉ hỗ trợ truy cập cục bộ trên máy chạy ứng dụng.', 403);
  // Next may construct request.url with "localhost" even when the client used
  // 127.0.0.1. Validate the actual Host authority; never trust forwarded headers.
  const host = request.headers.get('host') || url.host;
  if (!/^(localhost|127\.0\.0\.1|\[::1\])(?::\d{1,5})?$/.test(host))
    throw new AppError('local_only', 'Mốc hiện tại chỉ hỗ trợ truy cập cục bộ trên máy chạy ứng dụng.', 403);
  const expectedOrigin = new URL(`${url.protocol}//${host}`).origin;
  const origin = request.headers.get('origin');
  if ((mutation && !origin) || (origin && origin !== expectedOrigin))
    throw new AppError('origin_denied', 'Nguồn yêu cầu không hợp lệ. Hãy mở ứng dụng bằng địa chỉ cục bộ của nó.', 403);
}

export async function boundedBody(request: Request, limit: number): Promise<Uint8Array> {
  const length = request.headers.get('content-length');
  if (length && (!/^\d+$/.test(length) || Number(length) > limit)) throw new AppError('body_too_large', 'Dữ liệu gửi lên vượt giới hạn cho phép.', 413);
  if (!request.body) throw new AppError('body_empty', 'Yêu cầu chưa có dữ liệu.');
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > limit) {
        await reader.cancel();
        throw new AppError('body_too_large', 'Dữ liệu gửi lên vượt giới hạn cho phép.', 413);
      }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const body = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
  return body;
}
