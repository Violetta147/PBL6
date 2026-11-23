export class AppError extends Error {
  constructor(public code: string, message: string, public status = 400) {
    super(message);
  }
}

export function errorResponse(error: unknown, fields: Record<string, unknown> = {}): Response {
  // Never serialize an upstream body, exception message, settings object or key.
  const e = error instanceof AppError ? error :
    new AppError('internal_error', 'Không thể xử lý yêu cầu. Hãy thử lại; nếu còn lỗi, khởi động lại ứng dụng.', 500);
  return jsonResponse({ ...fields, error: { code: e.code, message: e.message } }, e.status);
}

export function jsonResponse(body: unknown, status = 200): Response {
  return Response.json(body, { status, headers: { 'Cache-Control': 'no-store' } });
}
