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
  autoSaveOnRest: false,
  showDiagnostics: false,
};

const STORAGE_KEY = 'pbl6.slr.settings.v2';

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
      slrBaseUrl: typeof parsed.slrBaseUrl === 'string' ? parsed.slrBaseUrl.trim() : '',
      cameraIndex: Number.isInteger(cam) && cam >= 0 && cam <= 16 ? cam : 0,
      autoSpeak: typeof parsed.autoSpeak === 'boolean' ? parsed.autoSpeak : true,
      autoSaveOnRest:
        typeof parsed.autoSaveOnRest === 'boolean' ? parsed.autoSaveOnRest : false,
      showDiagnostics:
        typeof parsed.showDiagnostics === 'boolean' ? parsed.showDiagnostics : false,
    };
  } catch {
    return { ...DEFAULT_SLR_SETTINGS };
  }
}

export function saveSlrSettings(next: SlrSettings): SlrSettings {
  const sanitized: SlrSettings = {
    slrBaseUrl: next.slrBaseUrl.trim().replace(/\/+$/, ''),
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
  const trimmed = (configuredUrl ?? '').trim().replace(/\/+$/, '');
  if (trimmed) {
    return trimmed;
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
