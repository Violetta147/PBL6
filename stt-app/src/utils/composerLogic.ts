import type { MessageSource } from '../contracts';

/**
 * Inserts a speech transcript into an existing draft at the specified cursor position,
 * handling appropriate spacing between words.
 */
export function insertTranscript(
  draft: string,
  transcript: string,
  cursorPosition?: number | null
): { newDraft: string; newCursor: number } {
  const cleanTranscript = transcript.trim();
  if (!cleanTranscript) {
    const pos = cursorPosition ?? draft.length;
    return { newDraft: draft, newCursor: Math.min(pos, draft.length) };
  }

  const pos = Math.max(0, Math.min(cursorPosition ?? draft.length, draft.length));
  const before = draft.slice(0, pos);
  const after = draft.slice(pos);

  // Spacing before transcript
  let sepBefore = '';
  if (
    before.length > 0 &&
    !/\s$/.test(before) &&
    !/^\s/.test(cleanTranscript) &&
    !/^[.,!?;:]/.test(cleanTranscript)
  ) {
    sepBefore = ' ';
  }

  // Spacing after transcript
  let sepAfter = '';
  if (after.length > 0 && !/^\s/.test(after) && !/\s$/.test(cleanTranscript)) {
    // If after starts with punctuation like '.', ',', '!', '?', do not insert space
    if (!/^[.,!?;:]/.test(after)) {
      sepAfter = ' ';
    }
  }

  const inserted = before + sepBefore + cleanTranscript + sepAfter;
  const newDraft = inserted + after;
  const newCursor = inserted.length;

  return { newDraft, newCursor };
}

/**
 * Determines whether the Send ("Gửi") button should be enabled and its visual latch state.
 *
 * Rules:
 * - When idle:
 *     - If draft is empty/whitespace: DISABLED.
 *     - If draft has non-whitespace: ENABLED.
 * - When recording or transcribing:
 *     - If already latched to send: DISABLED (locked).
 *     - If not latched: ENABLED (even if draft is empty!).
 * - When sending in progress: DISABLED.
 */
export function determineSendButtonState(params: {
  draft: string;
  recordingStatus: 'idle' | 'recording' | 'transcribing';
  isLatchedToSend: boolean;
  isSending: boolean;
}): {
  canClick: boolean;
  isDimmed: boolean;
} {
  const { draft, recordingStatus, isLatchedToSend, isSending } = params;

  if (isSending || isLatchedToSend) {
    return { canClick: false, isDimmed: true };
  }

  if (recordingStatus === 'recording' || recordingStatus === 'transcribing') {
    // Smart latch: clickable even if draft is empty!
    return { canClick: true, isDimmed: false };
  }

  // Idle state: enabled only if non-whitespace draft exists
  const hasText = draft.trim().length > 0;
  return {
    canClick: hasText,
    isDimmed: !hasText,
  };
}

/**
 * Calculates the sources array based on user interactions.
 */
export function calculateSources(params: {
  hasTyped: boolean;
  hasVoice: boolean;
}): MessageSource[] {
  const sources: MessageSource[] = [];
  if (params.hasTyped) sources.push('keyboard');
  if (params.hasVoice) sources.push('voice');
  return sources.length > 0 ? sources : ['keyboard'];
}

/**
 * Normalizes and validates conversation title for inline renaming.
 * Reverts to current title if new title is empty/whitespace.
 * Truncates at max 72 characters.
 */
export function validateTitle(newTitle: string, currentTitle: string): { title: string; changed: boolean } {
  const trimmed = newTitle.replace(/\s+/g, ' ').trim().slice(0, 72);
  if (!trimmed) {
    return { title: currentTitle, changed: false };
  }
  return { title: trimmed, changed: trimmed !== currentTitle };
}
