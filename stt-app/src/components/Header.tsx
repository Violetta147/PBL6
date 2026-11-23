'use client';

import React from 'react';
import { CameraIcon } from './Icons';

interface HeaderProps {
  onOpenHistory?: () => void;
  onOpenSettings?: () => void;
  isSigning?: boolean;
  isSigningBusy?: boolean;
  onToggleSigning?: () => void;
}

export function Header({
  onOpenHistory,
  onOpenSettings,
  isSigning = false,
  isSigningBusy = false,
  onToggleSigning,
}: HeaderProps) {
  return (
    <header className="flex w-full shrink-0 items-center justify-between gap-2 border-b border-[#BAC5D0] bg-white px-2 py-2 sm:px-4 min-[900px]:landscape:h-[64px]">
      {/* Left button: Hội thoại */}
      <div className="flex items-center select-none">
        <button
          type="button"
          onClick={onOpenHistory}
          className="flex min-h-[44px] min-w-[44px] items-center justify-center whitespace-nowrap rounded-xl border border-[#BAC5D0] bg-white px-2.5 py-2 text-[15px] font-semibold text-[#273D53] transition-colors hover:bg-[#F5F7F9] focus-visible:outline-2 focus-visible:outline-[#273D53] sm:px-4 sm:text-[18px]"
          aria-label="Mở danh sách hội thoại"
          data-testid="history-button"
        >
          Hội thoại
        </button>
      </div>

      {/* Right buttons: Bắt đầu ký + Cài đặt */}
      <div className="flex shrink-0 items-center justify-end gap-1.5 select-none sm:gap-2">
        {onToggleSigning && (
          <button
            type="button"
            onClick={onToggleSigning}
            disabled={isSigningBusy}
            data-testid="slr-toggle-button"
            aria-label={isSigning ? 'Dừng nhận dạng ký hiệu' : 'Bắt đầu nhận dạng ký hiệu'}
            className={`flex min-h-[44px] items-center justify-center gap-1.5 whitespace-nowrap rounded-xl px-2.5 py-2 text-[15px] font-semibold text-white transition-colors focus-visible:outline-2 focus-visible:outline-[#273D53] disabled:opacity-50 cursor-pointer sm:gap-2 sm:px-4 sm:text-[18px] ${
              isSigning
                ? 'bg-[#DC2626] hover:bg-[#B91C1C]'
                : 'bg-[#273D53] hover:bg-[#1E2F40]'
            }`}
          >
            <CameraIcon size={18} />
            <span>{isSigning ? 'Kết thúc phiên ký' : 'Bắt đầu ký'}</span>
          </button>
        )}
        <button
          type="button"
          onClick={onOpenSettings}
          className="flex min-h-[44px] min-w-[44px] items-center justify-center whitespace-nowrap rounded-xl border border-[#BAC5D0] bg-white px-2.5 py-2 text-[15px] font-semibold text-[#273D53] transition-colors hover:bg-[#F5F7F9] focus-visible:outline-2 focus-visible:outline-[#273D53] sm:px-4 sm:text-[18px]"
          aria-label="Mở cài đặt"
          data-testid="settings-button"
        >
          Cài đặt
        </button>
      </div>
    </header>
  );
}
