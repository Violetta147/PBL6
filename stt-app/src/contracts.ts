export const MAX_AUDIO_BYTES = 20 * 1024 * 1024;
export const MODELS = ['nova-3', 'nova-2'] as const;
export type Model = typeof MODELS[number];
export type PublicSettings = {
  provider: 'deepgram';
  language: 'vi';
  model: Model;
  timeoutSeconds: number;
  hasApiKey: boolean;
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
};
export type ApiError = { error: { code: string; message: string } };
