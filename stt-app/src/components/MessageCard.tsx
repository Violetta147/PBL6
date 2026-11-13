'use client';

import React from 'react';
import type { Message } from '../contracts';

interface MessageCardProps {
  message: Message;
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
        {message.text}
      </p>
    </article>
  );
}
