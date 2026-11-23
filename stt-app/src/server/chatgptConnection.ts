import { createHash, createPublicKey, randomBytes, randomUUID, verify, type JsonWebKey } from 'node:crypto';
import { createServer, type Server } from 'node:http';
import { mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { settingsDirectory } from './settings';
import { AppError, errorResponse, jsonResponse } from './errors';
import { boundedBody, requireLocalOrigin } from './http';

const ISSUER = 'https://auth.openai.com';
const RESOURCE = 'https://api.openai.com/v1';
const PLAN_SCOPE = 'chatgpt.tokens.use.direct';
type Account = { id: string; clientId: string; subject: string; email: string; accessToken: string;
  refreshToken: string; idToken: string; expiresAt: number; scopes: string[]; model: string };
type State = { hostId: string; activeId: string | null; source?: 'chatgpt' | 'api' | 'none'; accounts: Account[] };
type Pending = { state: string; nonce: string; verifier: string; redirect: string; account?: Account; server: Server; timer: NodeJS.Timeout; consumed: boolean };
type Claims = { sub: string; email?: string; iss: string; aud: string | string[]; exp: number; nonce?: string };
const failure = (message: string, code = 'chatgpt_connection', status = 409) => new AppError(code, message, status);

function escapeHtml(value: string): string {
  return value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
}

function callbackAppUrl(): string {
  return process.env.PBL6_STT_APP_URL || `http://127.0.0.1:${process.env.PORT || '3100'}/`;
}

function renderCallbackHtml(message: string, ok: boolean): string {
  const appUrl = callbackAppUrl();
  const safeMessage = escapeHtml(message);
  const title = ok ? 'Đã kết nối ChatGPT' : 'Chưa kết nối được ChatGPT';
  const accent = ok ? '#0F766E' : '#B91C1C';
  const autoCloseScript = ok
    ? `setTimeout(function () { try { window.close(); } catch (e) {} if (!window.opener) { setTimeout(function () { window.location.replace(${JSON.stringify(appUrl)}); }, 1400); } }, 450);`
    : '';
  return `<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(title)} — PBL6</title>
</head>
<body style="margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;background:#F5F7F9;color:#18212B;font-family:system-ui,-apple-system,sans-serif;">
  <main style="width:100%;max-width:460px;background:#FFFFFF;border:1px solid #BAC5D0;border-radius:16px;padding:24px;box-sizing:border-box;text-align:center;">
    <h1 style="margin:0 0 12px;font-size:22px;color:${accent};">${escapeHtml(title)}</h1>
    <p style="margin:0 0 20px;font-size:17px;line-height:1.5;">${safeMessage}</p>
    <button id="back-to-app" type="button" style="width:100%;min-height:56px;border:none;border-radius:12px;background:#273D53;color:#FFFFFF;font-size:18px;font-weight:700;cursor:pointer;">Quay lại ứng dụng PBL6</button>
  </main>
  <script>
    function backToApp() {
      try { window.close(); } catch (e) {}
      setTimeout(function () {
        if (!window.closed) window.location.replace(${JSON.stringify(appUrl)});
      }, 150);
    }
    document.getElementById('back-to-app').addEventListener('click', backToApp);
    ${autoCloseScript}
  </script>
</body>
</html>`;
}

export function verifyChatGptIdentity(token: string, clientId: string, nonce: string | undefined, keys: JsonWebKey[], now = Date.now()): Claims {
  try {
    if (token.length > 24000) throw Error();
    const [h, p, s, extra] = token.split('.');
    if (!h || !p || !s || extra) throw Error();
    const header = JSON.parse(Buffer.from(h, 'base64url').toString());
    const claims = JSON.parse(Buffer.from(p, 'base64url').toString());
    const key = keys.find(k => (k as JsonWebKey & { kid?: string }).kid === header.kid && k.kty === 'RSA' && (!k.use || k.use === 'sig'));
    if (header.alg !== 'RS256' || !key || !verify('RSA-SHA256', Buffer.from(`${h}.${p}`), createPublicKey({ key, format: 'jwk' }), Buffer.from(s, 'base64url'))) throw Error();
    if (claims.iss !== ISSUER || !(Array.isArray(claims.aud) ? claims.aud.includes(clientId) : claims.aud === clientId) ||
      typeof claims.exp !== 'number' || claims.exp * 1000 <= now || typeof claims.sub !== 'string' || !claims.sub ||
      (nonce !== undefined && claims.nonce !== nonce)) throw Error();
    return claims;
  } catch { throw failure('Không xác minh được danh tính ChatGPT. Hãy đăng nhập lại.'); }
}

export async function readCompletedResponse(response: Response): Promise<string> {
  if (!response.ok || !response.body) throw failure(`ChatGPT trả lỗi ${response.status}. Bản nháp vẫn được giữ.`, 'chatgpt_upstream', 502);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '', text = '', completed = false, received = 0;
  const event = (block: string) => {
    const payload = block.split('\n').filter(l => l.startsWith('data:')).map(l => l.slice(5).trimStart()).join('\n');
    if (!payload || payload === '[DONE]') return;
    let e;
    try { e = JSON.parse(payload); } catch { throw failure('Phản hồi ChatGPT không hợp lệ.', 'chatgpt_output', 502); }
    if (e.type === 'response.failed' || e.type === 'response.incomplete' || e.type === 'error') {
      throw failure('ChatGPT chưa hoàn tất câu hoặc đã hết hạn mức. Bản nháp vẫn còn; kiểm tra kết nối và hạn mức.', 'chatgpt_incomplete', 502);
    }
    if (e.type === 'response.output_text.delta' && typeof e.delta === 'string') text += e.delta;
    if (text.length > 16000) throw failure('Câu trả về quá dài.', 'chatgpt_output', 502);
    if (e.type === 'response.completed') {
      if (e.response?.status && e.response.status !== 'completed') throw failure('ChatGPT chưa hoàn tất câu.', 'chatgpt_incomplete', 502);
      if (!text) text = (e.response?.output ?? []).flatMap((o: any) => o.content ?? []).filter((c: any) => c.type === 'output_text').map((c: any) => c.text ?? '').join('');
      completed = true;
    }
  };
  try {
    while (!completed) {
      const { value, done } = await reader.read();
      if (done) { buffer += decoder.decode(); if (buffer.trim()) event(buffer); break; }
      received += value.byteLength;
      if (received > 2_000_000) throw failure('Phản hồi ChatGPT quá lớn.', 'chatgpt_output', 502);
      buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n/g, '\n');
      let end;
      while ((end = buffer.indexOf('\n\n')) >= 0) { const block = buffer.slice(0, end); buffer = buffer.slice(end + 2); event(block); if (completed) break; }
    }
    if (!completed || !text.trim() || text.length > 16000) throw failure('Kết nối kết thúc trước khi ChatGPT hoàn tất. Bản nháp vẫn còn.', 'chatgpt_incomplete', 502);
    return text;
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}

export class ChatGptConnection {
  private serial: Promise<unknown> = Promise.resolve();
  private refreshes = new Map<string, Promise<Account>>();
  private requests = new Set<AbortController>();
  private pending?: Pending;
  private notice = '';
  constructor(private directory = settingsDirectory, private transport: typeof fetch = fetch) {}
  private async load(): Promise<State> {
    try { return JSON.parse(await readFile(/* turbopackIgnore: true */ join(this.directory(), 'chatgpt-connections.json'), 'utf8')); }
    catch (e) { if ((e as NodeJS.ErrnoException).code !== 'ENOENT') throw failure('Không đọc được kết nối ChatGPT đã lưu.', 'chatgpt_storage', 503); }
    return { hostId: `urn:uuid:${randomUUID()}`, activeId: null, accounts: [] };
  }
  private async save(state: State) {
    const dir = this.directory(), temp = join(dir, `.chatgpt-${randomUUID()}.tmp`);
    await mkdir(dir, { recursive: true, mode: 0o700 });
    try { await writeFile(temp, JSON.stringify(state), { flag: 'wx', mode: 0o600 }); await rename(temp, join(dir, 'chatgpt-connections.json')); }
    finally { await rm(temp, { force: true }).catch(() => {}); }
  }
  private exclusive<T>(fn: () => Promise<T>): Promise<T> {
    const next = this.serial.then(fn); this.serial = next.catch(() => {}); return next;
  }
  private cancelRequests() { for (const c of this.requests) c.abort(); }
  async status() {
    const s = await this.load();
    return { activeId: s.activeId, source: s.source || 'api', pending: !!this.pending, notice: this.notice,
      accounts: s.accounts.map(a => ({ id: a.id, email: a.email, label: `${a.email || 'Tài khoản ChatGPT'} · ${a.clientId.slice(-6)}`, connected: !!a.accessToken, model: a.model })) };
  }
  async selected() {
    const s = await this.load();
    if (s.source === 'none') throw failure('Hãy kết nối hoặc chọn nguồn tạo câu trong Cài đặt.');
    return s.accounts.find(a => a.id === s.activeId);
  }
  private stopAttempt() { if (this.pending) { clearTimeout(this.pending.timer); this.pending.server.close(); this.pending = undefined; } }
  async start(accountId?: string) {
    return this.exclusive(async () => {
      this.stopAttempt(); this.notice = '';
      const s = await this.load(); await this.save(s);
      const account = accountId ? s.accounts.find(a => a.id === accountId) : undefined;
      if (accountId && !account) throw failure('Không tìm thấy tài khoản đã chọn.');
      const state = randomBytes(32).toString('base64url'), nonce = randomBytes(32).toString('base64url'), verifier = randomBytes(48).toString('base64url');
      const server = createServer((req, res) => { void this.callback(req.url || '', res); });
      await new Promise<void>((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', () => { server.off('error', reject); resolve(); }); });
      const address = server.address(); if (!address || typeof address === 'string') { server.close(); throw failure('Chưa mở được callback đăng nhập.'); }
      const redirect = `http://127.0.0.1:${address.port}/auth/callback`;
      const timer = setTimeout(() => { this.notice = 'Hết thời gian đăng nhập. Bạn có thể kết nối lại.'; this.stopAttempt(); }, 300000); timer.unref(); server.unref();
      this.pending = { state, nonce, verifier, redirect, account, server, timer, consumed: false };
      const url = new URL(`${ISSUER}/api/accounts/authorize`);
      url.search = new URLSearchParams({ client_id: account?.clientId || 'dynamic_agent_client', ext_agent_host_id: s.hostId,
        response_type: 'code', redirect_uri: redirect, scope: `openid profile email offline_access resource.invoke ${PLAN_SCOPE}`,
        resource: RESOURCE, state, nonce, code_challenge_method: 'S256', code_challenge: createHash('sha256').update(verifier).digest('base64url'),
        ...(account ? { ...(account.idToken ? { id_token_hint: account.idToken } : {}), ...(account.email ? { login_hint: account.email } : {}) } : { agent_name_hint: 'PBL6' }),
      }).toString();
      return { url: url.toString(), expiresIn: 300 };
    });
  }
  private async token(form: Record<string, string>) {
    const response = await this.transport(`${ISSUER}/api/accounts/oauth/token`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(form), signal: AbortSignal.timeout(20000) });
    if (!response.ok) throw failure('Không làm mới được kết nối ChatGPT. Hãy đăng nhập lại.', 'chatgpt_auth', 401);
    const t = await response.json();
    if (typeof t.access_token !== 'string' || !t.access_token || typeof t.expires_in !== 'number' || t.expires_in <= 0 || String(t.token_type).toLowerCase() !== 'bearer') throw failure('Thông tin kết nối ChatGPT không hợp lệ.');
    return t;
  }
  private async identity(token: string, clientId: string, nonce?: string) {
    const response = await this.transport(`${ISSUER}/.well-known/jwks.json`, { signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw failure('Chưa tải được khóa xác minh ChatGPT.');
    const data = await response.json();
    if (!Array.isArray(data.keys)) throw failure('Khóa xác minh ChatGPT không hợp lệ.');
    return verifyChatGptIdentity(token, clientId, nonce, data.keys);
  }
  private async callback(raw: string, res: import('node:http').ServerResponse) {
    const url = new URL(raw, 'http://127.0.0.1'); const p = this.pending;
    res.setHeader('Content-Type', 'text/html; charset=utf-8'); res.setHeader('Cache-Control', 'no-store');
    if (url.pathname !== '/auth/callback' || !p || p.consumed || url.searchParams.get('state') !== p.state) {
      res.statusCode = 400;
      res.end(renderCallbackHtml('Yêu cầu đăng nhập không hợp lệ.', false));
      return;
    }
    p.consumed = true;
    try {
      if (url.searchParams.has('error')) throw failure('Đăng nhập đã bị hủy hoặc chưa cấp quyền dùng ChatGPT.');
      const clientId = url.searchParams.get('client_id') || p.account?.clientId;
      const code = url.searchParams.get('code');
      if (!clientId || clientId === 'dynamic_agent_client' || (p.account && clientId !== p.account.clientId) || !code) throw failure('Đăng ký ChatGPT chưa hoàn tất.');
      const t = await this.token({ grant_type: 'authorization_code', client_id: clientId, code, code_verifier: p.verifier, redirect_uri: p.redirect, resource: RESOURCE });
      if (typeof t.id_token !== 'string') throw failure('Thiếu thông tin xác minh tài khoản.');
      const claims = await this.identity(t.id_token, clientId, p.nonce);
      if (p.account && claims.sub !== p.account.subject) throw failure('Danh tính không khớp tài khoản đã chọn.');
      const scopes = String(t.scope || '').split(/\s+/);
      if (!scopes.includes(PLAN_SCOPE)) throw failure('Chưa cấp quyền dùng gói ChatGPT. Hãy kết nối lại và cấp quyền.');
      await this.exclusive(async () => {
        if (this.pending !== p) throw failure('Lượt đăng nhập đã bị hủy hoặc thay thế.');
        const s = await this.load();
        const existing = s.accounts.find(a => a.clientId === clientId && a.subject === claims.sub);
        const a: Account = { id: existing?.id || randomUUID(), clientId, subject: claims.sub, email: typeof claims.email === 'string' ? claims.email : '',
          accessToken: t.access_token, refreshToken: t.refresh_token || '', idToken: t.id_token, expiresAt: Date.now() + t.expires_in * 1000, scopes, model: existing?.model || '' };
        s.accounts = [...s.accounts.filter(x => x.id !== a.id), a]; s.activeId = a.id; s.source = 'chatgpt'; this.cancelRequests(); await this.save(s);
      });
      this.notice = 'Đã kết nối ChatGPT. Quay lại PBL6 để chọn model.';
      res.end(renderCallbackHtml('Đã kết nối ChatGPT với PBL6. Cửa sổ này sẽ tự đóng để bạn chọn model.', true));
    } catch (e) { this.notice = e instanceof AppError ? e.message : 'Chưa kết nối được ChatGPT. Hãy thử lại.'; res.statusCode = 400; res.end(renderCallbackHtml(this.notice, false)); }
    finally { if (this.pending === p) this.stopAttempt(); }
  }
  private async access(id: string): Promise<Account> {
    const s = await this.load(), a = s.accounts.find(x => x.id === id);
    if (!a?.accessToken || !a.scopes.includes(PLAN_SCOPE)) throw failure('Hãy kết nối lại tài khoản ChatGPT đã chọn.', 'chatgpt_auth', 401);
    if (a.expiresAt > Date.now() + 60000) return a;
    const existing = this.refreshes.get(id); if (existing) return existing;
    const operation = (async () => {
      if (!a.refreshToken) throw failure('Hãy đăng nhập lại ChatGPT.', 'chatgpt_auth', 401);
      const t = await this.token({ grant_type: 'refresh_token', client_id: a.clientId, refresh_token: a.refreshToken, resource: RESOURCE });
      if (t.id_token && (await this.identity(t.id_token, a.clientId)).sub !== a.subject) throw failure('Danh tính làm mới không khớp.');
      return this.exclusive(async () => {
        const current = await this.load(), saved = current.accounts.find(x => x.id === id);
        if (!saved?.accessToken || saved.refreshToken !== a.refreshToken) throw failure('Kết nối đã thay đổi. Hãy thử lại.');
        const updated = { ...saved, accessToken: t.access_token, refreshToken: t.refresh_token || saved.refreshToken,
          idToken: t.id_token || saved.idToken, scopes: t.scope ? String(t.scope).split(/\s+/) : saved.scopes, expiresAt: Date.now() + t.expires_in * 1000 };
        if (!updated.scopes.includes(PLAN_SCOPE)) throw failure('Quyền dùng gói ChatGPT đã bị thu hồi.', 'chatgpt_auth', 401);
        current.accounts = current.accounts.map(x => x.id === id ? updated : x); await this.save(current); return updated;
      });
    })();
    this.refreshes.set(id, operation);
    try { return await operation; } finally { this.refreshes.delete(id); }
  }
  async models(id: string): Promise<{ id: string; name: string }[]> {
    const a = await this.access(id);
    const r = await this.transport(`${RESOURCE}/models`, { headers: { Authorization: `Bearer ${a.accessToken}` }, signal: AbortSignal.timeout(20000) });
    if (!r.ok) throw failure('Không tải được model của tài khoản. Hãy kiểm tra kết nối ChatGPT.', 'chatgpt_models', 502);
    const data = await r.json();
    if (!Array.isArray(data.models)) throw failure('Danh mục model ChatGPT chưa hợp lệ.', 'chatgpt_models', 502);
    return data.models.filter((m: any) => m.visibility === 'list' && typeof m.slug === 'string').map((m: any) => ({ id: m.slug as string, name: String(m.display_name || m.slug) }));
  }
  async select(id: string | null, model?: string) {
    if (id && model !== undefined && !(await this.models(id)).some(m => m.id === model)) throw failure('Model không có trong danh mục của tài khoản này.');
    await this.exclusive(async () => {
      const s = await this.load(); const a = s.accounts.find(x => x.id === id);
      if (id && !a?.accessToken) throw failure('Tài khoản chưa được kết nối.');
      if (a && model !== undefined) a.model = model;
      s.activeId = id; s.source = id ? 'chatgpt' : 'api'; this.cancelRequests(); await this.save(s);
    });
    return this.status();
  }
  async disconnect(id: string) {
    this.cancelRequests();
    await this.exclusive(async () => {
      const s = await this.load(), a = s.accounts.find(x => x.id === id); if (!a) throw failure('Không tìm thấy tài khoản.');
      let revoked = !a.refreshToken;
      if (a.refreshToken) {
        try { const r = await this.transport(`${ISSUER}/api/accounts/oauth/revoke`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ token: a.refreshToken, token_type_hint: 'refresh_token', client_id: a.clientId }), signal: AbortSignal.timeout(12000) }); revoked = r.ok; } catch {}
      }
      a.accessToken = ''; a.refreshToken = ''; a.idToken = ''; a.expiresAt = 0;
      if (s.activeId === id) { s.activeId = null; s.source = 'none'; }
      await this.save(s); this.notice = revoked ? 'Đã ngắt kết nối.' : 'Đã xóa token trên Pi. Chưa xác nhận thu hồi từ OpenAI; bạn có thể ngắt app trong ChatGPT Settings.';
    });
    return this.status();
  }
  async generate(instructions: string, input: string, signal?: AbortSignal) {
    const selected = await this.selected(); if (!selected?.model) throw failure('Hãy chọn model ChatGPT trong Cài đặt.');
    const controller = new AbortController(); this.requests.add(controller);
    try {
      const a = await this.access(selected.id);
      const r = await this.transport(`${RESOURCE}/responses`, { method: 'POST', headers: { Authorization: `Bearer ${a.accessToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: selected.model, instructions, input: [{ role: 'user', content: input }], store: false, stream: true }),
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(90000), ...(signal ? [signal] : [])]) });
      const text = await readCompletedResponse(r);
      const current = await this.selected();
      if (controller.signal.aborted || current?.id !== selected.id || current.model !== selected.model) throw failure('Kết nối/model đã thay đổi. Hãy tạo lại câu từ bản nháp.');
      return { text, model: selected.model };
    } finally { this.requests.delete(controller); }
  }
  cancelLogin() { this.stopAttempt(); this.notice = 'Đã hủy đăng nhập.'; }
}

const root = globalThis as typeof globalThis & { pbl6ChatGpt?: ChatGptConnection };
export const chatgpt = root.pbl6ChatGpt ||= new ChatGptConnection();

function localControl(request: Request) {
  requireLocalOrigin(request, true);
}
export async function chatGptGet(request: Request) {
  try {
    requireLocalOrigin(request);
    const id = new URL(request.url).searchParams.get('models');
    return jsonResponse(id ? { models: await chatgpt.models(id) } : await chatgpt.status());
  } catch (e) { return errorResponse(e); }
}
export async function chatGptPost(request: Request) {
  try {
    localControl(request);
    const body = JSON.parse(new TextDecoder().decode(await boundedBody(request, 8192)));
    if (body.action === 'start') return jsonResponse(await chatgpt.start(typeof body.id === 'string' ? body.id : undefined));
    if (body.action === 'cancel') { chatgpt.cancelLogin(); return jsonResponse(await chatgpt.status()); }
    if (body.action === 'select' && typeof body.id === 'string') return jsonResponse(await chatgpt.select(body.id, typeof body.model === 'string' ? body.model : undefined));
    if (body.action === 'use-api') return jsonResponse(await chatgpt.select(null));
    if (body.action === 'disconnect' && typeof body.id === 'string') return jsonResponse(await chatgpt.disconnect(body.id));
    throw failure('Thao tác kết nối không hợp lệ.');
  } catch (e) { return errorResponse(e); }
}
