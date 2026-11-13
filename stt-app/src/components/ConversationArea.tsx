'use client';

import React, { useEffect, useRef } from 'react';
import type { Message } from '../contracts';
import { MessageCard } from './MessageCard';

interface ConversationAreaProps {
  messages: Message[];
}

export function ConversationArea({ messages }: ConversationAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const prevCountRef = useRef(messages.length);

  useEffect(() => {
    // Auto-scroll when new messages arrive or when switching conversation
    if (messages.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
    prevCountRef.current = messages.length;
  }, [messages]);

  return (
    <section
      aria-label="Vùng hội thoại"
      className="flex flex-1 flex-col overflow-y-auto px-4 py-6 sm:px-8 space-y-4"
      data-testid="conversation-area"
    >
      {messages.length === 0 ? (
        // Empty state per spec: leave blank, no extraneous helper text
        <div className="flex-1" aria-hidden="true" />
      ) : (
        <div className="flex flex-col space-y-4">
          {messages.map((msg) => (
            <MessageCard key={msg.id} message={msg} />
          ))}
          <div ref={bottomRef} aria-hidden="true" className="h-1" />
        </div>
      )}
    </section>
  );
}
