'use client';

import React, { useState } from 'react';
import type { Message } from '../contracts';
import { VolumeIcon } from './Icons';
import { speakSentence } from '../lib/slrTts';

interface MessageCardProps {
  message: Message;
}

export function MessageText({ message }: MessageCardProps) {
  if (message.signSentence || !message.signGlosses?.length) return <>{message.text}</>;
  return <>{message.signGlosses.map((gloss, index) => (
    <React.Fragment key={`${gloss.utteranceId}:${gloss.segmentId}:${index}`}>
      {index > 0 && ' '}
      {gloss.status === 'unconfirmed' ? (
        <span
          className="rounded bg-orange-100 font-semibold text-orange-900"
          aria-label={`${gloss.label}, từ chưa rõ`}
        >
          {gloss.label}
        </span>
      ) : gloss.label}
    </React.Fragment>
  ))}</>;
}

export function MessageCard({ message }: MessageCardProps) {
  const [readStatus, setReadStatus] = useState('');
  return (
    <article
      className="w-full rounded-2xl border border-[#BAC5D0] bg-[#FFFFFF] p-5 shadow-[0_2px_8px_rgba(24,33,43,0.04)] sm:p-6"
      data-testid="message-card"
      data-message-id={message.id}
    >
      <div className="flex items-start justify-between gap-3">
        <p data-testid="message-text" className="min-w-0 flex-1 whitespace-pre-wrap break-words text-[24px] leading-relaxed text-[#18212B]">
          <MessageText message={message} />
        </p>
        <button type="button" data-testid="message-read-button" aria-label="Đọc tin nhắn"
          onClick={() => speakSentence(message.text, setReadStatus)}
          className="flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-xl border border-[#BAC5D0] px-3 text-[16px] font-semibold text-[#273D53]">
          <VolumeIcon size={18} />Đọc
        </button>
      </div>
      {readStatus && <p aria-live="polite" className="mt-1 text-[13px] text-[#4F5D6B]">{readStatus}</p>}
    </article>
  );
}
