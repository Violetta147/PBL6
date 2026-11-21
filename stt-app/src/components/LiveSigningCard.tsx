'use client';

import React from 'react';
import type { SlrTopCandidate } from '../lib/slrClient';
import { VolumeIcon } from './Icons';

export interface LiveGlossItem {
  segmentId: string;
  utteranceId: string;
  label: string;
  labelId: number;
  confidence: number;
  lowConfidence: boolean;
  top3: SlrTopCandidate[];
}

interface LiveSigningCardProps {
  running: boolean;
  glosses: LiveGlossItem[];
  autoSpeak: boolean;
  autoSaveOnRest: boolean;
  ttsStatus: string;
  onPickCandidate: (segmentId: string, candidate: SlrTopCandidate) => void;
  onDropGloss: (segmentId: string) => void;
  onReplayAudio: () => void;
  onManualSave: () => void;
}

export function LiveSigningCard({
  running,
  glosses,
  autoSpeak,
  autoSaveOnRest: _autoSaveOnRest,
  ttsStatus,
  onPickCandidate,
  onDropGloss,
  onReplayAudio,
  onManualSave,
}: LiveSigningCardProps) {
  const lastLow = [...glosses].reverse().find((g) => g.lowConfidence);
  const clearGlosses = glosses.filter((g) => !g.lowConfidence);
  const showManualSave = true;

  return (
    <article
      aria-label="Thẻ đang ký trực tiếp"
      data-testid="live-signing-card"
      className="w-full rounded-2xl border-2 border-[#273D53] bg-[#FFFFFF] p-4 shadow-[0_2px_8px_rgba(24,33,43,0.06)] space-y-2.5"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={`inline-block h-2.5 w-2.5 rounded-full ${
              running ? 'bg-[#087A47] animate-pulse' : 'bg-[#4F5D6B]'
            }`}
          />
          <span className="text-[13px] font-bold uppercase tracking-wider text-[#273D53]">
            Đang ký trực tiếp
          </span>
        </div>

        <span className="text-[13px] font-semibold text-[#087A47]">
          {ttsStatus || (autoSpeak ? 'Loa tự động: Bật' : 'Loa tự động: Tắt')}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2 min-h-[36px]">
        {glosses.length === 0 ? (
          <span className="text-[16px] text-[#4F5D6B]">
            Buông 2 tay 0.35 giây để bắt đầu ký...
          </span>
        ) : (
          glosses.map((g) =>
            g.lowConfidence ? (
              <span
                key={g.segmentId}
                className="rounded-xl border border-[#FCA5A5] bg-[#FDE7E7] px-3 py-1 text-[20px] font-bold text-[#C52236]"
              >
                CHƯA RÕ ({g.label})
              </span>
            ) : (
              <span
                key={g.segmentId}
                className="inline-flex items-center gap-1.5 rounded-xl bg-[#DDF7E9] py-1 pl-3 pr-2 text-[22px] font-bold text-[#0B6B45]"
              >
                <span>{g.label}</span>
                <button
                  type="button"
                  onClick={() => onDropGloss(g.segmentId)}
                  aria-label={`Xóa từ ${g.label}`}
                  className="inline-flex h-6 w-6 items-center justify-center rounded-lg text-[16px] font-bold text-[#0B6B45]/75 hover:bg-[#0B6B45]/15 hover:text-[#0B6B45] cursor-pointer"
                >
                  ×
                </button>
              </span>
            )
          )
        )}
      </div>

      {lastLow && (
        <div className="rounded-xl border border-[#FCA5A5] bg-[#FEF2F2] p-2.5 space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[13px] font-bold text-[#B91C1C]">
              Chưa rõ — chạm gợi ý đúng hoặc bỏ từ:
            </span>
            <button
              type="button"
              onClick={() => onDropGloss(lastLow.segmentId)}
              className="text-[13px] font-semibold text-[#B91C1C] underline cursor-pointer"
            >
              Bỏ từ này
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {lastLow.top3.map((cand) => (
              <button
                key={`${lastLow.segmentId}-${cand.label_id}`}
                type="button"
                onClick={() => onPickCandidate(lastLow.segmentId, cand)}
                className="min-h-[36px] rounded-lg border border-[#FCA5A5] bg-[#FFFFFF] px-3 py-1 text-[15px] font-bold text-[#18212B] hover:bg-[#FEE2E2] cursor-pointer"
              >
                {cand.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-[#E2E8F0] pt-2">
        <button
          type="button"
          onClick={onReplayAudio}
          disabled={clearGlosses.length === 0}
          data-testid="slr-replay-audio-button"
          className="flex min-h-[42px] items-center gap-1.5 rounded-xl border border-[#BAC5D0] bg-[#FFFFFF] px-3.5 py-1.5 text-[16px] font-semibold text-[#18212B] hover:bg-[#F5F7F9] disabled:opacity-45 cursor-pointer"
        >
          <VolumeIcon size={18} />
          Nghe lại
        </button>

        {showManualSave && (
          <button
            type="button"
            onClick={onManualSave}
            disabled={glosses.length === 0}
            data-testid="slr-save-message-button"
            className="flex min-h-[42px] items-center justify-center rounded-xl bg-[#273D53] px-4 py-1.5 text-[16px] font-semibold text-white hover:opacity-95 disabled:opacity-45 cursor-pointer"
          >
            Lưu vào hội thoại
          </button>
        )}
      </div>
    </article>
  );
}
