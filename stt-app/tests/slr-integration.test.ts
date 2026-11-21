import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_SLR_SETTINGS,
  loadSlrSettings,
  resolveSlrBaseUrl,
  saveSlrSettings,
  toWsUrl,
} from '../src/lib/slrSettings';
import {
  formatUserFacingState,
  getStateBorderColor,
} from '../src/lib/slrClient';

test('DEFAULT_SLR_SETTINGS keeps end-user defaults and hides dev diagnostics', () => {
  assert.equal(DEFAULT_SLR_SETTINGS.autoSpeak, true);
  assert.equal(DEFAULT_SLR_SETTINGS.autoSaveOnRest, true);
  assert.equal(DEFAULT_SLR_SETTINGS.showDiagnostics, false);
  assert.equal(DEFAULT_SLR_SETTINGS.cameraIndex, 0);
  assert.equal(DEFAULT_SLR_SETTINGS.slrBaseUrl, '');
});

test('resolveSlrBaseUrl resolves default host:8765 and strips trailing slashes', () => {
  assert.equal(resolveSlrBaseUrl('', '192.168.1.42'), 'http://192.168.1.42:8765');
  assert.equal(
    resolveSlrBaseUrl('http://10.0.0.5:8765///', '192.168.1.42'),
    'http://10.0.0.5:8765'
  );
});

test('toWsUrl converts http/https cleanly to ws/wss', () => {
  assert.equal(toWsUrl('http://192.168.1.15:8765/'), 'ws://192.168.1.15:8765');
  assert.equal(toWsUrl('https://slr.example.com'), 'wss://slr.example.com');
  assert.equal(toWsUrl('ws://127.0.0.1:8765'), 'ws://127.0.0.1:8765');
});

test('loadSlrSettings and saveSlrSettings degrade safely during SSR without window', () => {
  const loaded = loadSlrSettings();
  assert.deepEqual(loaded, DEFAULT_SLR_SETTINGS);

  const sanitized = saveSlrSettings({
    slrBaseUrl: '  http://192.168.1.10:8765/  ',
    cameraIndex: 99,
    autoSpeak: false,
    autoSaveOnRest: true,
    showDiagnostics: true,
  });
  assert.equal(sanitized.slrBaseUrl, 'http://192.168.1.10:8765');
  assert.equal(sanitized.cameraIndex, 0);
  assert.equal(sanitized.autoSpeak, false);
  assert.equal(sanitized.showDiagnostics, true);
});

test('formatUserFacingState and getStateBorderColor map M1 states cleanly', () => {
  assert.equal(formatUserFacingState(false, false, 'UNKNOWN'), 'Chưa bắt đầu');
  assert.equal(formatUserFacingState(true, true, 'READY'), 'Đang hoàn tất...');
  assert.equal(formatUserFacingState(true, false, 'UNKNOWN'), 'Đưa vai & 2 tay vào khung');
  assert.equal(formatUserFacingState(true, false, 'READY'), 'Sẵn sàng ký');
  assert.equal(formatUserFacingState(true, false, 'CAPTURING'), 'Đang nhận ký hiệu...');
  assert.equal(formatUserFacingState(true, false, 'END_PENDING'), 'Đang xác nhận...');

  assert.equal(getStateBorderColor(false, 'READY'), '#BAC5D0');
  assert.equal(getStateBorderColor(true, 'READY'), '#087A47');
  assert.equal(getStateBorderColor(true, 'CAPTURING'), '#DC2626');
  assert.equal(getStateBorderColor(true, 'END_PENDING'), '#D97706');
});
