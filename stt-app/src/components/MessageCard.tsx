'use client';

import React from 'react';
import type { Message } from '../contracts';

interface MessageCardProps {
  message: Message;
}

export function MessageText({ message }: MessageCardProps) {
  if (!message.signGlosses?.length) return <>{message.text}</>;
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
  return (
    <article
      className="w-full rounded-2xl border border-[#BAC5D0] bg-[#FFFFFF] p-5 shadow-[0_2px_8px_rgba(24,33,43,0.04)] sm:p-6"
      data-testid="message-card"
      data-message-id={message.id}
    >
      {/* 24px text, clean display, no sender names or roles, no TTS button, no sources badges */}
      <p className="whitespace-pre-wrap break-words text-[24px] leading-relaxed text-[#18212B]">
        <MessageText message={message} />
      </p>
    </article>
  );
}
