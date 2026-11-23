'use client';

import React from 'react';
import { signingIndicator, type SegmenterState } from '../lib/slrClient';

interface SlrDockProps {
  slrBaseUrl: string;
  running: boolean;
  draining: boolean;
  segmenterState: SegmenterState;
  arms?: readonly (string | null)[];
  wsConnected: boolean;
  captureFps: number;
  queueDepth: number;
  lastTiming?: {
    preprocessing_seconds?: number;
    inference_seconds?: number;
  } | null;
  showDiagnostics: boolean;
  errorMessage?: string | null;
  busy?: boolean;
  compact?: boolean;
  onStop: () => void;
}

export function SlrDock({
  slrBaseUrl,
  running,
  draining,
  segmenterState,
  arms = [],
  wsConnected,
  captureFps,
  queueDepth,
  lastTiming,
  showDiagnostics,
  errorMessage,
  busy = false,
  compact = false,
  onStop,
}: SlrDockProps) {
  const status = signingIndicator(running, draining, segmenterState, arms, wsConnected);
  const preText =
    typeof lastTiming?.preprocessing_seconds === 'number'
      ? `${lastTiming.preprocessing_seconds.toFixed(2)}s`
      : '—';
  const infText =
    typeof lastTiming?.inference_seconds === 'number'
      ? `${lastTiming.inference_seconds.toFixed(2)}s`
      : '—';

  return (
    <aside
      aria-label="Khung camera ký hiệu"
      data-testid="slr-dock"
      className="flex w-full shrink-0 flex-col gap-2 border-b border-[#BAC5D0] bg-white p-2.5 select-none sm:p-3 min-[900px]:landscape:w-[340px] min-[900px]:landscape:border-r min-[900px]:landscape:border-b-0"
    >
      <div className="grid min-h-0 grid-cols-2 gap-3 min-[900px]:landscape:flex min-[900px]:landscape:flex-1 min-[900px]:landscape:flex-col">
      <div
        data-testid="slr-video-panel"
        className={`relative flex min-h-0 items-center justify-center overflow-hidden rounded-xl border-2 border-[#BAC5D0] bg-[#0F172A] min-[900px]:landscape:h-auto min-[900px]:landscape:flex-1 ${
          compact ? 'h-[clamp(100px,16dvh,170px)]' : 'h-[clamp(116px,31dvh,320px)]'
        }`}
      >
        {/* Mirrored preview for natural signer feedback; backend keeps raw orientation */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        {(running || draining) ? <img
          src={`${slrBaseUrl}/video_feed`}
          alt="Camera nhận dạng ký hiệu"
          className="h-full w-full object-contain -scale-x-100"
        /> : <span className="text-[18px] text-white">Camera đã dừng · Không ghi hình</span>}

        {showDiagnostics && (
          <div
            data-testid="slr-diagnostics-bar"
            className="absolute bottom-2 inset-x-2 rounded-md bg-[#18212B]/85 px-2.5 py-1 text-center font-mono text-[12px] text-white"
          >
            FPS: {captureFps.toFixed(1)} | Q: {queueDepth} | pre: {preText} | 07b: {infText}
          </div>
        )}
      </div>
      <section data-testid="slr-status-panel" data-state={status.kind} role="status"
        className="flex min-h-[100px] flex-col items-center justify-center gap-3 rounded-xl border-2 px-3 py-4 text-center min-[900px]:landscape:shrink-0"
        style={{ backgroundColor: status.background, borderColor: status.border, color: status.color }}>
        <span data-testid="slr-user-status" className="text-[20px] font-bold leading-snug sm:text-[22px]">{status.label}</span>
        <span className={`text-[14px] leading-snug ${compact ? 'hidden' : ''}`}>{status.detail}</span>
      </section>
      </div>

      {errorMessage && (
        <p
          role="alert"
          className="text-[13px] font-medium text-[#DC2626] m-0 leading-snug"
        >
          {errorMessage}
        </p>
      )}

      <button
        type="button"
        onClick={onStop}
        disabled={busy || draining || !running}
        data-testid="slr-dock-stop"
        className="hidden h-[52px] w-full shrink-0 items-center justify-center rounded-xl bg-[#DC2626] px-4 text-[18px] font-semibold text-white transition-opacity hover:opacity-95 disabled:opacity-50 cursor-pointer min-[900px]:landscape:flex"
      >
        {draining ? 'Đang hoàn tất...' : running ? 'Kết thúc phiên ký' : 'Camera đã dừng'}
      </button>
    </aside>
  );
}
