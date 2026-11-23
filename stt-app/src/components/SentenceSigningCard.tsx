'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { SignGloss, SignSentence } from '../contracts';
import { LiveGlossPicker, type LiveGlossItem } from './LiveSigningCard';
import type { SlrTopCandidate } from '../lib/slrClient';

type Result = { sentence: string; needsClarification: boolean; explanation: string; fingerprint?: string; providerRevision?: string; metadata: Omit<SignSentence, 'confirmedAt'> };
function providerRevision(): string { try { return localStorage.getItem('pbl6-sentence-provider-revision') || ''; } catch { return ''; } }
export function glossFingerprint(items: SignGloss[]): string {
  return JSON.stringify(items.map(g => [g.segmentId, g.utteranceId, g.labelId, g.label, g.status]));
}

export function SentenceSigningCard({ running, glosses, sessionId, autoReadyIds, autoCreate, pendingRecognition,
  onFinish, onPickCandidate, onDropGloss, onDiscard, onSend, onEditFocus, onHideKeyboard, autoSpeak, keyboardOpen,
}: {
  running: boolean; glosses: LiveGlossItem[]; sessionId: string | null; autoReadyIds: string[]; autoCreate: boolean;
  pendingRecognition: boolean; autoSpeak: boolean; keyboardOpen: boolean;
  onFinish: (utteranceId: string) => Promise<void>;
  onPickCandidate: (id: string, candidate: SlrTopCandidate) => void;
  onDropGloss: (id: string) => void; onDiscard: (ids: string[]) => void;
  onSend: (text: string, items: SignGloss[], metadata: SignSentence) => Promise<boolean>;
  onEditFocus: (editing: boolean) => void; onHideKeyboard: () => void;
}) {
  const uid = glosses[0]?.utteranceId;
  const items = useMemo(() => glosses.filter(g => g.utteranceId === uid), [glosses, uid]);
  const fingerprint = glossFingerprint(items);
  const current = useRef({ items, fingerprint }); current.current = { items, fingerprint };
  const [result, setResult] = useState<Result | null>(null);
  const [sentence, setSentence] = useState('');
  const [busy, setBusy] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [editingGlosses, setEditingGlosses] = useState(false);
  const operation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const sendingRef = useRef(false);
  const held = useRef(new Set<string>());
  const attempted = useRef(new Set<string>());
  const cacheKey = `pbl6.sentence.review.${sessionId ?? 'idle'}.${uid ?? 'empty'}`;
  const cacheLoaded = useRef('');

  useEffect(() => {
    operation.current += 1; controller.current?.abort();
    setBusy(false); setResult(null); setSentence(''); setError(''); setEditingGlosses(false);
    cacheLoaded.current = cacheKey;
    try {
      const raw = localStorage.getItem(cacheKey);
      if (raw) {
        const saved = JSON.parse(raw);
        if (saved.fingerprint === fingerprint && saved.result?.sentence && typeof saved.sentence === 'string' && (saved.result.providerRevision || '') === providerRevision()) {
          saved.result.fingerprint = fingerprint;
          setResult(saved.result); setSentence(saved.sentence);
        }
      }
    } catch { /* The in-memory draft remains available if browser storage is unavailable. */ }
    return () => { operation.current += 1; controller.current?.abort(); };
  }, [fingerprint, cacheKey]);

  useEffect(() => {
    const changed = () => {
      operation.current += 1; controller.current?.abort(); setBusy(false); setResult(null); setSentence('');
      setError('Đã đổi dịch vụ hoặc model. Hãy tạo lại câu từ chuỗi gloss.');
      try { localStorage.removeItem(cacheKey); } catch {}
    };
    window.addEventListener('pbl6-sentence-provider-changed', changed);
    return () => window.removeEventListener('pbl6-sentence-provider-changed', changed);
  }, [cacheKey]);

  useEffect(() => {
    if (cacheLoaded.current !== cacheKey || (result && result.fingerprint !== fingerprint)) return;
    try { localStorage.setItem(cacheKey, JSON.stringify({ fingerprint, result, sentence })); }
    catch { /* The page retains the unsaved draft. */ }
  }, [cacheKey, fingerprint, result, sentence]);

  const generate = useCallback(async (finish: boolean) => {
    if (!current.current.items.length || current.current.items.some(g => g.lowConfidence) || sendingRef.current) return;
    const seq = ++operation.current;
    controller.current?.abort(); const abort = new AbortController(); controller.current = abort;
    setBusy(true); setError(''); setEditingGlosses(false);
    try {
      if (finish) await onFinish(current.current.items[0].utteranceId);
      if (seq !== operation.current) return;
      const source = current.current;
      const requestId = crypto.randomUUID();
      const response = await fetch('/api/sign-sentence', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ glosses: source.items, requestId }), signal: abort.signal });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message || 'Chưa tạo được câu. Hãy thử lại.');
      if (seq !== operation.current || source.fingerprint !== current.current.fingerprint || data.metadata?.requestId !== requestId) return;
      setResult({ ...data, fingerprint: source.fingerprint, providerRevision: providerRevision() }); setSentence(data.sentence);
      if (data.needsClarification) setError(data.explanation || 'Chưa đủ thông tin để tạo câu. Hãy kiểm tra chuỗi gloss.');
    } catch (e) {
      if (seq === operation.current && !abort.signal.aborted) setError(e instanceof Error ? e.message : 'Chưa tạo được câu. Bản nháp vẫn còn.');
    } finally { if (seq === operation.current) setBusy(false); }
  }, [onFinish]);

  useEffect(() => {
    if (!uid || !autoReadyIds.includes(uid)) return;
    if (items.some(g => g.lowConfidence)) {
      held.current.add(uid);
      try { localStorage.setItem(cacheKey + '.held', '1'); } catch {}
      return;
    }
    try { if (localStorage.getItem(cacheKey + '.held') === '1') held.current.add(uid); } catch {}
    if (!autoCreate || held.current.has(uid) || attempted.current.has(uid) || result || busy || pendingRecognition) return;
    attempted.current.add(uid); void generate(false);
  }, [uid, fingerprint, items, autoReadyIds, autoCreate, result, busy, pendingRecognition, generate, cacheKey]);

  const send = async () => {
    if (sendingRef.current || !result || result.fingerprint !== current.current.fingerprint || result.needsClarification || !sentence.trim() || busy) return;
    if ((result.providerRevision || '') !== providerRevision()) { setResult(null); setError('Dịch vụ/model đã thay đổi. Hãy tạo lại câu.'); return; }
    sendingRef.current = true; setSending(true); setError('');
    const source = current.current;
    try {
      const ok = await onSend(sentence.trim(), source.items, { ...result.metadata, confirmedAt: new Date().toISOString() });
      if (!ok) { setError('Chưa lưu được câu. Nội dung vẫn còn, hãy thử gửi lại.'); return; }
      try { localStorage.removeItem(cacheKey); localStorage.removeItem(cacheKey + '.held'); } catch {}
      setResult(null); setSentence(''); onEditFocus(false); onHideKeyboard();
    } finally { sendingRef.current = false; setSending(false); }
  };
  const unclear = items.some(g => g.lowConfidence);
  const review = !!result && !result.needsClarification && !editingGlosses;
  const groups = new Set(glosses.map(g => g.utteranceId)).size;
  const button = 'min-h-[44px] rounded-xl border px-3 py-2 text-[16px] font-semibold disabled:opacity-45 cursor-pointer';

  return <article aria-label="Thẻ đang ký trực tiếp" data-testid="live-signing-card" className="w-full rounded-2xl border-2 border-[#273D53] bg-white p-3 space-y-2">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <span className="text-[13px] font-bold uppercase text-[#273D53]" role="status">
        {busy ? 'Đang hoàn tất và tạo câu…' : review ? 'Kiểm tra câu gợi ý' : unclear ? 'Chờ chỉnh · Chưa gửi' : running ? 'Đang ký trực tiếp' : 'Bản nháp · Chưa gửi'}
        {groups > 1 ? ` · ${groups} câu đang chờ` : ''}
      </span>
      <span className="text-[13px] font-semibold text-[#087A47]">Loa tự động: {autoSpeak ? 'Bật' : 'Tắt'}</span>
      {keyboardOpen && <button type="button" onClick={onHideKeyboard} className="min-h-[44px] rounded-lg border border-[#BAC5D0] px-3 text-[14px] font-semibold">Ẩn bàn phím</button>}
    </div>
    {review ? <div className="flex flex-wrap gap-2" aria-label="Gloss nguồn">{items.map(g => <span key={g.segmentId} className="rounded-lg bg-[#DDF7E9] px-2 py-1 text-[18px] text-[#0B6B45]">{g.label}</span>)}</div>
      : <LiveGlossPicker glosses={items} onPickCandidate={onPickCandidate} onDropGloss={sending ? undefined : onDropGloss} emptyText="Chưa có từ nhận dạng." />}
    {review && <textarea aria-label="Câu tiếng Việt gợi ý" data-testid="sign-sentence-input" rows={2} maxLength={2000} value={sentence} disabled={sending}
      onFocus={() => onEditFocus(true)} onChange={e => setSentence(e.target.value)}
      className="min-h-[72px] max-h-[120px] w-full resize-y rounded-xl border-2 border-[#273D53] bg-[#F5F7F9] p-2 text-[20px] leading-snug outline-none" />}
    {error && <p role="alert" className="text-[14px] text-[#B91C1C]">{error}</p>}
    <div className="flex flex-wrap items-center justify-end gap-2 border-t border-[#E2E8F0] pt-2">
      {items.length > 0 && <button type="button" disabled={busy || sending} className={`${button} border-[#B54239] text-[#A8322A]`} onClick={() => { operation.current += 1; controller.current?.abort(); onDiscard(items.map(g => g.segmentId)); onEditFocus(false); onHideKeyboard(); }}>Bỏ bản nháp</button>}
      {review ? <>
        <button type="button" disabled={sending} className={`${button} border-[#BAC5D0]`} onClick={() => { setEditingGlosses(true); onEditFocus(false); onHideKeyboard(); }}>Sửa gloss</button>
        <button type="button" data-testid="sign-sentence-send" disabled={sending || !sentence.trim()} onClick={() => void send()} className={`${button} border-[#273D53] bg-[#273D53] text-white`}>{sending ? 'Đang gửi…' : 'Gửi câu'}</button>
      </> : <button type="button" data-testid="slr-save-message-button" disabled={!items.length || unclear || busy || sending || pendingRecognition} onClick={() => void generate(true)} className={`${button} border-[#273D53] bg-[#273D53] text-white`}>{busy ? 'Đang xử lý…' : 'Kết thúc câu'}</button>}
    </div>
  </article>;
}
