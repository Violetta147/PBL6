import test from 'node:test';
import assert from 'node:assert/strict';
import {
  insertTranscript,
  determineSendButtonState,
  calculateSources,
  validateTitle,
  getEffectiveMaxRecordSeconds,
} from '../src/utils/composerLogic';

test('insertTranscript: empty or whitespace transcript returns original draft', () => {
  const result1 = insertTranscript('Xin chào', '');
  assert.equal(result1.newDraft, 'Xin chào');
  assert.equal(result1.newCursor, 8);

  const result2 = insertTranscript('Xin chào', '   ', 3);
  assert.equal(result2.newDraft, 'Xin chào');
  assert.equal(result2.newCursor, 3);
});

test('insertTranscript: inserts into empty draft cleanly without extra spaces', () => {
  const result = insertTranscript('', 'Xin chào bạn');
  assert.equal(result.newDraft, 'Xin chào bạn');
  assert.equal(result.newCursor, 12);
});

test('insertTranscript: inserts at end of draft with single space separation', () => {
  const result = insertTranscript('Tôi muốn', 'gặp bạn vào sáng mai');
  assert.equal(result.newDraft, 'Tôi muốn gặp bạn vào sáng mai');
  assert.equal(result.newCursor, 29);
});

test('insertTranscript: does not duplicate space if draft ends with space', () => {
  const result = insertTranscript('Tôi muốn ', 'gặp bạn');
  assert.equal(result.newDraft, 'Tôi muốn gặp bạn');
  assert.equal(result.newCursor, 16);
});

test('insertTranscript: inserts in middle of sentence per Antigravity caret rules', () => {
  // User typed: "Tôi muốn vào sáng mai."
  // Cursor placed right after "Tôi muốn" (position 8)
  // Speech recognized: "hẹn gặp"
  const draft = 'Tôi muốn vào sáng mai.';
  const pos = 8;
  const result = insertTranscript(draft, 'hẹn gặp', pos);
  assert.equal(result.newDraft, 'Tôi muốn hẹn gặp vào sáng mai.');
});

test('insertTranscript: inserts before punctuation without creating unwanted gap', () => {
  const draft = 'Tôi muốn vào sáng mai.';
  // Inserting at position 21 (just before '.')
  const result = insertTranscript(draft, 'ngay', 21);
  assert.equal(result.newDraft, 'Tôi muốn vào sáng mai ngay.');
});

test('insertTranscript: transcript starting with punctuation does not insert space before punctuation', () => {
  const draft = 'Xin chào';
  const result = insertTranscript(draft, ', bạn khỏe không?');
  assert.equal(result.newDraft, 'Xin chào, bạn khỏe không?');
  assert.equal(result.newCursor, 25);
});

test('insertTranscript: null or undefined cursorPosition defaults to end of draft', () => {
  const draft = 'Tin nhắn ban đầu';
  const rNull = insertTranscript(draft, 'bổ sung', null);
  assert.equal(rNull.newDraft, 'Tin nhắn ban đầu bổ sung');

  const rUndef = insertTranscript(draft, 'tiếp theo', undefined);
  assert.equal(rUndef.newDraft, 'Tin nhắn ban đầu tiếp theo');
});

test('insertTranscript: concurrent edits before arrival - draft modified while awaiting transcript', () => {
  // Initial draft was "Tôi muốn". While waiting, user edited to "Tôi muốn uống trà" with cursor at 8
  const draft = 'Tôi muốn uống trà';
  const transcript = 'hẹn gặp và';
  const result = insertTranscript(draft, transcript, 8);
  assert.equal(result.newDraft, 'Tôi muốn hẹn gặp và uống trà');
  assert.equal(result.newCursor, 19);
});

test('determineSendButtonState: idle state with empty or whitespace draft is dimmed and disabled', () => {
  const empty = determineSendButtonState({
    draft: '',
    recordingStatus: 'idle',
    isLatchedToSend: false,
    isSending: false,
  });
  assert.equal(empty.canClick, false);
  assert.equal(empty.isDimmed, true);

  const whitespace = determineSendButtonState({
    draft: '   \n\t  ',
    recordingStatus: 'idle',
    isLatchedToSend: false,
    isSending: false,
  });
  assert.equal(whitespace.canClick, false);
  assert.equal(whitespace.isDimmed, true);
});

test('determineSendButtonState: idle state with non-whitespace text is enabled', () => {
  const state = determineSendButtonState({
    draft: 'A',
    recordingStatus: 'idle',
    isLatchedToSend: false,
    isSending: false,
  });
  assert.equal(state.canClick, true);
  assert.equal(state.isDimmed, false);
});

test('determineSendButtonState: smart latch enables send button during recording even if draft is empty', () => {
  const emptyRec = determineSendButtonState({
    draft: '',
    recordingStatus: 'recording',
    isLatchedToSend: false,
    isSending: false,
  });
  assert.equal(emptyRec.canClick, true);
  assert.equal(emptyRec.isDimmed, false);

  const textRec = determineSendButtonState({
    draft: 'Tôi muốn',
    recordingStatus: 'recording',
    isLatchedToSend: false,
    isSending: false,
  });
  assert.equal(textRec.canClick, true);
  assert.equal(textRec.isDimmed, false);
});

test('determineSendButtonState: smart latch enables send button during transcribing if not yet latched', () => {
  const transcribing = determineSendButtonState({
    draft: '',
    recordingStatus: 'transcribing',
    isLatchedToSend: false,
    isSending: false,
  });
  assert.equal(transcribing.canClick, true);
  assert.equal(transcribing.isDimmed, false);
});

test('determineSendButtonState: when latched to send, button is dimmed and disabled to prevent double send', () => {
  const latched = determineSendButtonState({
    draft: 'Tôi muốn',
    recordingStatus: 'transcribing',
    isLatchedToSend: true,
    isSending: false,
  });
  assert.equal(latched.canClick, false);
  assert.equal(latched.isDimmed, true);
});

test('determineSendButtonState: when sending is in progress, button is dimmed and disabled', () => {
  const sending = determineSendButtonState({
    draft: 'Tôi muốn',
    recordingStatus: 'idle',
    isLatchedToSend: false,
    isSending: true,
  });
  assert.equal(sending.canClick, false);
  assert.equal(sending.isDimmed, true);
});

test('calculateSources: accurately tracks keyboard, voice and combined multi-sources', () => {
  assert.deepEqual(calculateSources({ hasTyped: true, hasVoice: false }), ['keyboard']);
  assert.deepEqual(calculateSources({ hasTyped: false, hasVoice: true }), ['voice']);
  assert.deepEqual(calculateSources({ hasTyped: true, hasVoice: true }), ['keyboard', 'voice']);
  // Default fallback when neither explicitly flagged
  assert.deepEqual(calculateSources({ hasTyped: false, hasVoice: false }), ['keyboard']);
});

test('validateTitle: reverts to currentTitle if new title is empty or only whitespace', () => {
  const current = 'Hội thoại ban đầu';
  const r1 = validateTitle('', current);
  assert.equal(r1.title, current);
  assert.equal(r1.changed, false);

  const r2 = validateTitle('   \t\n  ', current);
  assert.equal(r2.title, current);
  assert.equal(r2.changed, false);
});

test('validateTitle: collapses whitespace, trims, and detects change', () => {
  const current = 'Hội thoại cũ';
  const r = validateTitle('   Hội   thoại    mới   ', current);
  assert.equal(r.title, 'Hội thoại mới');
  assert.equal(r.changed, true);

  const unchanged = validateTitle('Hội thoại cũ', current);
  assert.equal(unchanged.title, 'Hội thoại cũ');
  assert.equal(unchanged.changed, false);
});

test('validateTitle: truncates title at 72 characters max', () => {
  const longTitle = 'a'.repeat(100);
  const r = validateTitle(longTitle, 'cũ');
  assert.equal(r.title.length, 72);
  assert.equal(r.title, 'a'.repeat(72));
  assert.equal(r.changed, true);
});

test('getEffectiveMaxRecordSeconds: respects configured seconds in range [5, 300]', () => {
  assert.equal(getEffectiveMaxRecordSeconds(5), 5);
  assert.equal(getEffectiveMaxRecordSeconds(10), 10);
  assert.equal(getEffectiveMaxRecordSeconds(60), 60);
  assert.equal(getEffectiveMaxRecordSeconds(120), 120);
  assert.equal(getEffectiveMaxRecordSeconds(300), 300);
});

test('getEffectiveMaxRecordSeconds: defaults to 120 when undefined, null, out of range, or invalid', () => {
  assert.equal(getEffectiveMaxRecordSeconds(undefined), 120);
  assert.equal(getEffectiveMaxRecordSeconds(null), 120);
  assert.equal(getEffectiveMaxRecordSeconds(0), 120);
  assert.equal(getEffectiveMaxRecordSeconds(-5), 120);
  assert.equal(getEffectiveMaxRecordSeconds(4), 120);
  assert.equal(getEffectiveMaxRecordSeconds(301), 120);
  assert.equal(getEffectiveMaxRecordSeconds(NaN), 120);
  assert.equal(getEffectiveMaxRecordSeconds(Infinity), 120);
});

test('auto-stop timer: timer fires after configured maxRecordSeconds, cancels latch and stops recording', (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    let recordingStatus: 'idle' | 'recording' | 'transcribing' = 'idle';
    let isLatchedToSend = false;
    let draft = 'Bản nháp ban đầu';
    let stopCalled = false;
    let sendCalled = false;

    // Simulation of Composer's auto-stop schedule
    const durationSec = getEffectiveMaxRecordSeconds(5);
    recordingStatus = 'recording';
    let timer: NodeJS.Timeout | null = setTimeout(() => {
      // Auto-stop handler in Composer
      isLatchedToSend = false;
      stopRecording();
    }, durationSec * 1000);

    function stopRecording() {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
      stopCalled = true;
      recordingStatus = 'transcribing';

      // Simulate transcript arrival
      const transcript = 'văn bản mới';
      const insertResult = insertTranscript(draft, transcript, draft.length);
      draft = insertResult.newDraft;
      recordingStatus = 'idle';

      if (isLatchedToSend) {
        sendCalled = true;
      }
    }

    assert.equal(recordingStatus, 'recording');
    assert.equal(stopCalled, false);

    // Fast-forward 4999 ms -> still recording
    t.mock.timers.tick(4999);
    assert.equal(recordingStatus, 'recording');
    assert.equal(stopCalled, false);

    // Tick remaining 1 ms -> fires auto-stop
    t.mock.timers.tick(1);
    assert.equal(stopCalled, true);
    assert.equal(recordingStatus, 'idle');
    assert.equal(draft, 'Bản nháp ban đầu văn bản mới');
    assert.equal(sendCalled, false); // "Tự dừng vì hết giờ không tạo yêu cầu Gửi"
    assert.equal(isLatchedToSend, false);
  } finally {
    t.mock.timers.reset();
  }
});

test('auto-stop timer: manual stop before timeout clears timer and prevents late auto-stop', (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    let stopCalls = 0;
    const durationSec = getEffectiveMaxRecordSeconds(5);
    let timer: NodeJS.Timeout | null = setTimeout(() => {
      stopCalls++;
    }, durationSec * 1000);

    function manualStop() {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
      stopCalls++;
    }

    // Manual stop at 2 seconds
    t.mock.timers.tick(2000);
    manualStop();
    assert.equal(stopCalls, 1);

    // Advance past 5 seconds
    t.mock.timers.tick(4000);
    // stopCalls should remain 1, not 2
    assert.equal(stopCalls, 1);
  } finally {
    t.mock.timers.reset();
  }
});

test('auto-stop timer: cancelSignal before timeout cancels timer and resets state to idle', (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    let recordingStatus: 'idle' | 'recording' | 'transcribing' = 'recording';
    let isLatchedToSend = true;
    let stopCalled = false;

    const durationSec = getEffectiveMaxRecordSeconds(5);
    let timer: NodeJS.Timeout | null = setTimeout(() => {
      stopCalled = true;
    }, durationSec * 1000);

    function handleCancelSignal() {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
      recordingStatus = 'idle';
      isLatchedToSend = false;
    }

    // Cancel at 3 seconds (e.g. user opens Settings)
    t.mock.timers.tick(3000);
    handleCancelSignal();
    assert.equal(recordingStatus, 'idle');
    assert.equal(isLatchedToSend, false);

    // Advance past 5 seconds
    t.mock.timers.tick(5000);
    assert.equal(stopCalled, false);
    assert.equal(recordingStatus, 'idle');
  } finally {
    t.mock.timers.reset();
  }
});

test('auto-stop timer: smart latch Send during recording takes precedence, clears timer, and sends upon arrival', (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    let recordingStatus: 'idle' | 'recording' | 'transcribing' = 'recording';
    let isLatchedToSend = false;
    let draft = 'Tôi muốn';
    let sendCalled = false;
    let autoStopFired = false;

    const durationSec = getEffectiveMaxRecordSeconds(5);
    let timer: NodeJS.Timeout | null = setTimeout(() => {
      autoStopFired = true;
      isLatchedToSend = false;
    }, durationSec * 1000);

    // User clicks Send at 2000ms during recording
    t.mock.timers.tick(2000);
    // handleSendClick logic:
    isLatchedToSend = true;
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    recordingStatus = 'transcribing';

    // Simulate transcript arrival at 2500ms
    t.mock.timers.tick(500);
    const transcript = 'hẹn gặp';
    const insertResult = insertTranscript(draft, transcript, draft.length);
    draft = insertResult.newDraft;
    if (isLatchedToSend) {
      sendCalled = true;
      isLatchedToSend = false;
      draft = ''; // Cleared on successful send
    }
    recordingStatus = 'idle';

    assert.equal(sendCalled, true);
    assert.equal(draft, '');
    assert.equal(recordingStatus, 'idle');

    // Advance past original 5000ms mark
    t.mock.timers.tick(5000);
    assert.equal(autoStopFired, false);
  } finally {
    t.mock.timers.reset();
  }
});

test('auto-stop timer: latching Send during transcribing after auto-stop timeout sends message', (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    let recordingStatus: 'idle' | 'recording' | 'transcribing' = 'recording';
    let isLatchedToSend = false;
    let draft = 'Bản nháp';
    let sendCalled = false;

    const durationSec = getEffectiveMaxRecordSeconds(5);
    let timer: NodeJS.Timeout | null = setTimeout(() => {
      // Auto-stop fired: does not latch by default
      isLatchedToSend = false;
      recordingStatus = 'transcribing';
    }, durationSec * 1000);

    // Fast-forward 5000ms to trigger auto-stop
    t.mock.timers.tick(5000);
    assert.equal(recordingStatus, 'transcribing');
    assert.equal(isLatchedToSend, false);

    // User sees spinner and clicks "Gửi" while transcribing
    isLatchedToSend = true;

    // Transcript arrives 300ms later
    t.mock.timers.tick(300);
    const transcript = 'đoạn nói thêm';
    const insertResult = insertTranscript(draft, transcript, draft.length);
    draft = insertResult.newDraft;
    if (isLatchedToSend) {
      sendCalled = true;
      isLatchedToSend = false;
      draft = '';
    }
    recordingStatus = 'idle';

    assert.equal(sendCalled, true);
    assert.equal(draft, '');
    assert.equal(recordingStatus, 'idle');
  } finally {
    t.mock.timers.reset();
  }
});

test('auto-stop timer: mid-recording disconnect clears auto-stop timer and handles partial transcript', (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  try {
    let recordingStatus: 'idle' | 'recording' | 'transcribing' = 'recording';
    let isLatchedToSend = true; // Suppose user had latched or unlatched
    let autoStopFired = false;
    let draft = 'Ghi chú';
    let sendCalled = false;

    const durationSec = getEffectiveMaxRecordSeconds(5);
    let timer: NodeJS.Timeout | null = setTimeout(() => {
      autoStopFired = true;
    }, durationSec * 1000);

    // Mic disconnects at 2500ms
    t.mock.timers.tick(2500);
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    // Spec: "Mic bị ngắt kết nối. Đang nhận dạng phần đã thu." - unlatches send per spec
    isLatchedToSend = false;
    recordingStatus = 'transcribing';

    // Transcript arrives
    t.mock.timers.tick(400);
    const partialTranscript = 'nói được một nửa';
    draft = insertTranscript(draft, partialTranscript, draft.length).newDraft;
    if (isLatchedToSend) {
      sendCalled = true;
    }
    recordingStatus = 'idle';

    assert.equal(draft, 'Ghi chú nói được một nửa');
    assert.equal(sendCalled, false); // Must NOT auto-send on mid-recording disconnect per spec
    assert.equal(recordingStatus, 'idle');

    // Advance past 5000ms
    t.mock.timers.tick(5000);
    assert.equal(autoStopFired, false);
  } finally {
    t.mock.timers.reset();
  }
});
