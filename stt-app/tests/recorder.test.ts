import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { EventEmitter } from 'node:events';
import {
  HardwareRecorder,
  cleanupOrphanRecordings,
  createMockWavBuffer,
  createWavHeader,
} from '../src/server/recorder';
import { AppError } from '../src/server/errors';
import type { Settings } from '../src/server/settings';

const fakeSettings: Settings = {
  schemaVersion: 1,
  apiKey: 'FAKE_DEEPGRAM_KEY_1234567890',
  model: 'nova-3',
  timeoutSeconds: 30,
  maxRecordSeconds: 60,
};

function fakeTranscribe(audio: any) {
  return Promise.resolve({
    sessionId: 'test-session',
    fileName: audio.name,
    text: 'Văn bản nhận dạng từ bản ghi thử nghiệm.',
    status: 'completed' as const,
    provider: 'deepgram' as const,
    language: 'vi' as const,
    model: 'nova-3' as const,
    requestId: 'req-123',
    audioSeconds: 1.0,
    requestMs: 150,
  });
}

test('createWavHeader produces valid 44-byte RIFF header', () => {
  const header = createWavHeader(32000, 16000, 1, 16);
  assert.equal(header.length, 44);
  const view = new DataView(header.buffer);
  const tag = new TextDecoder().decode(header.slice(0, 4));
  assert.equal(tag, 'RIFF');
  const waveTag = new TextDecoder().decode(header.slice(8, 12));
  assert.equal(waveTag, 'WAVE');
  const fmtTag = new TextDecoder().decode(header.slice(12, 16));
  assert.equal(fmtTag, 'fmt ');
  const dataTag = new TextDecoder().decode(header.slice(36, 40));
  assert.equal(dataTag, 'data');
  assert.equal(view.getUint32(40, true), 32000);
});

test('createMockWavBuffer produces valid audio data with header', () => {
  const buffer = createMockWavBuffer(0.5, 16000);
  assert.ok(buffer.length > 44);
  assert.equal(new TextDecoder().decode(buffer.slice(0, 4)), 'RIFF');
});

test('cleanupOrphanRecordings removes lingering pbl6_rec_*.wav files', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'pbl6-orphan-test-'));
  try {
    await writeFile(join(dir, 'pbl6_rec_orphan1.wav'), 'dummy-wav-data');
    await writeFile(join(dir, 'pbl6_rec_orphan2.wav'), 'dummy-wav-data');
    await writeFile(join(dir, 'other_file.txt'), 'keep-me');

    const count = await cleanupOrphanRecordings(dir);
    assert.equal(count, 2);

    const remaining = await readdir(dir);
    assert.deepEqual(remaining, ['other_file.txt']);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

test('HardwareRecorder lifecycle: idle -> start -> stop -> idle', async () => {
  const recorder = new HardwareRecorder({
    readSettings: async () => fakeSettings,
    transcribe: fakeTranscribe,
  });

  // Initial state
  const initial = recorder.getState();
  assert.equal(initial.status, 'idle');
  assert.equal(initial.durationMs, 0);

  // Start recording
  const started = await recorder.start({ deviceId: 'test-mic' });
  assert.equal(started.status, 'recording');
  assert.equal(started.selectedDeviceId, 'test-mic');

  // Query state while recording
  const recordingState = recorder.getState();
  assert.equal(recordingState.status, 'recording');

  // Attempt to start again while busy
  await assert.rejects(recorder.start(), { code: 'recorder_busy' });

  // Wait a small duration
  await new Promise(r => setTimeout(r, 50));

  // Stop recording
  const result = await recorder.stop();
  assert.equal(result.text, 'Văn bản nhận dạng từ bản ghi thử nghiệm.');
  assert.equal(result.status, 'completed');

  // Final state
  const finalState = recorder.getState();
  assert.equal(finalState.status, 'idle');
});

test('HardwareRecorder cancel cleans up without transcribing', async () => {
  let transcribed = false;
  const recorder = new HardwareRecorder({
    readSettings: async () => fakeSettings,
    transcribe: async (audio) => {
      transcribed = true;
      return fakeTranscribe(audio);
    },
  });

  await recorder.start();
  assert.equal(recorder.getState().status, 'recording');

  const cancelResult = await recorder.cancel();
  assert.deepEqual(cancelResult, { cancelled: true });
  assert.equal(recorder.getState().status, 'idle');
  assert.equal(transcribed, false);
});

test('HardwareRecorder stop when not recording throws recorder_not_recording', async () => {
  const recorder = new HardwareRecorder({
    readSettings: async () => fakeSettings,
    transcribe: fakeTranscribe,
  });

  await assert.rejects(recorder.stop(), { code: 'recorder_not_recording' });
});

test('HardwareRecorder stops with error if API key is missing', async () => {
  const recorder = new HardwareRecorder({
    readSettings: async () => ({ ...fakeSettings, apiKey: '' }),
    transcribe: fakeTranscribe,
  });

  await recorder.start();
  await assert.rejects(recorder.stop(), { code: 'key_missing' });
  assert.equal(recorder.getState().status, 'idle');
});

test('HardwareRecorder auto-stops when maxDurationSeconds expires', async () => {
  let transcribed = false;
  const recorder = new HardwareRecorder({
    readSettings: async () => fakeSettings,
    transcribe: async (audio) => {
      transcribed = true;
      return fakeTranscribe(audio);
    },
  });

  // Start with 0.1s max duration
  await recorder.start({ maxDurationSeconds: 0.1 });
  assert.equal(recorder.getState().status, 'recording');

  // Wait for timeout to trigger auto-stop and transcribe
  for (let i = 0; i < 20; i++) {
    if (recorder.getState().status === 'idle') break;
    await new Promise(r => setTimeout(r, 50));
  }

  assert.equal(transcribed, true);
  assert.equal(recorder.getState().status, 'idle');
});

test('listMicrophones returns available devices with default', async () => {
  const recorder = new HardwareRecorder({
    readSettings: async () => fakeSettings,
    transcribe: fakeTranscribe,
  });

  const devices = await recorder.listMicrophones();
  assert.ok(Array.isArray(devices));
  assert.ok(devices.length >= 1);
  assert.ok(devices.some(d => d.isDefault));
});

test('HardwareRecorder stop after auto-stop timeout retrieves cached transcript', async () => {
  const recorder = new HardwareRecorder({
    readSettings: async () => fakeSettings,
    transcribe: fakeTranscribe,
  });

  await recorder.start({ maxDurationSeconds: 0.1 });
  assert.equal(recorder.getState().status, 'recording');

  // Wait for auto-stop timeout to finish
  for (let i = 0; i < 20; i++) {
    if (recorder.getState().status === 'idle') break;
    await new Promise(r => setTimeout(r, 50));
  }

  // Client calls stop right after timeout: should return cached transcript without error
  const transcript = await recorder.stop();
  assert.equal(transcript.text, 'Văn bản nhận dạng từ bản ghi thử nghiệm.');

  // Subsequent stop call should throw recorder_not_recording
  await assert.rejects(recorder.stop(), { code: 'recorder_not_recording' });
});

test('HardwareRecorder start throws no_microphone when no devices exist', async () => {
  const recorder = new HardwareRecorder({
    readSettings: async () => fakeSettings,
    transcribe: fakeTranscribe,
    execCommand: (async () => ({ stdout: JSON.stringify([]) })) as any,
  });

  await assert.rejects(recorder.start(), {
    code: 'no_microphone',
    message: 'Không tìm thấy mic. Hãy kết nối mic rồi thử lại.',
  });
});

test('HardwareRecorder start falls back to OS default when saved mic is unplugged', async () => {
  const mockNodes = [
    {
      id: 42,
      info: {
        props: {
          'media.class': 'Audio/Source',
          'node.name': 'alsa_input.usb-mic',
          'node.description': 'USB Microphone',
          'priority.session': 1000,
        },
      },
    },
  ];

  const recorder = new HardwareRecorder({
    readSettings: async () => ({ ...fakeSettings, selectedMicrophoneId: 'missing-mic-99' }),
    transcribe: fakeTranscribe,
    execCommand: (async () => ({ stdout: JSON.stringify(mockNodes) })) as any,
  });

  const state = await recorder.start();
  assert.equal(state.status, 'recording');
  assert.equal(state.selectedDeviceId, '42'); // Fell back to available device 42
  await recorder.cancel();
});

test('listMicrophones selects single highest priority device as default and handles 0 sources', async () => {
  const mockNodes = [
    {
      id: 10,
      info: {
        props: {
          'media.class': 'Audio/Source',
          'node.name': 'mic1',
          'priority.session': 500,
        },
      },
    },
    {
      id: 20,
      info: {
        props: {
          'media.class': 'Audio/Source',
          'node.name': 'mic2',
          'priority.session': 1500,
        },
      },
    },
  ];

  const recorder = new HardwareRecorder({
    readSettings: async () => fakeSettings,
    transcribe: fakeTranscribe,
    execCommand: (async () => ({ stdout: JSON.stringify(mockNodes) })) as any,
  });

  const devices = await recorder.listMicrophones();
  assert.equal(devices.length, 2);
  const defaults = devices.filter(d => d.isDefault);
  assert.equal(defaults.length, 1);
  assert.equal(defaults[0].id, '20'); // id 20 had highest priority 1500

  // Test 0 sources
  const recorderEmpty = new HardwareRecorder({
    readSettings: async () => fakeSettings,
    transcribe: fakeTranscribe,
    execCommand: (async () => ({ stdout: JSON.stringify([]) })) as any,
  });
  const emptyDevices = await recorderEmpty.listMicrophones();
  assert.deepEqual(emptyDevices, []);
});

test('mid-recording disconnect with audio > 44 bytes auto-transcribes with partial flag', async () => {
  let childEmitter: any;
  const mockSpawn = () => {
    childEmitter = new EventEmitter() as any;
    childEmitter.kill = () => true;
    return childEmitter;
  };

  const recorder = new HardwareRecorder({
    readSettings: async () => fakeSettings,
    transcribe: fakeTranscribe,
    spawnProcess: mockSpawn as any,
  });

  await recorder.start();
  assert.equal(recorder.getState().status, 'recording');

  // Simulate process writing partial audio file > 44 bytes
  const dir = tmpdir();
  const state = recorder.getState();
  // Find current file path from internal state
  const currentFilePath = (recorder as any).currentFilePath;
  await writeFile(currentFilePath, Buffer.from(createMockWavBuffer(0.5)));

  // Simulate unexpected disconnect / process exit
  childEmitter.emit('exit', 1, null);

  // Allow async stat and transcription promise to resolve
  for (let i = 0; i < 20; i++) {
    if (recorder.getState().status === 'idle') break;
    await new Promise(r => setTimeout(r, 50));
  }

  // Retrieve transcript
  const result = await recorder.stop();
  assert.equal(result.partial, true);
  assert.equal(result.text, 'Văn bản nhận dạng từ bản ghi thử nghiệm.');
});

test('mid-recording disconnect without audio <= 44 bytes sets error and cleans up', async () => {
  let childEmitter: any;
  const mockSpawn = () => {
    childEmitter = new EventEmitter() as any;
    childEmitter.kill = () => true;
    return childEmitter;
  };

  const recorder = new HardwareRecorder({
    readSettings: async () => fakeSettings,
    transcribe: fakeTranscribe,
    spawnProcess: mockSpawn as any,
  });

  await recorder.start();
  assert.equal(recorder.getState().status, 'recording');

  // Current file exists with only a tiny dummy header <= 44 bytes
  const currentFilePath = (recorder as any).currentFilePath;
  await writeFile(currentFilePath, Buffer.from('RIFF1234'));

  // Unexpected exit
  childEmitter.emit('exit', 1, null);

  for (let i = 0; i < 20; i++) {
    if (recorder.getState().status === 'error') break;
    await new Promise(r => setTimeout(r, 50));
  }

  const errorState = recorder.getState();
  assert.equal(errorState.status, 'error');
  assert.equal(errorState.error, 'Mic bị ngắt kết nối và không thu được âm thanh.');
});
