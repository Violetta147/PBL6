'use client';

import React, { useId, useState } from 'react';
import type { SignGloss } from '../contracts';
import type { SlrGlossRecord, SlrTopCandidate } from '../lib/slrClient';

export interface LiveGlossItem extends SignGloss {
  confidence: number;
  lowConfidence: boolean;
}

export function toLiveGlossItem(gloss: SlrGlossRecord): LiveGlossItem {
  const picked = gloss.selected_candidate;
  return {
    segmentId: gloss.segment_id,
    utteranceId: gloss.utterance_id,
    label: picked?.label ?? gloss.raw.top1_label,
    originalLabel: gloss.raw.top1_label,
    status: picked ? 'confirmed' : gloss.raw.low_confidence ? 'unconfirmed' : 'recognized',
    labelId: picked?.label_id ?? gloss.raw.top1_id,
    confidence: picked?.score ?? gloss.raw.confidence,
    lowConfidence: !picked && gloss.raw.low_confidence,
    top3: (gloss.raw.top5 ?? []).slice(0, 3),
  };
}

interface LiveSigningCardProps {
  running: boolean;
  glosses: LiveGlossItem[];
  autoSpeak: boolean;
  autoSaveOnRest: boolean;
  ttsStatus: string;
  onPickCandidate: (segmentId: string, candidate: SlrTopCandidate) => void;
  onDropGloss: (segmentId: string) => void;
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
  onManualSave,
}: LiveSigningCardProps) {
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

      <LiveGlossPicker
        glosses={glosses}
        onPickCandidate={onPickCandidate}
        onDropGloss={onDropGloss}
        emptyText="Buông 2 tay 0.35 giây để bắt đầu ký..."
      />

      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-[#E2E8F0] pt-2">
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

export function LiveGlossPicker({
  glosses, onPickCandidate, onDropGloss, emptyText,
}: {
  glosses: LiveGlossItem[];
  onPickCandidate: LiveSigningCardProps['onPickCandidate'];
  onDropGloss?: LiveSigningCardProps['onDropGloss'];
  emptyText: string;
}) {
  const [focusedSegment, setFocusedSegment] = useState<string | null>(null);
  const panelId = useId();
  const unclear = glosses.filter((gloss) => gloss.lowConfidence);
  const active = unclear.find((gloss) => gloss.segmentId === focusedSegment) ?? unclear[0];

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 min-h-[36px]">
        {glosses.length === 0 ? (
          <span className="text-[16px] text-[#4F5D6B]">
            {emptyText}
          </span>
        ) : (
          glosses.map((g) =>
            g.lowConfidence ? (
              <button
                type="button"
                key={g.segmentId}
                aria-pressed={active?.segmentId === g.segmentId}
                aria-label={`${g.label}, từ chưa rõ`}
                aria-controls={panelId}
                onClick={() => setFocusedSegment(g.segmentId)}
                className="min-h-[44px] cursor-pointer rounded-xl border-2 border-orange-300 bg-orange-100 px-3 py-1 text-[20px] font-bold text-orange-900 aria-pressed:border-orange-700 aria-pressed:ring-2 aria-pressed:ring-orange-300"
              >
                {g.label}
              </button>
            ) : (
              <span
                key={g.segmentId}
                className="inline-flex items-center gap-1.5 rounded-xl bg-[#DDF7E9] py-1 pl-3 pr-2 text-[22px] font-bold text-[#0B6B45]"
              >
                <span>{g.label}</span>
                {onDropGloss && <button
                  type="button"
                  onClick={() => onDropGloss(g.segmentId)}
                  aria-label={`Xóa từ ${g.label}`}
                  className="inline-flex h-6 w-6 items-center justify-center rounded-lg text-[16px] font-bold text-[#0B6B45]/75 hover:bg-[#0B6B45]/15 hover:text-[#0B6B45] cursor-pointer"
                >
                  ×
                </button>}
              </span>
            )
          )
        )}
      </div>

      {active && (
        <div id={panelId} className="rounded-xl border border-orange-300 bg-orange-50 p-2.5 space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[13px] font-bold text-orange-900">
              Đang chỉnh: {active.label}
            </span>
            {onDropGloss && <button
              type="button"
              onClick={() => onDropGloss(active.segmentId)}
              className="min-h-[44px] rounded-lg border border-orange-300 px-3 text-[15px] font-semibold text-orange-900 cursor-pointer"
            >
              Bỏ từ này
            </button>}
          </div>
          <div className="flex flex-wrap gap-2">
            {active.top3.map((cand) => (
              <button
                key={`${active.segmentId}-${cand.label_id}`}
                type="button"
                onClick={() => onPickCandidate(active.segmentId, cand)}
                className="min-h-[44px] rounded-lg border border-orange-300 bg-white px-3 py-1 text-[15px] font-bold text-[#18212B] hover:bg-orange-100 cursor-pointer"
              >
                {cand.label}
              </button>
            ))}
          </div>
        </div>
      )}

    </>
  );
}
