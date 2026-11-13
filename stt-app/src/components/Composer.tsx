'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import type { MessageSource, Transcript, RecorderState, ApiError } from '../contracts';
import {
  insertTranscript,
  determineSendButtonState,
  calculateSources,
  getEffectiveMaxRecordSeconds,
} from '../utils/composerLogic';
import { WebAudioRecorder } from '../utils/audioRecorder';
import { MicIcon, SquareIcon, SpinnerIcon } from './Icons';

interface ComposerProps {
  onSendMessage: (text: string, sources: MessageSource[]) => Promise<boolean>;
  disabled?: boolean;
  draft?: string;
  onDraftChange?: (val: string) => void;
  cancelSignal?: number;
  onRecordingStateChange?: (status: 'idle' | 'recording' | 'transcribing') => void;
  selectedMicrophoneId?: string;
  maxRecordSeconds?: number;
}

export function Composer({
  onSendMessage,
  disabled = false,
  draft: draftProp,
  onDraftChange,
  cancelSignal,
  onRecordingStateChange,
  selectedMicrophoneId,
  maxRecordSeconds = 120,
}: ComposerProps) {
  const [draft, setDraft] = useState(draftProp ?? '');
  const [hasTyped, setHasTyped] = useState(false);
  const [hasVoice, setHasVoice] = useState(false);

  const [recordingStatus, setRecordingStatus] = useState<
    'idle' | 'recording' | 'transcribing'
  >('idle');
  const [isLatchedToSend, setIsLatchedToSend] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Refs for tracking mutable latest state avoiding stale closures during async operations
  const draftRef = useRef(draftProp ?? '');
  const hasTypedRef = useRef(false);
  const hasVoiceRef = useRef(false);
  const isLatchedRef = useRef(false);
  const isSendingRef = useRef(false);
  const recordingStatusRef = useRef<'idle' | 'recording' | 'transcribing'>('idle');
  const cancelEpochRef = useRef(0);
  const isStoppingRef = useRef(false);
  const maxRecordSecondsRef = useRef(maxRecordSeconds);
  const autoStopTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lastSelectionRef = useRef<number | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const webRecorderRef = useRef<WebAudioRecorder | null>(null);

  useEffect(() => {
    maxRecordSecondsRef.current = maxRecordSeconds;
  }, [maxRecordSeconds]);

  // Sync with draftProp from parent
  useEffect(() => {
    if (draftProp !== undefined) {
      setDraft(draftProp);
      draftRef.current = draftProp;
      if (draftProp === '') {
        setHasTyped(false);
        setHasVoice(false);
        hasTypedRef.current = false;
        hasVoiceRef.current = false;
        lastSelectionRef.current = null;
      }
    }
  }, [draftProp]);

  // Sync refs with state
  useEffect(() => {
    draftRef.current = draft;
  }, [draft]);

  useEffect(() => {
    hasTypedRef.current = hasTyped;
  }, [hasTyped]);

  useEffect(() => {
    hasVoiceRef.current = hasVoice;
  }, [hasVoice]);

  useEffect(() => {
    isLatchedRef.current = isLatchedToSend;
  }, [isLatchedToSend]);

  useEffect(() => {
    isSendingRef.current = isSending;
  }, [isSending]);

  useEffect(() => {
    recordingStatusRef.current = recordingStatus;
    onRecordingStateChange?.(recordingStatus);
  }, [recordingStatus, onRecordingStateChange]);

  const clearPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const clearAutoStopTimeout = useCallback(() => {
    if (autoStopTimeoutRef.current) {
      clearTimeout(autoStopTimeoutRef.current);
      autoStopTimeoutRef.current = null;
    }
  }, []);

  // Helper to ensure the line containing the cursor remains in view
  const scrollCursorIntoView = useCallback((textarea: HTMLTextAreaElement, cursorPos: number) => {
    try {
      const textBefore = textarea.value.slice(0, cursorPos);
      const lines = textBefore.split('\n');
      const lineIndex = lines.length - 1;
      const estimatedLineHeight = 32; // ~21px text with leading-relaxed
      const targetTop = lineIndex * estimatedLineHeight;
      const currentScroll = textarea.scrollTop;
      const clientHeight = textarea.clientHeight;
      if (targetTop < currentScroll) {
        textarea.scrollTop = targetTop;
      } else if (targetTop + estimatedLineHeight > currentScroll + clientHeight) {
        textarea.scrollTop = targetTop + estimatedLineHeight - clientHeight;
      }
    } catch {
      // Ignore if element is unmounted or detached
    }
  }, []);

  // Record caret position when user interacts with textarea
  const updateCaret = useCallback(() => {
    if (textareaRef.current) {
      const pos = textareaRef.current.selectionStart;
      lastSelectionRef.current = pos;
      scrollCursorIntoView(textareaRef.current, pos);
    }
  }, [scrollCursorIntoView]);

  // Clean up polling timer, auto-stop timer, and cancel hardware recorder on unmount
  useEffect(() => {
    return () => {
      clearPolling();
      clearAutoStopTimeout();
      if (webRecorderRef.current?.recording) {
        webRecorderRef.current.cancelRecording();
      }
      if (recordingStatusRef.current !== 'idle') {
        void fetch('/api/record/cancel', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }).catch(() => {});
      }
    };
  }, [clearPolling, clearAutoStopTimeout]);

  // Cancel recording on external cancelSignal
  useEffect(() => {
    if (cancelSignal && cancelSignal > 0) {
      cancelEpochRef.current++;
      clearPolling();
      clearAutoStopTimeout();
      isStoppingRef.current = false;
      if (webRecorderRef.current?.recording) {
        webRecorderRef.current.cancelRecording();
      }
      if (recordingStatusRef.current !== 'idle') {
        void fetch('/api/record/cancel', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }).catch(() => {});
      }
      setRecordingStatus('idle');
      recordingStatusRef.current = 'idle';
      setIsLatchedToSend(false);
      isLatchedRef.current = false;
      setIsSending(false);
      isSendingRef.current = false;
      setErrorMessage('');
    }
  }, [cancelSignal, clearPolling, clearAutoStopTimeout]);

  function handleTextChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const val = e.target.value;
    setDraft(val);
    draftRef.current = val;
    onDraftChange?.(val);
    setHasTyped(true);
    hasTypedRef.current = true;
    updateCaret();
    // Clear error message when user types per spec
    if (errorMessage) {
      setErrorMessage('');
    }
  }

  // Triggered when user initiates send
  const performSend = useCallback(
    async (textToSend: string, typed: boolean, voice: boolean) => {
      if (isSendingRef.current) return;

      const trimmed = textToSend.trim();
      if (!trimmed) {
        setIsSending(false);
        isSendingRef.current = false;
        setIsLatchedToSend(false);
        isLatchedRef.current = false;
        return;
      }

      setIsSending(true);
      isSendingRef.current = true;
      if (errorMessage) {
        setErrorMessage('');
      }

      const sources = calculateSources({ hasTyped: typed, hasVoice: voice });
      try {
        const success = await onSendMessage(trimmed, sources);
        if (success) {
          setDraft('');
          draftRef.current = '';
          onDraftChange?.('');
          setHasTyped(false);
          hasTypedRef.current = false;
          setHasVoice(false);
          hasVoiceRef.current = false;
          setErrorMessage('');
          lastSelectionRef.current = null;
        } else {
          // Send failed: preserve draft and show error notice
          setErrorMessage('Không gửi được. Hãy thử lại.');
        }
      } catch {
        setErrorMessage('Không gửi được. Hãy thử lại.');
      } finally {
        setIsSending(false);
        isSendingRef.current = false;
        setIsLatchedToSend(false);
        isLatchedRef.current = false;
      }
    },
    [errorMessage, onSendMessage, onDraftChange]
  );

  // Handle final transcript from recording
  const handleTranscriptResult = useCallback(
    async (transcript: Transcript) => {
      setRecordingStatus('idle');
      recordingStatusRef.current = 'idle';

      const shouldSend = isLatchedRef.current;

      if (transcript.status === 'completed' && transcript.text.trim()) {
        // Read latest draftRef to avoid discarding user edits typed during transcription
        const currentDraft = draftRef.current;
        const currentPos = lastSelectionRef.current ?? currentDraft.length;
        const { newDraft, newCursor } = insertTranscript(
          currentDraft,
          transcript.text,
          currentPos
        );

        draftRef.current = newDraft;
        lastSelectionRef.current = newCursor;
        setHasVoice(true);
        hasVoiceRef.current = true;

        if (shouldSend) {
          // Smart latch: send the combined text immediately
          setIsLatchedToSend(false);
          isLatchedRef.current = false;
          await performSend(newDraft, hasTypedRef.current, true);
        } else {
          setDraft(newDraft);
          onDraftChange?.(newDraft);
          // Restore caret position and keep line visible
          setTimeout(() => {
            if (textareaRef.current) {
              textareaRef.current.setSelectionRange(newCursor, newCursor);
              scrollCursorIntoView(textareaRef.current, newCursor);
            }
          }, 0);
        }
      } else {
        // completed_empty: cancel pending send, keep draft intact
        setIsLatchedToSend(false);
        isLatchedRef.current = false;
      }
    },
    [performSend, scrollCursorIntoView, onDraftChange]
  );

  // Stop recording and retrieve transcript
  const stopRecording = useCallback(async () => {
    if (isStoppingRef.current || recordingStatusRef.current === 'idle') {
      return;
    }
    isStoppingRef.current = true;
    const currentEpoch = cancelEpochRef.current;
    clearPolling();
    clearAutoStopTimeout();
    setRecordingStatus('transcribing');
    recordingStatusRef.current = 'transcribing';

    try {
      // If Web Audio recorder is active on client
      if (webRecorderRef.current?.recording) {
        const { blob, hasAudio } = webRecorderRef.current.stopRecording();
        if (!hasAudio) {
          setRecordingStatus('idle');
          recordingStatusRef.current = 'idle';
          setIsLatchedToSend(false);
          isLatchedRef.current = false;
          return;
        }
        try {
          const formData = new FormData();
          formData.append('audio', blob, 'recording.wav');
          const response = await fetch('/api/record/stop', {
            method: 'POST',
            body: formData,
          });

          if (currentEpoch !== cancelEpochRef.current) return;
          if (!response.ok) {
            const errData: ApiError = await response.json();
            throw new Error(errData.error?.message || 'Lỗi nhận dạng âm thanh.');
          }

          const data = await response.json();
          if (currentEpoch !== cancelEpochRef.current) return;
          await handleTranscriptResult({
            sessionId: 'web-session',
            fileName: 'recording.wav',
            text: data.transcript || '',
            status: (data.transcript || '').trim() ? 'completed' : 'completed_empty',
            provider: 'deepgram',
            language: 'vi',
            model: 'nova-3',
            requestId: null,
            audioSeconds: (data.durationMs || 0) / 1000,
            requestMs: 0,
          });
        } catch (err: unknown) {
          if (currentEpoch !== cancelEpochRef.current) return;
          setRecordingStatus('idle');
          recordingStatusRef.current = 'idle';
          setIsLatchedToSend(false);
          isLatchedRef.current = false;
          const msg =
            err instanceof Error
              ? err.message
              : 'Không nhận dạng được âm thanh. Hãy thử lại.';
          setErrorMessage(msg);
        }
        return;
      }

      try {
        const response = await fetch('/api/record/stop', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });

        if (currentEpoch !== cancelEpochRef.current) {
          return; // Discard late response
        }

        if (!response.ok) {
          const errData: ApiError = await response.json();
          throw new Error(errData.error?.message || 'Lỗi nhận dạng âm thanh.');
        }

        const transcript: Transcript = await response.json();
        if (currentEpoch !== cancelEpochRef.current) {
          return; // Discard late response
        }
        await handleTranscriptResult(transcript);
      } catch (err: unknown) {
        if (currentEpoch !== cancelEpochRef.current) return;
        setRecordingStatus('idle');
        recordingStatusRef.current = 'idle';
        setIsLatchedToSend(false);
        isLatchedRef.current = false;
        const msg =
          err instanceof Error
            ? err.message
            : 'Không nhận dạng được âm thanh. Hãy thử lại.';
        setErrorMessage(msg);
      }
    } finally {
      isStoppingRef.current = false;
    }
  }, [clearPolling, clearAutoStopTimeout, handleTranscriptResult]);

  // Cancel recording via /api/record/cancel
  const cancelRecording = useCallback(async () => {
    clearPolling();
    clearAutoStopTimeout();
    isStoppingRef.current = false;
    if (webRecorderRef.current?.recording) {
      webRecorderRef.current.cancelRecording();
    }
    setRecordingStatus('idle');
    recordingStatusRef.current = 'idle';
    setIsLatchedToSend(false);
    isLatchedRef.current = false;
    try {
      await fetch('/api/record/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
    } catch {
      // Ignore cancellation failures
    }
  }, [clearPolling, clearAutoStopTimeout]);

  // Start recording
  async function startRecording() {
    // Clear error message when user taps mic per spec
    setErrorMessage('');
    updateCaret();
    isStoppingRef.current = false;
    clearAutoStopTimeout();

    const durationSec = getEffectiveMaxRecordSeconds(maxRecordSecondsRef.current);

    const scheduleAutoStop = () => {
      clearAutoStopTimeout();
      autoStopTimeoutRef.current = setTimeout(() => {
        // Auto-stopped due to reaching max duration
        // Per spec: "Tự dừng vì hết giờ không tạo yêu cầu Gửi."
        setIsLatchedToSend(false);
        isLatchedRef.current = false;
        void stopRecording();
      }, durationSec * 1000);
    };

    const hasMedia =
      typeof navigator !== 'undefined' &&
      Boolean(navigator.mediaDevices?.getUserMedia);

    if (hasMedia) {
      try {
        if (!webRecorderRef.current) {
          webRecorderRef.current = new WebAudioRecorder();
        }
        await webRecorderRef.current.startRecording(selectedMicrophoneId, () => {
          clearAutoStopTimeout();
          setErrorMessage('Mic bị ngắt kết nối. Đang nhận dạng phần đã thu.');
          setIsLatchedToSend(false);
          isLatchedRef.current = false;
          void stopRecording();
        });
        setRecordingStatus('recording');
        recordingStatusRef.current = 'recording';
        scheduleAutoStop();
        return;
      } catch {
        setErrorMessage('Không tìm thấy mic. Hãy kết nối mic rồi thử lại.');
        return;
      }
    }

    try {
      const response = await fetch('/api/record/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deviceId: selectedMicrophoneId,
          maxDurationSeconds: durationSec,
        }),
      });

      if (!response.ok) {
        const errData: ApiError = await response.json();
        if (errData.error?.code === 'no_microphone') {
          setErrorMessage('Không tìm thấy mic. Hãy kết nối mic rồi thử lại.');
        } else {
          setErrorMessage(errData.error?.message || 'Không thể bắt đầu thu âm.');
        }
        return;
      }

      setRecordingStatus('recording');
      recordingStatusRef.current = 'recording';
      scheduleAutoStop();

      // Poll hardware status for auto-stop or hardware disconnect
      clearPolling();
      pollIntervalRef.current = setInterval(async () => {
        try {
          const statusRes = await fetch('/api/record/status');
          if (!statusRes.ok) return;
          const state: RecorderState = await statusRes.json();

          if (state.error === 'microphone_disconnected') {
            clearAutoStopTimeout();
            setErrorMessage('Mic bị ngắt kết nối. Đang nhận dạng phần đã thu.');
            setIsLatchedToSend(false);
            isLatchedRef.current = false;
            void stopRecording();
          } else if (state.status === 'transcribing') {
            clearAutoStopTimeout();
            setRecordingStatus('transcribing');
            recordingStatusRef.current = 'transcribing';
          } else if (state.status === 'idle') {
            // Auto-stopped on backend due to maxDuration
            // Per spec: "Tự dừng vì hết giờ không tạo yêu cầu Gửi."
            clearAutoStopTimeout();
            setIsLatchedToSend(false);
            isLatchedRef.current = false;
            void stopRecording();
          }
        } catch {
          // Ignore network glitch during poll
        }
      }, 1000);
    } catch {
      setErrorMessage('Không tìm thấy mic. Hãy kết nối mic rồi thử lại.');
    }
  }

  // Handle tap on Mic button
  function handleMicClick() {
    if (disabled || isSending) return;

    if (recordingStatus === 'idle') {
      void startRecording();
    } else if (recordingStatus === 'recording') {
      void stopRecording();
    }
  }

  // Handle tap on Send ("Gửi") button
  function handleSendClick() {
    if (disabled || isSending || isLatchedToSend) return;

    if (errorMessage) {
      setErrorMessage('');
    }

    if (recordingStatus === 'recording') {
      // Smart Latch: Stop recording and flag latch to send once transcript arrives
      setIsLatchedToSend(true);
      isLatchedRef.current = true;
      void stopRecording();
    } else if (recordingStatus === 'transcribing') {
      // Clicked while transcribing: latch to send once transcript arrives
      setIsLatchedToSend(true);
      isLatchedRef.current = true;
    } else {
      // Normal send from idle
      void performSend(draftRef.current, hasTypedRef.current, hasVoiceRef.current);
    }
  }

  // Send button enabled/dimmed calculation
  const sendButtonState = determineSendButtonState({
    draft,
    recordingStatus,
    isLatchedToSend,
    isSending,
  });

  return (
    <footer
      className="shrink-0 border-t border-[#BAC5D0] bg-[#FFFFFF] p-4 sm:p-5"
      data-testid="composer"
    >
      <div className="mx-auto flex max-w-4xl flex-col space-y-3">
        {/* Multi-line Textarea */}
        <textarea
          ref={textareaRef}
          rows={3}
          value={draft}
          onChange={handleTextChange}
          onSelect={updateCaret}
          onClick={updateCaret}
          onTouchEnd={updateCaret}
          onKeyUp={updateCaret}
          onBlur={updateCaret}
          disabled={disabled || isSending}
          placeholder="Nhập tin nhắn hoặc chạm mic để nói…"
          aria-label="Vùng soạn tin nhắn"
          data-testid="composer-textarea"
          className="w-full resize-none rounded-xl border border-[#BAC5D0] bg-[#FFFFFF] p-3 text-[21px] leading-relaxed text-[#18212B] placeholder:text-[#4F5D6B] focus:border-[#273D53] focus:outline-none select-text"
        />

        {/* Controls row: Mic | Error notice | Send */}
        <div className="flex items-center justify-between gap-3 select-none">
          {/* Left: Mic button */}
          <button
            type="button"
            onClick={handleMicClick}
            disabled={disabled || recordingStatus === 'transcribing' || isSending}
            aria-label={
              recordingStatus === 'idle'
                ? 'Bắt đầu thu âm'
                : recordingStatus === 'recording'
                ? 'Dừng thu âm'
                : 'Đang nhận dạng…'
            }
            data-testid="mic-button"
            data-status={recordingStatus}
            className={`flex min-h-[48px] min-w-[48px] items-center justify-center rounded-xl transition-all ${
              recordingStatus === 'recording'
                ? 'bg-[#DC2626] text-white hover:bg-[#B91C1C]'
                : recordingStatus === 'transcribing'
                ? 'cursor-not-allowed bg-[#BAC5D0] text-[#18212B]'
                : 'bg-[#273D53] text-white hover:bg-[#1E2F40]'
            }`}
          >
            {recordingStatus === 'idle' && <MicIcon size={24} />}
            {recordingStatus === 'recording' && <SquareIcon size={20} />}
            {recordingStatus === 'transcribing' && <SpinnerIcon size={24} />}
          </button>

          {/* Center / Beside Mic: Error notice */}
          <div
            className="flex min-h-[24px] flex-1 items-center px-2"
            aria-live="polite"
          >
            {errorMessage && (
              <p
                role="alert"
                className="text-[16px] font-medium text-[#DC2626]"
                data-testid="composer-error-notice"
              >
                {errorMessage}
              </p>
            )}
          </div>

          {/* Right: Send ("Gửi") button */}
          <button
            type="button"
            onClick={handleSendClick}
            disabled={!sendButtonState.canClick}
            aria-label="Gửi tin nhắn"
            data-testid="send-button"
            data-latched={isLatchedToSend}
            className={`flex min-h-[48px] min-w-[96px] items-center justify-center rounded-xl px-6 text-[18px] font-semibold transition-all ${
              sendButtonState.canClick
                ? 'cursor-pointer bg-[#273D53] text-white hover:bg-[#1E2F40]'
                : 'cursor-not-allowed bg-[#BAC5D0] text-white opacity-60'
            }`}
          >
            Gửi
          </button>
        </div>
      </div>
    </footer>
  );
}