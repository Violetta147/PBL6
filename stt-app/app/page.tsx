'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import type { Conversation, Message, MessageSource, SignGloss, SignSentence } from '../src/contracts';
import { Header } from '../src/components/Header';
import { ConversationArea } from '../src/components/ConversationArea';
import { Composer } from '../src/components/Composer';
import { HistoryDrawer } from '../src/components/HistoryDrawer';
import { SettingsView } from '../src/components/SettingsView';
import { SlrDock } from '../src/components/SlrDock';
import { toLiveGlossItem, type LiveGlossItem } from '../src/components/LiveSigningCard';
import {
  loadSlrSettings,
  saveSlrSettings,
  resolveSlrBaseUrl,
  toWsUrl,
  DEFAULT_SLR_SETTINGS,
  type SlrSettings,
} from '../src/lib/slrSettings';
import {
  pickSlrCandidate,
  startSlrSession,
  stopSlrSession,
  type SegmenterState,
  type SlrTopCandidate,
  type SlrWsEvent,
} from '../src/lib/slrClient';
import { SentenceSigningCard } from '../src/components/SentenceSigningCard';
import { speakSentence } from '../src/lib/slrTts';

type KeyboardBridge = {
  onScreenKeyboardChange?: (listener: (visible: boolean) => void) => () => void;
};

export default function Home() {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState<string>('');
  const [cancelSignal, setCancelSignal] = useState<number>(0);
  const [recordingStatus, setRecordingStatus] = useState<
    'idle' | 'recording' | 'transcribing'
  >('idle');
  const [selectedMicrophoneId, setSelectedMicrophoneId] = useState<string | undefined>(undefined);
  const [maxRecordSeconds, setMaxRecordSeconds] = useState<number>(120);

  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [keyboardCeiling, setKeyboardCeiling] = useState<number>();
  const [isOskOpen, setIsOskOpen] = useState<boolean>(false);
  const lastOskReqRef = useRef<{ visible: boolean; at: number } | null>(null);
  const baseViewportHeightRef = useRef<number>(0);

  // SLR Live + Unified Conversation State
  const [hasMounted, setHasMounted] = useState<boolean>(false);
  const [slrSettings, setSlrSettings] = useState<SlrSettings>(DEFAULT_SLR_SETTINGS);
  const [slrWsConnected, setSlrWsConnected] = useState<boolean>(false);
  const [slrRunning, setSlrRunning] = useState<boolean>(false);
  const [slrDraining, setSlrDraining] = useState<boolean>(false);
  const [slrBusy, setSlrBusy] = useState<boolean>(false);
  const [segmenterState, setSegmenterState] = useState<SegmenterState>('UNKNOWN');
  const [slrArms, setSlrArms] = useState<(string | null)[]>([null, null]);
  const [captureFps, setCaptureFps] = useState<number>(0);
  const [queueDepth, setQueueDepth] = useState<number>(0);
  const [liveGlosses, setLiveGlosses] = useState<LiveGlossItem[]>([]);
  const [lastTiming, setLastTiming] = useState<{
    preprocessing_seconds?: number;
    inference_seconds?: number;
  } | null>(null);
  const [ttsStatus, setTtsStatus] = useState<string>('');
  const [slrError, setSlrError] = useState<string | null>(null);

  const conversationRef = useRef<Conversation | null>(null);
  conversationRef.current = conversation;
  const slrSettingsRef = useRef<SlrSettings>(slrSettings);
  slrSettingsRef.current = slrSettings;
  const liveGlossesRef = useRef<LiveGlossItem[]>(liveGlosses);
  liveGlossesRef.current = liveGlosses;

  const seenSegmentIdsRef = useRef<Set<string>>(new Set());
  const savedSegmentIdsRef = useRef<Set<string>>(new Set());
  const activeSessionKeyRef = useRef<string | null>(null);
  const activeSessionIdRef = useRef<string | null>(null);
  const [closedUtteranceIds, setClosedUtteranceIds] = useState<string[]>([]);
  const [autoReadyIds, setAutoReadyIds] = useState<string[]>([]);
  const [sentenceEditing, setSentenceEditing] = useState(false);
  const closedRef = useRef<string[]>([]); closedRef.current = closedUtteranceIds;

  useEffect(() => {
    setHasMounted(true);
    setSlrSettings(loadSlrSettings());
    try {
      const saved = JSON.parse(localStorage.getItem('pbl6.sign.pending.v1') || 'null');
      if (saved && Array.isArray(saved.items) && Array.isArray(saved.savedIds)) {
        setLiveGlosses(saved.items);
        savedSegmentIdsRef.current = new Set(saved.savedIds);
        activeSessionIdRef.current = saved.sessionId || null;
        setClosedUtteranceIds(saved.closedIds || []);
        if (saved.conversationId) void fetch(`/api/conversations/${encodeURIComponent(saved.conversationId)}`)
          .then(r => r.ok ? r.json() : null).then(data => { if (data) { setConversation(data.conversation); setMessages(data.messages); } }).catch(() => {});
      }
    } catch { /* Keep a fresh session when an old browser cache is invalid. */ }
  }, []);

  useEffect(() => {
    if (!hasMounted) return;
    try {
      localStorage.setItem('pbl6.sign.pending.v1', JSON.stringify({
        items: liveGlosses, savedIds: [...savedSegmentIdsRef.current],
        sessionId: activeSessionIdRef.current, closedIds: closedUtteranceIds,
        conversationId: conversation?.id || null,
      }));
    } catch { setSlrError('Không lưu được bản nháp trên trình duyệt. Hãy giữ trang mở cho đến khi gửi xong.'); }
  }, [hasMounted, liveGlosses, closedUtteranceIds, conversation?.id]);

  const slrBaseUrl = useMemo(
    () =>
      hasMounted
        ? resolveSlrBaseUrl(slrSettings.slrBaseUrl)
        : 'http://127.0.0.1:8765',
    [hasMounted, slrSettings.slrBaseUrl]
  );
  const slrBaseUrlRef = useRef<string>(slrBaseUrl);
  slrBaseUrlRef.current = slrBaseUrl;

  useEffect(() => {
    const bridge = (window as Window & { electronAPI?: KeyboardBridge }).electronAPI;
    return bridge?.onScreenKeyboardChange?.((visible) => {
      // The NH2067 keyboard covers the lower part of the screen even when
      // Wayland does not resize the Electron surface. Leave room above it.
      setKeyboardCeiling(visible ? Math.floor(window.screen.height * 0.58) : undefined);
    });
  }, []);

  useEffect(() => {
    if (isOskOpen || typeof window === 'undefined') return;
    const updateBaseHeight = () => {
      if (window.innerHeight > 0) {
        baseViewportHeightRef.current = window.innerHeight;
      }
    };
    updateBaseHeight();
    window.addEventListener('resize', updateBaseHeight);
    return () => window.removeEventListener('resize', updateBaseHeight);
  }, [isOskOpen]);

  const computeOskCeiling = useCallback((visible: boolean): number | undefined => {
    if (!visible || typeof window === 'undefined') return undefined;
    const vh = window.innerHeight || 564;
    const baseVh = baseViewportHeightRef.current;
    // When labwc resizes the maximized Firefox viewport for Squeekboard's exclusive zone
    // (landscape ~564 -> ~354, portrait ~988 -> ~680), let h-dvh fill 100% with 0px gap.
    if (vh <= 420 || (baseVh > 0 && baseVh - vh >= 120)) return undefined;
    return Math.max(336, vh - 210);
  }, []);

  useEffect(() => {
    if (!isOskOpen) return;
    const handleResize = () => {
      setKeyboardCeiling(computeOskCeiling(true));
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isOskOpen, computeOskCeiling]);

  const requestOskVisible = useCallback(async (visible: boolean) => {
    const now = Date.now();
    const prev = lastOskReqRef.current;
    if (prev && prev.visible === visible && now - prev.at < 80) {
      return;
    }
    lastOskReqRef.current = { visible, at: now };

    setIsOskOpen(visible);
    setKeyboardCeiling(computeOskCeiling(visible));
    try {
      const res = await fetch('/api/osk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ visible }),
      });
      if (res.ok) {
        const data = (await res.json()) as { visible?: boolean; supported?: boolean };
        if (data && data.supported === false) {
          setKeyboardCeiling(undefined);
        }
      }
    } catch {
      // Best-effort OSK trigger
    }
  }, [computeOskCeiling]);

  const handleToggleOsk = useCallback(() => {
    void requestOskVisible(!isOskOpen);
  }, [isOskOpen, requestOskVisible]);

  const refreshSettings = useCallback(() => {
    fetch('/api/settings', { cache: 'no-store' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (typeof data?.selectedMicrophoneId === 'string') {
          setSelectedMicrophoneId(data.selectedMicrophoneId);
        } else {
          setSelectedMicrophoneId(undefined);
        }
        if (typeof data?.maxRecordSeconds === 'number') {
          setMaxRecordSeconds(data.maxRecordSeconds);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshSettings();
  }, [refreshSettings]);

  // Send message handler (First message creates conversation; subsequent appends)
  const handleSendMessage = useCallback(async (
    text: string,
    sources: MessageSource[],
    signGlosses?: SignGloss[],
    signSentence?: SignSentence
  ): Promise<boolean> => {
    try {
      const currentConv = conversationRef.current;
      if (!currentConv) {
        // First message of conversation
        const response = await fetch('/api/conversations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, sources, signGlosses, signSentence }),
        });

        if (!response.ok) {
          return false;
        }

        const data: { conversation: Conversation; message: Message } =
          await response.json();
        conversationRef.current = data.conversation;
        setConversation(data.conversation);
        setMessages([data.message]);
        return true;
      } else {
        // Subsequent message in existing conversation
        const response = await fetch(
          `/api/conversations/${encodeURIComponent(currentConv.id)}/messages`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, sources, signGlosses, signSentence }),
          }
        );

        if (!response.ok) {
          return false;
        }

        const newMessage: Message = await response.json();
        setMessages((prev) => [...prev, newMessage]);
        return true;
      }
    } catch {
      return false;
    }
  }, []);

  const mergeGlosses = useCallback((records: LiveGlossItem[]) => {
    setLiveGlosses(prev => {
      const merged = [...prev];
      for (const item of records) {
        if (savedSegmentIdsRef.current.has(item.segmentId)) continue;
        const i = merged.findIndex(g => g.segmentId === item.segmentId);
        if (i < 0) merged.push(item);
        else if (merged[i].status !== 'confirmed' || item.status === 'confirmed') merged[i] = item;
      }
      return merged;
    });
  }, []);

  useEffect(() => {
    if (!hasMounted) return;
    let disposed = false;
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    const markClosed = (utterances: { utterance_id: string; reason: string }[]) => {
      setClosedUtteranceIds(prev => [...new Set([...prev, ...utterances.map(u => u.utterance_id)])]);
      setAutoReadyIds(prev => [...new Set([...prev, ...utterances.filter(u => u.reason === 'utterance_rest').map(u => u.utterance_id)])]);
    };
    const connect = () => {
      if (disposed) return;
      try { ws = new WebSocket(`${toWsUrl(slrBaseUrl)}/ws/live`); }
      catch { scheduleReconnect(); return; }
      ws.onopen = () => { setSlrWsConnected(true); setSlrError(null); };
      ws.onclose = () => { setSlrWsConnected(false); scheduleReconnect(); };
      ws.onerror = () => {};
      ws.onmessage = event => {
        let msg: SlrWsEvent;
        try { msg = JSON.parse(String(event.data)); } catch { return; }
        if (msg.type === 'snapshot') {
          const snap = msg.snapshot;
          if (activeSessionIdRef.current && snap.session_id && snap.session_id !== activeSessionIdRef.current && liveGlossesRef.current.length) {
            setSlrError('Máy nhận dạng đã mở phiên khác. Bản nháp cũ vẫn được giữ, hãy xử lý trước khi bắt đầu lại.'); return;
          }
          activeSessionIdRef.current = snap.session_id || activeSessionIdRef.current;
          activeSessionKeyRef.current = snap.session_id ? `${snap.session_id}:${snap.epoch}` : null;
          setSlrRunning(Boolean(snap.running)); setSlrDraining(Boolean(snap.draining));
          setSlrError(snap.last_error ?? null);
          setSegmenterState(snap.segmenter_state ?? 'UNKNOWN'); setSlrArms(snap.arms ?? [null, null]); setCaptureFps(snap.capture_fps ?? 0); setQueueDepth(snap.queue_depth ?? 0);
          for (const g of snap.glosses ?? []) seenSegmentIdsRef.current.add(g.segment_id);
          mergeGlosses((snap.glosses ?? []).map(toLiveGlossItem)); markClosed(snap.utterances ?? []);
        } else if (msg.type === 'session_started') {
          activeSessionIdRef.current = msg.session_id ?? null;
          seenSegmentIdsRef.current.clear(); savedSegmentIdsRef.current.clear();
          setClosedUtteranceIds([]); setAutoReadyIds([]); setTtsStatus(''); setSlrError(null);
          setSlrRunning(true); setSlrDraining(false); setSegmenterState('UNKNOWN'); setSlrArms([null, null]);
        } else if (msg.type === 'status') {
          setSlrError((prev) => (prev && prev.includes('Vision Backend') ? null : prev));
          setSegmenterState(msg.segmenter_state ?? 'UNKNOWN'); setSlrArms(msg.arms ?? [null, null]); setQueueDepth(msg.queue_depth ?? 0); setCaptureFps(msg.capture_fps ?? 0);
        } else if (msg.type === 'gloss_result') {
          if (seenSegmentIdsRef.current.has(msg.gloss.segment_id)) return;
          seenSegmentIdsRef.current.add(msg.gloss.segment_id); setLastTiming(msg.gloss.timing ?? null);
          mergeGlosses([toLiveGlossItem(msg.gloss)]);
        } else if (msg.type === 'gloss_corrected') {
          if (msg.session_id === activeSessionIdRef.current) mergeGlosses([toLiveGlossItem(msg.gloss)]);
        } else if (msg.type === 'utterance_ready') {
          mergeGlosses((msg.utterance.segments ?? []).map(toLiveGlossItem)); markClosed([msg.utterance]);
        } else if (msg.type === 'session_stopped') {
          setSlrRunning(Boolean(msg.snapshot?.running)); setSlrDraining(Boolean(msg.snapshot?.draining));
          mergeGlosses((msg.snapshot?.glosses ?? []).map(toLiveGlossItem)); markClosed(msg.snapshot?.utterances ?? []);
        } else if (msg.type === 'error') setSlrError(msg.message || 'Lỗi từ máy chủ nhận dạng SLR.');
        else if (msg.type === 'error_cleared') setSlrError(null);
      };
    };
    const scheduleReconnect = () => { if (!disposed && reconnectTimer === null) reconnectTimer = setTimeout(() => { reconnectTimer = null; connect(); }, 2000); };
    connect();
    return () => { disposed = true; if (reconnectTimer) clearTimeout(reconnectTimer); ws?.close(); };
  }, [hasMounted, slrBaseUrl, mergeGlosses]);

  const handleSlrSettingsChange = useCallback((next: SlrSettings) => {
    const saved = saveSlrSettings(next);
    setSlrSettings(saved);
  }, []);

  const handleToggleSigning = useCallback(async () => {
    if (slrBusy) return;
    setSlrBusy(true);
    setSlrError(null);
    try {
      if (slrRunning || slrDraining) {
        const snap = await stopSlrSession(slrBaseUrl);
        setSlrRunning(Boolean(snap.running));
        setSlrDraining(Boolean(snap.draining));
      } else {
        if (liveGlossesRef.current.length) {
          setSlrError('Hãy gửi hoặc bỏ bản nháp trước khi bắt đầu phiên ký mới.');
          return;
        }
        void requestOskVisible(false);
        seenSegmentIdsRef.current.clear();
        savedSegmentIdsRef.current.clear();
        setLiveGlosses([]);
        setTtsStatus('');
        const snap = await startSlrSession(slrBaseUrl, slrSettings.cameraIndex);
        activeSessionIdRef.current = snap.session_id;
        setSlrRunning(Boolean(snap.running));
        setSlrDraining(Boolean(snap.draining));
        setSegmenterState(snap.segmenter_state ?? 'UNKNOWN');
      }
    } catch (error) {
      const msg =
        error instanceof Error
          ? error.message
          : `Không kết nối được máy chủ SLR (${slrBaseUrl}).`;
      setSlrError(msg);
    } finally {
      setSlrBusy(false);
    }
  }, [slrBusy, slrRunning, slrDraining, slrBaseUrl, slrSettings.cameraIndex, requestOskVisible]);

  const handlePickSlrCandidate = useCallback(
    async (segmentId: string, candidate: SlrTopCandidate) => {
      const sessionId = activeSessionIdRef.current;
      if (!sessionId) return;
      setSlrError(null);
      try {
        const gloss = await pickSlrCandidate(
          slrBaseUrlRef.current, sessionId, segmentId, candidate.label_id,
          true
        );
        if (activeSessionIdRef.current === sessionId) {
          setLiveGlosses((prev) => prev.map((g) => g.segmentId === segmentId ? toLiveGlossItem(gloss) : g));
        }
      } catch (error) {
        if (activeSessionIdRef.current === sessionId) {
          setSlrError(error instanceof Error ? error.message : 'Không xác nhận được từ này.');
        }
      }
    },
    []
  );

  const handleDropSlrGloss = useCallback((segmentId: string) => {
    savedSegmentIdsRef.current.add(segmentId);
    setLiveGlosses((prev) => prev.filter((g) => g.segmentId !== segmentId));
  }, []);

  const handleFinishSentence = useCallback(async (utteranceId: string) => {
    if (closedRef.current.includes(utteranceId)) return;
    const response = await fetch(`${slrBaseUrlRef.current}/api/session/utterance/finish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: activeSessionIdRef.current, utterance_id: utteranceId }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Chưa hoàn tất lượt ký. Hãy chờ và thử lại.');
    mergeGlosses((data.state?.glosses ?? []).map(toLiveGlossItem));
    setClosedUtteranceIds(prev => [...new Set([...prev, utteranceId])]);
  }, [mergeGlosses]);

  const handleDiscardSentence = useCallback((ids: string[]) => {
    for (const id of ids) savedSegmentIdsRef.current.add(id);
    const removed = new Set(ids);
    setLiveGlosses(prev => prev.filter(g => !removed.has(g.segmentId)));
  }, []);

  const handleSendSentence = useCallback(async (text: string, items: SignGloss[], metadata: SignSentence) => {
    const ok = await handleSendMessage(text, ['sign'], items, metadata);
    if (!ok) return false;
    handleDiscardSentence(items.map(g => g.segmentId));
    if (slrSettingsRef.current.autoSpeak) speakSentence(text, setTtsStatus);
    return true;
  }, [handleSendMessage, handleDiscardSentence]);

  // History Drawer openers / actions
  function handleOpenHistory() {
    // Opening drawer does NOT interrupt in-flight recording or transcribing
    void requestOskVisible(false);
    setIsHistoryOpen(true);
  }

  function handleCloseHistory() {
    setIsHistoryOpen(false);
  }

  async function handleSelectConversation(id: string) {
    if (liveGlossesRef.current.length && id !== conversationRef.current?.id) {
      setSlrError('Hãy gửi hoặc bỏ bản nháp trước khi đổi hội thoại.'); setIsHistoryOpen(false); return;
    }
    if (conversation && conversation.id === id) {
      // Tapping the active conversation closes drawer without discarding draft or cancelling recording
      setIsHistoryOpen(false);
      return;
    }
    setCancelSignal((prev) => prev + 1);
    setDraft('');
    try {
      const res = await fetch(`/api/conversations/${encodeURIComponent(id)}`);
      if (res.ok) {
        const data: { conversation: Conversation; messages: Message[] } =
          await res.json();
        setConversation(data.conversation);
        setMessages(data.messages);
      }
    } catch {
      // Ignore fetch error
    } finally {
      setIsHistoryOpen(false);
    }
  }

  function handleNewConversation() {
    if (liveGlossesRef.current.length) {
      setSlrError('Hãy gửi hoặc bỏ bản nháp trước khi tạo hội thoại mới.'); setIsHistoryOpen(false); return;
    }
    if (
      !conversation &&
      messages.length === 0 &&
      draft === '' &&
      recordingStatus === 'idle'
    ) {
      // Screen is already blank and idle: simply closes drawer per spec
      setIsHistoryOpen(false);
      return;
    }
    // Cancel in-flight recording, clear draft and start fresh blank conversation
    setCancelSignal((prev) => prev + 1);
    setDraft('');
    setConversation(null);
    setMessages([]);
    setIsHistoryOpen(false);
  }

  // Settings View openers / actions
  function handleOpenSettings() {
    // Cancels in-flight recording or transcribing, but preserves draft
    void requestOskVisible(false);
    setCancelSignal((prev) => prev + 1);
    setIsSettingsOpen(true);
  }

  function handleCloseSettings() {
    void requestOskVisible(false);
    setIsSettingsOpen(false);
    refreshSettings();
  }

  function handleActiveConversationDeleted() {
    setConversation(null);
    setMessages([]);
    setDraft('');
  }

  const showSlrDock = slrRunning || slrDraining;
  const showLiveCard = showSlrDock || liveGlosses.length > 0;

  return (
    <main
      className="relative flex h-dvh w-full flex-col overflow-hidden bg-[#F5F7F9] text-[#18212B]"
      style={{ maxHeight: keyboardCeiling }}
      onPointerDownCapture={(e) => {
        if (!isOskOpen) return;
        const target = e.target as HTMLElement | null;
        if (!target) return;
        if (
          target.closest('textarea, input, select, [data-testid="osk-button"], [data-testid="send-button"], [data-testid="live-signing-card"]')
        ) {
          return;
        }
        if (
          typeof document !== 'undefined' &&
          document.activeElement instanceof HTMLElement &&
          (document.activeElement.tagName === 'TEXTAREA' || document.activeElement.tagName === 'INPUT')
        ) {
          document.activeElement.blur();
        }
        void requestOskVisible(false);
      }}
      onFocusCapture={(e) => {
        const target = e.target as HTMLElement | null;
        if (!target) return;
        if (target.tagName === 'TEXTAREA') {
          void requestOskVisible(true);
        } else if (
          target.tagName === 'INPUT' &&
          !['checkbox', 'radio', 'button', 'submit', 'range'].includes(
            (target as HTMLInputElement).type
          )
        ) {
          void requestOskVisible(true);
        }
      }}
    >
      {/* Top Header */}
      <Header
        onOpenHistory={handleOpenHistory}
        onOpenSettings={handleOpenSettings}
        isSigning={showSlrDock}
        isSigningBusy={slrBusy}
        onToggleSigning={() => void handleToggleSigning()}
      />

      {slrError && !showSlrDock && (
        <div
          role="alert"
          data-testid="slr-error-banner"
          className="flex items-center justify-between gap-3 border-b border-[#FCA5A5] bg-[#FEF2F2] px-4 py-2 text-[15px] font-medium text-[#B91C1C]"
        >
          <span>{slrError}</span>
          <button
            type="button"
            onClick={() => setSlrError(null)}
            className="text-[14px] font-semibold underline cursor-pointer shrink-0"
          >
            Đóng
          </button>
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto min-[900px]:landscape:flex-row min-[900px]:landscape:overflow-hidden">
        {(showSlrDock || liveGlosses.length > 0) && (
          <SlrDock
            slrBaseUrl={slrBaseUrl}
            running={slrRunning}
            draining={slrDraining}
            segmenterState={segmenterState}
            arms={slrArms}
            wsConnected={slrWsConnected}
            captureFps={captureFps}
            queueDepth={queueDepth}
            lastTiming={lastTiming}
            showDiagnostics={slrSettings.showDiagnostics}
            errorMessage={slrError}
            busy={slrBusy}
            compact={isOskOpen}
            onStop={() => void handleToggleSigning()}
          />
        )}

        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          {showLiveCard && (
            <div
              className={`shrink-0 overflow-y-auto px-3 py-2 sm:px-5 min-[900px]:landscape:px-8 min-[900px]:landscape:pt-0 ${
                sentenceEditing && isOskOpen ? 'min-h-0 flex-1' : 'max-h-[330px]'
              }`}
            >
              <SentenceSigningCard
                key={`${activeSessionIdRef.current}:${liveGlosses[0]?.utteranceId ?? 'empty'}`}
                running={slrRunning}
                glosses={liveGlosses}
                autoSpeak={slrSettings.autoSpeak}
                sessionId={activeSessionIdRef.current}
                autoReadyIds={autoReadyIds}
                autoCreate={slrSettings.autoSaveOnRest}
                pendingRecognition={!closedUtteranceIds.includes(liveGlosses[0]?.utteranceId) && (slrDraining || queueDepth > 0 || segmenterState === 'CAPTURING' || segmenterState === 'END_PENDING')}
                onFinish={handleFinishSentence}
                onDiscard={handleDiscardSentence}
                onSend={handleSendSentence}
                onEditFocus={setSentenceEditing}
                keyboardOpen={sentenceEditing && isOskOpen}
                onHideKeyboard={() => { setSentenceEditing(false); void requestOskVisible(false); }}
                onPickCandidate={handlePickSlrCandidate}
                onDropGloss={handleDropSlrGloss}
              />
            </div>
          )}

          {!(sentenceEditing && isOskOpen) && <ConversationArea messages={messages} className="-order-1" />}

          {/* Shared Bottom Composer */}
          {!(sentenceEditing && isOskOpen) && <Composer
            onSendMessage={handleSendMessage}
            draft={draft}
            onDraftChange={setDraft}
            cancelSignal={cancelSignal}
            onRecordingStateChange={setRecordingStatus}
            selectedMicrophoneId={selectedMicrophoneId}
            maxRecordSeconds={maxRecordSeconds}
            isOskOpen={isOskOpen}
            onToggleOsk={handleToggleOsk}
            onRequestOsk={(visible) => void requestOskVisible(visible)}
          />}
        </div>
      </div>

      {/* History Drawer */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={handleCloseHistory}
        activeConversationId={conversation?.id}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />

      {/* Settings View */}
      <SettingsView
        isOpen={isSettingsOpen}
        onClose={handleCloseSettings}
        activeConversationId={conversation?.id}
        onActiveConversationDeleted={handleActiveConversationDeleted}
        onSettingsSaved={refreshSettings}
        slrSettings={slrSettings}
        onSlrSettingsChange={handleSlrSettingsChange}
      />
    </main>
  );
}
