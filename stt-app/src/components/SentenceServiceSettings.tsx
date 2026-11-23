'use client';

import React, { useEffect, useRef, useState } from 'react';
type Account = { id: string; email: string; label: string; connected: boolean; model: string };
type Connection = { activeId: string | null; source: string; accounts: Account[]; pending: boolean; notice: string };
const field = 'min-h-[44px] w-full rounded-xl border border-[#BAC5D0] bg-white px-3 py-2 text-[16px]';
const button = 'min-h-[44px] rounded-xl border border-[#BAC5D0] bg-white px-4 py-2 text-[16px] font-semibold text-[#273D53] disabled:opacity-50';
const POPUP_FEATURES = 'popup=yes,width=640,height=760';

export function SentenceServiceSettings() {
  const [connection, setConnection] = useState<Connection>({ activeId: null, source: 'api', accounts: [], pending: false, notice: '' });
  const [chosenId, setChosenId] = useState('');
  const [models, setModels] = useState<{ id: string; name: string }[]>([]);
  const [editable, setEditable] = useState(false);
  const [manage, setManage] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [showApi, setShowApi] = useState(false);
  const [provider, setProvider] = useState('openai');
  const [baseUrl, setBaseUrl] = useState('https://api.openai.com/v1');
  const [model, setModel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [configured, setConfigured] = useState(false);
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const popupRef = useRef<Window | null>(null);
  const closePopup = () => {
    try {
      if (popupRef.current && !popupRef.current.closed) popupRef.current.close();
    } catch {}
    popupRef.current = null;
  };
  const chosen = connection.accounts.find(a => a.id === chosenId);
  const active = connection.accounts.find(a => a.id === connection.activeId);
  const readStatus = async () => {
    const r = await fetch('/api/chatgpt', { cache: 'no-store' }); const data = await r.json();
    if (!r.ok) throw new Error(data.error?.message || 'Chưa đọc được kết nối ChatGPT.');
    setConnection(data); setChosenId(id => id || data.activeId || data.accounts[0]?.id || '');
    if (!data.pending) closePopup();
    if (data.notice) setNotice(data.notice);
  };
  useEffect(() => {
    setEditable(['127.0.0.1', 'localhost', '[::1]'].includes(location.hostname));
    void readStatus().catch(e => setNotice(e.message));
    void fetch('/api/sign-sentence?source=api').then(r => r.ok ? r.json() : null).then(data => {
      if (data?.configured) { setConfigured(true); setProvider(data.provider); setBaseUrl(data.baseUrl); setModel(data.model); }
    }).catch(() => setNotice('Chưa đọc được cấu hình API.'));
  }, []);
  useEffect(() => {
    if (!connection.pending) return;
    const timer = setInterval(() => { void readStatus().catch(() => {}); }, 2000);
    return () => clearInterval(timer);
  }, [connection.pending]);
  useEffect(() => {
    setModels([]); if (!connection.activeId) return;
    let cancelled = false;
    void fetch(`/api/chatgpt?models=${encodeURIComponent(connection.activeId)}`).then(async r => {
      const data = await r.json(); if (!r.ok) throw new Error(data.error?.message || 'Chưa tải được model.');
      if (!cancelled) setModels(data.models);
    }).catch(e => { if (!cancelled) setNotice(e.message); });
    return () => { cancelled = true; };
  }, [connection.activeId, connection.pending]);
  const action = async (body: object) => {
    const r = await fetch('/api/chatgpt', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const data = await r.json(); if (!r.ok) throw new Error(data.error?.message || 'Chưa cập nhật được kết nối.');
    return data;
  };
  const change = async (body: object, successMessage?: string) => {
    if ((body as { action?: string }).action === 'cancel') closePopup();
    setBusy(true); setNotice('');
    try {
      setConnection(await action(body));
      localStorage.setItem('pbl6-sentence-provider-revision', crypto.randomUUID());
      window.dispatchEvent(new Event('pbl6-sentence-provider-changed'));
      if (successMessage) setNotice(successMessage);
    }
    catch (e) { setNotice(e instanceof Error ? e.message : 'Chưa cập nhật được kết nối.'); }
    finally { setBusy(false); }
  };
  const connect = async (id?: string) => {
    const popup = window.open('about:blank', 'pbl6-chatgpt-login', POPUP_FEATURES);
    if (!popup) { setNotice('Hãy cho phép mở cửa sổ đăng nhập rồi thử lại.'); return; }
    popupRef.current = popup;
    setBusy(true); setNotice('');
    try { const data = await action({ action: 'start', ...(id ? { id } : {}) }); popup.location.href = data.url; setManage(false); await readStatus(); }
    catch (e) { closePopup(); setNotice(e instanceof Error ? e.message : 'Chưa bắt đầu được đăng nhập.'); }
    finally { setBusy(false); }
  };
  const saveApi = async () => {
    setBusy(true); setNotice('');
    try {
      const r = await fetch('/api/sign-sentence', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ provider, baseUrl, model, apiKey }) });
      const data = await r.json(); if (!r.ok) throw new Error(data.error?.message || 'Chưa lưu được cấu hình.');
      setConnection(await action({ action: 'use-api' })); setApiKey(''); setConfigured(true); setShowApi(false);
      localStorage.setItem('pbl6-sentence-provider-revision', crypto.randomUUID()); window.dispatchEvent(new Event('pbl6-sentence-provider-changed')); setNotice('Đã chọn dịch vụ API để tạo câu.');
    } catch (e) { setNotice(e instanceof Error ? e.message : 'Chưa lưu được cấu hình.'); }
    finally { setBusy(false); }
  };
  return <section className="space-y-5" aria-label="Nhà cung cấp AI">
    <h3 className="text-[20px] font-bold">Nhà cung cấp AI</h3>
    <div className="space-y-3 border-b border-[#BAC5D0] pb-5">
      <h4 className="text-[13px] font-semibold tracking-wide text-[#4F5D6B]">API KEY</h4>
      {configured && <div className="flex flex-wrap items-center gap-3"><span>{provider === 'gemini' ? 'Google Gemini' : 'OpenAI / API tương thích'} · {model}</span>
        <button type="button" className={button} disabled={busy || !editable} onClick={() => void change({ action: 'use-api' })}>{connection.source === 'api' ? 'Đang dùng' : 'Sử dụng'}</button></div>}
      <button type="button" className={button} onClick={() => setShowApi(!showApi)}>{configured ? 'Cấu hình API' : '+ Thêm nhà cung cấp'}</button>
      {showApi && <div className="space-y-3 rounded-xl border border-[#BAC5D0] p-3">
        <label className="block">Nhà cung cấp<select className={field} value={provider} onChange={e => { const v = e.target.value; setProvider(v); setBaseUrl(v === 'gemini' ? 'https://generativelanguage.googleapis.com/v1beta' : 'https://api.openai.com/v1'); }}>
          <option value="openai">OpenAI / API tương thích</option><option value="gemini">Google Gemini</option></select></label>
        <label className="block">Địa chỉ API<input className={field} value={baseUrl} onChange={e => setBaseUrl(e.target.value)} autoComplete="off" /></label>
        <label className="block">Tên model<input className={field} value={model} onChange={e => setModel(e.target.value)} /></label>
        <label className="block">API key{configured ? ' (để trống để giữ key hiện có)' : ''}<input type="password" className={field} value={apiKey} onChange={e => setApiKey(e.target.value)} autoComplete="new-password" /></label>
        <button type="button" disabled={busy || !editable} onClick={() => void saveApi()} className={button}>Lưu và sử dụng</button>
      </div>}
    </div>
    <div className="space-y-3">
      <h4 className="text-[13px] font-semibold tracking-wide text-[#4F5D6B]">SUBSCRIPTION</h4>
      <div className="flex flex-wrap items-center gap-3"><strong className="text-[18px]">ChatGPT</strong>
        {connection.accounts.length > 0 ? <>
          <select aria-label="Tài khoản ChatGPT" className={`${field} min-w-0 flex-1 basis-48`} value={chosenId} disabled={busy} onChange={e => { const id = e.target.value; setChosenId(id); if (connection.accounts.find(a => a.id === id)?.connected) void change({ action: 'select', id }); }}>
            {connection.accounts.map(a => <option key={a.id} value={a.id}>{a.label}{a.connected ? '' : ' (đã ngắt)'}</option>)}
          </select>
          <button type="button" className={button} disabled={busy || !editable} onClick={() => { setDisconnecting(false); setManage(true); }}>Quản lý…</button>
        </> : <button type="button" className={button} data-testid="chatgpt-connect" disabled={busy || !editable || connection.pending} onClick={() => void connect()}>Kết nối</button>}
      </div>
      {connection.pending && <div role="status" className="flex flex-wrap items-center gap-3"><span>Đang chờ bạn đăng nhập và cấp quyền…</span><button type="button" className={button} onClick={() => void change({ action: 'cancel' })}>Hủy đăng nhập</button></div>}
      {active?.connected && <label className="block">Model tạo câu<select aria-label="Model ChatGPT" data-testid="chatgpt-model" className={field} value={active.model} disabled={busy || !editable || models.length === 0} onChange={e => { const nextModel = e.target.value; const picked = models.find(m => m.id === nextModel)?.name || nextModel; void change({ action: 'select', id: active.id, model: nextModel }, `✓ Đã lưu model: ${picked}`); }}>
        <option value="" disabled>{models.length ? 'Chọn model của tài khoản' : 'Đang tải model…'}</option>
        {active.model && !models.some(m => m.id === active.model) && <option value={active.model}>{active.model} (đã lưu)</option>}
        {models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}</select></label>}
      {!editable && <p className="text-[14px] text-[#4F5D6B]">Mở Cài đặt trên màn hình Pi để kết nối hoặc thay đổi dịch vụ AI.</p>}
    </div>
    {notice && <p role="status" className={`text-[14px] ${notice.startsWith('✓') ? 'font-semibold text-emerald-700' : ''}`}>{notice}</p>}
    {manage && <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#18212B]/40 p-4"><section role="dialog" aria-modal="true" aria-label="Quản lý ChatGPT" className="w-full max-w-lg space-y-4 rounded-2xl bg-white p-5 shadow-xl">
      <h3 className="text-[20px] font-bold">{disconnecting ? 'Ngắt kết nối tài khoản?' : 'ChatGPT'}</h3><p className="break-all">{chosen?.label}</p>
      {disconnecting ? <>
        <p>Xóa kết nối đã lưu trên Pi. Không hủy gói ChatGPT hoặc xóa hội thoại PBL6.</p>
        <div className="flex flex-wrap justify-end gap-2"><button type="button" className={button} onClick={() => setDisconnecting(false)}>Hủy</button><button type="button" disabled={busy} className={`${button} border-red-700 text-red-700`} onClick={async () => { await change({ action: 'disconnect', id: chosenId }); setManage(false); }}>Ngắt kết nối</button></div>
      </> : <>
        <p className="text-[14px] text-[#4F5D6B]">Chuỗi gloss cần tạo câu sẽ được gửi tới OpenAI và sử dụng hạn mức của tài khoản bạn kết nối.</p>
        <div className="flex flex-wrap gap-2"><button type="button" className={button} disabled={busy} onClick={() => void connect()}>Thêm tài khoản</button>
          {chosen && <button type="button" className={button} disabled={busy} onClick={() => void connect(chosen.id)}>Đăng nhập lại</button>}</div>
        <a
          href="https://chatgpt.com/settings/usage"
          target="_blank"
          rel="noreferrer"
          className="inline-block underline"
          onClick={e => {
            e.preventDefault();
            window.open('https://chatgpt.com/settings/usage', 'pbl6-chatgpt-usage', POPUP_FEATURES);
          }}
        >Quản lý hạn mức trong ChatGPT</a>
        <div className="flex flex-wrap justify-between gap-2"><button type="button" className={`${button} text-red-700`} disabled={busy || !chosen?.connected} onClick={() => setDisconnecting(true)}>Ngắt kết nối</button><button type="button" className={button} onClick={() => setManage(false)}>Đóng</button></div>
      </>}
    </section></div>}
  </section>;
}
