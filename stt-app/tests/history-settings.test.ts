import test from 'node:test';
import assert from 'node:assert/strict';

// Helper tests for History & Settings business logic

function validateMaxRecordSeconds(val: unknown): { valid: boolean; error?: string } {
  const num = Number(val);
  if (!Number.isInteger(num) || num < 5 || num > 300) {
    return {
      valid: false,
      error: 'Thời lượng thu tối đa phải là số nguyên từ 5 đến 300 giây.',
    };
  }
  return { valid: true };
}

function validateTimeoutSeconds(val: unknown): { valid: boolean; error?: string } {
  const num = Number(val);
  if (!Number.isInteger(num) || num < 5 || num > 300) {
    return {
      valid: false,
      error: 'Thời gian chờ phải là số nguyên từ 5 đến 300 giây.',
    };
  }
  return { valid: true };
}

interface SttState {
  selectedMicId: string;
  maxRecordSeconds: number;
  timeoutSeconds: number;
  apiKey: string;
  clearApiKey: boolean;
}

function checkSttDirty(current: SttState, initial: SttState): boolean {
  if (current.selectedMicId !== initial.selectedMicId) return true;
  if (current.maxRecordSeconds !== initial.maxRecordSeconds) return true;
  if (current.timeoutSeconds !== initial.timeoutSeconds) return true;
  if (current.apiKey.trim().length > 0) return true;
  if (current.clearApiKey) return true;
  return false;
}

function formatDrawerDate(isoString: string, now: Date = new Date()): string {
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '';
    const isToday =
      d.getDate() === now.getDate() &&
      d.getMonth() === now.getMonth() &&
      d.getFullYear() === now.getFullYear();

    const timeStr = d.toLocaleTimeString('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });

    if (isToday) {
      return timeStr;
    }
    const dateStr = d.toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
    });
    return `${timeStr} · ${dateStr}`;
  } catch {
    return '';
  }
}

interface ConvItem {
  id: string;
  title: string;
  updatedAt: string;
}

function filterConversations(
  items: ConvItem[],
  query?: string,
  olderThanDays?: number,
  nowMs: number = Date.now()
): ConvItem[] {
  let list = [...items];
  if (query && query.trim()) {
    const q = query.trim().toLowerCase();
    list = list.filter((c) => c.title.toLowerCase().includes(q));
  }
  if (olderThanDays !== undefined && olderThanDays > 0) {
    const cutoff = nowMs - olderThanDays * 24 * 60 * 60 * 1000;
    list = list.filter((c) => new Date(c.updatedAt).getTime() < cutoff);
  }
  return list;
}

test('validateMaxRecordSeconds: accepts integers in [5, 300]', () => {
  assert.equal(validateMaxRecordSeconds(5).valid, true);
  assert.equal(validateMaxRecordSeconds(120).valid, true);
  assert.equal(validateMaxRecordSeconds(300).valid, true);
  assert.equal(validateMaxRecordSeconds('120').valid, true);
});

test('validateMaxRecordSeconds: rejects values < 5, > 300, decimals, or non-numbers', () => {
  assert.equal(validateMaxRecordSeconds(4).valid, false);
  assert.equal(validateMaxRecordSeconds(301).valid, false);
  assert.equal(validateMaxRecordSeconds(0).valid, false);
  assert.equal(validateMaxRecordSeconds(-10).valid, false);
  assert.equal(validateMaxRecordSeconds(12.5).valid, false);
  assert.equal(validateMaxRecordSeconds('').valid, false);
  assert.equal(validateMaxRecordSeconds('abc').valid, false);
});

test('validateTimeoutSeconds: accepts integers in [5, 300] and rejects out of range', () => {
  assert.equal(validateTimeoutSeconds(60).valid, true);
  assert.equal(validateTimeoutSeconds(4).valid, false);
  assert.equal(validateTimeoutSeconds(301).valid, false);
});

test('checkSttDirty: clean when equal to initial state', () => {
  const initial: SttState = {
    selectedMicId: 'mic-1',
    maxRecordSeconds: 120,
    timeoutSeconds: 60,
    apiKey: '',
    clearApiKey: false,
  };
  const current: SttState = { ...initial };
  assert.equal(checkSttDirty(current, initial), false);
});

test('checkSttDirty: dirty when any setting field is modified', () => {
  const initial: SttState = {
    selectedMicId: 'mic-1',
    maxRecordSeconds: 120,
    timeoutSeconds: 60,
    apiKey: '',
    clearApiKey: false,
  };

  assert.equal(checkSttDirty({ ...initial, selectedMicId: 'mic-2' }, initial), true);
  assert.equal(checkSttDirty({ ...initial, maxRecordSeconds: 150 }, initial), true);
  assert.equal(checkSttDirty({ ...initial, timeoutSeconds: 90 }, initial), true);
  assert.equal(checkSttDirty({ ...initial, apiKey: 'new-key-123456789' }, initial), true);
  assert.equal(checkSttDirty({ ...initial, clearApiKey: true }, initial), true);
});

test('checkSttDirty: reverting modified fields returns dirty state to false', () => {
  const initial: SttState = {
    selectedMicId: 'mic-os-default',
    maxRecordSeconds: 120,
    timeoutSeconds: 60,
    apiKey: '',
    clearApiKey: false,
  };

  const modified: SttState = { ...initial, maxRecordSeconds: 180 };
  assert.equal(checkSttDirty(modified, initial), true);

  // Revert back
  modified.maxRecordSeconds = 120;
  assert.equal(checkSttDirty(modified, initial), false);
});

test('History Drawer date formatting: formats today, past days, and invalid dates', () => {
  const referenceNow = new Date('2026-11-12T14:30:00Z');

  // Today
  const todayIso = new Date('2026-11-12T08:15:00Z').toISOString();
  const formattedToday = formatDrawerDate(todayIso, referenceNow);
  assert.ok(formattedToday.length > 0);
  assert.ok(!formattedToday.includes('·')); // No date suffix for today

  // Past day (e.g. 5 days ago)
  const pastIso = new Date('2026-11-07T09:00:00Z').toISOString();
  const formattedPast = formatDrawerDate(pastIso, referenceNow);
  assert.ok(formattedPast.includes('·')); // Has date suffix

  // Invalid date
  assert.equal(formatDrawerDate('invalid-iso-date', referenceNow), '');
});

test('+ Hội thoại mới behavior: resets state or closes drawer per Codex Desktop spec', () => {
  interface ChatState {
    conversationId: string | null;
    messageCount: number;
    draft: string;
    cancelSignal: number;
    drawerOpen: boolean;
  }

  function onNewConversation(state: ChatState): ChatState {
    if (!state.conversationId && state.messageCount === 0 && state.draft === '') {
      return { ...state, drawerOpen: false };
    }
    return {
      conversationId: null,
      messageCount: 0,
      draft: '',
      cancelSignal: state.cancelSignal + 1,
      drawerOpen: false,
    };
  }

  // Case 1: Already on blank new chat with no draft -> simply closes drawer
  const blankState: ChatState = {
    conversationId: null,
    messageCount: 0,
    draft: '',
    cancelSignal: 0,
    drawerOpen: true,
  };
  const blankResult = onNewConversation(blankState);
  assert.equal(blankResult.drawerOpen, false);
  assert.equal(blankResult.cancelSignal, 0); // Not incremented

  // Case 2: On blank chat but has unsubmitted draft -> cancels and discards draft
  const draftState: ChatState = {
    conversationId: null,
    messageCount: 0,
    draft: 'Bản nháp đang soạn',
    cancelSignal: 0,
    drawerOpen: true,
  };
  const draftResult = onNewConversation(draftState);
  assert.equal(draftResult.drawerOpen, false);
  assert.equal(draftResult.draft, '');
  assert.equal(draftResult.cancelSignal, 1);

  // Case 3: In an existing conversation with messages -> resets to new chat and increments cancel
  const convState: ChatState = {
    conversationId: 'c-123',
    messageCount: 5,
    draft: 'Nháp trong c-123',
    cancelSignal: 2,
    drawerOpen: true,
  };
  const convResult = onNewConversation(convState);
  assert.equal(convResult.drawerOpen, false);
  assert.equal(convResult.conversationId, null);
  assert.equal(convResult.messageCount, 0);
  assert.equal(convResult.draft, '');
  assert.equal(convResult.cancelSignal, 3);
});

test('History Drawer vs Settings View: cancelSignal and draft preservation semantics', () => {
  let cancelSignal = 0;
  let draft = 'Tin nhắn chưa gửi';
  let isHistoryOpen = false;
  let isSettingsOpen = false;

  // Opening & closing History drawer does NOT interrupt in-flight recording or transcribing
  function openHistory() {
    isHistoryOpen = true;
  }
  function closeHistory() {
    isHistoryOpen = false;
  }

  openHistory();
  assert.equal(isHistoryOpen, true);
  assert.equal(cancelSignal, 0);
  assert.equal(draft, 'Tin nhắn chưa gửi');

  closeHistory();
  assert.equal(isHistoryOpen, false);
  assert.equal(cancelSignal, 0);
  assert.equal(draft, 'Tin nhắn chưa gửi');

  // Opening Settings cancels in-flight recording/transcribing, but PRESERVES draft
  function openSettings() {
    cancelSignal++;
    isSettingsOpen = true;
  }
  function closeSettings() {
    isSettingsOpen = false;
  }

  openSettings();
  assert.equal(isSettingsOpen, true);
  assert.equal(cancelSignal, 1); // Canceled in-flight
  assert.equal(draft, 'Tin nhắn chưa gửi'); // Preserved!

  closeSettings();
  assert.equal(isSettingsOpen, false);
  assert.equal(draft, 'Tin nhắn chưa gửi'); // Still preserved on return
});

test('Unsaved Changes Modal state machine: Lưu, Không lưu, Ở lại', () => {
  interface SettingsSession {
    currentStt: SttState;
    initialStt: SttState;
    isModalOpen: boolean;
    activeTab: 'stt' | 'history';
    currentScreen: 'settings' | 'conversation';
    pendingNavigation: (() => void) | null;
  }

  const initial: SttState = {
    selectedMicId: 'mic-1',
    maxRecordSeconds: 120,
    timeoutSeconds: 60,
    apiKey: '',
    clearApiKey: false,
  };

  function createSession(dirty: boolean, valid: boolean = true): SettingsSession {
    return {
      currentStt: dirty
        ? { ...initial, maxRecordSeconds: valid ? 150 : 400 }
        : { ...initial },
      initialStt: { ...initial },
      isModalOpen: false,
      activeTab: 'stt',
      currentScreen: 'settings',
      pendingNavigation: null,
    };
  }

  function navigateWithGuard(session: SettingsSession, target: () => void) {
    const isDirty = checkSttDirty(session.currentStt, session.initialStt);
    if (session.activeTab === 'stt' && isDirty) {
      session.pendingNavigation = target;
      session.isModalOpen = true;
    } else {
      target();
    }
  }

  // Test 1: Clean state navigates immediately without modal
  const cleanSession = createSession(false);
  navigateWithGuard(cleanSession, () => {
    cleanSession.currentScreen = 'conversation';
  });
  assert.equal(cleanSession.isModalOpen, false);
  assert.equal(cleanSession.currentScreen, 'conversation');

  // Test 2: Dirty state intercepts navigation and displays modal
  const dirtySession = createSession(true);
  navigateWithGuard(dirtySession, () => {
    dirtySession.currentScreen = 'conversation';
  });
  assert.equal(dirtySession.isModalOpen, true);
  assert.equal(dirtySession.currentScreen, 'settings'); // Still in settings

  // Modal Action: "Ở lại"
  function onModalStay(session: SettingsSession) {
    session.isModalOpen = false;
    session.pendingNavigation = null;
  }
  onModalStay(dirtySession);
  assert.equal(dirtySession.isModalOpen, false);
  assert.equal(dirtySession.currentScreen, 'settings'); // Stayed in settings

  // Modal Action: "Không lưu"
  const dirtySession2 = createSession(true);
  navigateWithGuard(dirtySession2, () => {
    dirtySession2.currentScreen = 'conversation';
  });
  function onModalDiscard(session: SettingsSession) {
    session.isModalOpen = false;
    session.currentStt = { ...session.initialStt }; // Reverted
    if (session.pendingNavigation) {
      session.pendingNavigation();
    }
    session.pendingNavigation = null;
  }
  onModalDiscard(dirtySession2);
  assert.equal(dirtySession2.isModalOpen, false);
  assert.equal(dirtySession2.currentScreen, 'conversation');
  assert.equal(checkSttDirty(dirtySession2.currentStt, dirtySession2.initialStt), false);

  // Modal Action: "Lưu" (valid)
  const dirtySession3 = createSession(true, true);
  navigateWithGuard(dirtySession3, () => {
    dirtySession3.currentScreen = 'conversation';
  });
  function onModalSave(session: SettingsSession): boolean {
    const valid = validateMaxRecordSeconds(session.currentStt.maxRecordSeconds).valid;
    if (!valid) return false;
    session.initialStt = { ...session.currentStt }; // Saved to snapshot
    session.isModalOpen = false;
    if (session.pendingNavigation) {
      session.pendingNavigation();
    }
    session.pendingNavigation = null;
    return true;
  }
  const saveSuccess = onModalSave(dirtySession3);
  assert.equal(saveSuccess, true);
  assert.equal(dirtySession3.isModalOpen, false);
  assert.equal(dirtySession3.currentScreen, 'conversation');
  assert.equal(dirtySession3.initialStt.maxRecordSeconds, 150);

  // Modal Action: "Lưu" (invalid: 400 > 300) -> does not navigate
  const dirtySession4 = createSession(true, false);
  navigateWithGuard(dirtySession4, () => {
    dirtySession4.currentScreen = 'conversation';
  });
  const saveFail = onModalSave(dirtySession4);
  assert.equal(saveFail, false);
  assert.equal(dirtySession4.currentScreen, 'settings'); // Blocked from navigating
});

test('History management: 7-day, 30-day, all-time, search query and combined filters', () => {
  const nowMs = 1700000000000;
  const dayMs = 24 * 60 * 60 * 1000;

  const items: ConvItem[] = [
    { id: '1', title: 'Hội thoại hôm nay', updatedAt: new Date(nowMs - 1 * dayMs).toISOString() },
    { id: '2', title: 'Hội thoại tuần trước', updatedAt: new Date(nowMs - 10 * dayMs).toISOString() },
    { id: '3', title: 'Hội thoại tháng trước', updatedAt: new Date(nowMs - 35 * dayMs).toISOString() },
    { id: '4', title: 'Thảo luận kỹ thuật', updatedAt: new Date(nowMs - 40 * dayMs).toISOString() },
  ];

  // All time
  const all = filterConversations(items, '', undefined, nowMs);
  assert.equal(all.length, 4);

  // Older than 7 days (should match id: 2, 3, 4)
  const older7 = filterConversations(items, '', 7, nowMs);
  assert.equal(older7.length, 3);
  assert.deepEqual(older7.map((c) => c.id).sort(), ['2', '3', '4']);

  // Older than 30 days (should match id: 3, 4)
  const older30 = filterConversations(items, '', 30, nowMs);
  assert.equal(older30.length, 2);
  assert.deepEqual(older30.map((c) => c.id).sort(), ['3', '4']);

  // Search by query: "thảo luận"
  const searchMatch = filterConversations(items, 'thảo luận', undefined, nowMs);
  assert.equal(searchMatch.length, 1);
  assert.equal(searchMatch[0].id, '4');

  // Combined search and 30-day filter: query "hội thoại" and older than 30 days -> only id: 3
  const combined = filterConversations(items, 'hội thoại', 30, nowMs);
  assert.equal(combined.length, 1);
  assert.equal(combined[0].id, '3');

  // Query with no match
  const noMatch = filterConversations(items, 'không tồn tại', undefined, nowMs);
  assert.equal(noMatch.length, 0);
});

test('Zero results classification: totalConversationsCount vs filtered matches', () => {
  function getEmptyMessage(totalCount: number, filteredCount: number): string {
    if (filteredCount > 0) return '';
    if (totalCount === 0) {
      return 'Chưa có hội thoại đã lưu.';
    }
    return 'Không có hội thoại khớp điều kiện.';
  }

  // Zero conversations in database (whether query/filter applied or not)
  assert.equal(getEmptyMessage(0, 0), 'Chưa có hội thoại đã lưu.');

  // Conversations exist, but filtered search yields 0 matches
  assert.equal(getEmptyMessage(5, 0), 'Không có hội thoại khớp điều kiện.');
});

test('formatHistoryDate: safely formats valid dates and handles empty/corrupt strings gracefully', () => {
  function formatHistoryDate(isoString: string): string {
    try {
      const d = new Date(isoString);
      if (isNaN(d.getTime())) return '';
      return d.toLocaleDateString('vi-VN');
    } catch {
      return '';
    }
  }

  assert.equal(formatHistoryDate(''), '');
  assert.equal(formatHistoryDate('corrupted-date-xyz'), '');
  assert.ok(formatHistoryDate('2026-11-12T10:00:00.000Z').length > 0);
});

test('Batch select and delete button labels and enabled states', () => {
  function getSelectAllLabel(itemsCount: number, selectedCount: number): { label: string; disabled: boolean } {
    if (itemsCount === 0) {
      return { label: 'Chọn 0 kết quả', disabled: true };
    }
    if (selectedCount === itemsCount) {
      return { label: 'Bỏ chọn tất cả', disabled: false };
    }
    return { label: `Chọn ${itemsCount} kết quả`, disabled: false };
  }

  function getDeleteButtonLabel(selectedCount: number, isDeleting: boolean): { label: string; disabled: boolean } {
    if (isDeleting) {
      return { label: 'Đang xóa…', disabled: true };
    }
    if (selectedCount === 0) {
      return { label: 'Xóa 0 hội thoại', disabled: true };
    }
    return { label: `Xóa ${selectedCount} hội thoại`, disabled: false };
  }

  // 0 results
  assert.deepEqual(getSelectAllLabel(0, 0), { label: 'Chọn 0 kết quả', disabled: true });
  assert.deepEqual(getDeleteButtonLabel(0, false), { label: 'Xóa 0 hội thoại', disabled: true });

  // 5 results, none selected
  assert.deepEqual(getSelectAllLabel(5, 0), { label: 'Chọn 5 kết quả', disabled: false });
  assert.deepEqual(getDeleteButtonLabel(0, false), { label: 'Xóa 0 hội thoại', disabled: true });

  // 5 results, all 5 selected
  assert.deepEqual(getSelectAllLabel(5, 5), { label: 'Bỏ chọn tất cả', disabled: false });
  assert.deepEqual(getDeleteButtonLabel(5, false), { label: 'Xóa 5 hội thoại', disabled: false });

  // 5 results, 3 selected (partially selected)
  assert.deepEqual(getSelectAllLabel(5, 3), { label: 'Chọn 5 kết quả', disabled: false });
  assert.deepEqual(getDeleteButtonLabel(3, false), { label: 'Xóa 3 hội thoại', disabled: false });

  // In deleting state
  assert.deepEqual(getDeleteButtonLabel(3, true), { label: 'Đang xóa…', disabled: true });
});

test('Batch select logic: Select all / Deselect all / Filter change reset', () => {
  const allIds = ['c1', 'c2', 'c3'];
  let selected = new Set<string>();

  // Select All
  selected = new Set(allIds);
  assert.equal(selected.size, 3);
  assert.equal(allIds.every((id) => selected.has(id)), true);

  // Deselect one
  selected.delete('c2');
  assert.equal(selected.size, 2);
  assert.equal(allIds.every((id) => selected.has(id)), false);

  // Deselect all
  selected.clear();
  assert.equal(selected.size, 0);

  // On search/filter change, selection must reset per spec
  selected.add('c1');
  const onSearchChange = () => {
    selected = new Set();
  };
  onSearchChange();
  assert.equal(selected.size, 0);
});

test('Active conversation deletion detection & session reset', () => {
  interface AppState {
    activeConversationId: string | null;
    messages: string[];
    draft: string;
  }

  function handleBatchDeleteResult(state: AppState, deletedIds: Set<string>): AppState {
    if (state.activeConversationId && deletedIds.has(state.activeConversationId)) {
      return {
        activeConversationId: null,
        messages: [],
        draft: '',
      };
    }
    return state;
  }

  // Active conversation is deleted
  const stateWithActive: AppState = {
    activeConversationId: 'c-active',
    messages: ['tin nhắn 1', 'tin nhắn 2'],
    draft: 'bản nháp trong c-active',
  };
  const resetResult = handleBatchDeleteResult(stateWithActive, new Set(['c-active', 'c-other']));
  assert.equal(resetResult.activeConversationId, null);
  assert.equal(resetResult.messages.length, 0);
  assert.equal(resetResult.draft, '');

  // Active conversation is NOT deleted
  const retainedResult = handleBatchDeleteResult(stateWithActive, new Set(['c-other-1', 'c-other-2']));
  assert.equal(retainedResult.activeConversationId, 'c-active');
  assert.equal(retainedResult.messages.length, 2);
  assert.equal(retainedResult.draft, 'bản nháp trong c-active');
});

function validateApiKey(key: string): { valid: boolean; error?: string } {
  const trimmed = key.trim();
  if (trimmed === '') return { valid: true };
  if (!/^[A-Za-z0-9_-]{16,512}$/.test(trimmed)) {
    return {
      valid: false,
      error: 'API key phải dài 16–512 ký tự, không chứa khoảng trắng hoặc ký tự điều khiển.',
    };
  }
  return { valid: true };
}

test('validateApiKey: validates format and length [16, 512] alphanumeric/dash/underscore', () => {
  assert.equal(validateApiKey('').valid, true); // Empty allowed (keeps existing)
  assert.equal(validateApiKey('1234567890abcdef1234567890abcdef').valid, true);
  assert.equal(validateApiKey('valid_key-with-dashes-and-underscores-123').valid, true);

  // Rejections
  assert.equal(validateApiKey('too-short').valid, false); // < 16 chars
  assert.equal(validateApiKey('has space inside 1234567890abcdef').valid, false);
  assert.equal(validateApiKey('has$special%chars*1234567890abcdef').valid, false);
});

test('handleSelectConversation: selecting current active conversation preserves draft and does not cancel capture', () => {
  interface ChatSelectState {
    activeConversationId: string | null;
    draft: string;
    cancelSignal: number;
    drawerOpen: boolean;
  }

  function onSelectConversation(state: ChatSelectState, selectedId: string): ChatSelectState {
    if (state.activeConversationId && state.activeConversationId === selectedId) {
      return { ...state, drawerOpen: false };
    }
    return {
      activeConversationId: selectedId,
      draft: '',
      cancelSignal: state.cancelSignal + 1,
      drawerOpen: false,
    };
  }

  const initial: ChatSelectState = {
    activeConversationId: 'conv-active-1',
    draft: 'Bản nháp đang soạn rất quan trọng',
    cancelSignal: 0,
    drawerOpen: true,
  };

  // Case 1: Tapping the currently active conversation -> keeps draft and cancelSignal
  const resultSame = onSelectConversation(initial, 'conv-active-1');
  assert.equal(resultSame.drawerOpen, false);
  assert.equal(resultSame.draft, 'Bản nháp đang soạn rất quan trọng');
  assert.equal(resultSame.cancelSignal, 0);

  // Case 2: Tapping a different conversation -> wipes draft and increments cancelSignal
  const resultDifferent = onSelectConversation(initial, 'conv-other-2');
  assert.equal(resultDifferent.drawerOpen, false);
  assert.equal(resultDifferent.activeConversationId, 'conv-other-2');
  assert.equal(resultDifferent.draft, '');
  assert.equal(resultDifferent.cancelSignal, 1);
});

test('handleNewConversation: cancels capture when recording is active even if screen is otherwise empty', () => {
  interface NewChatState {
    conversationId: string | null;
    messageCount: number;
    draft: string;
    cancelSignal: number;
    drawerOpen: boolean;
    recordingStatus: 'idle' | 'recording' | 'transcribing';
  }

  function handleNew(state: NewChatState): NewChatState {
    if (
      !state.conversationId &&
      state.messageCount === 0 &&
      state.draft === '' &&
      state.recordingStatus === 'idle'
    ) {
      return { ...state, drawerOpen: false };
    }
    return {
      conversationId: null,
      messageCount: 0,
      draft: '',
      cancelSignal: state.cancelSignal + 1,
      drawerOpen: false,
      recordingStatus: 'idle',
    };
  }

  // Blank screen and idle -> just closes drawer
  const idleBlank: NewChatState = {
    conversationId: null,
    messageCount: 0,
    draft: '',
    cancelSignal: 0,
    drawerOpen: true,
    recordingStatus: 'idle',
  };
  const idleResult = handleNew(idleBlank);
  assert.equal(idleResult.drawerOpen, false);
  assert.equal(idleResult.cancelSignal, 0);

  // Blank screen but recording is IN-FLIGHT -> must cancel recording!
  const recordingBlank: NewChatState = {
    conversationId: null,
    messageCount: 0,
    draft: '',
    cancelSignal: 0,
    drawerOpen: true,
    recordingStatus: 'recording',
  };
  const recResult = handleNew(recordingBlank);
  assert.equal(recResult.drawerOpen, false);
  assert.equal(recResult.cancelSignal, 1);
  assert.equal(recResult.recordingStatus, 'idle');
});

test('Saved disconnected microphone: preserves user choice when device is unplugged and never flags default as disconnected', () => {
  interface DeviceOption {
    id: string;
    label: string;
  }

  function buildMicOptions(connectedDevices: { id: string; name: string }[], savedMicId: string): DeviceOption[] {
    const normSaved = savedMicId === 'default' ? '' : savedMicId;
    const options: DeviceOption[] = [{ id: '', label: '(Mặc định hệ điều hành)' }];
    if (normSaved && !connectedDevices.some((d) => d.id === normSaved)) {
      options.push({ id: normSaved, label: `${normSaved} (Đã ngắt kết nối)` });
    }
    for (const d of connectedDevices.filter((d) => d.id && d.id !== 'default')) {
      options.push({ id: d.id, label: d.name });
    }
    return options;
  }

  const connected = [
    { id: 'usb-mic-1', name: 'USB Headset Microphone' },
  ];

  // Case 1: User has saved USB mic that is currently disconnected
  const options = buildMicOptions(connected, 'usb-mic-plugged-out');
  assert.equal(options.length, 3);
  assert.equal(options[1].id, 'usb-mic-plugged-out');
  assert.equal(options[1].label, 'usb-mic-plugged-out (Đã ngắt kết nối)');

  // Selected value matches an option in dropdown so browser does not reset it
  const hasMatchingOption = options.some((opt) => opt.id === 'usb-mic-plugged-out');
  assert.equal(hasMatchingOption, true);

  // Case 2: User has 'default' or '' saved -> MUST NOT be marked disconnected!
  const optionsDefault = buildMicOptions(connected, 'default');
  assert.equal(optionsDefault.length, 2);
  assert.equal(optionsDefault.some((o) => o.label.includes('Đã ngắt kết nối')), false);

  // Case 3: Empty ID devices from unpermissioned enumerations MUST NOT collide or create duplicate value=""
  const unpermissioned = [{ id: '', name: 'Microphone 1' }];
  const optionsUnperm = buildMicOptions(unpermissioned, '');
  assert.equal(optionsUnperm.length, 1);
  assert.equal(optionsUnperm[0].id, '');
  // Guarantee all option IDs in dropdown are strictly unique
  const ids = optionsUnperm.map((o) => o.id);
  assert.equal(new Set(ids).size, ids.length);
});

test('Stale query sequence rejection: out-of-order search responses are discarded', () => {
  let latestSeq = 0;
  let displayedConversations: string[] = [];

  function simulateResponse(seq: number, results: string[]) {
    if (seq !== latestSeq) {
      // Stale out-of-order response dropped!
      return;
    }
    displayedConversations = results;
  }

  // Request 1 issued (seq = 1)
  const req1Seq = ++latestSeq;
  // Request 2 issued (seq = 2)
  const req2Seq = ++latestSeq;

  // Request 2 resolves first
  simulateResponse(req2Seq, ['Kết quả mới của req 2']);
  assert.deepEqual(displayedConversations, ['Kết quả mới của req 2']);

  // Request 1 resolves late
  simulateResponse(req1Seq, ['Kết quả cũ của req 1']);
  // Must NOT overwrite req 2's results
  assert.deepEqual(displayedConversations, ['Kết quả mới của req 2']);
});

test('Permissions-Policy configuration allows self microphone access', async () => {
  const nextConfigModule = await import('../next.config');
  const config = nextConfigModule.default || nextConfigModule;
  assert.ok(typeof config.headers === 'function');
  const headersList = await config.headers();
  assert.ok(Array.isArray(headersList));
  const rootHeaderEntry = headersList.find((h: any) => h.source === '/(.*)');
  assert.ok(rootHeaderEntry);
  const permHeader = rootHeaderEntry.headers.find((hdr: any) => hdr.key === 'Permissions-Policy');
  assert.ok(permHeader);
  assert.ok(
    permHeader.value.includes('microphone=(self)') || permHeader.value.includes('microphone=*'),
    `Permissions-Policy MUST allow microphone on self, got: ${permHeader.value}`
  );
  assert.ok(!permHeader.value.includes('microphone=()'), 'microphone=() disallows mic access and must not be used');
});

test('SettingsView microphone resolution maps server GUID to matching WebAudio device', () => {
  const serverMics = [
    {
      id: '{821a377a-8f39-4d65-9b85-ac6bc53096f5}',
      name: 'Internal Microphone (Conexant SmartAudio HD)',
      isDefault: true,
    },
  ];
  const webMics = [
    {
      id: '7f38d0f9e3ea57f7e682847a34ed5a7047a3ca45d29b23c3299f2ab6de67f199',
      name: 'Internal Microphone (Conexant SmartAudio HD)',
      isDefault: true,
    },
    {
      id: 'communications',
      name: 'Communications - Internal Microphone (Conexant SmartAudio HD)',
      isDefault: false,
    },
  ];

  // Logic from SettingsView: resolve loaded server GUID against detected webMics
  function resolveMicrophoneId(savedMicId: string, availableWebMics: typeof webMics, availableServerMics: typeof serverMics) {
    if (!savedMicId || savedMicId === 'default') return '';
    const direct = availableWebMics.find((m) => m.id === savedMicId);
    if (direct) return direct.id;

    const serverMatch = availableServerMics.find((s) => s.id === savedMicId);
    if (serverMatch) {
      const webMatch = availableWebMics.find(
        (w) =>
          w.name === serverMatch.name ||
          w.name.includes(serverMatch.name) ||
          serverMatch.name.includes(w.name)
      );
      if (webMatch) return webMatch.id;
    }
    return savedMicId;
  }

  const resolved = resolveMicrophoneId('{821a377a-8f39-4d65-9b85-ac6bc53096f5}', webMics, serverMics);
  assert.equal(resolved, '7f38d0f9e3ea57f7e682847a34ed5a7047a3ca45d29b23c3299f2ab6de67f199');
});

test('Settings refresh parses maxRecordSeconds and selectedMicrophoneId', () => {
  const settingsPayload = {
    provider: 'deepgram',
    language: 'vi',
    model: 'nova-3',
    timeoutSeconds: 60,
    hasApiKey: true,
    selectedMicrophoneId: 'web-mic-123',
    maxRecordSeconds: 5,
  };

  let maxRecord = 120;
  let micId: string | undefined = undefined;

  if (typeof settingsPayload.selectedMicrophoneId === 'string') {
    micId = settingsPayload.selectedMicrophoneId;
  }
  if (typeof settingsPayload.maxRecordSeconds === 'number') {
    maxRecord = settingsPayload.maxRecordSeconds;
  }

  assert.equal(maxRecord, 5);
  assert.equal(micId, 'web-mic-123');
});

test('Settings refresh resets selectedMicrophoneId to undefined when cleared to OS default', () => {
  let micId: string | undefined = 'old-device-guid-123';

  function applyRefresh(data: { selectedMicrophoneId?: string | null }) {
    if (typeof data?.selectedMicrophoneId === 'string') {
      micId = data.selectedMicrophoneId;
    } else {
      micId = undefined;
    }
  }

  // User resets microphone to OS default in Settings
  applyRefresh({ selectedMicrophoneId: undefined });
  assert.equal(micId, undefined);

  // User selects another mic
  applyRefresh({ selectedMicrophoneId: 'new-usb-mic' });
  assert.equal(micId, 'new-usb-mic');
});
