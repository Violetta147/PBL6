'use client';

import React, { useState, useEffect, useRef } from 'react';
import { validateTitle } from '../utils/composerLogic';

interface HeaderProps {
  title: string;
  isNew: boolean;
  onRename?: (newTitle: string) => Promise<boolean | void>;
  onOpenHistory?: () => void;
  onOpenSettings?: () => void;
}

export function Header({
  title,
  isNew,
  onRename,
  onOpenHistory,
  onOpenSettings,
}: HeaderProps) {
  const [editableTitle, setEditableTitle] = useState(title);
  const cancelCommitRef = useRef(false);

  useEffect(() => {
    setEditableTitle(title);
  }, [title]);

  async function handleCommit() {
    if (cancelCommitRef.current) {
      cancelCommitRef.current = false;
      return;
    }
    const { title: finalTitle, changed } = validateTitle(editableTitle, title);
    setEditableTitle(finalTitle);
    if (changed && onRename) {
      try {
        const ok = await onRename(finalTitle);
        if (ok === false) {
          setEditableTitle(title);
        }
      } catch {
        setEditableTitle(title);
      }
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.currentTarget.blur();
    } else if (e.key === 'Escape') {
      cancelCommitRef.current = true;
      setEditableTitle(title);
      e.currentTarget.blur();
    }
  }

  return (
    <header className="flex h-[64px] w-full shrink-0 items-center justify-between border-b border-[#BAC5D0] bg-[#FFFFFF] px-4">
      {/* Left button: Hội thoại */}
      <div className="flex items-center select-none">
        <button
          type="button"
          onClick={onOpenHistory}
          className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-[#BAC5D0] bg-[#FFFFFF] px-4 py-2 text-[18px] font-semibold text-[#273D53] transition-colors hover:bg-[#F5F7F9] focus-visible:outline-2 focus-visible:outline-[#273D53]"
          aria-label="Mở danh sách hội thoại"
          data-testid="history-button"
        >
          Hội thoại
        </button>
      </div>

      {/* Center: Inline Title */}
      <div className="flex flex-1 items-center justify-center px-2">
        {isNew ? (
          <span
            className="max-w-[500px] truncate text-center text-[24px] font-bold text-[#18212B] select-none"
            data-testid="conversation-title-locked"
          >
            Hội thoại mới
          </span>
        ) : (
          <input
            type="text"
            maxLength={72}
            value={editableTitle}
            onChange={(e) => setEditableTitle(e.target.value)}
            onBlur={handleCommit}
            onKeyDown={handleKeyDown}
            aria-label="Tiêu đề hội thoại"
            data-testid="conversation-title-input"
            className="max-w-[500px] truncate border-0 bg-transparent text-center text-[24px] font-bold text-[#18212B] outline-none transition-opacity focus:ring-0 select-text"
          />
        )}
      </div>

      {/* Right button: Cài đặt */}
      <div className="flex items-center select-none">
        <button
          type="button"
          onClick={onOpenSettings}
          className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-[#BAC5D0] bg-[#FFFFFF] px-4 py-2 text-[18px] font-semibold text-[#273D53] transition-colors hover:bg-[#F5F7F9] focus-visible:outline-2 focus-visible:outline-[#273D53]"
          aria-label="Mở cài đặt"
          data-testid="settings-button"
        >
          Cài đặt
        </button>
      </div>
    </header>
  );
}
