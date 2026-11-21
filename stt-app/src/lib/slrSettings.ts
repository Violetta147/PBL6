export interface SlrSettings {
  slrBaseUrl: string;
  cameraIndex: number;
  autoSpeak: boolean;
  autoSaveOnRest: boolean;
  showDiagnostics: boolean;
}

export const DEFAULT_SLR_SETTINGS: SlrSettings = {
  slrBaseUrl: '',
  cameraIndex: 0,
  autoSpeak: true,
  autoSaveOnRest: true,
  showDiagnostics: false,
};

const STORAGE_KEY = 'pbl6.slr.settings.v3';

export function normalizeSlrBaseUrl(raw?: string): string {
  const trimmed = (raw ?? '').trim().replace(/\/+$/, '');
  if (!trimmed) {
    return '';
  }
  if (/^https?:\/\//i.test(trimmed)) {
    const withoutScheme = trimmed.replace(/^https?:\/\//i, '');
    return withoutScheme ? trimmed : '';
  }
  if (/^https?:$/i.test(trimmed)) {
    return '';
  }
  const hostPort = trimmed.replace(/^\/+/, '');
  return hostPort ? `http://${hostPort}` : '';
}

export function stripSlrUrlScheme(raw?: string): string {
  return (raw ?? '').trim().replace(/^http:\/\//i, '').replace(/\/+$/, '');
}

export function loadSlrSettings(): SlrSettings {
  if (typeof window === 'undefined') {
    return { ...DEFAULT_SLR_SETTINGS };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_SLR_SETTINGS };
    const parsed = JSON.parse(raw) as Partial<SlrSettings>;
    const cam = Number(parsed.cameraIndex);
    return {
      slrBaseUrl: typeof parsed.slrBaseUrl === 'string' ? normalizeSlrBaseUrl(parsed.slrBaseUrl) : '',
      cameraIndex: Number.isInteger(cam) && cam >= 0 && cam <= 16 ? cam : 0,
      autoSpeak: typeof parsed.autoSpeak === 'boolean' ? parsed.autoSpeak : true,
      autoSaveOnRest:
        typeof parsed.autoSaveOnRest === 'boolean' ? parsed.autoSaveOnRest : true,
      showDiagnostics:
        typeof parsed.showDiagnostics === 'boolean' ? parsed.showDiagnostics : false,
    };
  } catch {
    return { ...DEFAULT_SLR_SETTINGS };
  }
}

export function saveSlrSettings(next: SlrSettings): SlrSettings {
  const sanitized: SlrSettings = {
    slrBaseUrl: normalizeSlrBaseUrl(next.slrBaseUrl),
    cameraIndex:
      Number.isInteger(next.cameraIndex) && next.cameraIndex >= 0 && next.cameraIndex <= 16
        ? next.cameraIndex
        : 0,
    autoSpeak: Boolean(next.autoSpeak),
    autoSaveOnRest: Boolean(next.autoSaveOnRest),
    showDiagnostics: Boolean(next.showDiagnostics),
  };
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sanitized));
    } catch {
      // Ignore storage quota errors on kiosk browsers.
    }
  }
  return sanitized;
}

export function resolveSlrBaseUrl(
  configuredUrl?: string,
  fallbackHost?: string
): string {
  const normalized = normalizeSlrBaseUrl(configuredUrl);
  if (normalized) {
    return normalized;
  }
  const host =
    fallbackHost ??
    (typeof window !== 'undefined' && window.location.hostname
      ? window.location.hostname
      : '127.0.0.1');
  const proto =
    typeof window !== 'undefined' && window.location.protocol === 'https:'
      ? 'https:'
      : 'http:';
  return `${proto}//${host}:8765`;
}

export function toWsUrl(baseUrl: string): string {
  const clean = baseUrl.trim().replace(/\/+$/, '');
  if (clean.startsWith('https://')) {
    return `wss://${clean.slice('https://'.length)}`;
  }
  if (clean.startsWith('http://')) {
    return `ws://${clean.slice('http://'.length)}`;
  }
  if (clean.startsWith('ws://') || clean.startsWith('wss://')) {
    return clean;
  }
  return `ws://${clean}`;
}
