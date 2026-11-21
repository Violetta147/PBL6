'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import type { Conversation, Message } from '../../src/contracts';
import {
  DEFAULT_SLR_SETTINGS,
  loadSlrSettings,
  resolveSlrBaseUrl,
  toWsUrl,
  type SlrSettings,
} from '../../src/lib/slrSettings';
import {
  formatUserFacingState,
  startSlrSession,
  stopSlrSession,
  type SegmenterState,
  type SlrGlossRecord,
  type SlrWsEvent,
} from '../../src/lib/slrClient';

export default function CompanionPage() {
  const [hasMounted, setHasMounted] = useState(false);
  const [slrSettings, setSlrSettings] = useState<SlrSettings>(DEFAULT_SLR_SETTINGS);
  const [wsConnected, setWsConnected] = useState(false);
  const [running, setRunning] = useState(false);
  const [draining, setDraining] = useState(false);
  const [busy, setBusy] = useState(false);
  const [segmenterState, setSegmenterState] = useState<SegmenterState>('UNKNOWN');
  const [liveGlosses, setLiveGlosses] = useState<SlrGlossRecord[]>([]);
  const [latestUtterance, setLatestUtterance] = useState<string>('');
  const [errorText, setErrorText] = useState<string | null>(null);

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConvId, setSelectedConvId] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);

  const seenSegIdsRef = useRef<Set<string>>(new Set());
  const activeSessionKeyRef = useRef<string | null>(null);
  const selectedConvIdRef = useRef<string>('');
  selectedConvIdRef.current = selectedConvId;

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

  const loadConversations = useCallback(async (preferId?: string) => {
    try {
      const listRes = await fetch('/api/conversations', { cache: 'no-store' });
      if (!listRes.ok) return;
      const list = (await listRes.json()) as Conversation[];
      setConversations(list);

      const targetId =
        preferId && list.some((c) => c.id === preferId)
          ? preferId
          : selectedConvIdRef.current && list.some((c) => c.id === selectedConvIdRef.current)
          ? selectedConvIdRef.current
          : list[0]?.id ?? '';

      setSelectedConvId(targetId);
      if (targetId) {
        const detailRes = await fetch(
          `/api/conversations/${encodeURIComponent(targetId)}`,
          { cache: 'no-store' }
        );
        if (detailRes.ok) {
          const data = (await detailRes.json()) as {
            conversation: Conversation;
            messages: Message[];
          };
          setMessages(data.messages ?? []);
        }
      } else {
        setMessages([]);
      }
    } catch {
      // Ignore transient network errors.
    }
  }, []);

  useEffect(() => {
    if (!hasMounted) return;
    void loadConversations();
  }, [hasMounted, loadConversations]);

  useEffect(() => {
    if (!hasMounted) return;
    let disposed = false;
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (disposed) return;
      try {
        ws = new WebSocket(`${toWsUrl(slrBaseUrl)}/ws/live`);
      } catch {
        scheduleReconnect();
        return;
      }

      ws.onopen = () => {
        setWsConnected(true);
        setErrorText(null);
      };

      ws.onclose = () => {
        setWsConnected(false);
        scheduleReconnect();
      };

      ws.onerror = () => {};

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
            seenSegIdsRef.current.clear();
          }
          setRunning(Boolean(snap.running));
          setDraining(Boolean(snap.draining));
          setSegmenterState(snap.segmenter_state ?? 'UNKNOWN');

          const closedUtt = new Set(
            (snap.utterances ?? []).map((u) => u.utterance_id)
          );
          for (const g of snap.glosses ?? []) {
            seenSegIdsRef.current.add(g.segment_id);
          }
          setLiveGlosses(
            (snap.glosses ?? []).filter((g) => !closedUtt.has(g.utterance_id))
          );
          const lastUtt = snap.utterances?.[snap.utterances.length - 1];
          if (lastUtt) {
            setLatestUtterance(lastUtt.raw_glosses.join(' '));
          }
        } else if (msg.type === 'session_started') {
          seenSegIdsRef.current.clear();
          setLiveGlosses([]);
          setRunning(true);
          setDraining(false);
          setSegmenterState('UNKNOWN');
          setErrorText(null);
        } else if (msg.type === 'status') {
          setSegmenterState(msg.segmenter_state ?? 'UNKNOWN');
        } else if (msg.type === 'gloss_result') {
          if (seenSegIdsRef.current.has(msg.gloss.segment_id)) return;
          seenSegIdsRef.current.add(msg.gloss.segment_id);
          setLiveGlosses((prev) => [...prev, msg.gloss]);
        } else if (msg.type === 'utterance_ready') {
          const joined = (msg.utterance.raw_glosses ?? []).join(' ');
          setLatestUtterance(joined);
          setLiveGlosses((prev) =>
            prev.filter((g) => g.utterance_id !== msg.utterance.utterance_id)
          );
          setTimeout(() => {
            void loadConversations();
          }, 300);
        } else if (msg.type === 'session_stopped') {
          setRunning(Boolean(msg.snapshot?.running));
          setDraining(Boolean(msg.snapshot?.draining));
          void loadConversations();
        } else if (msg.type === 'error') {
          setErrorText(msg.message);
        }
      };
    };

    const scheduleReconnect = () => {
      if (disposed || timer !== null) return;
      timer = setTimeout(() => {
        timer = null;
        connect();
      }, 2500);
    };

    connect();
    return () => {
      disposed = true;
      if (timer !== null) clearTimeout(timer);
      try {
        ws?.close();
      } catch {
        // Ignore close errors.
      }
    };
  }, [hasMounted, slrBaseUrl, loadConversations]);

  const handleToggleSession = async () => {
    if (busy) return;
    setBusy(true);
    setErrorText(null);
    try {
      if (running || draining) {
        const snap = await stopSlrSession(slrBaseUrl);
        setRunning(Boolean(snap.running));
        setDraining(Boolean(snap.draining));
      } else {
        seenSegIdsRef.current.clear();
        setLiveGlosses([]);
        const snap = await startSlrSession(slrBaseUrl, slrSettings.cameraIndex);
        setRunning(Boolean(snap.running));
        setDraining(Boolean(snap.draining));
        setSegmenterState(snap.segmenter_state ?? 'UNKNOWN');
      }
    } catch (error) {
      setErrorText(
        error instanceof Error
          ? error.message
          : `Không kết nối được máy chủ SLR (${slrBaseUrl}).`
      );
    } finally {
      setBusy(false);
    }
  };

  const handleSelectConversation = async (id: string) => {
    setSelectedConvId(id);
    await loadConversations(id);
  };

  const userStatus = formatUserFacingState(running, draining, segmenterState);

  return (
    <main className="min-h-dvh bg-[#F5F7F9] text-[#18212B] flex flex-col">
      <header className="bg-[#273D53] text-white px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-[18px] font-bold leading-tight">
            PBL6 · Trình duyệt đồng hành
          </h1>
          <div className="text-[13px] text-white/80">
            {wsConnected
              ? 'Đã đồng bộ trực tiếp với thiết bị chính'
              : `Đang nối lại tới ${slrBaseUrl}...`}
          </div>
        </div>

        <button
          type="button"
          onClick={() => void handleToggleSession()}
          disabled={busy || draining}
          data-testid="companion-session-button"
          className={`min-h-[44px] rounded-xl px-4 py-2 text-[16px] font-bold text-white transition cursor-pointer disabled:opacity-50 ${
            running || draining
              ? 'bg-[#DC2626] hover:bg-[#B91C1C]'
              : 'bg-[#087A47] hover:opacity-95'
          }`}
        >
          {draining ? 'Đang hoàn tất...' : running ? 'Kết thúc ký' : 'Bắt đầu ký'}
        </button>
      </header>

      <div className="mx-auto w-full max-w-2xl flex-1 p-4 space-y-4">
        {errorText && (
          <div
            role="alert"
            className="rounded-xl border border-[#FCA5A5] bg-[#FEF2F2] p-3 text-[15px] font-medium text-[#B91C1C]"
          >
            {errorText}
          </div>
        )}

        {/* Live Signing Status Card */}
        <section className="rounded-2xl border border-[#BAC5D0] bg-[#FFFFFF] p-4 space-y-3 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-[13px] font-bold uppercase tracking-wider text-[#4F5D6B]">
              Đang dịch trực tiếp
            </span>
            <span className="rounded-full bg-[#F5F7F9] border border-[#BAC5D0] px-3 py-1 text-[13px] font-semibold text-[#18212B]">
              {userStatus}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2 min-h-[40px]">
            {liveGlosses.length === 0 ? (
              <span className="text-[16px] text-[#4F5D6B]">
                {running
                  ? 'Chờ ký hiệu mới...'
                  : 'Chưa bật phiên ký. Chạm "Bắt đầu ký" để bắt đầu.'}
              </span>
            ) : (
              liveGlosses.map((g) => (
                <span
                  key={g.segment_id}
                  className={`rounded-xl px-3 py-1 text-[20px] font-bold ${
                    g.raw.low_confidence
                      ? 'bg-[#FDE7E7] text-[#C52236] border border-[#FCA5A5]'
                      : 'bg-[#DDF7E9] text-[#0B6B45]'
                  }`}
                >
                  {g.raw.low_confidence
                    ? `CHƯA RÕ (${g.raw.top1_label})`
                    : g.raw.top1_label}
                </span>
              ))
            )}
          </div>

          {latestUtterance && (
            <div className="border-t border-[#E2E8F0] pt-2">
              <div className="text-[13px] font-semibold text-[#4F5D6B]">
                Chuỗi vừa chốt:
              </div>
              <div className="text-[20px] font-bold text-[#18212B]">
                {latestUtterance}
              </div>
            </div>
          )}
        </section>

        {/* Conversation History Card */}
        <section className="rounded-2xl border border-[#BAC5D0] bg-[#FFFFFF] p-4 space-y-3 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-[13px] font-bold uppercase tracking-wider text-[#4F5D6B]">
              Lịch sử hội thoại
            </span>
            <div className="flex items-center gap-2">
              <select
                value={selectedConvId}
                onChange={(e) => void handleSelectConversation(e.target.value)}
                aria-label="Chọn hội thoại"
                className="min-h-[38px] max-w-[220px] rounded-lg border border-[#BAC5D0] bg-[#F5F7F9] px-2.5 py-1 text-[14px] text-[#18212B]"
              >
                {conversations.length === 0 ? (
                  <option value="">Chưa có hội thoại</option>
                ) : (
                  conversations.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.title}
                    </option>
                  ))
                )}
              </select>
              <button
                type="button"
                onClick={() => void loadConversations()}
                className="min-h-[38px] rounded-lg border border-[#BAC5D0] bg-[#FFFFFF] px-3 py-1 text-[14px] font-semibold text-[#273D53] hover:bg-[#F5F7F9] cursor-pointer"
              >
                Làm mới
              </button>
            </div>
          </div>

          <div className="space-y-2.5">
            {messages.length === 0 ? (
              <p className="text-[15px] text-[#4F5D6B] py-4 text-center">
                Chưa có tin nhắn nào trong hội thoại này.
              </p>
            ) : (
              messages.map((m) => (
                <article
                  key={m.id}
                  className="rounded-xl border border-[#BAC5D0] bg-[#F5F7F9] p-3 space-y-1"
                >
                  <div className="flex items-center justify-between text-[13px] font-semibold">
                    <span
                      className={
                        m.sources?.includes('sign')
                          ? 'text-[#087A47]'
                          : 'text-[#273D53]'
                      }
                    >
                      {m.sources?.includes('sign') ? 'Ký hiệu (SLR)' : 'Giọng nói / Chữ'}
                    </span>
                    <span className="text-[#4F5D6B] font-normal">
                      {new Date(m.createdAt).toLocaleTimeString('vi-VN', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                  <p className="text-[19px] leading-relaxed text-[#18212B] whitespace-pre-wrap break-words m-0">
                    {m.text}
                  </p>
                </article>
              ))
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
