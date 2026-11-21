'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import type { Conversation, Message, MessageSource } from '../src/contracts';
import { Header } from '../src/components/Header';
import { ConversationArea } from '../src/components/ConversationArea';
import { Composer } from '../src/components/Composer';
import { HistoryDrawer } from '../src/components/HistoryDrawer';
import { SettingsView } from '../src/components/SettingsView';
import { SlrDock } from '../src/components/SlrDock';
import { LiveSigningCard, type LiveGlossItem } from '../src/components/LiveSigningCard';
import {
  loadSlrSettings,
  saveSlrSettings,
  resolveSlrBaseUrl,
  toWsUrl,
  DEFAULT_SLR_SETTINGS,
  type SlrSettings,
} from '../src/lib/slrSettings';
import {
  startSlrSession,
  stopSlrSession,
  type SegmenterState,
  type SlrGlossRecord,
  type SlrTopCandidate,
  type SlrWsEvent,
} from '../src/lib/slrClient';
import { speakOutput } from '../src/lib/slrTts';

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

  // SLR Live + Unified Conversation State
  const [hasMounted, setHasMounted] = useState<boolean>(false);
  const [slrSettings, setSlrSettings] = useState<SlrSettings>(DEFAULT_SLR_SETTINGS);
  const [slrWsConnected, setSlrWsConnected] = useState<boolean>(false);
  const [slrRunning, setSlrRunning] = useState<boolean>(false);
  const [slrDraining, setSlrDraining] = useState<boolean>(false);
  const [slrBusy, setSlrBusy] = useState<boolean>(false);
  const [segmenterState, setSegmenterState] = useState<SegmenterState>('UNKNOWN');
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
  const signSaveChainRef = useRef<Promise<void>>(Promise.resolve());

  useEffect(() => {
    setHasMounted(true);
    setSlrSettings(loadSlrSettings());
  }, []);

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

  const computeOskCeiling = useCallback((visible: boolean): number | undefined => {
    if (!visible || typeof window === 'undefined') return undefined;
    const vh = window.innerHeight || 564;
    // When labwc resizes the maximized Firefox viewport for Squeekboard's 210px exclusive zone
    // (vh drops from ~564px to ~354px), let h-dvh fill 100% down to the keyboard edge with 0px gap.
    if (vh <= 420) return undefined;
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
    sources: MessageSource[]
  ): Promise<boolean> => {
    try {
      const currentConv = conversationRef.current;
      if (!currentConv) {
        // First message of conversation
        const response = await fetch('/api/conversations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, sources }),
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
            body: JSON.stringify({ text, sources }),
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

  const enqueueSignSave = useCallback(
    (text: string) => {
      const clean = text.trim();
      if (!clean) return;
      signSaveChainRef.current = signSaveChainRef.current
        .then(async () => {
          const ok = await handleSendMessage(clean, ['sign']);
          if (!ok) {
            setSlrError('Không lưu được câu ký hiệu vào hội thoại.');
          }
        })
        .catch(() => {
          setSlrError('Không lưu được câu ký hiệu vào hội thoại.');
        });
    },
    [handleSendMessage]
  );

  useEffect(() => {
    if (!hasMounted) return;
    let disposed = false;
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;

    const toLiveItem = (gloss: SlrGlossRecord): LiveGlossItem => ({
      segmentId: gloss.segment_id,
      utteranceId: gloss.utterance_id,
      label: gloss.raw.top1_label,
      labelId: gloss.raw.top1_id,
      confidence: gloss.raw.confidence,
      lowConfidence: gloss.raw.low_confidence,
      top3: (gloss.raw.top5 ?? []).slice(0, 3),
    });

    const connect = () => {
      if (disposed) return;
      const wsUrl = `${toWsUrl(slrBaseUrl)}/ws/live`;
      try {
        ws = new WebSocket(wsUrl);
      } catch {
        scheduleReconnect();
        return;
      }

      ws.onopen = () => {
        attempt = 0;
        setSlrWsConnected(true);
        setSlrError(null);
      };

      ws.onclose = () => {
        setSlrWsConnected(false);
        scheduleReconnect();
      };

      ws.onerror = () => {
        // Quietly handle connection errors when SLR backend is offline.
      };

      ws.onmessage = (event) => {
        let msg: SlrWsEvent;
        try {
          msg = JSON.parse(String(event.data)) as SlrWsEvent;
        } catch {
          return;
        }

        if (msg.type === 'snapshot') {
          const snap = msg.snapshot;
          const sessionKey = snap.session_id ? `${snap.session_id}:${snap.epoch}` : null;
          if (sessionKey && sessionKey !== activeSessionKeyRef.current) {
            activeSessionKeyRef.current = sessionKey;
            seenSegmentIdsRef.current.clear();
            savedSegmentIdsRef.current.clear();
          }

          setSlrRunning(Boolean(snap.running));
          setSlrDraining(Boolean(snap.draining));
          setSegmenterState(snap.segmenter_state ?? 'UNKNOWN');
          setCaptureFps(snap.capture_fps ?? 0);
          setQueueDepth(snap.queue_depth ?? 0);

          for (const g of snap.glosses ?? []) {
            seenSegmentIdsRef.current.add(g.segment_id);
          }

          if (snap.running) {
            const activeItems = (snap.glosses ?? [])
              .filter((g) => !savedSegmentIdsRef.current.has(g.segment_id))
              .map(toLiveItem);
            setLiveGlosses(activeItems);
          }
        } else if (msg.type === 'session_started') {
          seenSegmentIdsRef.current.clear();
          savedSegmentIdsRef.current.clear();
          setLiveGlosses([]);
          setTtsStatus('');
          setSlrError(null);
          setSlrRunning(true);
          setSlrDraining(false);
          setSegmenterState('UNKNOWN');
        } else if (msg.type === 'status') {
          setSegmenterState(msg.segmenter_state ?? 'UNKNOWN');
          setQueueDepth(msg.queue_depth ?? 0);
          setCaptureFps(msg.capture_fps ?? 0);
        } else if (msg.type === 'gloss_result') {
          const gloss = msg.gloss;
          if (seenSegmentIdsRef.current.has(gloss.segment_id)) return;
          seenSegmentIdsRef.current.add(gloss.segment_id);
          setLastTiming(gloss.timing ?? null);

          const item = toLiveItem(gloss);
          setLiveGlosses((prev) => [...prev, item]);

          if (!item.lowConfidence && slrSettingsRef.current.autoSpeak) {
            speakOutput(
              {
                glossIds: [item.labelId],
                labels: [item.label],
                slrBaseUrl: slrBaseUrlRef.current,
              },
              setTtsStatus
            );
          }
        } else if (msg.type === 'utterance_ready') {
          const utt = msg.utterance;
          if (slrSettingsRef.current.autoSaveOnRest) {
            const matchingLive = liveGlossesRef.current.filter(
              (g) =>
                g.utteranceId === utt.utterance_id &&
                !savedSegmentIdsRef.current.has(g.segmentId)
            );
            const fallbackSegments = (utt.segments ?? []).filter(
              (s) => !savedSegmentIdsRef.current.has(s.segment_id)
            );
            const segIds =
              matchingLive.length > 0
                ? matchingLive.map((g) => g.segmentId)
                : fallbackSegments.map((s) => s.segment_id);
            const text =
              matchingLive.length > 0
                ? matchingLive.map((g) => g.label).join(' ').trim()
                : fallbackSegments.map((s) => s.raw.top1_label).join(' ').trim();
            for (const sid of segIds) {
              savedSegmentIdsRef.current.add(sid);
            }
            if (segIds.length > 0) {
              const segSet = new Set(segIds);
              setLiveGlosses((prev) => prev.filter((g) => !segSet.has(g.segmentId)));
            }
            if (text) {
              enqueueSignSave(text);
            }
          }
        } else if (msg.type === 'session_stopped') {
          setSlrRunning(Boolean(msg.snapshot?.running));
          setSlrDraining(Boolean(msg.snapshot?.draining));
          if (slrSettingsRef.current.autoSaveOnRest) {
            const pending = liveGlossesRef.current.filter(
              (g) => !savedSegmentIdsRef.current.has(g.segmentId)
            );
            if (pending.length > 0) {
              for (const g of pending) {
                savedSegmentIdsRef.current.add(g.segmentId);
              }
              const text = pending.map((g) => g.label).join(' ').trim();
              setLiveGlosses([]);
              if (text) {
                enqueueSignSave(text);
              }
            }
          }
        } else if (msg.type === 'error') {
          setSlrError(msg.message || 'Lỗi từ máy chủ nhận dạng SLR.');
        }
      };
    };

    const scheduleReconnect = () => {
      if (disposed || reconnectTimer !== null) return;
      attempt += 1;
      const delay = Math.min(5000, 2000 + attempt * 500);
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connect();
      }, delay);
    };

    connect();
    return () => {
      disposed = true;
      if (reconnectTimer !== null) clearTimeout(reconnectTimer);
      try {
        ws?.close();
      } catch {
        // Ignore close errors.
      }
    };
  }, [hasMounted, slrBaseUrl, enqueueSignSave]);

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
        void requestOskVisible(false);
        seenSegmentIdsRef.current.clear();
        savedSegmentIdsRef.current.clear();
        setLiveGlosses([]);
        setTtsStatus('');
        const snap = await startSlrSession(slrBaseUrl, slrSettings.cameraIndex);
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
    (segmentId: string, candidate: SlrTopCandidate) => {
      setLiveGlosses((prev) =>
        prev.map((g) =>
          g.segmentId === segmentId
            ? {
                ...g,
                label: candidate.label,
                labelId: candidate.label_id,
                confidence: candidate.score,
                lowConfidence: false,
              }
            : g
        )
      );
      if (slrSettingsRef.current.autoSpeak) {
        speakOutput(
          {
            glossIds: [candidate.label_id],
            labels: [candidate.label],
            slrBaseUrl: slrBaseUrlRef.current,
          },
          setTtsStatus
        );
      }
    },
    []
  );

  const handleDropSlrGloss = useCallback((segmentId: string) => {
    savedSegmentIdsRef.current.add(segmentId);
    setLiveGlosses((prev) => prev.filter((g) => g.segmentId !== segmentId));
  }, []);

  const handleReplaySlrAudio = useCallback(() => {
    const clear = liveGlossesRef.current.filter((g) => !g.lowConfidence);
    if (clear.length === 0) return;
    speakOutput(
      {
        glossIds: clear.map((g) => g.labelId),
        labels: clear.map((g) => g.label),
        slrBaseUrl: slrBaseUrlRef.current,
      },
      setTtsStatus
    );
  }, []);

  const handleManualSaveSlr = useCallback(() => {
    const current = liveGlossesRef.current;
    if (current.length === 0) return;
    const text = current.map((g) => g.label).join(' ').trim();
    for (const g of current) {
      savedSegmentIdsRef.current.add(g.segmentId);
    }
    setLiveGlosses([]);
    enqueueSignSave(text);
  }, [enqueueSignSave]);

  // Conversation title rename handler
  async function handleRename(newTitle: string) {
    if (!conversation) return;
    try {
      const response = await fetch(
        `/api/conversations/${encodeURIComponent(conversation.id)}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: newTitle }),
        }
      );

      if (response.ok) {
        const updated: Conversation = await response.json();
        setConversation(updated);
      }
    } catch {
      // Revert / ignore on error
    }
  }

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
          target.closest('textarea, input, select, [data-testid="osk-button"], [data-testid="send-button"]')
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
        title={conversation ? conversation.title : 'Hội thoại mới'}
        isNew={conversation === null || messages.length === 0}
        onRename={handleRename}
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

      {/* Unified Multimodal Workspace: optional left Camera Dock + Conversation + Composer */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {showSlrDock && (
          <SlrDock
            slrBaseUrl={slrBaseUrl}
            running={slrRunning}
            draining={slrDraining}
            segmenterState={segmenterState}
            wsConnected={slrWsConnected}
            captureFps={captureFps}
            queueDepth={queueDepth}
            lastTiming={lastTiming}
            showDiagnostics={slrSettings.showDiagnostics}
            errorMessage={slrError}
            busy={slrBusy}
            onStop={() => void handleToggleSigning()}
          />
        )}

        <div className="flex flex-1 min-w-0 flex-col">
          {/* Main Conversation Message Area */}
          <ConversationArea messages={messages} />

          {/* Live Signing Bubble directly above Composer */}
          {showLiveCard && (
            <div
              className={`shrink-0 overflow-y-auto px-4 pb-3 sm:px-8 ${
                isOskOpen ? 'max-h-[96px]' : 'max-h-[260px]'
              }`}
            >
              <LiveSigningCard
                running={slrRunning}
                glosses={liveGlosses}
                autoSpeak={slrSettings.autoSpeak}
                autoSaveOnRest={slrSettings.autoSaveOnRest}
                ttsStatus={ttsStatus}
                onPickCandidate={handlePickSlrCandidate}
                onDropGloss={handleDropSlrGloss}
                onReplayAudio={handleReplaySlrAudio}
                onManualSave={handleManualSaveSlr}
              />
            </div>
          )}

          {/* Shared Bottom Composer */}
          <Composer
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
          />
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
