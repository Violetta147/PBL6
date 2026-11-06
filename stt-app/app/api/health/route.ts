import { hostname } from 'node:os';
import { errorResponse, jsonResponse } from '../../../src/server/errors';
import { requireLocalOrigin } from '../../../src/server/http';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export function GET(request: Request) {
  try {
    requireLocalOrigin(request);
    return jsonResponse({ application: 'pbl6-stt', version: '0.1.0', milestone: 'V1-P1', host: hostname(),
      capabilities: { singleFile: true, batch: false, piCapture: false, streaming: false } });
  } catch (error) { return errorResponse(error); }
}
