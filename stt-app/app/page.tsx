'use client';

import { useEffect, useRef, useState } from 'react';
import { MAX_AUDIO_BYTES, type PublicSettings, type Transcript, type ApiError } from '../src/contracts';

type Health = { host: string; version: string };
async function readResponse<T>(response: Response): Promise<T> {
  const data = await response.json();
  if (!response.ok) throw new Error((data as ApiError).error?.message || 'Yêu cầu không thành công.');
  return data as T;
}
function FileIcon({ large = false }: { large?: boolean }) {
  return <svg width={large ? 36 : 22} height={large ? 36 : 22} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8zM14 3v6h5M8 13h8M8 17h6" /></svg>;
}

export default function Home() {
  const [view, setView] = useState<'file' | 'settings'>('file');
  const [settings, setSettings] = useState<PublicSettings | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [bootError, setBootError] = useState('');
  const [key, setKey] = useState('');
  const [model, setModel] = useState('nova-3');
  const [timeout, setTimeoutValue] = useState(60);
  const [saving, setSaving] = useState(false);
  const [settingsNote, setSettingsNote] = useState('');
  const [settingsError, setSettingsError] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<Transcript | null>(null);
  const [copyNote, setCopyNote] = useState('');
  const pending = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetch('/api/settings', { signal: controller.signal }).then(readResponse<PublicSettings>),
      fetch('/api/health', { signal: controller.signal }).then(readResponse<Health>),
    ]).then(([s, h]) => { setSettings(s); setModel(s.model); setTimeoutValue(s.timeoutSeconds); setHealth(h); })
      .catch(() => { if (!controller.signal.aborted) setBootError('Chưa đọc được cấu hình ứng dụng. Kiểm tra cửa sổ chạy ứng dụng rồi tải lại.'); });
    return () => { controller.abort(); pending.current?.abort(); };
  }, []);

  async function save(clearApiKey = false) {
    setSaving(true); setSettingsError(''); setSettingsNote('');
    try {
      const s = await fetch('/api/settings', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, timeoutSeconds: timeout, ...(clearApiKey ? { clearApiKey: true } : key ? { apiKey: key } : {}) }),
      }).then(readResponse<PublicSettings>);
      setSettings(s);
      setSettingsNote(clearApiKey ? 'Đã xóa key tại máy chạy ứng dụng.' : 'Đã lưu cấu hình. Quyền API sẽ được kiểm chứng khi bạn nhận dạng một file.');
    } catch (e) { setSettingsError(e instanceof Error ? e.message : 'Không lưu được cấu hình.'); }
    finally { setKey(''); setSaving(false); }
  }

  async function recognize() {
    if (!file || busy) return;
    setError(''); setCopyNote('');
    if (file.size > MAX_AUDIO_BYTES || !file.size) { setError('Chọn file không trống và không quá 20 MiB.'); return; }
    setBusy(true);
    const controller = new AbortController(); pending.current = controller;
    try {
      const form = new FormData(); form.set('file', file);
      const response = await fetch('/api/transcriptions', { method: 'POST', body: form, signal: controller.signal });
      const transcript = await readResponse<Transcript>(response);
      setResult(transcript);
    } catch (e) {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Không nhận được kết quả. Kiểm tra kết nối và thử lại.');
    } finally { if (pending.current === controller) { pending.current = null; setBusy(false); } }
  }

  function download() {
    if (!result) return;
    const url = URL.createObjectURL(new Blob([result.text], { type: 'text/plain;charset=utf-8' }));
    const a = document.createElement('a'); a.href = url; a.download = `${result.fileName.replace(/\.[^.]+$/, '')}-transcript.txt`; a.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <main className="mx-auto max-w-7xl px-5 py-6 sm:px-10 sm:py-9">
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-[#dce3db] pb-6">
      <div className="flex items-center gap-3"><div className="flex size-11 items-center justify-center rounded-xl bg-[#126c59] text-white"><FileIcon /></div><div><p className="text-xl font-bold tracking-tight">STT <span className="font-normal muted">/ Tiếng Việt</span></p><p className="mt-0.5 text-xs muted">Từ âm thanh đến văn bản</p></div></div>
      <div className="flex items-center gap-2 rounded-full border border-[#dce3db] bg-white px-4 py-2 text-sm"><span className="status-dot" />Chạy cục bộ <span className="muted">· {health?.host || 'đang tải'}</span></div>
    </header>

    <nav aria-label="Chức năng" className="my-7 flex gap-2">
      <button className={`button ${view === 'file' ? 'primary' : ''}`} onClick={() => setView('file')}>Nhận dạng file</button>
      <button className={`button ${view === 'settings' ? 'primary' : ''}`} onClick={() => setView('settings')}>Cài đặt</button>
    </nav>
    {bootError && <div role="alert" className="error mb-6 flex flex-wrap items-center justify-between gap-3">{bootError}<button className="button" onClick={() => window.location.reload()}>Tải lại</button></div>}

    {view === 'file' ? <>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4"><div><p className="eyebrow text-[#126c59]">NHẬN DẠNG TIẾNG VIỆT</p><h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Nghe lại bằng con chữ.</h1><p className="mt-3 muted">Chọn một bản thu, gửi nhận dạng và xem văn bản cuối.</p></div><p className="rounded-full bg-[#e7eee4] px-3 py-1 text-xs font-semibold">Deepgram · vi</p></div>
      <div className="grid items-start gap-6 lg:grid-cols-[.9fr_1.2fr]">
        <section className="card p-6 sm:p-7" aria-labelledby="input-title">
          <p className="eyebrow muted">01 / ĐẦU VÀO</p><h2 id="input-title" className="mt-2 text-xl font-semibold">Một file âm thanh</h2>
          <label className={`mt-6 flex min-h-44 flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-[#b9cbbd] bg-[#f6f9f4] px-4 py-7 text-center ${busy ? 'opacity-50' : 'cursor-pointer'}`}>
            <FileIcon large /><span className="font-semibold">{file ? file.name : 'Chọn file từ máy của bạn'}</span>
            <span className="text-sm muted">{file ? `${(file.size / 1024 / 1024).toFixed(2)} MiB · nhấn để đổi file` : 'WAV, MP3 hoặc FLAC · tối đa 20 MiB'}</span>
            <input aria-label="Chọn file âm thanh" className="sr-only" type="file" accept=".wav,.mp3,.flac" disabled={busy} onChange={e => { setFile(e.target.files?.[0] || null); setError(''); }} />
          </label>
          <p className="mt-4 text-sm leading-6 muted">Khi nhấn nhận dạng, audio sẽ được gửi tới Deepgram qua Internet. Bản tải lên không được lưu vào ổ đĩa của ứng dụng.</p>
          {!settings?.hasApiKey && <div className="notice mt-5">Chưa cấu hình API key. <button className="font-semibold underline" onClick={() => setView('settings')}>Mở Cài đặt</button> để nhập key tại máy.</div>}
          <button className="button primary mt-6 w-full" disabled={!file || !settings?.hasApiKey || busy || saving} onClick={recognize}>{busy ? 'Đang nhận dạng…' : 'Nhận dạng file'}</button>
          <p role="status" className="mt-3 min-h-6 text-center text-sm muted">{busy ? <><span className="status-dot pending mr-2" />Đang chờ kết quả · tối đa {settings?.timeoutSeconds} giây cho yêu cầu Deepgram</> : settings?.hasApiKey ? `Đã có key · ${settings.model} · ngôn ngữ vi` : 'Key được giữ tại máy chạy ứng dụng'}</p>
          {error && <div role="alert" className="error mt-4">{error}</div>}
        </section>
        <section className="card min-h-[410px] p-6 sm:p-7" aria-labelledby="result-title">
          <div className="flex items-start justify-between gap-3"><div><p className="eyebrow muted">02 / KẾT QUẢ</p><h2 id="result-title" className="mt-2 text-xl font-semibold">Văn bản cuối</h2></div>{result && <span className="rounded-full bg-[#e5f3e9] px-3 py-1 text-xs font-semibold text-[#126c59]">Đã hoàn tất</span>}</div>
          {result ? <div aria-live="polite">
            <p className="mt-6 break-all text-sm muted">Kết quả của {result.fileName}</p>
            <p className="mt-4 whitespace-pre-wrap break-words text-2xl leading-relaxed" data-testid="transcript">{result.text || 'Deepgram không trả về lời nói trong file này.'}</p>
            <div className="mt-7 flex flex-wrap gap-2"><button className="button" onClick={download}>Lưu .txt</button><button className="button" onClick={async () => { try { await navigator.clipboard.writeText(result.text); setCopyNote('Đã sao chép.'); } catch { setCopyNote('Không sao chép được. Bạn có thể dùng Lưu .txt.'); } }}>Sao chép</button></div>
            <p role="status" className="mt-2 text-sm muted">{copyNote}</p>
            <dl className="mt-6 grid grid-cols-2 gap-4 border-t border-[#e4e9e2] pt-4 text-sm"><div><dt className="muted">Model</dt><dd className="mt-1 font-semibold">{result.model}</dd></div><div><dt className="muted">Yêu cầu Deepgram</dt><dd className="mt-1 font-semibold">{(result.requestMs / 1000).toFixed(2)} giây</dd></div></dl>
            {error && <p className="mt-4 text-sm muted">Kết quả đã hoàn tất ở trên được giữ lại; yêu cầu mới chưa thành công.</p>}
          </div> : <div className="flex min-h-64 flex-col items-center justify-center text-center muted"><span className="mb-4 flex size-14 items-center justify-center rounded-full bg-[#f1f5ee]"><FileIcon /></span><p className="font-medium">Văn bản sẽ xuất hiện tại đây</p><p className="mt-2 max-w-xs text-sm leading-6">Kết quả hiện sau khi nhận dạng xong. Nếu có lỗi, ứng dụng sẽ báo nguyên nhân để bạn xử lý.</p></div>}
        </section>
      </div>
      <aside className="mt-6 rounded-xl border border-[#dce3db] px-5 py-4 text-sm leading-6 muted">Bản hiện tại nhận dạng một file. Thu âm micro Pi và danh sách nhiều file sẽ được bổ sung ở bước tiếp theo.</aside>
    </> : <section className="card max-w-3xl p-6 sm:p-8" aria-labelledby="settings-title">
      <p className="eyebrow text-[#126c59]">CẤU HÌNH TẠI MÁY</p><h1 id="settings-title" className="mt-2 text-3xl font-semibold">Cài đặt nhận dạng</h1>
      <p className="mt-3 leading-6 muted">Cấu hình được lưu trên {health?.host || 'máy chạy ứng dụng'}. Thay đổi áp dụng cho yêu cầu nhận dạng tiếp theo.</p>
      <form className="mt-7 space-y-6" onSubmit={e => { e.preventDefault(); void save(); }}>
        <div><label htmlFor="api-key" className="mb-2 block font-semibold">Deepgram API key</label><input id="api-key" className="field" type="password" autoComplete="off" spellCheck={false} placeholder={settings?.hasApiKey ? 'Đã có key · để trống để giữ nguyên' : 'Nhập API key của bạn'} value={key} onChange={e => setKey(e.target.value)} disabled={saving || busy} /><p className="mt-2 text-sm leading-6 muted">Key được lưu trong file cấu hình tại máy, chưa mã hóa. Ứng dụng không trả lại key đã lưu cho giao diện. Không gửi key vào chat.</p></div>
        <div className="grid gap-5 sm:grid-cols-2"><div><label htmlFor="model" className="mb-2 block font-semibold">Model</label><select id="model" className="field" value={model} onChange={e => setModel(e.target.value)} disabled={saving || busy}><option value="nova-3">Nova-3</option><option value="nova-2">Nova-2</option></select></div><div><label htmlFor="language" className="mb-2 block font-semibold">Ngôn ngữ</label><input id="language" className="field" value="Tiếng Việt · vi" readOnly /></div></div>
        <div className="max-w-xs"><label htmlFor="timeout" className="mb-2 block font-semibold">Thời gian chờ (giây)</label><input id="timeout" className="field" type="number" min={15} max={180} step={1} value={timeout} onChange={e => setTimeoutValue(Number(e.target.value))} disabled={saving || busy} /></div>
        <div className="flex flex-wrap gap-3"><button className="button primary" disabled={!settings || saving || busy} type="submit">{saving ? 'Đang lưu…' : 'Lưu cấu hình'}</button><button className="button text-[#91342f]" disabled={!settings?.hasApiKey || saving || busy} type="button" onClick={() => void save(true)}>Xóa key đã lưu</button></div>
        {settingsNote && <p role="status" className="text-sm font-medium text-[#126c59]">{settingsNote}</p>}{settingsError && <div role="alert" className="error">{settingsError}</div>}
      </form>
    </section>}
    <footer className="mt-9 flex flex-wrap justify-between gap-3 border-t border-[#dce3db] pt-5 text-xs muted"><span>PBL6 · STT {health?.version || '0.1.0'}</span><span>Một file · chữ cuối · Deepgram tiếng Việt</span></footer>
  </main>;
}
