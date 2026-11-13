export const MAX_AUDIO_BYTES = 20 * 1024 * 1024;
export const MODELS = ['nova-3', 'nova-2'] as const;
export type Model = (typeof MODELS)[number];

export const MESSAGE_SOURCES = ['voice', 'keyboard', 'sign', 'external'] as const;
export type MessageSource = (typeof MESSAGE_SOURCES)[number];

export type Conversation = {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
};

export type Message = {
  id: string;
  conversationId: string;
  text: string;
  createdAt: string;
  sources: MessageSource[];
};

export type AudioDevice = {
  id: string;
  name: string;
  isDefault: boolean;
};

export type RecorderState = {
  status: 'idle' | 'recording' | 'transcribing' | 'error';
  durationMs: number;
  selectedDeviceId?: string;
  error?: string;
};

export type PublicSettings = {
  provider: 'deepgram';
  language: 'vi';
  model: Model;
  timeoutSeconds: number;
  hasApiKey: boolean;
  selectedMicrophoneId?: string;
  maxRecordSeconds: number;
};

export type SettingsInput = {
  apiKey?: string;
  clearApiKey?: boolean;
  model?: Model;
  timeoutSeconds?: number;
  selectedMicrophoneId?: string;
  maxRecordSeconds?: number;
};

export type Transcript = {
  sessionId: string;
  fileName: string;
  text: string;
  status: 'completed' | 'completed_empty';
  provider: 'deepgram';
  language: 'vi';
  model: Model;
  requestId: string | null;
  audioSeconds: number | null;
  requestMs: number;
  partial?: boolean;
};

export type ApiError = { error: { code: string; message: string } };
