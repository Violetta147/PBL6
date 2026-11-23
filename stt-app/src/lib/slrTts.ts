export interface SpeakOutputOptions {
  glossIds?: number[];
  labels?: string[];
  sentence?: string | null;
  slrBaseUrl: string;
}

interface QueueItem {
  url: string;
  label: string;
}

const audioQueue: QueueItem[] = [];
let activeAudio: HTMLAudioElement | null = null;
let isPlaying = false;
let activeStatusCb: ((status: string) => void) | undefined;

function notify(status: string): void {
  if (activeStatusCb) {
    try {
      activeStatusCb(status);
    } catch {
      // Ignore UI callback failures.
    }
  }
}

function playNext(): void {
  if (typeof window === 'undefined' || typeof Audio === 'undefined') {
    audioQueue.length = 0;
    isPlaying = false;
    return;
  }

  const next = audioQueue.shift();
  if (!next) {
    isPlaying = false;
    activeAudio = null;
    notify('');
    return;
  }

  isPlaying = true;
  notify(`Đang phát loa: "${next.label}"`);

  const audio = new Audio(next.url);
  activeAudio = audio;

  const advance = () => {
    if (activeAudio === audio) {
      activeAudio = null;
      playNext();
    }
  };

  audio.addEventListener('ended', advance, { once: true });
  audio.addEventListener('error', advance, { once: true });

  void audio.play().catch(() => {
    // Browser autoplay policy may block until first user gesture; fail gracefully.
    advance();
  });
}

export function stopSpeech(): void {
  if (typeof window !== 'undefined') window.speechSynthesis?.cancel();
  audioQueue.length = 0;
  if (activeAudio) {
    try {
      activeAudio.pause();
      activeAudio.src = '';
    } catch {
      // Ignore cleanup failures.
    }
    activeAudio = null;
  }
  isPlaying = false;
  notify('');
}

/** Read only a user-confirmed sentence; never read an AI draft automatically. */
export function speakSentence(sentence: string, onStatus?: (status: string) => void): void {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    onStatus?.('Thiết bị chưa hỗ trợ đọc câu.'); return;
  }
  stopSpeech();
  const utterance = new SpeechSynthesisUtterance(sentence);
  utterance.lang = 'vi-VN';
  const voice = window.speechSynthesis.getVoices().find(v => v.lang.toLowerCase().startsWith('vi'));
  if (voice) utterance.voice = voice;
  utterance.onstart = () => onStatus?.('Đang đọc câu đã gửi…');
  utterance.onend = () => onStatus?.('');
  utterance.onerror = () => onStatus?.('Không đọc được câu trên thiết bị này.');
  window.speechSynthesis.speak(utterance);
}

/**
 * Unified output voice entry point.
 * Step 4 plays sequential offline MP3 clips for clear VSL400 gloss IDs.
 * Step 6 (M3) will plug full-sentence Vietnamese TTS into the `sentence` branch.
 */
export function speakOutput(
  options: SpeakOutputOptions,
  onStatus?: (status: string) => void
): void {
  if (onStatus) {
    activeStatusCb = onStatus;
  }

  const base = options.slrBaseUrl.trim().replace(/\/+$/, '');
  const ids = options.glossIds ?? [];
  const labels = options.labels ?? [];

  // Future Step 6 M3 hook: if a full Vietnamese sentence engine is wired, handle `options.sentence` here.
  if (ids.length === 0) {
    return;
  }

  for (let i = 0; i < ids.length; i += 1) {
    const id = ids[i];
    if (!Number.isInteger(id) || id < 0 || id >= 400) continue;
    const label = labels[i] ?? `#${id}`;
    audioQueue.push({
      url: `${base}/api/tts/${id}.mp3`,
      label,
    });
  }

  if (!isPlaying) {
    playNext();
  }
}
