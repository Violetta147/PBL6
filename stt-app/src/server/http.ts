import { AppError } from './errors';

const LOOPBACK_HOSTS = new Set(['127.0.0.1', 'localhost', '[::1]', '::1']);
const MDNS_LOCAL_RE = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.local$/i;
const IPV4_RE = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
const HOST_AUTHORITY_RE = /^(\[[0-9a-fA-F:]+\]|[a-zA-Z0-9.-]+)(?::(\d{1,5}))?$/;

function isValidOctet(segment: string): number | null {
  if (!/^(?:0|[1-9]\d{0,2})$/.test(segment)) return null;
  const n = Number(segment);
  return n >= 0 && n <= 255 ? n : null;
}

export function isPrivateLanHostname(hostname: string): boolean {
  const clean = hostname.trim().toLowerCase();
  if (!clean) return false;
  if (LOOPBACK_HOSTS.has(clean)) return true;
  if (MDNS_LOCAL_RE.test(clean)) return true;

  const ipv4Match = clean.match(IPV4_RE);
  if (!ipv4Match) return false;
  const octets = ipv4Match.slice(1).map(isValidOctet);
  if (octets.some((v) => v === null)) return false;
  const [a, b] = octets as number[];

  if (a === 10) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  return false;
}

function validateOriginHeader(request: Request, expectedOrigin: string, mutation: boolean, message: string): void {
  const origin = request.headers.get('origin');
  if ((mutation && !origin) || (origin && origin !== expectedOrigin)) {
    throw new AppError('origin_denied', message, 403);
  }
}

export function requireLocalOrigin(request: Request, mutation = false): void {
  const url = new URL(request.url);
  // Next.js bound to 0.0.0.0 constructs request.url with hostname 0.0.0.0; Host header still enforces loopback below.
  if (!['127.0.0.1', 'localhost', '[::1]', '0.0.0.0'].includes(url.hostname))
    throw new AppError('local_only', 'Mốc hiện tại chỉ hỗ trợ truy cập cục bộ trên máy chạy ứng dụng.', 403);
  // Next may construct request.url with "localhost" even when the client used
  // 127.0.0.1. Validate the actual Host authority; never trust forwarded headers.
  const host = request.headers.get('host') || url.host;
  if (!/^(localhost|127\.0\.0\.1|\[::1\])(?::\d{1,5})?$/.test(host))
    throw new AppError('local_only', 'Mốc hiện tại chỉ hỗ trợ truy cập cục bộ trên máy chạy ứng dụng.', 403);
  const expectedOrigin = new URL(`${url.protocol}//${host}`).origin;
  validateOriginHeader(
    request,
    expectedOrigin,
    mutation,
    'Nguồn yêu cầu không hợp lệ. Hãy mở ứng dụng bằng địa chỉ cục bộ của nó.'
  );
}

/** Allow read-only Companion history sync from loopback or RFC1918 / .local LAN hosts only. */
export function requireCompanionReadOrigin(request: Request): void {
  const url = new URL(request.url);
  if (url.hostname !== '0.0.0.0' && !isPrivateLanHostname(url.hostname)) {
    throw new AppError('local_only', 'Trình duyệt đồng hành chỉ hỗ trợ trong mạng cục bộ (LAN).', 403);
  }
  const host = request.headers.get('host') || url.host;
  const parsed = host.match(HOST_AUTHORITY_RE);
  if (!parsed) {
    throw new AppError('local_only', 'Trình duyệt đồng hành chỉ hỗ trợ trong mạng cục bộ (LAN).', 403);
  }
  const [, authorityHost, portStr] = parsed;
  if (portStr !== undefined) {
    const port = Number(portStr);
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
      throw new AppError('local_only', 'Cổng truy cập không hợp lệ.', 403);
    }
  }
  if (!isPrivateLanHostname(authorityHost)) {
    throw new AppError('local_only', 'Trình duyệt đồng hành chỉ hỗ trợ trong mạng cục bộ (LAN).', 403);
  }
  let expectedOrigin: string;
  try {
    expectedOrigin = new URL(`${url.protocol}//${host}`).origin;
  } catch {
    throw new AppError('local_only', 'Địa chỉ máy chủ không hợp lệ.', 403);
  }
  validateOriginHeader(
    request,
    expectedOrigin,
    false,
    'Nguồn yêu cầu không hợp lệ. Hãy mở trình duyệt đồng hành qua đúng địa chỉ LAN của thiết bị.'
  );
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
