'use client';

import React, { useEffect, useState, useCallback } from 'react';
import type { Conversation } from '../contracts';
import { XIcon, PlusIcon, MessageSquareIcon } from './Icons';

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeConversationId?: string | null;
  onSelectConversation: (conversationId: string) => Promise<void>;
  onNewConversation: () => void;
}

export function HistoryDrawer({
  isOpen,
  onClose,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
}: HistoryDrawerProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);

  // Fetch conversations whenever drawer opens
  const fetchConversations = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/conversations');
      if (res.ok) {
        const data: Conversation[] = await res.json();
        setConversations(data);
      }
    } catch {
      // Retain existing list on network error
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      void fetchConversations();
    }
  }, [isOpen, fetchConversations]);

  // Handle ESC key to close
  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  function formatDate(isoString: string): string {
    try {
      const d = new Date(isoString);
      if (isNaN(d.getTime())) return '';
      const now = new Date();
      const isToday =
        d.getDate() === now.getDate() &&
        d.getMonth() === now.getMonth() &&
        d.getFullYear() === now.getFullYear();

      const timeStr = d.toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      });

      if (isToday) {
        return timeStr;
      }
      const dateStr = d.toLocaleDateString('vi-VN', {
        day: '2-digit',
        month: '2-digit',
      });
      return `${timeStr} · ${dateStr}`;
    } catch {
      return '';
    }
  }

  return (
    <div className="absolute inset-0 z-50 flex select-none" role="dialog" aria-modal="true" aria-label="Bảng lịch sử hội thoại">
      {/* Dark backdrop overlay covering the rest of the screen */}
      <div
        className="absolute inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
        data-testid="history-drawer-backdrop"
        aria-label="Đóng bảng lịch sử"
      />

      {/* Slide-in drawer from left edge (360px width on 1024x600) */}
      <aside
        className="relative z-10 flex h-full w-[360px] max-w-[90vw] flex-col border-r border-[#BAC5D0] bg-[#FFFFFF] shadow-2xl animate-in slide-in-from-left duration-200"
        data-testid="history-drawer"
      >
        {/* Drawer Top Header: Title & Close Button */}
        <div className="flex h-[64px] shrink-0 items-center justify-between border-b border-[#BAC5D0] px-4">
          <h2 className="text-[20px] font-bold text-[#18212B]">
            Lịch sử hội thoại
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng"
            data-testid="history-drawer-close"
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-[#273D53] hover:bg-[#F5F7F9] focus-visible:outline-2 focus-visible:outline-[#273D53]"
          >
            <XIcon size={24} />
          </button>
        </div>

        {/* Top of drawer: + Hội thoại mới button */}
        <div className="p-4 border-b border-[#BAC5D0]">
          <button
            type="button"
            onClick={onNewConversation}
            data-testid="new-conversation-button"
            className="flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl bg-[#273D53] px-4 py-2.5 text-[18px] font-semibold text-white shadow-sm transition-all hover:bg-[#1E2F40] active:scale-[0.99] focus-visible:outline-2 focus-visible:outline-[#273D53]"
          >
            <PlusIcon size={20} />
            Hội thoại mới
          </button>
        </div>

        {/* Conversation List / Empty State */}
        <div className="flex-1 overflow-y-auto p-3" data-testid="history-list">
          {loading && conversations.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-[16px] text-[#4F5D6B]">
              Đang tải…
            </div>
          ) : conversations.length === 0 ? (
            <div
              className="flex h-40 flex-col items-center justify-center px-4 text-center text-[18px] text-[#4F5D6B]"
              data-testid="history-empty"
            >
              <MessageSquareIcon size={32} className="mb-2 text-[#BAC5D0]" />
              <p>Chưa có hội thoại đã lưu.</p>
            </div>
          ) : (
            <ul className="flex flex-col space-y-1.5" role="list">
              {conversations.map((conv) => {
                const isActive = conv.id === activeConversationId;
                return (
                  <li key={conv.id}>
                    <button
                      type="button"
                      onClick={() => void onSelectConversation(conv.id)}
                      data-testid={`history-item-${conv.id}`}
                      data-history-item="true"
                      className={`flex min-h-[52px] w-full flex-col justify-center rounded-xl px-3.5 py-2 text-left transition-colors ${
                        isActive
                          ? 'bg-[#EBF1F6] border-l-4 border-[#273D53]'
                          : 'hover:bg-[#F5F7F9] border-l-4 border-transparent'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-[18px] font-medium text-[#18212B]">
                          {conv.title}
                        </span>
                        <span className="shrink-0 text-[14px] text-[#4F5D6B]">
                          {formatDate(conv.updatedAt)}
                        </span>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </aside>
    </div>
  );
}
