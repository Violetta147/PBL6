'use client';

import React from 'react';
import {
  formatUserFacingState,
  getStateBorderColor,
  type SegmenterState,
} from '../lib/slrClient';

interface SlrDockProps {
  slrBaseUrl: string;
  running: boolean;
  draining: boolean;
  segmenterState: SegmenterState;
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
  onStop: () => void;
}

export function SlrDock({
  slrBaseUrl,
  running,
  draining,
  segmenterState,
  wsConnected,
  captureFps,
  queueDepth,
  lastTiming,
  showDiagnostics,
  errorMessage,
  busy = false,
  onStop,
}: SlrDockProps) {
  const borderColor = getStateBorderColor(running, segmenterState);
  const statusLabel = formatUserFacingState(running, draining, segmenterState);
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
      className="flex w-[320px] sm:w-[340px] shrink-0 flex-col justify-between gap-2.5 border-r border-[#BAC5D0] bg-[#FFFFFF] p-3 select-none"
    >
      <div
        className="relative flex-1 min-h-0 overflow-hidden rounded-xl border-4 bg-[#0F172A] flex items-center justify-center transition-colors"
        style={{ borderColor }}
      >
        {/* Mirrored preview for natural signer feedback; backend keeps raw orientation */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`${slrBaseUrl}/video_feed`}
          alt="Camera nhận dạng ký hiệu"
          className="h-full w-full object-cover -scale-x-100"
        />

        <div className="absolute top-2.5 inset-x-2.5 flex justify-center">
          <span
            data-testid="slr-user-status"
            className="rounded-full bg-[#18212B]/90 px-3 py-1 text-[13px] font-bold text-white shadow"
          >
            {statusLabel}
          </span>
        </div>

        {!wsConnected && (
          <div className="absolute inset-x-2.5 bottom-10 rounded-lg bg-[#DC2626]/90 px-2.5 py-1.5 text-center text-[12px] font-semibold text-white">
            Mất kết nối tới máy chủ SLR ({slrBaseUrl})
          </div>
        )}

        {showDiagnostics && (
          <div
            data-testid="slr-diagnostics-bar"
            className="absolute bottom-2 inset-x-2 rounded-md bg-[#18212B]/85 px-2.5 py-1 text-center font-mono text-[12px] text-white"
          >
            FPS: {captureFps.toFixed(1)} | Q: {queueDepth} | pre: {preText} | 07b: {infText}
          </div>
        )}
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
        disabled={busy || draining}
        data-testid="slr-dock-stop"
        className="flex h-[52px] w-full shrink-0 items-center justify-center rounded-xl bg-[#DC2626] px-4 text-[18px] font-semibold text-white transition-opacity hover:opacity-95 disabled:opacity-50 cursor-pointer"
      >
        {draining ? 'Đang hoàn tất...' : 'Kết thúc ký'}
      </button>
    </aside>
  );
}
