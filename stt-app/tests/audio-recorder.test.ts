import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createWavHeader,
  resampleAudio,
  floatTo16BitPCM,
  encodeWavBlob,
  WebAudioRecorder,
} from '../src/utils/audioRecorder';

test('createWavHeader: generates valid 44-byte RIFF header for 16kHz Mono 16-bit PCM', () => {
  const dataLength = 32000; // 1 second of audio
  const header = createWavHeader(dataLength, 16000, 1, 16);
  assert.equal(header.length, 44);

  const view = new DataView(header.buffer);
  const textDecoder = new TextDecoder();

  // RIFF Chunk
  assert.equal(textDecoder.decode(header.slice(0, 4)), 'RIFF');
  assert.equal(view.getUint32(4, true), 36 + dataLength);
  assert.equal(textDecoder.decode(header.slice(8, 12)), 'WAVE');

  // fmt Subchunk
  assert.equal(textDecoder.decode(header.slice(12, 16)), 'fmt ');
  assert.equal(view.getUint32(16, true), 16); // Subchunk1Size
  assert.equal(view.getUint16(20, true), 1); // AudioFormat (PCM)
  assert.equal(view.getUint16(22, true), 1); // NumChannels (Mono)
  assert.equal(view.getUint32(24, true), 16000); // SampleRate
  assert.equal(view.getUint32(28, true), 32000); // ByteRate = 16000 * 1 * 16 / 8
  assert.equal(view.getUint16(32, true), 2); // BlockAlign = 1 * 16 / 8
  assert.equal(view.getUint16(34, true), 16); // BitsPerSample

  // data Subchunk
  assert.equal(textDecoder.decode(header.slice(36, 40)), 'data');
  assert.equal(view.getUint32(40, true), dataLength);
});

test('resampleAudio: returns original buffer when inputRate equals targetRate', () => {
  const input = new Float32Array([0.1, 0.5, -0.3, 0.8]);
  const resampled = resampleAudio(input, 16000, 16000);
  assert.equal(resampled, input);
});

test('resampleAudio: downsamples from 48000 Hz to 16000 Hz (3:1 ratio)', () => {
  // 48000 Hz: 300 samples -> 16000 Hz: 100 samples
  const input = new Float32Array(300);
  for (let i = 0; i < input.length; i++) {
    input[i] = Math.sin((2 * Math.PI * 440 * i) / 48000);
  }

  const resampled = resampleAudio(input, 48000, 16000);
  assert.equal(resampled.length, 100);

  // Peak amplitude should be close to 1
  let maxVal = 0;
  for (let i = 0; i < resampled.length; i++) {
    if (Math.abs(resampled[i]) > maxVal) maxVal = Math.abs(resampled[i]);
  }
  assert.ok(maxVal > 0.85, `Expected max peak > 0.85, got ${maxVal}`);
});

test('resampleAudio: downsamples from 44100 Hz to 16000 Hz', () => {
  // 44100 Hz: 441 samples -> ~160 samples
  const input = new Float32Array(441);
  for (let i = 0; i < input.length; i++) {
    input[i] = Math.cos((2 * Math.PI * 440 * i) / 44100);
  }

  const resampled = resampleAudio(input, 44100, 16000);
  assert.equal(resampled.length, 160);
});

test('floatTo16BitPCM: converts and clamps Float32 to Int16 correctly', () => {
  const input = new Float32Array([0.0, 1.0, -1.0, 0.5, -0.5, 1.5, -2.0]);
  const pcm = floatTo16BitPCM(input);

  assert.equal(pcm.length, input.length);
  assert.equal(pcm[0], 0);
  assert.equal(pcm[1], 32767);
  assert.equal(pcm[2], -32768);
  assert.equal(pcm[3], Math.floor(0.5 * 32767));
  assert.equal(pcm[4], Math.floor(-0.5 * 32768));
  // Clamped values
  assert.equal(pcm[5], 32767);
  assert.equal(pcm[6], -32768);
});

test('encodeWavBlob: produces a Blob with correct size and type', () => {
  const pcm = new Int16Array([100, 200, -300, 400]);
  const blob = encodeWavBlob(pcm, 16000);

  assert.equal(blob.type, 'audio/wav');
  assert.equal(blob.size, 44 + pcm.byteLength);
});

test('WebAudioRecorder: safe fallback in non-browser environment', async () => {
  const mics = await WebAudioRecorder.enumerateMicrophones();
  assert.deepEqual(mics, []);

  const unbind = WebAudioRecorder.onDeviceChange(() => {});
  assert.equal(typeof unbind, 'function');
  unbind();
});

test('WebAudioRecorder: enumerateMicrophones filters unpermissioned empty IDs and maps real physical devices', async () => {
  const originalMediaDevices = Object.getOwnPropertyDescriptor(globalThis.navigator, 'mediaDevices');
  try {
    const mockDevices = [
      { kind: 'audioinput', deviceId: 'default', label: 'Default - Realtek Audio' },
      { kind: 'audioinput', deviceId: 'real-mic-id-123', label: 'Realtek High Definition Audio' },
      { kind: 'videoinput', deviceId: 'camera-1', label: 'Webcam' },
    ];

    Object.defineProperty(globalThis.navigator, 'mediaDevices', {
      value: {
        enumerateDevices: async () => mockDevices,
      },
      configurable: true,
      writable: true,
    });

    const result = await WebAudioRecorder.enumerateMicrophones();
    // Must filter out videoinput and virtual 'default' when physical device exists
    assert.equal(result.length, 1);
    assert.equal(result[0].id, 'real-mic-id-123');
    assert.equal(result[0].name, 'Realtek High Definition Audio');
  } finally {
    if (originalMediaDevices) {
      Object.defineProperty(globalThis.navigator, 'mediaDevices', originalMediaDevices);
    } else {
      delete (globalThis.navigator as unknown as { mediaDevices?: unknown }).mediaDevices;
    }
  }
});
