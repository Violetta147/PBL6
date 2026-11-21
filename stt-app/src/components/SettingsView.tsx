'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import type { AudioDevice, PublicSettings, Conversation } from '../contracts';
import {
  DEFAULT_SLR_SETTINGS,
  normalizeSlrBaseUrl,
  stripSlrUrlScheme,
  type SlrSettings,
} from '../lib/slrSettings';
import { WebAudioRecorder } from '../utils/audioRecorder';
import { ArrowLeftIcon, SearchIcon, TrashIcon } from './Icons';

interface SettingsViewProps {
  isOpen: boolean;
  onClose: () => void;
  activeConversationId?: string | null;
  onActiveConversationDeleted?: () => void;
  onSettingsSaved?: () => void;
  slrSettings?: SlrSettings;
  onSlrSettingsChange?: (next: SlrSettings) => void;
}

type TabType = 'stt' | 'slr' | 'history';

interface InitialSttState {
  selectedMicrophoneId: string;
  maxRecordSeconds: number;
  timeoutSeconds: number;
  hasApiKey: boolean;
}

function formatHistoryDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleDateString('vi-VN');
  } catch {
    return '';
  }
}

export function SettingsView({
  isOpen,
  onClose,
  activeConversationId,
  onActiveConversationDeleted,
  onSettingsSaved,
  slrSettings = DEFAULT_SLR_SETTINGS,
  onSlrSettingsChange,
}: SettingsViewProps) {
  const [activeTab, setActiveTab] = useState<TabType>('stt');

  // STT Settings State
  const [microphones, setMicrophones] = useState<AudioDevice[]>([]);
  const [selectedMicId, setSelectedMicId] = useState<string>('');
  const [maxRecordSeconds, setMaxRecordSeconds] = useState<number | string>(120);
  const [timeoutSeconds, setTimeoutSeconds] = useState<number | string>(60);
  const [apiKey, setApiKey] = useState<string>('');
  const [clearApiKey, setClearApiKey] = useState<boolean>(false);
  const [hasApiKey, setHasApiKey] = useState<boolean>(false);
  const [saveNotice, setSaveNotice] = useState<string>('');
  const [saveError, setSaveError] = useState<string>('');

  // Initial STT snapshot for dirty tracking
  const [initialStt, setInitialStt] = useState<InitialSttState>({
    selectedMicrophoneId: '',
    maxRecordSeconds: 120,
    timeoutSeconds: 60,
    hasApiKey: false,
  });

  // Modal for unsaved changes confirmation
  const [showUnsavedModal, setShowUnsavedModal] = useState<boolean>(false);
  const [pendingNavigation, setPendingNavigation] = useState<
    (() => void) | null
  >(null);

  // History Tab State
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterDays, setFilterDays] = useState<string>('');
  const [historyConversations, setHistoryConversations] = useState<Conversation[]>([]);
  const [totalConversationsCount, setTotalConversationsCount] = useState<number>(0);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [deleteError, setDeleteError] = useState<string>('');
  const searchSeqRef = React.useRef(0);

  // Load Settings and Microphones (only when SettingsView opens)
  const loadSttSettings = useCallback(async () => {
    try {
      const [settingsRes, micsRes] = await Promise.all([
        fetch('/api/settings', { cache: 'no-store' }),
        fetch(`/api/devices/microphones?t=${Date.now()}`, { cache: 'no-store' }),
      ]);

      let loadedMicId = '';
      if (settingsRes.ok) {
        const settings: PublicSettings = await settingsRes.json();
        const rawMic = settings.selectedMicrophoneId || '';
        const micId = rawMic === 'default' ? '' : rawMic;
        loadedMicId = micId;
        const maxSec = settings.maxRecordSeconds ?? 120;
        const timeSec = settings.timeoutSeconds ?? 60;
        const hasKey = Boolean(settings.hasApiKey);

        setSelectedMicId(micId);
        setMaxRecordSeconds(maxSec);
        setTimeoutSeconds(timeSec);
        setHasApiKey(hasKey);
        setClearApiKey(false);
        setApiKey('');
        setSaveError('');

        setInitialStt({
          selectedMicrophoneId: micId,
          maxRecordSeconds: maxSec,
          timeoutSeconds: timeSec,
          hasApiKey: hasKey,
        });
      }

      let devList: AudioDevice[] = [];
      let webMics: AudioDevice[] = [];
      try {
        webMics = await WebAudioRecorder.enumerateMicrophones();
      } catch {}

      let serverMics: AudioDevice[] = [];
      if (micsRes.ok) {
        try {
          const micsData = await micsRes.json();
          serverMics = micsData.devices || [];
        } catch {}
      }

      const hasRealWebMics = webMics.some((m) => m.id && m.id !== 'default');
      const hasRealServerMics = serverMics.some((m) => m.id && m.id !== 'default');

      if (hasRealWebMics) {
        devList = webMics;
      } else if (hasRealServerMics) {
        devList = serverMics;
      } else if (webMics.length > 0) {
        devList = webMics;
      } else {
        devList = serverMics;
      }

      // If user saved a Windows GUID from backend and webMics provides a matching device:
      // Map to web device ID so it seamlessly selects without showing "(Đã ngắt kết nối)"
      if (loadedMicId && hasRealWebMics) {
        const direct = devList.find((m) => m.id === loadedMicId);
        if (!direct) {
          const serverMatch = serverMics.find((s) => s.id === loadedMicId);
          if (serverMatch) {
            const webMatch = devList.find(
              (w) =>
                w.name === serverMatch.name ||
                w.name.includes(serverMatch.name) ||
                serverMatch.name.includes(w.name)
            );
            if (webMatch) {
              setSelectedMicId(webMatch.id);
              setInitialStt((prev) => ({ ...prev, selectedMicrophoneId: webMatch.id }));
            }
          }
        }
      }

      setMicrophones(devList);
    } catch {
      // Ignore network errors on initial load
    }
  }, []);

  // Hotplug detection for microphones
  useEffect(() => {
    if (!isOpen) return;
    const unbind = WebAudioRecorder.onDeviceChange(async () => {
      try {
        let webMics: AudioDevice[] = [];
        try {
          webMics = await WebAudioRecorder.enumerateMicrophones();
        } catch {}

        let serverMics: AudioDevice[] = [];
        try {
          const res = await fetch(`/api/devices/microphones?t=${Date.now()}`, { cache: 'no-store' });
          if (res.ok) {
            const data = await res.json();
            serverMics = data.devices || [];
          }
        } catch {}

        const hasRealWebMics = webMics.some((m) => m.id && m.id !== 'default');
        const hasRealServerMics = serverMics.some((m) => m.id && m.id !== 'default');

        if (hasRealWebMics) {
          setMicrophones(webMics);
        } else if (hasRealServerMics) {
          setMicrophones(serverMics);
        } else if (webMics.length > 0) {
          setMicrophones(webMics);
        } else if (serverMics.length > 0) {
          setMicrophones(serverMics);
        }
      } catch {}
    });
    return unbind;
  }, [isOpen]);

  // Load History list with query and filter, tracking sequence to discard stale responses
  const loadHistoryList = useCallback(async (query: string, days: string) => {
    const seq = ++searchSeqRef.current;
    try {
      const params = new URLSearchParams();
      if (query.trim()) params.set('query', query.trim());
      if (days) params.set('olderThanDays', days);

      const qs = params.toString();
      const url = qs ? `/api/conversations?${qs}` : '/api/conversations';
      const res = await fetch(url);
      if (seq !== searchSeqRef.current) return;

      if (res.ok) {
        const list: Conversation[] = await res.json();
        if (seq !== searchSeqRef.current) return;
        setHistoryConversations(list);
        if (!query.trim() && !days) {
          setTotalConversationsCount(list.length);
        }
      }

      // If filters are active, fetch unfiltered count to accurately distinguish zero total vs zero matches
      if (query.trim() || days) {
        const countRes = await fetch('/api/conversations');
        if (seq !== searchSeqRef.current) return;
        if (countRes.ok) {
          const allList: Conversation[] = await countRes.json();
          if (seq !== searchSeqRef.current) return;
          setTotalConversationsCount(allList.length);
        }
      }
    } catch {
      // Ignore fetch error
    }
  }, []);

  // Initial load of STT settings when dialog opens
  useEffect(() => {
    if (isOpen) {
      void loadSttSettings();
    }
  }, [isOpen, loadSttSettings]);

  // Debounced load of History list whenever search or filter changes
  useEffect(() => {
    if (!isOpen) return;
    const timer = setTimeout(
      () => {
        void loadHistoryList(searchQuery, filterDays);
      },
      searchQuery ? 150 : 0
    );
    return () => clearTimeout(timer);
  }, [isOpen, searchQuery, filterDays, loadHistoryList]);

  // Validation rules for STT
  const parsedMaxRecord = Number(maxRecordSeconds);
  const isMaxRecordValid =
    Number.isInteger(parsedMaxRecord) &&
    parsedMaxRecord >= 5 &&
    parsedMaxRecord <= 300;

  const parsedTimeout = Number(timeoutSeconds);
  const isTimeoutValid =
    Number.isInteger(parsedTimeout) &&
    parsedTimeout >= 5 &&
    parsedTimeout <= 300;

  const trimmedApiKey = apiKey.trim();
  const isApiKeyFormatValid =
    trimmedApiKey === '' || /^[A-Za-z0-9_-]{16,512}$/.test(trimmedApiKey);

  const isSttValid = isMaxRecordValid && isTimeoutValid && isApiKeyFormatValid;

  // Dirty check: comparison against baseline
  const isSttDirty = useMemo(() => {
    const normSelected = selectedMicId === 'default' ? '' : selectedMicId;
    const normInitial =
      initialStt.selectedMicrophoneId === 'default'
        ? ''
        : initialStt.selectedMicrophoneId;
    if (normSelected !== normInitial) return true;
    if (parsedMaxRecord !== initialStt.maxRecordSeconds) return true;
    if (parsedTimeout !== initialStt.timeoutSeconds) return true;
    if (apiKey.trim().length > 0) return true;
    if (clearApiKey) return true;
    return false;
  }, [
    selectedMicId,
    initialStt,
    parsedMaxRecord,
    parsedTimeout,
    apiKey,
    clearApiKey,
  ]);

  // Save STT settings
  const handleSaveStt = useCallback(async (): Promise<boolean> => {
    if (!isSttValid) return false;

    const normSelected = selectedMicId === 'default' ? '' : selectedMicId;
    const normInitial =
      initialStt.selectedMicrophoneId === 'default'
        ? ''
        : initialStt.selectedMicrophoneId;

    const payload: Record<string, unknown> = {};
    if (normSelected !== normInitial) {
      payload.selectedMicrophoneId = normSelected;
    }
    if (parsedMaxRecord !== initialStt.maxRecordSeconds) {
      payload.maxRecordSeconds = parsedMaxRecord;
    }
    if (parsedTimeout !== initialStt.timeoutSeconds) {
      payload.timeoutSeconds = parsedTimeout;
    }
    if (clearApiKey) {
      payload.clearApiKey = true;
    } else if (apiKey.trim()) {
      payload.apiKey = apiKey.trim();
    }

    try {
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        setSaveError(errJson?.error?.message || 'Không thể lưu cài đặt.');
        return false;
      }

      const updated: PublicSettings = await res.json();
      const updatedRawMic = updated.selectedMicrophoneId || '';
      const updatedMic = updatedRawMic === 'default' ? '' : updatedRawMic;
      const updatedMax = updated.maxRecordSeconds ?? 120;
      const updatedTime = updated.timeoutSeconds ?? 60;
      const updatedHasKey = Boolean(updated.hasApiKey);

      setSelectedMicId(updatedMic);
      setMaxRecordSeconds(updatedMax);
      setTimeoutSeconds(updatedTime);
      setHasApiKey(updatedHasKey);
      setApiKey('');
      setClearApiKey(false);
      setSaveError('');

      setInitialStt({
        selectedMicrophoneId: updatedMic,
        maxRecordSeconds: updatedMax,
        timeoutSeconds: updatedTime,
        hasApiKey: updatedHasKey,
      });

      setSaveNotice('Đã lưu cài đặt.');
      onSettingsSaved?.();
      setTimeout(() => setSaveNotice(''), 3000);
      return true;
    } catch {
      setSaveError('Lỗi kết nối khi lưu cài đặt.');
      return false;
    }
  }, [
    isSttValid,
    selectedMicId,
    initialStt,
    parsedMaxRecord,
    parsedTimeout,
    clearApiKey,
    apiKey,
  ]);

  // Discard STT edits and revert to snapshot
  const handleDiscardStt = useCallback(() => {
    const normInitial =
      initialStt.selectedMicrophoneId === 'default'
        ? ''
        : initialStt.selectedMicrophoneId;
    setSelectedMicId(normInitial);
    setMaxRecordSeconds(initialStt.maxRecordSeconds);
    setTimeoutSeconds(initialStt.timeoutSeconds);
    setApiKey('');
    setClearApiKey(false);
  }, [initialStt]);

  // Navigation guard when leaving STT tab with dirty changes
  function navigateWithGuard(destinationAction: () => void) {
    if (activeTab === 'stt' && isSttDirty) {
      setPendingNavigation(() => destinationAction);
      setShowUnsavedModal(true);
    } else {
      destinationAction();
    }
  }

  // Handle Unsaved Confirmation Modal options:
  // 1. "Lưu"
  async function handleUnsavedModalSave() {
    if (!isSttValid) {
      setShowUnsavedModal(false);
      setPendingNavigation(null);
      return;
    }
    const success = await handleSaveStt();
    setShowUnsavedModal(false);
    if (success && pendingNavigation) {
      pendingNavigation();
    }
    setPendingNavigation(null);
  }

  // 2. "Không lưu"
  function handleUnsavedModalDiscard() {
    setShowUnsavedModal(false);
    handleDiscardStt();
    if (pendingNavigation) {
      pendingNavigation();
    }
    setPendingNavigation(null);
  }

  // 3. "Ở lại"
  function handleUnsavedModalStay() {
    setShowUnsavedModal(false);
    setPendingNavigation(null);
  }

  // Handle ESC key to dismiss modal or navigate back
  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        if (showUnsavedModal) {
          handleUnsavedModalStay();
        } else {
          navigateWithGuard(onClose);
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, showUnsavedModal, isSttDirty, onClose]);

  // History Tab: Search change resets selection (query debounced automatically)
  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setSearchQuery(val);
    setSelectedIds(new Set()); // Reset selections per spec
  }

  // History Tab: Filter change resets selection
  function handleFilterChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value;
    setFilterDays(val);
    setSelectedIds(new Set()); // Reset selections per spec
  }

  // History Tab: Toggle selection for one conversation
  function handleToggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  // History Tab: Select All / Deselect All
  const areAllSelected =
    historyConversations.length > 0 &&
    historyConversations.every((c) => selectedIds.has(c.id));

  function handleToggleSelectAll() {
    if (historyConversations.length === 0) return;
    if (areAllSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(historyConversations.map((c) => c.id)));
    }
  }

  // History Tab: Batch Delete
  async function handleBatchDelete() {
    if (selectedIds.size === 0 || isDeleting) return;

    setIsDeleting(true);
    setDeleteError('');
    const idsToDelete = Array.from(selectedIds);
    try {
      const res = await fetch('/api/conversations/batch-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: idsToDelete }),
      });

      if (res.ok) {
        setDeleteError('');
        // If active conversation was deleted, notify parent to switch to new blank chat & clear draft
        if (activeConversationId && selectedIds.has(activeConversationId)) {
          onActiveConversationDeleted?.();
        }

        setSelectedIds(new Set());
        await loadHistoryList(searchQuery, filterDays);
      } else {
        setDeleteError('Xóa hội thoại thất bại. Vui lòng thử lại.');
        setTimeout(() => setDeleteError(''), 4000);
      }
    } catch {
      setDeleteError('Xóa hội thoại thất bại. Lỗi kết nối mạng.');
      setTimeout(() => setDeleteError(''), 4000);
    } finally {
      setIsDeleting(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div
      className="absolute inset-0 z-50 flex flex-col bg-[#F5F7F9] select-none text-[#18212B]"
      data-testid="settings-view"
      role="dialog"
      aria-modal="true"
      aria-label="Cài đặt"
    >
      {/* Header bar: 64px height with Back button and centered title */}
      <header className="flex h-[64px] shrink-0 items-center justify-between border-b border-[#BAC5D0] bg-[#FFFFFF] px-4">
        <button
          type="button"
          onClick={() => navigateWithGuard(onClose)}
          data-testid="settings-back-button"
          aria-label="Quay lại"
          className="flex min-h-[44px] min-w-[44px] items-center justify-center gap-2 rounded-xl border border-[#BAC5D0] bg-[#FFFFFF] px-4 py-2 text-[18px] font-semibold text-[#273D53] transition-colors hover:bg-[#F5F7F9] focus-visible:outline-2 focus-visible:outline-[#273D53]"
        >
          <ArrowLeftIcon size={20} />
          Quay lại
        </button>

        <h1 className="text-[24px] font-bold text-[#18212B]">Cài đặt</h1>

        <div className="w-[88px]" aria-hidden="true" />
      </header>

      {/* Main Body: 2 columns on 1024x600 screen */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Navigation Sidebar */}
        <nav
          className="flex w-[260px] shrink-0 flex-col gap-2 border-r border-[#BAC5D0] bg-[#FFFFFF] p-4"
          aria-label="Nhóm cài đặt"
        >
          <button
            type="button"
            onClick={() => {
              if (activeTab !== 'stt') {
                setActiveTab('stt');
              }
            }}
            data-testid="settings-tab-stt"
            className={`flex min-h-[48px] w-full items-center rounded-xl px-4 py-3 text-left text-[18px] transition-colors focus-visible:outline-2 focus-visible:outline-[#273D53] ${
              activeTab === 'stt'
                ? 'bg-[#273D53] font-semibold text-white'
                : 'text-[#18212B] hover:bg-[#F5F7F9] font-medium'
            }`}
          >
            Giọng nói thành chữ (STT)
          </button>

          <button
            type="button"
            onClick={() => navigateWithGuard(() => setActiveTab('slr'))}
            data-testid="settings-tab-slr"
            className={`flex min-h-[48px] w-full items-center rounded-xl px-4 py-3 text-left text-[18px] transition-colors focus-visible:outline-2 focus-visible:outline-[#273D53] ${
              activeTab === 'slr'
                ? 'bg-[#273D53] font-semibold text-white'
                : 'text-[#18212B] hover:bg-[#F5F7F9] font-medium'
            }`}
          >
            Ngôn ngữ ký hiệu (SLR)
          </button>

          <button
            type="button"
            onClick={() => navigateWithGuard(() => setActiveTab('history'))}
            data-testid="settings-tab-history"
            className={`flex min-h-[48px] w-full items-center rounded-xl px-4 py-3 text-left text-[18px] transition-colors focus-visible:outline-2 focus-visible:outline-[#273D53] ${
              activeTab === 'history'
                ? 'bg-[#273D53] font-semibold text-white'
                : 'text-[#18212B] hover:bg-[#F5F7F9] font-medium'
            }`}
          >
            Lịch sử
          </button>
        </nav>

        {/* Right Content Panel */}
        <main className="flex flex-1 flex-col overflow-y-auto p-4 sm:p-6" data-testid="settings-content">
          {activeTab === 'stt' ? (
            /* Tab 1: Giọng nói thành chữ (STT) */
            <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 rounded-2xl border border-[#BAC5D0] bg-[#FFFFFF] p-6 shadow-sm">
              {/* Group: Thu âm */}
              <section className="flex flex-col gap-4 border-b border-[#BAC5D0] pb-5">
                <h2 className="text-[20px] font-bold text-[#273D53]">Thu âm</h2>

                {/* Microphone dropdown */}
                <div className="flex flex-col gap-1.5">
                  <label
                    htmlFor="mic-select"
                    className="text-[16px] font-semibold text-[#18212B]"
                  >
                    Nguồn micro
                  </label>
                  <select
                    id="mic-select"
                    value={selectedMicId === 'default' ? '' : selectedMicId}
                    onChange={(e) => {
                      setSelectedMicId(e.target.value);
                      setSaveError('');
                    }}
                    data-testid="settings-mic-select"
                    className="min-h-[44px] w-full rounded-xl border border-[#BAC5D0] bg-[#FFFFFF] px-3.5 py-2 text-[18px] text-[#18212B] focus:border-[#273D53] focus:outline-none"
                  >
                    <option value="">(Mặc định hệ điều hành)</option>
                    {selectedMicId &&
                      selectedMicId !== 'default' &&
                      !microphones.some((m) => m.id === selectedMicId) && (
                        <option key={selectedMicId} value={selectedMicId}>
                          {selectedMicId} (Đã ngắt kết nối)
                        </option>
                      )}
                    {microphones
                      .filter((m) => m.id && m.id !== 'default')
                      .map((mic) => (
                        <option key={mic.id} value={mic.id}>
                          {mic.name} {mic.isDefault ? '(Mặc định OS)' : ''}
                        </option>
                      ))}
                  </select>
                </div>

                {/* Max record duration */}
                <div className="flex flex-col gap-1.5">
                  <label
                    htmlFor="max-duration"
                    className="text-[16px] font-semibold text-[#18212B]"
                  >
                    Thời lượng thu tối đa (giây)
                  </label>
                  <input
                    id="max-duration"
                    type="number"
                    min={5}
                    max={300}
                    value={maxRecordSeconds}
                    onChange={(e) => {
                      setMaxRecordSeconds(e.target.value);
                      setSaveError('');
                    }}
                    data-testid="settings-max-duration"
                    className={`min-h-[44px] w-full rounded-xl border px-3.5 py-2 text-[18px] text-[#18212B] focus:outline-none ${
                      isMaxRecordValid
                        ? 'border-[#BAC5D0] focus:border-[#273D53]'
                        : 'border-[#DC2626] bg-red-50'
                    }`}
                  />
                  {!isMaxRecordValid && (
                    <p
                      className="text-[14px] font-medium text-[#DC2626]"
                      data-testid="max-duration-error"
                      role="alert"
                    >
                      Thời lượng thu tối đa phải là số nguyên từ 5 đến 300 giây.
                    </p>
                  )}
                </div>
              </section>

              {/* Group: Nhận dạng */}
              <section className="flex flex-col gap-4 border-b border-[#BAC5D0] pb-5">
                <h2 className="text-[20px] font-bold text-[#273D53]">Nhận dạng</h2>

                {/* Recognition timeout */}
                <div className="flex flex-col gap-1.5">
                  <label
                    htmlFor="timeout-seconds"
                    className="text-[16px] font-semibold text-[#18212B]"
                  >
                    Giới hạn chờ nhận dạng (giây)
                  </label>
                  <input
                    id="timeout-seconds"
                    type="number"
                    min={5}
                    max={300}
                    value={timeoutSeconds}
                    onChange={(e) => {
                      setTimeoutSeconds(e.target.value);
                      setSaveError('');
                    }}
                    data-testid="settings-timeout"
                    className={`min-h-[44px] w-full rounded-xl border px-3.5 py-2 text-[18px] text-[#18212B] focus:outline-none ${
                      isTimeoutValid
                        ? 'border-[#BAC5D0] focus:border-[#273D53]'
                        : 'border-[#DC2626] bg-red-50'
                    }`}
                  />
                  {!isTimeoutValid && (
                    <p
                      className="text-[14px] font-medium text-[#DC2626]"
                      data-testid="timeout-error"
                      role="alert"
                    >
                      Thời gian chờ phải là số nguyên từ 5 đến 300 giây.
                    </p>
                  )}
                </div>

                {/* Deepgram API Key */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <label
                      htmlFor="api-key"
                      className="text-[16px] font-semibold text-[#18212B]"
                    >
                      Deepgram API Key
                    </label>
                    {hasApiKey && !clearApiKey && (
                      <span className="text-[14px] font-medium text-emerald-600">
                        ✓ Đã lưu key tại máy
                      </span>
                    )}
                  </div>
                  <input
                    id="api-key"
                    type="password"
                    autoComplete="off"
                    value={apiKey}
                    onChange={(e) => {
                      setApiKey(e.target.value);
                      setSaveError('');
                      if (clearApiKey) setClearApiKey(false);
                    }}
                    placeholder={
                      clearApiKey
                        ? 'Key sẽ bị xóa khi lưu'
                        : hasApiKey
                        ? 'Đã có key · để trống để giữ nguyên'
                        : 'Nhập API key Deepgram…'
                    }
                    data-testid="settings-api-key"
                    className={`min-h-[44px] w-full rounded-xl border px-3.5 py-2 text-[18px] text-[#18212B] focus:outline-none ${
                      isApiKeyFormatValid
                        ? 'border-[#BAC5D0] bg-[#FFFFFF] focus:border-[#273D53]'
                        : 'border-[#DC2626] bg-red-50'
                    }`}
                  />
                  {!isApiKeyFormatValid && (
                    <p
                      className="text-[14px] font-medium text-[#DC2626]"
                      data-testid="api-key-error"
                      role="alert"
                    >
                      API key phải dài 16–512 ký tự, không chứa khoảng trắng hoặc ký tự điều khiển.
                    </p>
                  )}
                  {hasApiKey && !clearApiKey && (
                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={() => {
                          setClearApiKey(true);
                          setApiKey('');
                          setSaveError('');
                        }}
                        data-testid="settings-clear-key-button"
                        className="flex min-h-[44px] items-center gap-1.5 rounded-xl border border-[#DC2626] px-4 py-2 text-[16px] font-semibold text-[#DC2626] hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-[#DC2626]"
                      >
                        <TrashIcon size={18} />
                        Xóa key đã lưu
                      </button>
                    </div>
                  )}
                  {clearApiKey && (
                    <div className="flex items-center justify-between text-[14px] text-[#DC2626]">
                      <span>Key hiện tại sẽ bị xóa khi bấm &quot;Lưu cài đặt&quot;.</span>
                      <button
                        type="button"
                        onClick={() => setClearApiKey(false)}
                        className="font-medium underline hover:text-red-700"
                      >
                        Hủy xóa
                      </button>
                    </div>
                  )}
                </div>
              </section>

              {/* Action row: Save Notice / Save Error & Save Button */}
              <div className="flex items-center justify-between pt-2">
                <div className="flex items-center gap-2">
                  {saveNotice && (
                    <span
                      className="text-[16px] font-semibold text-emerald-600"
                      data-testid="save-notice"
                    >
                      {saveNotice}
                    </span>
                  )}
                  {saveError && (
                    <span
                      className="text-[14px] font-medium text-[#DC2626]"
                      data-testid="save-error"
                      role="alert"
                    >
                      {saveError}
                    </span>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => void handleSaveStt()}
                  disabled={!isSttDirty || !isSttValid}
                  data-testid="settings-save-button"
                  className={`flex min-h-[48px] items-center justify-center rounded-xl px-6 py-2.5 text-[18px] font-semibold transition-all ${
                    isSttDirty && isSttValid
                      ? 'cursor-pointer bg-[#273D53] text-white hover:bg-[#1E2F40] shadow-sm'
                      : 'cursor-not-allowed bg-[#BAC5D0] text-white opacity-60'
                  }`}
                >
                  Lưu cài đặt
                </button>
              </div>
            </div>
          ) : activeTab === 'slr' ? (
            /* Tab 2: Ngôn ngữ ký hiệu (SLR) */
            <div className="mx-auto flex w-full max-w-2xl flex-col gap-5 rounded-2xl border border-[#BAC5D0] bg-[#FFFFFF] p-6 shadow-sm">
              <h2 className="text-[20px] font-bold text-[#273D53]">
                Nhận dạng ký hiệu &amp; Phát loa
              </h2>

              <label className="flex items-start justify-between gap-4 rounded-xl border border-[#BAC5D0] bg-[#F5F7F9] p-4 cursor-pointer">
                <div>
                  <div className="text-[17px] font-bold text-[#18212B]">
                    Tự động đọc loa
                  </div>
                  <div className="text-[14px] text-[#4F5D6B]">
                    Tự phát MP3 khi nhận được ký hiệu rõ ràng (bỏ qua từ chưa rõ).
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={slrSettings.autoSpeak}
                  data-testid="slr-setting-autospeak"
                  onChange={(e) =>
                    onSlrSettingsChange?.({
                      ...slrSettings,
                      autoSpeak: e.target.checked,
                    })
                  }
                  className="mt-1 h-5 w-5 accent-[#273D53] cursor-pointer"
                />
              </label>

              <label className="flex items-start justify-between gap-4 rounded-xl border border-[#BAC5D0] bg-[#F5F7F9] p-4 cursor-pointer">
                <div>
                  <div className="text-[17px] font-bold text-[#18212B]">
                    Tự động lưu câu vào hội thoại khi nghỉ 4 giây (Phương án A)
                  </div>
                  <div className="text-[14px] text-[#4F5D6B]">
                    Gom toàn bộ các từ ký trong cùng 1 câu và tự gửi thành 1 tin nhắn vào hội thoại khi buông 2 tay nghỉ 4 giây.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={slrSettings.autoSaveOnRest}
                  data-testid="slr-setting-autosave"
                  onChange={(e) =>
                    onSlrSettingsChange?.({
                      ...slrSettings,
                      autoSaveOnRest: e.target.checked,
                    })
                  }
                  className="mt-1 h-5 w-5 accent-[#273D53] cursor-pointer"
                />
              </label>

              <label className="flex items-start justify-between gap-4 rounded-xl border border-[#BAC5D0] bg-[#F5F7F9] p-4 cursor-pointer">
                <div>
                  <div className="text-[17px] font-bold text-[#18212B]">
                    Hiển thị thông số chẩn đoán (Dev)
                  </div>
                  <div className="text-[14px] text-[#4F5D6B]">
                    Mặc định TẮT. Chỉ bật khi cần đo FPS, hàng đợi và độ trễ xử lý trên camera.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={slrSettings.showDiagnostics}
                  data-testid="slr-setting-diagnostics"
                  onChange={(e) =>
                    onSlrSettingsChange?.({
                      ...slrSettings,
                      showDiagnostics: e.target.checked,
                    })
                  }
                  className="mt-1 h-5 w-5 accent-[#273D53] cursor-pointer"
                />
              </label>

              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="slr-base-url"
                  className="text-[16px] font-semibold text-[#18212B]"
                >
                  Địa chỉ máy chủ SLR
                </label>
                <div className="flex min-h-[44px] w-full items-stretch overflow-hidden rounded-xl border border-[#BAC5D0] bg-[#FFFFFF] focus-within:border-[#273D53]">
                  <span
                    aria-hidden="true"
                    className="flex items-center border-r border-[#BAC5D0] bg-[#F5F7F9] px-3 font-mono text-[16px] font-semibold text-[#4F5D6B] select-none"
                  >
                    http://
                  </span>
                  <input
                    id="slr-base-url"
                    type="text"
                    inputMode="url"
                    autoCapitalize="off"
                    autoCorrect="off"
                    spellCheck={false}
                    value={stripSlrUrlScheme(slrSettings.slrBaseUrl)}
                    placeholder="172.16.59.16:8765 (để trống = tự nhận)"
                    data-testid="slr-setting-baseurl"
                    onChange={(e) =>
                      onSlrSettingsChange?.({
                        ...slrSettings,
                        slrBaseUrl: normalizeSlrBaseUrl(e.target.value),
                      })
                    }
                    className="min-w-0 flex-1 bg-[#FFFFFF] px-3.5 py-2 font-mono text-[16px] text-[#18212B] focus:outline-none"
                  />
                </div>
                <p className="text-[13px] text-[#4F5D6B]">
                  Chỉ cần nhập IP:cổng (ví dụ 172.16.59.16:8765), hệ thống tự gắn http://.
                </p>
              </div>

              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="slr-camera-index"
                  className="text-[16px] font-semibold text-[#18212B]"
                >
                  Chỉ số camera USB
                </label>
                <input
                  id="slr-camera-index"
                  type="number"
                  min={0}
                  max={16}
                  value={slrSettings.cameraIndex}
                  data-testid="slr-setting-camera"
                  onChange={(e) => {
                    const num = Number(e.target.value);
                    onSlrSettingsChange?.({
                      ...slrSettings,
                      cameraIndex:
                        Number.isInteger(num) && num >= 0 && num <= 16 ? num : 0,
                    });
                  }}
                  className="min-h-[44px] w-full rounded-xl border border-[#BAC5D0] bg-[#FFFFFF] px-3.5 py-2 text-[18px] text-[#18212B] focus:border-[#273D53] focus:outline-none"
                />
              </div>
            </div>
          ) : (
            /* Tab 3: Lịch sử */
            <div className="mx-auto flex h-full max-h-[calc(100vh-112px)] w-full max-w-4xl flex-col rounded-2xl border border-[#BAC5D0] bg-[#FFFFFF] p-5 shadow-sm overflow-hidden">
              {/* Top Controls: Search box | Date filter | Select all */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#BAC5D0] pb-4">
                {/* Search input */}
                <div className="relative flex flex-1 min-w-[200px] max-w-xs items-center">
                  <SearchIcon
                    size={20}
                    className="absolute left-3 text-[#4F5D6B] pointer-events-none"
                  />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={handleSearchChange}
                    placeholder="Tìm theo tên…"
                    data-testid="history-search-input"
                    className="min-h-[44px] w-full rounded-xl border border-[#BAC5D0] bg-[#FFFFFF] pl-10 pr-3.5 py-2 text-[18px] text-[#18212B] placeholder:text-[#4F5D6B] focus:border-[#273D53] focus:outline-none"
                  />
                </div>

                {/* Filter dropdown */}
                <div className="flex items-center gap-2">
                  <select
                    value={filterDays}
                    onChange={handleFilterChange}
                    data-testid="history-filter-select"
                    aria-label="Lọc theo thời gian"
                    className="min-h-[44px] rounded-xl border border-[#BAC5D0] bg-[#FFFFFF] px-3.5 py-2 text-[18px] text-[#18212B] focus:border-[#273D53] focus:outline-none"
                  >
                    <option value="">Tất cả thời gian</option>
                    <option value="7">Cũ hơn 7 ngày</option>
                    <option value="30">Cũ hơn 30 ngày</option>
                  </select>

                  {/* Select All Toggle Button */}
                  <button
                    type="button"
                    onClick={handleToggleSelectAll}
                    disabled={historyConversations.length === 0}
                    data-testid="history-select-all-button"
                    className={`flex min-h-[44px] items-center justify-center rounded-xl px-4 py-2 text-[18px] font-semibold transition-colors ${
                      historyConversations.length === 0
                        ? 'cursor-not-allowed bg-[#BAC5D0] text-white opacity-60'
                        : 'border border-[#BAC5D0] bg-[#FFFFFF] text-[#273D53] hover:bg-[#F5F7F9]'
                    }`}
                  >
                    {historyConversations.length === 0
                      ? 'Chọn 0 kết quả'
                      : areAllSelected
                      ? 'Bỏ chọn tất cả'
                      : `Chọn ${historyConversations.length} kết quả`}
                  </button>
                </div>
              </div>

              {/* Scrollable Conversation List */}
              <div
                className="flex-1 overflow-y-auto my-3 rounded-xl border border-[#BAC5D0] divide-y divide-[#BAC5D0]/40"
                data-testid="history-management-list"
              >
                {historyConversations.length === 0 ? (
                  <div
                    className="flex h-48 flex-col items-center justify-center p-6 text-center text-[18px] text-[#4F5D6B]"
                    data-testid={
                      totalConversationsCount === 0
                        ? 'zero-conversations'
                        : 'zero-matches'
                    }
                  >
                    {totalConversationsCount === 0 ? (
                      <p>Chưa có hội thoại đã lưu.</p>
                    ) : (
                      <p>Không có hội thoại khớp điều kiện.</p>
                    )}
                  </div>
                ) : (
                  historyConversations.map((conv) => {
                    const isChecked = selectedIds.has(conv.id);
                    return (
                      <div
                        key={conv.id}
                        onClick={() => handleToggleSelect(conv.id)}
                        data-testid={`delete-item-${conv.id}`}
                        className={`flex min-h-[52px] cursor-pointer items-center gap-3.5 px-4 py-3 transition-colors ${
                          isChecked ? 'bg-[#EBF1F6]' : 'hover:bg-[#F5F7F9]'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => handleToggleSelect(conv.id)}
                          onClick={(e) => e.stopPropagation()}
                          data-testid={`checkbox-${conv.id}`}
                          aria-label={`Chọn xóa ${conv.title}`}
                          className="h-5 w-5 rounded border-[#BAC5D0] text-[#273D53] focus:ring-0 cursor-pointer"
                        />
                        <span className="flex-1 truncate text-[18px] font-medium text-[#18212B]">
                          {conv.title}
                        </span>
                        <span className="shrink-0 text-[14px] text-[#4F5D6B]">
                          {formatHistoryDate(conv.updatedAt)}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Bottom Bar: Delete Button */}
              <div className="flex shrink-0 items-center justify-between border-t border-[#BAC5D0] pt-3">
                <div className="flex items-center gap-3">
                  <span className="text-[16px] text-[#4F5D6B]">
                    Đã chọn: {selectedIds.size} hội thoại
                  </span>
                  {deleteError && (
                    <span
                      className="text-[14px] font-semibold text-[#DC2626]"
                      data-testid="delete-error"
                      role="alert"
                    >
                      {deleteError}
                    </span>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => void handleBatchDelete()}
                  disabled={selectedIds.size === 0 || isDeleting}
                  data-testid="batch-delete-button"
                  className={`flex min-h-[48px] items-center justify-center rounded-xl px-6 py-2.5 text-[18px] font-semibold transition-all ${
                    selectedIds.size > 0 && !isDeleting
                      ? 'cursor-pointer bg-[#DC2626] text-white hover:bg-[#B91C1C] shadow-sm'
                      : 'cursor-not-allowed bg-[#BAC5D0] text-white opacity-60'
                  }`}
                >
                  {isDeleting
                    ? 'Đang xóa…'
                    : selectedIds.size === 0
                    ? 'Xóa 0 hội thoại'
                    : `Xóa ${selectedIds.size} hội thoại`}
                </button>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Confirmation Modal for Unsaved Changes */}
      {showUnsavedModal && (
        <div
          className="absolute inset-0 z-60 flex items-center justify-center bg-black/50 p-4 select-none"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="unsaved-modal-title"
          data-testid="unsaved-modal"
        >
          <div className="flex w-full max-w-md flex-col gap-5 rounded-2xl border border-[#BAC5D0] bg-[#FFFFFF] p-6 shadow-2xl animate-in zoom-in-95 duration-150">
            <h2
              id="unsaved-modal-title"
              className="text-[20px] font-bold text-[#18212B]"
            >
              Bạn có muốn lưu thay đổi?
            </h2>
            <p className="text-[16px] text-[#4F5D6B]">
              Có thay đổi chưa lưu trong mục Giọng nói thành chữ.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={handleUnsavedModalStay}
                data-testid="unsaved-stay"
                className="flex min-h-[44px] items-center justify-center rounded-xl border border-[#BAC5D0] bg-[#FFFFFF] px-4 py-2 text-[18px] font-semibold text-[#18212B] hover:bg-[#F5F7F9] focus-visible:outline-2 focus-visible:outline-[#273D53]"
              >
                Ở lại
              </button>

              <button
                type="button"
                onClick={handleUnsavedModalDiscard}
                data-testid="unsaved-discard"
                className="flex min-h-[44px] items-center justify-center rounded-xl border border-[#DC2626] bg-[#FFFFFF] px-4 py-2 text-[18px] font-semibold text-[#DC2626] hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-[#DC2626]"
              >
                Không lưu
              </button>

              <button
                type="button"
                onClick={() => void handleUnsavedModalSave()}
                data-testid="unsaved-save"
                className="flex min-h-[44px] items-center justify-center rounded-xl bg-[#273D53] px-5 py-2 text-[18px] font-semibold text-white hover:bg-[#1E2F40] shadow-sm focus-visible:outline-2 focus-visible:outline-[#273D53]"
              >
                Lưu
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
