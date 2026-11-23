export type SegmenterState = 'UNKNOWN' | 'READY' | 'CAPTURING' | 'END_PENDING';

export interface SlrTopCandidate {
  label: string;
  label_id: number;
  score: number;
}

export interface SlrGlossRecord {
  segment_id: string;
  utterance_id: string;
  start: number;
  movement_start: number;
  movement_end: number;
  end: number;
  selected_candidate?: SlrTopCandidate;
  raw: {
    top1_label: string;
    top1_id: number;
    confidence: number;
    low_confidence: boolean;
    top5: SlrTopCandidate[];
  };
  timing?: {
    preprocessing_seconds?: number;
    inference_seconds?: number;
    queue_and_classify_seconds?: number;
  };
  source_frames?: number;
}

export interface SlrUtteranceRecord {
  utterance_id: string;
  revision: number;
  reason: string;
  timestamp: number;
  raw_glosses: string[];
  segments: SlrGlossRecord[];
  revised_glosses: string[] | null;
  vietnamese_sentence: string | null;
}

export interface SlrSnapshot {
  schema_version: string;
  session_id: string | null;
  epoch: number;
  running: boolean;
  draining: boolean;
  segmenter_state: SegmenterState;
  arms: (string | null)[];
  queue_depth: number;
  capture_fps: number;
  glosses: SlrGlossRecord[];
  utterances: SlrUtteranceRecord[];
  last_error: string | null;
}

export type SlrWsEvent =
  | { type: 'snapshot'; snapshot: SlrSnapshot }
  | {
      type: 'status';
      segmenter_state: SegmenterState;
      arms: (string | null)[];
      timestamp: number;
      queue_depth: number;
      capture_fps: number;
    }
  | { type: 'segment_complete'; segment: { segment_id: string }; frame_count: number }
  | { type: 'segment_incomplete'; segment: { segment_id: string; reason?: string } }
  | { type: 'gloss_result'; gloss: SlrGlossRecord }
  | { type: 'gloss_corrected'; session_id: string; gloss: SlrGlossRecord }
  | { type: 'utterance_ready'; utterance: SlrUtteranceRecord }
  | { type: 'session_started'; source: string; session_id?: string }
  | { type: 'session_stopped'; snapshot: SlrSnapshot }
  | { type: 'error'; message: string }
  | { type: 'error_cleared' };

export function formatUserFacingState(
  running: boolean,
  draining: boolean,
  state?: SegmenterState | string | null
): string {
  if (draining) return 'Đang hoàn tất...';
  if (!running) return 'Chưa bắt đầu';
  switch (state) {
    case 'READY':
      return 'Sẵn sàng ký';
    case 'CAPTURING':
      return 'Đang nhận ký hiệu...';
    case 'END_PENDING':
      return 'Đang xác nhận...';
    case 'UNKNOWN':
    default:
      return 'Đưa vai & 2 tay vào khung';
  }
}

export function getStateBorderColor(
  running: boolean,
  state?: SegmenterState | string | null
): string {
  if (!running) return '#BAC5D0';
  switch (state) {
    case 'READY':
      return '#087A47';
    case 'CAPTURING':
      return '#2563EB';
    case 'END_PENDING':
      return '#2563EB';
    case 'UNKNOWN':
    default:
      return '#F97316';
  }
}

export function signingIndicator(running: boolean, draining: boolean, state: SegmenterState,
  arms: readonly (string | null)[] = [], connected = true) {
  const colors = {
    orange: { background: '#FFF7ED', border: '#FFB86A', color: '#7E2A0C' },
    blue: { background: '#EFF6FF', border: '#93C5FD', color: '#1D4ED8' },
    green: { background: '#DDF7E9', border: '#86D4B0', color: '#087A47' },
    gray: { background: '#F0F3F6', border: '#BAC5D0', color: '#4F5D6B' },
  };
  if (!running && !draining) return { kind: 'stopped', label: 'Camera đã dừng', detail: 'Không ghi hình', ...colors.gray };
  if (!connected) return { kind: 'unknown', label: 'Mất kết nối', detail: 'Đang kết nối lại máy nhận dạng', ...colors.orange };
  if (draining) return { kind: 'processing', label: 'Đang hoàn tất', detail: 'Chờ kết quả nhận dạng còn lại', ...colors.blue };
  if (state === 'READY') return { kind: 'ready', label: 'Sẵn sàng ký', detail: 'Bạn có thể bắt đầu ký hiệu tiếp theo', ...colors.green };
  if (state === 'CAPTURING') return { kind: 'capturing', label: 'Đang nhận ký hiệu', detail: 'Giữ người và hai tay trong khung', ...colors.blue };
  if (state === 'END_PENDING' || (arms.length === 2 && arms.every(a => a === 'rest'))) {
    return { kind: 'rest', label: 'Đang nghỉ', detail: 'Đang chờ xác nhận tư thế', ...colors.blue };
  }
  if (arms.length === 2 && arms.every(a => a === 'rest' || a === 'active')) {
    return { kind: 'unknown', label: 'Chờ tư thế bắt đầu', detail: 'Buông hai tay để sẵn sàng ký', ...colors.orange };
  }
  return { kind: 'unknown', label: 'Chưa thấy rõ người ký', detail: 'Đưa vai và hai tay vào khung', ...colors.orange };
}

export async function fetchSlrState(baseUrl: string): Promise<SlrSnapshot> {
  const res = await fetch(`${baseUrl}/api/state`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Không đọc được trạng thái SLR (${res.status})`);
  }
  return (await res.json()) as SlrSnapshot;
}

export async function startSlrSession(
  baseUrl: string,
  cameraIndex = 0
): Promise<SlrSnapshot> {
  const res = await fetch(`${baseUrl}/api/session/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ camera_index: cameraIndex }),
  });
  const data = (await res.json().catch(() => null)) as
    | { detail?: string; state?: SlrSnapshot }
    | null;
  if (!res.ok || !data?.state) {
    throw new Error(data?.detail || `Không bật được camera SLR (${res.status})`);
  }
  return data.state;
}

export async function stopSlrSession(baseUrl: string): Promise<SlrSnapshot> {
  const res = await fetch(`${baseUrl}/api/session/stop`, { method: 'POST' });
  const data = (await res.json().catch(() => null)) as
    | { detail?: string; state?: SlrSnapshot }
    | null;
  if (!res.ok || !data?.state) {
    throw new Error(data?.detail || `Không dừng được phiên SLR (${res.status})`);
  }
  return data.state;
}

export async function pickSlrCandidate(
  baseUrl: string, sessionId: string, segmentId: string, labelId: number, allowClosed = false
): Promise<SlrGlossRecord> {
  const res = await fetch(`${baseUrl}/api/session/glosses/${encodeURIComponent(segmentId)}/candidate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, label_id: labelId, allow_closed: allowClosed }),
  });
  const data = (await res.json().catch(() => null)) as
    | { detail?: string; gloss?: SlrGlossRecord }
    | null;
  if (!res.ok || !data?.gloss) {
    throw new Error(typeof data?.detail === 'string' ? data.detail : 'Không xác nhận được từ này.');
  }
  return data.gloss;
}
